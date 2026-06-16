
import fitz  # PyMuPDF
import os
from PIL import Image
import io
import easyocr
import json
import re


from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.getenv("LLM_API_KEY"))

# ------------------------------
# ① PDF → 画像保存
# ------------------------------
def pdf_to_images(pdf_path):
    doc = fitz.open(pdf_path)

    output_dir = "images"
    os.makedirs(output_dir, exist_ok=True)

    image_paths = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=300)
        img_bytes = pix.tobytes("png")

        img = Image.open(io.BytesIO(img_bytes))
        img = img.convert("L")  # OCR精度UP

        file_path = os.path.join(output_dir, f"page_{i+1}.png")
        img.save(file_path)

        image_paths.append(file_path)

    return image_paths


# ------------------------------
# ② OCR（EasyOCR）
# ------------------------------
def extract_text_with_easyocr(pdf_path):
    print("▶ EasyOCR 実行中...")

    image_paths = pdf_to_images(pdf_path)

    reader = easyocr.Reader(['ja', 'en'])

    text = ""

    for i, img_path in enumerate(image_paths):
        print(f"▶ ページ {i+1}: {img_path}")

        result = reader.readtext(img_path)

        if not result:
            print("⚠ OCR結果なし")
            continue

        for bbox, detected_text, conf in result:
            text += detected_text + "\n"

    return text


# ------------------------------
# ③ JSONパース
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
# ④ LLM処理
# ------------------------------
def extract_structured_data(text):
    prompt = f"""
以下の日本語の見積テキストから情報を抽出し、指定のJSON形式で出力してください。

【出力形式】
{{
  "items": [
    {{
      "process": "行程名",
      "description": "行程の説明",
      "man_months": number,
      "subtotal": number
    }}
  ]
}}

【Field Mapping】
- 工程 → process
- 詳細 → description
- 工数 → man_months
- 小計（税別） → subtotal

【ルール】
- 数値は数値型（例：1,000円 → 1000）
- 1行ごとに1データ
- 見出し・合計行は除外
- 不明は null
- JSONのみ出力

【テキスト】
{text}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "あなたは帳票解析AIです"},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return safe_json_parse(response.choices[0].message.content)


# ------------------------------
# ⑤ メイン処理
# ------------------------------
def pdf_to_json(pdf_path):
    print(f"▶ 処理開始: {pdf_path}")

    text = extract_text_with_easyocr(pdf_path)

    print("▶ OCR結果（先頭500文字）:")
    print(text[:500])

    result = extract_structured_data(text)

    return result


# ------------------------------
# ⑥ 実行
# ------------------------------
if __name__ == "__main__":
    pdf_path = "見積もりサンプル.pdf"

    result = pdf_to_json(pdf_path)

    print("\n▶ JSON結果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
