import sys
try:
    from pymongo import MongoClient
except ImportError as e:
    missing = getattr(e, 'name', str(e))
    print(f"Missing dependency: {missing}")
    print("Activate the project virtual environment or install dependencies with:")
    print("  python -m pip install -r requirements.txt")
    sys.exit(1)
import pandas as pd
from sklearn.linear_model import LinearRegression
import warnings
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

warnings.filterwarnings('ignore')

# ==========================================
# 🎯 Interactive Input System
# ==========================================
print("\n" + "="*50)
print("🤖 Welcome to AI Stock & Gold Prediction System")
print("="*50)
# Ask for user input
TARGET_TICKER = input("👉 Please enter the desired Ticker (e.g., AAPL, MSFT, GC=F): ").strip().upper()
print("-" * 50)

# ==========================================
# 1. Load Data from MongoDB
# ==========================================
print(f"📥 Fetching {TARGET_TICKER} data from MongoDB...")
uri = "mongodb+srv://6631501001_db_user:hUxalPBLLxkxLqSB@cluster0.34btd8c.mongodb.net/?appName=Cluster0"
try:
    client = MongoClient(uri, tls=True, serverSelectionTimeoutMS=10000)
    client.admin.command('ping')
except Exception as e:
    print('❌ MongoDB connection failed:', e)
    print('💡 If this is an Atlas cluster, verify your network/TLS settings and that dnspython is installed.')
    print('  python -m pip install -r requirements.txt')
    sys.exit(1)

db = client["BDA_Project"]
collection = db["StockData"]

cursor = collection.find({"Ticker": TARGET_TICKER})
df = pd.DataFrame(list(cursor))

# Check if data exists in Database
if df.empty:
    print(f"❌ Error: No data found for '{TARGET_TICKER}' in the database!")
    print("💡 Hint: Please add the ticker to 'ingest_data.py' and run it to fetch data first.")
    sys.exit()

df = df.drop(columns=['_id']) 

# ==========================================
# 2. Data Preparation
# ==========================================
print("🧠 Preparing data for AI model...")
df['Date'] = pd.to_datetime(df['Date'], utc=True)
df = df.sort_values(by='Date').reset_index(drop=True)

df['Target_Next_Close'] = df['Close'].shift(-1)

train_df = df.dropna(subset=['Target_Next_Close'])
today_df = df.tail(1)

features = ['Open', 'High', 'Low', 'Close', 'Volume']

X_train = train_df[features]
y_train = train_df['Target_Next_Close']
X_today = today_df[features]

# ==========================================
# 3. Train Model & Predict
# ==========================================
print("🤖 Training AI Model (Linear Regression)...")
model = LinearRegression()
model.fit(X_train, y_train)

print(f"🔮 Predicting tomorrow's {TARGET_TICKER} price...")
predicted_tomorrow_price = model.predict(X_today)[0]
today_close_price = today_df['Close'].values[0]
latest_date = today_df['Date'].dt.strftime('%Y-%m-%d').values[0]

# ==========================================
# 4. Results & Recommendation
# ==========================================
print("\n=======================================================")
print(f"📈 {TARGET_TICKER} Analysis for {latest_date}")
print("=======================================================")
print(f"💵 Today's Close Price (Actual):   {today_close_price:.2f} USD")
print(f"🤖 AI Predicted Price (Tomorrow):  {predicted_tomorrow_price:.2f} USD")
print("-------------------------------------------------------")

is_buy = predicted_tomorrow_price > today_close_price
if is_buy:
    print(f"🎯 Recommendation: 🟢 BUY - AI predicts {TARGET_TICKER} will go UP!")
else:
    print(f"🎯 Recommendation: 🔴 SELL / HOLD - AI predicts {TARGET_TICKER} will go DOWN!")
print("=======================================================\n")

# ==========================================
# 📊 NEW VISUALIZATION SECTION
# ==========================================
print("📊 Generating historical price chart & AI prediction...")

# Select recent data to plot (e.g., last 60 actual trading days) for better readability
plot_data = df.tail(60).copy()

# Create the figure
plt.figure(figsize=(12, 6))

# Plot historical data as a smooth blue line
plt.plot(plot_data['Date'], plot_data['Close'], label='Historical Close Price', color='blue', linewidth=2)

# Calculate a pseudo-date for tomorrow just for plotting.
# Matplotlib handles datetime objects correctly on the x-axis.
pred_date = today_df['Date'].iloc[0] + pd.Timedelta(days=1)

# Color prediction dot based on recommendation (Green for Buy, Red for Sell/Hold)
pred_color = 'green' if is_buy else 'red'

# Add a distinct point for the prediction
plt.scatter(pred_date, predicted_tomorrow_price, color=pred_color, s=200, label='AI Prediction', edgecolors='black', zorder=5)

# Annotate prediction value text on the chart
plt.annotate(f'Predicted: ${predicted_tomorrow_price:.2f}',
             xy=(pred_date, predicted_tomorrow_price),
             xytext=(15, 0), textcoords='offset points', color=pred_color, fontweight='bold', fontsize=12)

# Chart Formatting (Title, Labels, Grid, Legend)
plt.title(f'{TARGET_TICKER} Price Chart & AI Prediction for {latest_date} onward', fontsize=16)
plt.ylabel('Price (USD)', fontsize=12)
plt.xlabel('Date', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend()

# Improve date formatting on the x-axis
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d')) # Format as YYYY-MM-DD
plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=10)) # Show date label every 10 trading days
plt.gcf().autofmt_xdate() # Automatically rotate and align the tick labels for readability

# Finalize and Show
plt.tight_layout()
print("🚀 Opening chart window (script will pause)...")
plt.show() # This opens the window and blocks execution until closed
print("✅ Chart window closed.")
# ==================================