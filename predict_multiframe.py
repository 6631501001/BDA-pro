import sys

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    from pymongo import MongoClient
    from sklearn.linear_model import LinearRegression
    import plotly.graph_objects as go
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

print("==================================================")
print("🤖 Real-Time AI Predictor (Multi-Timeframe)")
print("==================================================\n")

# Step 1: Select Interval
print("📊 Available Timeframes:")
print("  1️⃣  M15 (15-minute)")
print("  2️⃣  1H (Hourly)")
print("  3️⃣  4H (4-hourly)")
interval_choice = input("\n👉 Select timeframe (1/2/3): ").strip()

interval_map = {
    "1": ("M15", "15m"),
    "2": ("1H", "1h"),
    "3": ("4H", "4h"),
}

if interval_choice not in interval_map:
    print("❌ Invalid selection. Defaulting to M15...")
    interval_choice = "1"

interval_name, interval_symbol = interval_map[interval_choice]
collection_name = f"StockData_{interval_name}"
collection = client["BDA_Project"][collection_name]

print(f"✅ Selected: {interval_name} ({interval_symbol})")

# Step 2: Select Ticker
target_ticker = input("\n👉 Please enter Ticker (e.g., AAPL, GC=F, EURUSD=X): ").strip().upper()
print(f"☁️ Fetching {target_ticker} {interval_name} data from MongoDB...")

cursor = collection.find({"Ticker": target_ticker}).sort("Datetime", 1)
data = list(cursor)

if not data:
    print(f"❌ No data found for {target_ticker} in {interval_name}.")
    print(f"   Please run: python ingest_multiframe.py")
    sys.exit(1)

df = pd.DataFrame(data)
df = df.drop(columns=["_id"], errors="ignore")
df["Datetime"] = pd.to_datetime(df["Datetime"])
df = df.sort_values(by="Datetime").reset_index(drop=True)

if df.shape[0] < 10:
    print("❌ Not enough data to train a model. Need at least 10 rows.")
    sys.exit(1)

# Step 3: Train AI Model
print(f"🧠 Preparing {interval_name} data & training AI model...")
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

# Determine time horizon
time_horizons = {
    "15m": "next 15 minutes",
    "1h": "next hour",
    "4h": "next 4 hours",
}
time_horizon = time_horizons.get(interval_symbol, "next period")

print("\n" + "="*50)
print(f"📈 {target_ticker} Analysis ({interval_name}) | Latest: {latest_timestamp}")
print("="*50)
print(f"💵 Current Price (Now):      {actual_current_price:.2f}")
print(f"🔮 AI Predicted ({time_horizon}): {predicted_price:.2f}")
print("-"*50)

if predicted_price > actual_current_price:
    print(f"🎯 Recommendation: 🟢 BUY - AI predicts price will go UP in the {time_horizon}!")
else:
    print(f"🎯 Recommendation: 🔴 SELL / HOLD - AI predicts price will go DOWN!")
print("="*50 + "\n")

# Step 4: Generate Interactive Chart
print(f"📊 Generating interactive {interval_name} Candlestick chart...")
plot_data = df.tail(50).copy()

direction = "UP" if predicted_price > actual_current_price else "DOWN"
color_choice = "#00ff00" if direction == "UP" else "#ff0000"

last_time = plot_data['Datetime'].iloc[-1]

# Calculate next time based on interval
if interval_symbol == "15m":
    next_time = last_time + pd.Timedelta(minutes=15)
elif interval_symbol == "1h":
    next_time = last_time + pd.Timedelta(hours=1)
elif interval_symbol == "4h":
    next_time = last_time + pd.Timedelta(hours=4)
else:
    next_time = last_time + pd.Timedelta(minutes=15)

fig = go.Figure(data=[go.Candlestick(
    x=plot_data['Datetime'],
    open=plot_data['Open'],
    high=plot_data['High'],
    low=plot_data['Low'],
    close=plot_data['Close'],
    name=f'Historical {interval_name}',
    increasing_line_color='#00ff00',
    decreasing_line_color='#ff0000'
)])

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

fig.update_layout(
    title=f"<b>{target_ticker} AI Prediction ({interval_name})</b><br><sup>Expected to go {direction}</sup>",
    yaxis_title='Price (USD)',
    xaxis_title='Time',
    template='plotly_dark',
    xaxis_rangeslider_visible=False,
    margin=dict(l=50, r=50, t=80, b=50)
)

fig.show()
