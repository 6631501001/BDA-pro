import sys
try:
    import yfinance as yf
    import pandas as pd
    from pymongo import MongoClient
except ImportError as e:
    missing = getattr(e, 'name', str(e))
    print(f"Missing dependency: {missing}")
    print("Activate the project virtual environment or install dependencies with:")
    print("  python -m pip install -r requirements.txt")
    sys.exit(1)

# MongoDB Connection String
uri = "mongodb+srv://6631501001_db_user:hUxalPBLLxkxLqSB@cluster0.34btd8c.mongodb.net/?appName=Cluster0"

# 1. Connect to Database
client = MongoClient(uri, tls=True)

# Define Database and Collection names
db = client["BDA_Project"]
collection = db["StockData"]

# ==========================================
# 2. Configure Target Tickers
# ==========================================
# Selecting major tech stocks and Gold Futures for the initial system test
tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "GC=F"]

print("🚀 Starting Data Ingestion and uploading to MongoDB...")

for ticker in tickers:
    # Initialize the Ticker object
    stock = yf.Ticker(ticker)
    
    # Fetch 5 years of historical data
    df = stock.history(period="5y")
    
    if not df.empty:
        df.reset_index(inplace=True)
        
        # Convert 'Date' to string to prevent Timezone issues in MongoDB
        df['Date'] = df['Date'].astype(str)
        
        # Add a ticker label to each row
        df['Ticker'] = ticker
        
        # Select primary columns for analysis
        df = df[['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        # ==========================================
        # 3. Upload Data to MongoDB
        # ==========================================
        # Convert Pandas DataFrame to JSON (Dictionary format used by MongoDB)
        data_dict = df.to_dict("records")
        
        # Insert records into the collection
        collection.insert_many(data_dict)
        print(f"✅ Successfully uploaded {ticker} to Database! Total records: {len(data_dict)}")
    else:
        print(f"❌ No data found for {ticker}")

print("🎉 Process Complete! Data is now stored in MongoDB.")