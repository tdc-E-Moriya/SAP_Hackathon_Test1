import fitz  # PyMuPDF
import os
import json
import re

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("LLM_API_KEY"))

# ------------------------------
# ① PDF → テキスト抽出（OCRなし）
# ------------------------------
def extract_text(pdf_path):
    # print("▶ PyMuPDF テキスト抽出中...")

    doc = fitz.open(pdf_path)

    text = ""

    for i, page in enumerate(doc):
        page_text = page.get_text()

        # print(f"▶ ページ {i+1}: {len(page_text)}文字")

        text += page_text + "\n"

    return text


# ------------------------------
# ② JSONパース
# ------------------------------
def safe_json_parse(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            return json.loads(match.group())
        raise


# ------------------------------
# ③ LLM処理
# ------------------------------
def extract_structured_data(text):
    prompt = f"""
以下の日本語の見積書テキストから情報を抽出し、指定のJSON形式で出力してください。

【出力形式】
{{
  "supplier": string,
  "currency": "JPY",
  "estimates": [
    {{
      "estimate_id": string,
      "date": "YYYY-MM-DD",
      "products": [
        {{
          "product_name": string,
          "quantity": number,
          "unit_price": number,
          "amount": number
        }}
      ],
      "total_amount": number
    }}
  ]
}}

【抽出ルール】
- 仕入先：会社名（株式会社など含める）
- 見積番号 → estimate_id
- 見積日 → date（YYYY-MM-DD形式）
- 金額は数値型（カンマ・円を除去）
- 数量・単価・金額は明細行から抽出
- 「式」は quantity=1 とする
- 小計・合計・税は除外
- 明細ごとに1レコード
- 日本語はそのまま使用
- JSONのみ出力

【補足】
- 単価 → unit_price
- 金額 → amount
- 数量 → quantity
- 品目 → product_name

【テキスト】
{text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "帳票解析AI"},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return safe_json_parse(response.choices[0].message.content)


# ------------------------------
# ④ メイン処理
# ------------------------------
def pdf_to_json(pdf_path):
    # print(f"▶ 処理開始: {pdf_path}")

    text = extract_text(pdf_path)

    # print("▶ 抽出テキスト（先頭500文字）:")
    # print(text[:500])

    result = extract_structured_data(text)

    return result


# ------------------------------
# ⑤ 実行
# ------------------------------
if __name__ == "__main__":
    pdf_path = "sample.pdf"

    result = pdf_to_json(pdf_path)

    # print("\n▶ JSON結果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))