from fastapi import FastAPI, HTTPException
import json
import os

from app.pdf_json import pdf_to_json_bytes
from app.risk_judge import analyze_risk

app = FastAPI()

PDF_PATH = "./pdfs/sample.pdf"  # ← 固定PDF

@app.post("/analyze")
def analyze_pdf():
    try:
       
        return {"parsed":{"supplier":"大和精密工業株式会社","currency":"JPY","estimates":[{"estimate_id":"Q20260135","date":"2026-06-19","title":"制御盤一式（更新工事）","products":[{"product_name":"制御パネル本体（更新用）　型番：CTL-䐸䐹䐴X","quantity":2,"unit_price":1850000,"amount":3700000},{"product_name":"配線・組付作業費","quantity":1,"unit_price":720000,"amount":720000}],"total_amount":4420000}],"comments":"本見積書は星和精機株式会社が発行する正式な見積回答です。ご不明点は上記担当までお問い合わせください\n・本見積の単価は2025年6月時点の部材市場価格に基づくものです。\n・設置場所については現地確認後に決定いたします。現地状況により追加費用が発生する可能性がございます。\n・既存配管・既存ケーブルの再利用を前提とした見積となっております。\n・上記以外の附帯工事（仮設電源、足場設置等）については別途協議とさせていただきます。\n・本見積には機器搬入後の試運転調整費は含まれておりません。"},"result":{"supplier":"大和精密工業株式会社","overall_risk":"Midium（リスク中）","total":{"risk":"全体の平均金額は5048750で、過去平均比で-12.45%の減少、標準偏差は1310925、zスコアは-0.48","validation":"caution","reason":"価格低下"},"products":[{"product":"制御パネル本体","quantity":{"risk":"数量の平均は1で、過去平均比で14.29%の増加、標準偏差は0、zスコアは0.35","validation":"caution","reason":"数量異常"},"amount":{"risk":"金額の平均は3041250で、過去平均比で21.66%の増加、標準偏差は1272123、zスコアは0.52","validation":"caution","reason":"コスト増加"}},{"product":"配線・組付作業費","quantity":{"risk":"数量は評価しない","validation":"warning","reason":""},"amount":{"risk":"金額の平均は702500で、過去平均比で2.49%の増加、標準偏差は37701、zスコアは0.46","validation":"warning","reason":"価格変動"}}],"comments_risk":{"risk":"なし","validation":"warning","reason":""},"mail_header":"見積回答についてご確認","mail_body":"大和精密工業株式会社ご担当者様 平素よりお世話になっております。見積内容���ついて、以下の点を確認させてください。全体の平均金額は5048750で、過去平均比で-12.45%の減少、制御パネル本体の数量の平均は1で、過去平均比で14.29%の増加、制御パネル本体の金額の平均は3041250で、過去平均比で21.66%の増加、配線・組付作業費の金額の平均は702500で、過去平均比で2.49%の増加"}}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))