from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pymongo import MongoClient
from sklearn.linear_model import LinearRegression
import certifi
import yfinance as yf
from textblob import TextBlob
import sys
import asyncio
from contextlib import asynccontextmanager
import subprocess


# วิธีเขียนแบบใหม่ของ FastAPI (Lifespan) แก้อาการขีดเส้นใต้สีเหลือง
@asynccontextmanager
# 1. ฟังก์ชันสั่งรันไฟล์ดึงข้อมูลโดยตรง
def run_ingest_script():
    print("🔄 [Auto-Start] กำลังดึงข้อมูลล่าสุดจากตลาดลง Database...")
    try:
        # สั่งรันไฟล์ ingest_multiframe.py แบบรอให้เสร็จแล้วค่อยไปต่อ
        subprocess.run([sys.executable, "ingest_multiframe.py"], check=True)
        print("✅ [Auto-Start] ดึงข้อมูลและอัปเดตฐานข้อมูลสำเร็จเรียบร้อย!")
    except Exception as e:
        print(f"❌ [Auto-Start] เกิดข้อผิดพลาดในการดึงข้อมูล: {repr(e)}")

# 2. ให้มันรันอัตโนมัติทันทีตอนเปิดเซิร์ฟเวอร์
@asynccontextmanager
async def lifespan_event(app: FastAPI):
    # สั่งให้มันทำงานดึงข้อมูลก่อนที่แอปจะพร้อมรับคำขอ
    run_ingest_script()
    yield

app = FastAPI(lifespan=lifespan_event)

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
    
    # 🌟 1. คำนวณ RSI (14) ด้วย pandas
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 🌟 2. คำนวณ MACD (12, 26) ด้วย pandas
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26

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
    
    # 🌟 3. คำนวณ Confidence Score จาก R-Squared ของโมเดล (แปลงเป็น 0-100%)
    r2_score = model.score(X_train, y_train)
    confidence_score = max(0.0, min(100.0, round(r2_score * 100, 2)))
    
    # 🌟 4. ดึงค่าล่าสุดมาโชว์ที่หน้าบ้าน
    latest_rsi = round(df.iloc[-1]['RSI'], 2) if not pd.isna(df.iloc[-1]['RSI']) else 50.0
    latest_macd = round(df.iloc[-1]['MACD'], 2) if not pd.isna(df.iloc[-1]['MACD']) else 0.0
    # ========== 🌟 1. News Sentiment Analysis (อ่านข่าวล่าสุด) ==========
    sentiment_score = 0.0
    sentiment_label = "NEUTRAL 😶"
    try:
        yf_ticker = yf.Ticker(ticker)
        news_data = yf_ticker.news
        if news_data:
            # ดึงพาดหัวข่าว 5 อันดับแรกมาให้ AI วิเคราะห์อารมณ์
            headlines = [n['title'] for n in news_data[:5] if 'title' in n]
            polarities = [TextBlob(title).sentiment.polarity for title in headlines]
            if polarities:
                sentiment_score = sum(polarities) / len(polarities)
                
            if sentiment_score > 0.1:
                sentiment_label = "POSITIVE 🟢"
            elif sentiment_score < -0.1:
                sentiment_label = "NEGATIVE 🔴"
    except Exception as e:
        print(f"News Error: {e}")

    # ========== 🌍 2. Macro Data (ดัชนีความกลัวตลาด VIX) ==========
    current_vix = 0.0
    risk_level = "NORMAL"
    try:
        vix_data = yf.Ticker("^VIX").history(period="1d")
        if not vix_data.empty:
            current_vix = round(float(vix_data['Close'].iloc[-1]), 2)
            if current_vix > 20.0:
                risk_level = "HIGH RISK ⚠️"
    except Exception as e:
        print(f"VIX Error: {e}")

    # ========== ⚖️ 3. ปรับคำแนะนำขั้นสุดท้าย (Quant Overlay) ==========
    # ถ้ากราฟบอกให้ BUY แต่ข่าวแย่มาก หรือตลาดผันผวนจัด ให้ระวัง (HOLD)
    raw_recommendation = "BUY" if predicted_price > current_price else "SELL"
    final_recommendation = raw_recommendation

    if raw_recommendation == "BUY" and (sentiment_score < -0.15 or current_vix > 25.0):
        final_recommendation = "HOLD (Risk Alert)"
    elif raw_recommendation == "SELL" and sentiment_score > 0.15:
        final_recommendation = "HOLD (Good News Alert)"

    direction = "UP 🟢" if predicted_price > current_price else "DOWN 🔴"

    # ดึงข้อมูลล่าสุดเพื่อส่งไปทำกราฟแท่ง
    num_history_points = min(15, len(df))
    history_data = df.tail(num_history_points).to_dict("records")
    history_list = [
        {
            "time": str(row["Datetime"]), 
            "price": round(float(row["Close"]), 2)
        }
        for row in history_data
    ]

    # ส่งผลลัพธ์กลับไปให้แอปมือถือ
    return {
        "ticker": ticker.upper(),
        "interval": interval,
        "latest_time": str(df.iloc[-1]["Datetime"]),
        "current_price": round(current_price, 2),
        "predicted_price": round(predicted_price, 2),
        "direction": direction,
        "recommendation": final_recommendation, # ใช้อันที่ผ่านการกรองแล้ว
        "time_horizon": TIME_HORIZONS[interval],
        "history": history_list,
        "confidence": confidence_score,
        "rsi": latest_rsi,
        "macd": latest_macd,
        # ส่งค่าใหม่ไปรอที่หน้าบ้าน
        "news_sentiment": sentiment_label,
        "market_vix": current_vix,
        "market_risk": risk_level
    }