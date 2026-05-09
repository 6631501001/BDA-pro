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

TICKERS = [
    # Commodities (Meta5 favorites)
    "GC=F",      # Gold
    "SI=F",      # Silver
    "CL=F",      # Crude Oil (WTI)
    "NG=F",      # Natural Gas
    # Major Forex Pairs
    "EURUSD=X",  # EUR/USD
    "GBPUSD=X",  # GBP/USD
    "USDJPY=X",  # USD/JPY
    "AUDUSD=X",  # AUD/USD
    # Stocks
    "AAPL",
    "MSFT",
]

INTERVALS = {
    "15m": {"period": "60d", "collection": "StockData_M15"},
    "1h":  {"period": "730d", "collection": "StockData_1H"},
    "4h":  {"period": "730d", "collection": "StockData_4H"},
}

print("🚀 Starting multi-timeframe data ingestion...")

for interval, config in INTERVALS.items():
    print(f"\n{'='*50}")
    print(f"📊 Ingesting {interval} interval data...")
    print(f"{'='*50}")
    
    collection = db[config["collection"]]
    collection.delete_many({})
    
    for ticker in TICKERS:
        print(f"⏳ Fetching {ticker} {interval} bars for {config['period']}...")
        
        try:
            df = yf.download(ticker, period=config["period"], interval=interval, progress=False)
        except Exception as e:
            print(f"❌ Error fetching {ticker}: {e}")
            continue

        if df.empty:
            print(f"❌ No data found for {ticker}")
            continue

        df.reset_index(inplace=True)
        if "Datetime" not in df.columns and "Date" in df.columns:
            df.rename(columns={"Date": "Datetime"}, inplace=True)
        
        # Handle MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.columns.name = None
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        df = df.sort_values(by="Datetime").reset_index(drop=True)
        df["Datetime"] = df["Datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df["Ticker"] = ticker
        df["Interval"] = interval

        df = df[["Datetime", "Ticker", "Interval", "Open", "High", "Low", "Close", "Volume"]]
        records = df.to_dict("records")
        
        if records:
            collection.insert_many(records)
            print(f"✅ Uploaded {ticker} ({interval}): {len(records)} rows")
        else:
            print(f"❌ No valid rows for {ticker}")

print("\n" + "="*50)
print("🎉 Multi-timeframe ingestion complete!")
print("✅ Collections created: StockData_M15, StockData_1H, StockData_4H")
print("="*50)
