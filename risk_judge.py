#サプライヤ抽出のみ

import json
import statistics

# =========================
# 設定
# =========================
THRESHOLD = 0.2  # 20%

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
    for supplier in data:
        if supplier["supplier"] == supplier_name:
            return supplier["estimates"]
    return []

data_2025 = extract_supplier(past_data_all, current_supplier)

# =========================
# 統計値計算
# =========================
values = [d["total_amount"] for d in data_2025]

avg_2025 = statistics.mean(values)
median_2025 = statistics.median(values)

# 標準偏差（2件以上必要）
std_2025 = statistics.stdev(values) if len(values) > 1 else 0

# =========================
# 現在データ
# =========================
current_value = current_data["total_amount"]

# =========================
# 差分計算
# =========================
diff_avg = current_value - avg_2025
rate_avg = diff_avg / avg_2025

diff_median = current_value - median_2025
rate_median = diff_median / median_2025

# =========================
# 標準偏差ベース異常検知（Zスコア）
# =========================
if std_2025 > 0:
    z_score = (current_value - avg_2025) / std_2025
else:
    z_score = 0

# ルール例
is_anomaly_rate = abs(rate_avg) >= THRESHOLD
is_anomaly_z = abs(z_score) >= 2  # ±2σ

# =========================
# summary
# =========================
summary = {
    "supplier": current_supplier,
    "current_month": current_data["date"][:7],

    # 統計
    "past_avg": int(avg_2025),
    "past_median": int(median_2025),
    "past_stddev": int(std_2025),

    # 現在
    "current_value": current_value,

    # 差分
    "diff_avg": int(diff_avg),
    "rate_avg": round(rate_avg * 100, 2),

    "diff_median": int(diff_median),
    "rate_median": round(rate_median * 100, 2),

    # 異常判定
    "z_score": round(z_score, 2),
    "anomaly_rate": is_anomaly_rate,
    "anomaly_zscore": is_anomaly_z
}

# =========================
# 出力
# =========================
final_output = {
    "summary": summary
}

print(json.dumps(final_output, ensure_ascii=False, indent=2))

# 保存
#with open("analysis_output.json", "w", encoding="utf-8") as f:
#    json.dump(final_output, f, ensure_ascii=False, indent=2)