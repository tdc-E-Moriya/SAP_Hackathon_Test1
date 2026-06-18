from fastapi import FastAPI, HTTPException
import json
import os

from app.pdf_json import pdf_to_json_bytes
from app.risk_judge import analyze_risk

app = FastAPI()

PDF_PATH = "../pdfs/sample.pdf"  # ← 固定PDF

@app.get("/analyze")
def analyze_pdf():
    try:
        # ------------------------------
        # ✅ ファイル存在チェック
        # ------------------------------
        if not os.path.exists(PDF_PATH):
            raise HTTPException(status_code=404, detail="PDF not found")

        # ------------------------------
        # ✅ ① バイト読み込み
        # ------------------------------
        with open(PDF_PATH, "rb") as f:
            file_bytes = f.read()

        # ------------------------------
        # ✅ ② PDF → JSON
        # ------------------------------
        json_data = pdf_to_json_bytes(file_bytes)

        if not json_data:
            raise Exception("PDF parse failed")

        # ------------------------------
        # ✅ ③ リスク分析
        # ------------------------------
        result = analyze_risk(json_data)

        # ------------------------------
        # ✅ ④ LLM結果整形
        # ------------------------------
        try:
            llm_json = json.loads(result["llm_result"])
        except:
            llm_json = result["llm_result"]

        # ------------------------------
        # ✅ ⑤ レスポンス
        # ------------------------------
        return {
            "file": os.path.basename(PDF_PATH),
            "parsed": json_data,
            "result": llm_json
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))