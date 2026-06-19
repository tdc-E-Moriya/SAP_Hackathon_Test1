# 軽量Python
FROM python:3.11-slim

# 作業ディレクトリ
WORKDIR /app

# 依存コピー
COPY requirements.txt .

# install
RUN pip install --no-cache-dir -r requirements.txt

# コードコピー
COPY app/ app/
COPY data/ data/
COPY .env .env

# ポート
EXPOSE 8080

# 起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]