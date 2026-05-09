from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pymongo import MongoClient
from sklearn.linear_model import LinearRegression
import certifi

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# เชื่อมต่อ MongoDB
uri = "mongodb+srv://6631501001_db_user:hUxalPBLLxkxLqSB@cluster0.34btd8c.mongodb.net/?appName=Cluster0"
client = MongoClient(uri, tlsCAFile=certifi.where())
db = client["BDA_Project"]
INTERVAL_COLLECTIONS = {
    "M15": "StockData_M15",
    "1H": "StockData_1H",
    "4H": "StockData_4H",
}
TIME_HORIZONS = {
    "M15": "next 15 minutes",
    "1H": "next hour",
    "4H": "next 4 hours",
}

@app.get("/")
def read_root():
    return {"message": "🚀 Welcome to PREDI API! Server is running."}

@app.get("/predict")
def get_prediction(
    ticker: str = "GC=F",
    interval: str = "M15",
    timeframe: Optional[str] = None,
):
    if timeframe:
        interval = timeframe

    interval = interval.upper()
    if interval not in INTERVAL_COLLECTIONS:
        raise HTTPException(
            status_code=400,
            detail="Invalid interval. Use M15, 1H, or 4H.",
        )

    collection_name = INTERVAL_COLLECTIONS[interval]
    collection = db[collection_name]

    cursor = collection.find({"Ticker": ticker.upper()}).sort("Datetime", 1)
    data = list(cursor)

    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for {ticker.upper()} in {interval}. Please run ingest_multiframe.py first.",
        )

    # เตรียมข้อมูล
    df = pd.DataFrame(data)
    df = df.drop(columns=["_id"], errors="ignore")
    df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")
    df = df.sort_values(by="Datetime").reset_index(drop=True)
    df["Target_Next_Close"] = df["Close"].shift(-1)
    train_df = df.dropna(subset=["Target_Next_Close"])

    if train_df.empty:
        raise HTTPException(
            status_code=400,
            detail="Not enough data to train the model for this ticker and interval.",
        )

    features = ["Open", "High", "Low", "Close", "Volume"]
    X_train = train_df[features]
    y_train = train_df["Target_Next_Close"]
    X_today = df.iloc[[-1]][features]

    # เทรนและทำนาย
    model = LinearRegression()
    model.fit(X_train, y_train)
    predicted_price = float(model.predict(X_today)[0])
    current_price = float(df.iloc[-1]["Close"])
    
    direction = "UP 🟢" if predicted_price > current_price else "DOWN 🔴"

    # ส่งผลลัพธ์กลับไปให้แอปมือถือ
    return {
        "ticker": ticker.upper(),
        "interval": interval,
        "latest_time": str(df.iloc[-1]["Datetime"]),
        "current_price": round(current_price, 2),
        "actual_current_price": round(current_price, 2),
        "predicted_price": round(predicted_price, 2),
        "direction": direction,
        "recommendation": "BUY" if predicted_price > current_price else "SELL/HOLD",
        "time_horizon": TIME_HORIZONS[interval],
    }