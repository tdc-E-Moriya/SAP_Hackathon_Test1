import json
import statistics
from collections import defaultdict
from groq import Groq
from dotenv import load_dotenv
import os

def normalize_product_name(name):
    return name.split("（")[0]

THRESHOLD = 0.2

# =========================
# ✅ 過去データ読み込み（そのまま）
# =========================
def load_past(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)["data"]

def extract_supplier(data, supplier_name):
    for s in data:
        if s["supplier"] == supplier_name:
            return s["estimates"]
    return []

# =========================
# ✅ メイン関数化（ここが重要）
# =========================
def analyze_risk(current_json, past_file="data/pastdata.json"):

    current_supplier = current_json["supplier"]
    current_data = current_json["estimates"][0]

    past_data_all = load_past(past_file)
    past_data = extract_supplier(past_data_all, current_supplier)

    product_groups = defaultdict(lambda: {
        "amount": [],
        "unit_price": [],
        "quantity": []
    })

    for item in past_data:
        for p in item["products"]:
            name = normalize_product_name(p["product_name"])

            product_groups[name]["amount"].append(p["amount"])
            product_groups[name]["unit_price"].append(p["unit_price"])
            product_groups[name]["quantity"].append(p["quantity"])

    def calc_stats(values, current):
        avg = statistics.mean(values)
        median = statistics.median(values)
        std = statistics.stdev(values) if len(values) > 1 else 0

        diff = current - avg
        rate = diff / avg if avg != 0 else 0
        z = (current - avg) / std if std > 0 else 0

        return {
            "avg": int(avg),
            "median": int(median),
            "stddev": int(std),
            "diff": int(diff),
            "rate": round(rate * 100, 2),
            "z_score": round(z, 2),
            "anomaly_rate": abs(rate) >= THRESHOLD,
            "anomaly_zscore": abs(z) >= 2
        }

    # ----------------------
    # 商品分析
    # ----------------------
    analysis_result = []

    for p in current_data["products"]:
        name = normalize_product_name(p["product_name"])

        if name not in product_groups:
            continue

        stats = {}

        for key in ["amount", "unit_price", "quantity"]:
            stats[key] = calc_stats(
                product_groups[name][key],
                p[key]
            )

        analysis_result.append({
            "product": name,
            "analysis": stats
        })

    # ----------------------
    # トータル
    # ----------------------
    total_values = [item["total_amount"] for item in past_data]

    total_stats = calc_stats(
        total_values,
        current_data["total_amount"]
    )

    result = {
        "supplier": current_supplier,
        "current_month": current_data["date"][:7],
        "total_analysis": total_stats,
        "products": analysis_result
    }

    # ----------------------
    # LLM
    # ----------------------
    load_dotenv()
    client = Groq(api_key=os.getenv("LLM_API_KEY"))

    prompt = f"""
あなたは製造業の見積分析の専門家です。

以下のJSONデータをもとに、
全体および各商品ごとのリスクを分析してください。
回答はJSON型のみにし、```これもなしにしてください。
# 入力データ
{json.dumps(result, ensure_ascii=False)}

# 分析観点
- total_analysis → 全体リスク
- products → 商品別リスク
- anomaly_rate / z_score を必ず使う
- quantity急増はリスク
- unit_price上昇はコスト増
- 構成バランスの崩れも考慮
- reasonはリスクの根拠を文章で説明。例）金額が過去実績と比較して高額となっています。根拠の確認が必要です。
- mail_header / mail_bodyは全体リスクがHighかMediumの場合に、リスクで挙げられた部分を確認するメールを作成。文章は敬語でかつ簡潔に確認点は箇条書き（改行コードはなし）で説明。
- 件名は「見積回答についてご確認」、本文は「ご担当者様 平素よりお世話になっております。見積内容について、以下の点を確認させてください。」で始める。ご担当者様の前に仕入先名を入れてください。
- overall_riskは全体的な評価。過去との差異が5%未満であればsafety,10%未満であればwarning,20%未満であればcaution,20%以上でerrorとしてください。
# 出力形式
{{
  "supplier": "...",
  "overall_risk": "error / caution / warning / safety",
  "total": {{
    "risk": "...",
    "reason": "..."
  }},
  "products": [
    {{
      "product": "...",
      "risk": "error / caution / warning / safety",
      "reason": "..."
    }}
  ]
  "mail_header": "件名",
  "mail_body": "本文"
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "分析AI"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return {
        "stat_result": result,
        "llm_result": response.choices[0].message.content
    }