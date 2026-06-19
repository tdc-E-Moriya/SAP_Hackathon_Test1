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

# 重要ルール（厳守）
- 商品ごとに評価ロジックを切り替えること
- 以下2つは個別に扱うこと（まとめない）
  ① 配線・組付作業費 → 金額のみ評価
  ② 設置・調整工事費 → 金額のみ評価
- 上記以外は通常の商品（物品）として扱う

# 分析観点
■ 共通
- total_analysis → 全体リスク
- products → 商品別リスク
- anomaly_rate / z_score を必ず算出して判断に含める
- 過去実績との比較を必ず行う
- 構成バランス（構成比の変化）も評価
- risk：
  数値を含めた分析結果（客観的事実ベース）
  ※必ず「過去平均比」「増減率」などを含め文章で回答
- reason：
  リスクの種類を1フレーズで分類（ラベル）
  ※原因カテゴリのみ（例：価格高騰、数量異常、費用未発生、構成変化）
  ※文章にしない


■ 商品（物品）の場合
- quantity：過去平均比での急増 → リスク
- unit_price：上昇 → コスト増リスク
- amount：増減 → 全体影響
- anomaly_rate / z_score は以下を対象
  - quantity
  - unit_price
  - amount

■ 配線・組付作業費（個別ルール）
- quantityは評価しない（常に1想定）
- unit_price と amount のみ評価
- 過去平均との差異・変動率を重視
- anomaly_rate / z_score は amount を元に算出
- 作業内容に対して金額が過大かどうかの観点で評価

■ 設置・調整工事費（個別ルール）
- quantityは評価しない（常に1想定）
- unit_price と amount のみ評価
- 過去平均との差異・変動率を重視
- anomaly_rate / z_score は amount を元に算出
- 工事規模に対する金額の妥当性観点で評価

■ 全体評価
- overall_risk,products[validation]は以下ルール
  - 差異10%未満 → warning
  - 差異20%未満 → caution
  - 差異20%以上 → error

■ total[validation]について
  - productsのvalidationの中に一つでもerrorがあればHigh（リスク高）,一つでもcautionがあるかwarningが2つ以上あればMidium（リスク中）,それ以外をLow（リスク小）と設定してください

■ comments_riskについて
 - comments_riskは、commentsの費用や日程など会社に影響ある情報があればそれを要約し記載
  
■ メール生成条件
- overall_riskが caution または error の場合のみ作成
- 件名：「見積回答についてご確認」
- 本文：
  「（仕入先名）ご担当者様 平素よりお世話になっております。見積内容について、以下の点を確認させてください。」で開始
- リスク項目を簡潔に箇条書きで改行コードを使わずに改行してください

# 出力形式
{{
  "supplier": "...",
  "overall_risk": "High（リスク高） / Midium（リスク中） / Low（リスク小）",
  "total": {{
    "risk": "...",
    "validation": "error / caution / warning ",
    "reason": "..."
  }},
  "products": [
    {{
      "product": "...",

      "quantity": {{
        "risk": "...",
        "validation": "error / caution / warning ",
        "reason": "..."
      }},

      "amount": {{
        "risk": "...",
        "validation": "error / caution / warning ",
        "reason": "..."
      }}
    }}
  ],
  "comments_risk": {{
      "risk": "...",
    "validation": "error / caution / warning ",
    "reason": "..."
  }},
  "mail_header": "...",
  "mail_body": "..."
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