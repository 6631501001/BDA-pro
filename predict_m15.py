import sys

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    from pymongo import MongoClient
    from sklearn.linear_model import LinearRegression
except ImportError as e:
    missing = getattr(e, 'name', str(e))
    print(f"Missing dependency: {missing}")
    print("Install dependencies with: python -m pip install -r requirements.txt")
    sys.exit(1)

uri = (
    "mongodb+srv://6631501001_db_user:hUxalPBLLxkxLqSB@cluster0.34btd8c.mongodb.net/"
    "?appName=Cluster0&tls=true"
)

try:
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    print("💡 If needed for your environment, add tlsAllowInvalidCertificates=true to the connection string.")
    print("Install dependencies with: python -m pip install -r requirements.txt")
    sys.exit(1)

collection = client["BDA_Project"]["StockData_M15"]

print("==================================================")
print("🤖 Real-Time AI Predictor (M15 Interval)")
print("==================================================")

target_ticker = input("👉 Please enter Ticker (e.g., AAPL, MSFT, GC=F): ").strip().upper()
print(f"☁️ Fetching {target_ticker} M15 data from MongoDB...")

cursor = collection.find({"Ticker": target_ticker}).sort("Datetime", 1)
data = list(cursor)

if not data:
    print(f"❌ No data found for {target_ticker}. Please run ingest_m15.py first.")
    sys.exit(1)


df = pd.DataFrame(data)
df = df.drop(columns=["_id"], errors="ignore")
df["Datetime"] = pd.to_datetime(df["Datetime"])
df = df.sort_values(by="Datetime").reset_index(drop=True)

if df.shape[0] < 10:
    print("❌ Not enough data to train a model. Need at least 10 rows.")
    sys.exit(1)

print("🧠 Preparing data & training AI model...")
df["Target_Next_Close"] = df["Close"].shift(-1)
train_df = df.dropna(subset=["Target_Next_Close"]).copy()

features = ["Open", "High", "Low", "Close", "Volume"]
X_train = train_df[features]
y_train = train_df["Target_Next_Close"]
X_today = df.iloc[[-1]][features]

model = LinearRegression()
model.fit(X_train, y_train)

predicted_price = model.predict(X_today)[0]
actual_current_price = df.iloc[-1]["Close"]
latest_timestamp = df.iloc[-1]["Datetime"]

print("\n==================================================")
print(f"📈 {target_ticker} Real-Time Analysis (Latest: {latest_timestamp})")
print("==================================================")
print(f"💵 Current Price (Now):     {actual_current_price:.2f} USD")
print(f"🔮 AI Predicted (Next 15m): {predicted_price:.2f} USD")
print("--------------------------------------------------")

if predicted_price > actual_current_price:
    print("🎯 Recommendation: 🟢 BUY - AI predicts price will go UP in the next 15 mins!")
else:
    print("🎯 Recommendation: 🔴 SELL / HOLD - AI predicts price will go DOWN!")
print("==================================================\n")

# ==================================================
# ส่วนที่ 7: วาดกราฟแท่งเทียน (Interactive Candlestick) ด้วย Plotly
# ==================================================
import plotly.graph_objects as go

print("📊 Generating real-time interactive Candlestick chart...")
plot_data = df.tail(50).copy()

# กำหนดสีและทิศทางสำหรับแสดงผลบนกราฟ
direction = "UP" if predicted_price > actual_current_price else "DOWN"
color_choice = "#00ff00" if direction == "UP" else "#ff0000" # สีเขียวสว่าง / แดงสว่าง

# คำนวณเวลาของแท่งอนาคต (บวกเพิ่ม 15 นาทีจากแท่งล่าสุด)
last_time = plot_data['Datetime'].iloc[-1]
next_time = last_time + pd.Timedelta(minutes=15)

# 1. สร้างกราฟแท่งเทียน
fig = go.Figure(data=[go.Candlestick(
    x=plot_data['Datetime'],
    open=plot_data['Open'],
    high=plot_data['High'],
    low=plot_data['Low'],
    close=plot_data['Close'],
    name='Historical M15',
    increasing_line_color='#00ff00', # สีเขียวตอนราคาขึ้น
    decreasing_line_color='#ff0000'  # สีแดงตอนราคาลง
)])

# 2. วางจุดทำนาย (AI Prediction) ในอนาคต
fig.add_trace(go.Scatter(
    x=[next_time],
    y=[predicted_price],
    mode='markers+text',
    marker=dict(color=color_choice, size=16, symbol='star', line=dict(color='white', width=2)),
    text=[f"AI Prediction: {direction}<br>${predicted_price:.2f}"],
    textposition="top center",
    textfont=dict(color=color_choice, size=14, family="Arial Black"),
    name='AI Prediction'
))

# 3. ปรับแต่งหน้าตาให้เป็น Dark Mode ระดับมืออาชีพ
fig.update_layout(
    title=f"<b>{target_ticker} AI Intraday Prediction (M15)</b><br><sup>Expected to go {direction}</sup>",
    yaxis_title='Price (USD)',
    xaxis_title='Time',
    template='plotly_dark', # ธีมสีดำ
    xaxis_rangeslider_visible=False, # ซ่อนแถบเลื่อนด้านล่างให้ดูสะอาด
    margin=dict(l=50, r=50, t=80, b=50)
)

# เปิดกราฟบน Web Browser ทันที
fig.show()