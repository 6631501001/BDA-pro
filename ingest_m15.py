import sys
from datetime import datetime

try:
    import yfinance as yf
    import pandas as pd
    from pymongo import MongoClient
except ImportError as e:
    missing = getattr(e, 'name', str(e))
    print(f"Missing dependency: {missing}")
    print("Install dependencies with: python -m pip install -r requirements.txt")
    sys.exit(1)

# MongoDB Connection String
uri = (
    "mongodb+srv://6631501001_db_user:hUxalPBLLxkxLqSB@cluster0.34btd8c.mongodb.net/"
    "?appName=Cluster0&tls=true"
)

# Use this only if you cannot complete the TLS handshake normally.
# Insecure: tlsAllowInvalidCertificates=true
uri = uri + "&tlsAllowInvalidCertificates=true"

try:
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    print("💡 Check your network, Atlas IP access list, and TLS settings.")
    print("Install dependencies with: python -m pip install -r requirements.txt")
    sys.exit(1)

db = client["BDA_Project"]
collection = db["StockData_M15"]

TICKERS = ["AAPL", "MSFT", "GC=F"]
PERIOD = "60d"
INTERVAL = "15m"

print("🚀 Starting intraday ingestion for M15 data...")
collection.delete_many({})

for ticker in TICKERS:
    print(f"⏳ Fetching {ticker} {INTERVAL} bars for {PERIOD}...")
    df = yf.download(ticker, period=PERIOD, interval=INTERVAL, progress=False)

    if df.empty:
        print(f"❌ No data found for {ticker}")
        continue

    df.reset_index(inplace=True)
    if "Datetime" not in df.columns and "Date" in df.columns:
        df.rename(columns={"Date": "Datetime"}, inplace=True)
    if not df.empty:
        df.reset_index(inplace=True)
        
        # --- เพิ่ม 2 บรรทัดนี้เพื่อแก้ปัญหาคอลัมน์ซ้อนกัน (MultiIndex) ---
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # --------------------------------------------------------

        # ข้อมูลรายนาที คอลัมน์จะชื่อ 'Datetime' ไม่ใช่ 'Date'
        df['Datetime'] = df['Datetime'].astype(str)
        df['Ticker'] = ticker

    df.columns.name = None
    df["Datetime"] = pd.to_datetime(df["Datetime"])
    df = df.sort_values(by="Datetime").reset_index(drop=True)
    df["Datetime"] = df["Datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df["Ticker"] = ticker

    df = df[["Datetime", "Ticker", "Open", "High", "Low", "Close", "Volume"]]
    records = df.to_dict("records")
    if records:
        collection.insert_many(records)
        print(f"✅ Uploaded {ticker} (M15): {len(records)} rows")
    else:
        print(f"❌ No valid rows for {ticker}")

print("🎉 Ingestion complete. Check MongoDB collection StockData_M15.")
