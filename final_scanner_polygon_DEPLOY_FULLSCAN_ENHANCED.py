
import os
import time
import traceback
from datetime import datetime
from polygon import RESTClient
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD
import pandas as pd
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 設定 API 與參數
API_KEY = os.getenv("POLYGON_API_KEY") or "YOUR_API_KEY"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL") or "https://discord.com/api/webhooks/xxxxxxxx"
SCAN_INTERVAL = 60
SPREADSHEET_NAME = "MarketSignalLogs"

# Google Sheets 認證
def setup_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    return sheet

sheet = None
try:
    sheet = setup_google_sheets()
except Exception as e:
    print(f"[WARNING] Google Sheets 無法啟動: {e}")

# 抓股票資料
def fetch_stock_data(symbol):
    try:
        client = RESTClient(api_key=API_KEY)
        end = datetime.now()
        start = end - pd.Timedelta(minutes=35)
        aggs = client.get_aggs(
            symbol=symbol,
            multiplier=5,
            timespan="minute",
            from_=start.strftime("%Y-%m-%d"),
            to=end.strftime("%Y-%m-%d"),
            limit=100
        )
        data = [{
            "timestamp": pd.to_datetime(bar["t"], unit='ms'),
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

# 技術指標訊號分析
def analyze_signal(symbol, df):
    try:
        close = df['close']
        if len(close) < 35:
            return None
        rsi = RSIIndicator(close).rsi().iloc[-1]
        macd = MACD(close).macd_diff().iloc[-1]
        kd = StochasticOscillator(high=df['high'], low=df['low'], close=close)
        k_value = kd.stoch().iloc[-1]
        d_value = kd.stoch_signal().iloc[-1]

        if rsi < 30 and macd > 0 and k_value > d_value:
            return "多頭進場訊號"
        elif rsi > 70 and macd < 0 and k_value < d_value:
            return "空頭進場訊號"
        return None
    except Exception as e:
        print(f"[ERROR] 分析指標失敗 {symbol}: {e}")
        return None

# 發送 Discord 通知
def push_to_discord(symbol, signal):
    try:
        content = {
            "content": f"【技術訊號】{symbol} 出現 {signal}"
        }
        requests.post(DISCORD_WEBHOOK, json=content)
    except Exception as e:
        print(f"[ERROR] Discord 推播失敗 {symbol}: {e}")

# 寫入 Google Sheets
def log_to_sheets(symbol, signal):
    try:
        if sheet:
            sheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), symbol, signal])
    except Exception as e:
        print(f"[ERROR] 寫入 Sheets 失敗 {symbol}: {e}")

# 掃描所有股票
def scan_all_symbols():
    print("▶️ 開始掃描所有股票...")
    try:
        stock_list = pd.read_csv("filtered_us_stocks_common_only.csv")["symbol"].tolist()
        for symbol in stock_list:
            df = fetch_stock_data(symbol)
            if df is not None:
                signal = analyze_signal(symbol, df)
                if signal:
                    print(f"【推播通知】{symbol}: {signal}")
                    push_to_discord(symbol, signal)
                    log_to_sheets(symbol, signal)
    except Exception as e:
        print(f"[ERROR] 掃描過程錯誤: {traceback.format_exc()}")

# 主流程
def main():
    print("✅ [INFO] 腳本啟動成功，進入主流程...")
    while True:
        scan_all_symbols()
        print(f"⏳ [TRACE] 等待 {SCAN_INTERVAL} 秒後進行下一輪...")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()
