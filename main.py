from fastapi import FastAPI
import pandas as pd
from pymongo import MongoClient
from sklearn.linear_model import LinearRegression
import certifi

app = FastAPI()

# เชื่อมต่อ MongoDB
uri = "mongodb+srv://6631501001_db_user:hUxalPBLLxkxLqSB@cluster0.34btd8c.mongodb.net/?appName=Cluster0"
client = MongoClient(uri, tlsCAFile=certifi.where())
collection = client["BDA_Project"]["StockData_M15"]

@app.get("/")
def read_root():
    return {"message": "🚀 Welcome to PREDI API! Server is running."}

@app.get("/predict")
def get_prediction(ticker: str = "GC=F"):
    # ดึงข้อมูลจาก MongoDB
    cursor = collection.find({"Ticker": ticker.upper()}).sort("Datetime", 1)
    data = list(cursor)
    
    if not data:
        return {"error": "❌ No data found. Please run ingest first."}

    # เตรียมข้อมูล
    df = pd.DataFrame(data)
    df = df.drop(columns=["_id"], errors="ignore")
    df["Target_Next_Close"] = df["Close"].shift(-1)
    train_df = df.dropna(subset=["Target_Next_Close"])

    features = ["Open", "High", "Low", "Close", "Volume"]
    X_train = train_df[features]
    y_train = train_df["Target_Next_Close"]
    X_today = df.iloc[[-1]][features]

    # เทรนและทำนาย
    model = LinearRegression()
    model.fit(X_train, y_train)
    predicted_price = model.predict(X_today)[0]
    current_price = df.iloc[-1]["Close"]
    
    direction = "UP 🟢" if predicted_price > current_price else "DOWN 🔴"

    # ส่งผลลัพธ์กลับไปให้แอปมือถือ
    return {
        "ticker": ticker.upper(),
        "latest_time": str(df.iloc[-1]["Datetime"]),
        "current_price": round(current_price, 2),
        "predicted_price": round(predicted_price, 2),
        "direction": direction,
        "recommendation": "BUY" if predicted_price > current_price else "SELL/HOLD"
    }