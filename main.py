from pdf_json import pdf_to_json
from risk_judge import analyze_risk
import json

PDF_FILE = "sample.pdf"
json_data = pdf_to_json(PDF_FILE)

result = analyze_risk(json_data)

print(result["llm_result"])