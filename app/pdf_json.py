import fitz  # PyMuPDF
import json
import re
import os

from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("LLM_API_KEY"))


# ------------------------------
# ✅ ① バイトデータ直接処理
# ------------------------------
def extract_text_from_bytes(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    text = ""

    for page in doc:
        text += page.get_text() + "\n"

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
以下の日本語の見積書テキストから情報を抽出し、JSON形式で出力してください。

【出力形式】
{{
  "supplier": string,
  "currency": "JPY",
  "estimates": [
    {{
      "estimate_id": string,
      "date": "YYYY-MM-DD",
      "title": string
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
  "comments": string
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
- commentsには【備考・条件】などの情報
- titleは「件名」を設定
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
    print(response.choices[0].message.content)
    return safe_json_parse(response.choices[0].message.content)


# ------------------------------
# ✅ ④ main関数（bytes対応）
# ------------------------------
def pdf_to_json_bytes(file_bytes):
    text = extract_text_from_bytes(file_bytes)
    result = extract_structured_data(text)
    return result
    