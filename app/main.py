from fastapi import FastAPI, UploadFile, File, HTTPException
import json

from app.pdf_json import pdf_to_json_bytes
from app.risk_judge import analyze_risk


app = FastAPI()


@app.post("/analyze")
async def analyze_pdf(file: UploadFile = File(...)):
    try:
        # ------------------------------
        # ✅ ① メモリに読み込み（保存なし）
        # ------------------------------
        file_bytes = await file.read()

        # ------------------------------
        # ✅ ② PDF → JSON
        # ------------------------------
        json_data = pdf_to_json_bytes(file_bytes)

        # ------------------------------
        # ✅ ③ リスク分析
        # ------------------------------
        result = analyze_risk(json_data)

        # ------------------------------
        # ✅ ④ LLM結果をJSON化
        # ------------------------------
        try:
            llm_json = json.loads(result["llm_result"])
        except:
            llm_json = result["llm_result"]

        # ------------------------------
        # ✅ ⑤ JSONレスポンス
        # ------------------------------
        return {
            "parsed": json_data,
            "result": llm_json
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))