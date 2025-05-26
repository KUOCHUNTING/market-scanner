
import os
import time
import traceback
from datetime import datetime, timedelta
from polygon import RESTClient
import pandas as pd
import requests
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from concurrent.futures import ThreadPoolExecutor

# === 設定區 ===
API_KEY = os.getenv("POLYGON_API_KEY") or "YOUR_API_KEY"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL") or "YOUR_WEBHOOK"
SPREADSHEET_NAME = "MarketSignalLogs"
SCAN_INTERVAL = 60
MAX_THREADS = 10
STOCK_LIST_CSV = "filtered_us_stocks_common_only.csv"

# === Google Sheets 認證 ===
def setup_google_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open(SPREADSHEET_NAME).sheet1
        return sheet
    except Exception as e:
        print("[警告] Google Sheets 認證失敗：", e)
        return None

# === 推播到 Discord ===
def push_to_discord(title, message):
    try:
        data = {"content": f"**{title}**
{message}"}
        requests.post(DISCORD_WEBHOOK, json=data, timeout=10)
    except Exception as e:
        print("[推播錯誤]", e)

# === 技術指標計算 ===
def analyze_signal(symbol, df):
    try:
        if df is None or df.empty or "timestamp" not in df.columns:
            return None
        close = df["close"]
        high = df["high"]
        low = df["low"]

        rsi = RSIIndicator(close).rsi().iloc[-1]
        macd = MACD(close).macd_diff().iloc[-1]
        kd = StochasticOscillator(high=high, low=low, close=close)
        k_value = kd.stoch().iloc[-1]
        d_value = kd.stoch_signal().iloc[-1]

        if rsi < 30 and macd > 0 and k_value > d_value:
            return "多頭訊號"
        elif rsi > 70 and macd < 0 and k_value < d_value:
            return "空頭訊號"
        return None
    except Exception as e:
        print(f"[分析錯誤] {symbol}：", e)
        return None

# === 抓取股票資料 ===
def fetch_stock_data(symbol):
    try:
        client = RESTClient(api_key=API_KEY)
        end = datetime.now()
        start = end - timedelta(minutes=35)
        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=5,
            timespan="minute",
            from_=start.strftime("%Y-%m-%d"),
            to=end.strftime("%Y-%m-%d"),
            limit=100
        )
        data = [{
            "timestamp": pd.to_datetime(bar["t"], unit="ms"),
            "open": bar["o"],
            "high": bar["h"],
            "low": bar["l"],
            "close": bar["c"],
            "volume": bar["v"]
        } for bar in aggs]
        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        print(f"[ERROR] 抓取資料失敗 {symbol}: {e}")
        return None

# === 單一個股處理流程 ===
def process_symbol(symbol):
    df = fetch_stock_data(symbol)
    signal = analyze_signal(symbol, df)
    if signal:
        print(f"[訊號] {symbol}：{signal}")
        push_to_discord(f"股票訊號 - {symbol}", f"{signal} 已觸發")

# === 載入股票清單 ===
def load_symbols():
    df = pd.read_csv(STOCK_LIST_CSV)
    return df["symbol"].tolist()

# === 主掃描流程 ===
def scan_all_symbols(symbols):
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        executor.map(process_symbol, symbols)

# === 主流程 ===
if __name__ == "__main__":
    print("✅ 腳本啟動成功，進入主流程...")
    symbols = load_symbols()
    while True:
        print(f"🔍 掃描中（{len(symbols)} 檔股票）...")
        scan_all_symbols(symbols)
        print(f"⏳ 等待 {SCAN_INTERVAL} 秒後執行下一輪...
")
        time.sleep(SCAN_INTERVAL)
