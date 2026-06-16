import json
import statistics
from collections import defaultdict
from groq import Groq
from dotenv import load_dotenv
import os


# =========================
# 共通関数
# =========================
def normalize_product_name(name):
    return name.split("（")[0]

# =========================
# 設定
# =========================
THRESHOLD = 0.2

file_2025 = "pastdata.json"
file_2026 = "currentdata.json"

# =========================
# データ読み込み
# =========================
def load_past(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)["data"]

def load_current(file):
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["supplier"], data["estimates"][0]

past_data_all = load_past(file_2025)
current_supplier, current_data = load_current(file_2026)

# =========================
# サプライヤー抽出
# =========================
def extract_supplier(data, supplier_name):
    for s in data:
        if s["supplier"] == supplier_name:
            return s["estimates"]
    return []

data_2025 = extract_supplier(past_data_all, current_supplier)

# =========================
# 商品別グループ（内訳も保持）
# =========================
product_groups = defaultdict(lambda: {
    "total": [],
    "product": [],
    "installation": [],
    "commissioning": []
})

for item in data_2025:
    for p in item["products"]:
        name = normalize_product_name(p["product_name"])

        product_groups[name]["total"].append(item["total_amount"])
        product_groups[name]["product"].append(p["product_cost"])
        product_groups[name]["installation"].append(p["installation_cost"])
        product_groups[name]["commissioning"].append(p["commissioning_cost"])

# =========================
# 現在データ
# =========================
p = current_data["products"][0]
current_product = normalize_product_name(p["product_name"])

current_values = {
    "total": current_data["total_amount"],
    "product": p["product_cost"],
    "installation": p["installation_cost"],
    "commissioning": p["commissioning_cost"]
}

# =========================
# 統計計算関数
# =========================
def calc_stats(values, current):
    avg = statistics.mean(values)
    median = statistics.median(values)
    std = statistics.stdev(values) if len(values) > 1 else 0

    diff = current - avg
    rate = diff / avg
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

# =========================
# 商品単位の統計処理
# =========================
if current_product in product_groups:

    stats = {}

    for key in ["total", "product", "installation", "commissioning"]:
        stats[key] = calc_stats(
            product_groups[current_product][key],
            current_values[key]
        )

    result = {
        "supplier": current_supplier,
        "product": current_product,
        "current_month": current_data["date"][:7],
        "analysis": stats
    }

else:
    result = {
        "supplier": current_supplier,
        "product": current_product,
        "message": "過去データに同じ商品が存在しません"
    }

# =========================
# 出力
# =========================
print(json.dumps(result, ensure_ascii=False, indent=2))

#with open("analysis_output.json", "w", encoding="utf-8") as f:
#    json.dump(result, f, ensure_ascii=False, indent=2)

# =========================
# LLM連携（リスク・妥当性評価）
# =========================
load_dotenv()
client = Groq(api_key=os.getenv("LLM_API_KEY"))

# プロンプト作成
prompt = f"""
あなたは製造業の見積分析の専門家です。

以下のJSONデータをもとに、
各項目（total / product / installation / commissioning）の
リスクと妥当性を分析してください。

# 入力データ
{json.dumps(result, ensure_ascii=False)}

# 分析ルール
- anomaly_rate, anomaly_zscore を必ず考慮
- rate（%）と z_score を元に判断
- 明らかに平均から乖離しているものは 高
- 軽微な差は 低
- 中間は 中
- 現在データで0がある場合は漏れで確認対象
- 回答の際はproductを製品、installationを設置費、commissioningを試運転費と呼称し、z_score、anomaly_zscoreやfalseは具体的な数値と日本語を使って要約して説明してください
- mail_bodyは、評価が高、中の場合、評価が上がった項目がなぜこのようになっているかを評価した数値は入れずに箇条書きで確認する文章を作成。
- 箇条書き以外はメールの分としての敬語を使用して下さい。
- 回答はJSONのみ「```」も排除で、以下の形式を厳守してください。
# 出力形式（JSON厳守）
{{
  "supplier": "...",
  "product": "...",
  "overall_risk": "High / Medium / Low",
  "details": [
    {{
      "category": "total",
      "risk": "High/Medium/Low",
      "reason": "...",
      "validation": "妥当 / 注意 / 要確認"
    }},
    {{
      "category": "product",
      "risk": "...",
      "reason": "...",
      "validation": "..."
    }},
    {{
      "category": "installation",
      "risk": "...",
      "reason": "...",
      "validation": "..."
    }},
    {{
      "category": "commissioning",
      "risk": "...",
      "reason": "...",
      "validation": "..."
    }}
  ],
  "summary": "全体の評価"
  "mail_body": "仕入先に確認すべきメールの文面"
}}
"""

# LLM実行
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "system", "content": "あなたはデータ分析とリスク評価の専門家です"},
        {"role": "user", "content": prompt}
    ],
    temperature=0.2
)

# 結果取得
llm_result = response.choices[0].message.content

print("\n=== LLM RESULT ===")
print(llm_result)
