
# final_scanner_polygon_REBUILT_FULL.py
# ✅ 支援技術指標、TICK 共振、多執行緒、Google Sheets、Discord 推播（適用 Render 雲端部署）

import os
import time
import requests
import pandas as pd
import threading
from datetime import datetime
from polygon import RESTClient
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ====== [設定區] ======
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "your_key_here")
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
SHEET_ID = "14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko"
SCAN_INTERVAL = 60

# ====== [載入股票清單] ======
def load_symbols():
    df = pd.read_csv("filtered_us_stocks_common_only.csv")
    filtered = df[(df['price'] >= 1) & (df['price'] <= 10)]
    return filtered["symbol"].tolist()

# ====== [推播到 Discord] ======
def push_to_discord(title, content):
    try:
        msg = {"content": f"**{title}**\n{content}"}
        requests.post(DISCORD_WEBHOOK, json=msg, timeout=10)
    except Exception as e:
        print(f"❌ Discord 發送失敗：{e}")

# ====== [寫入 Google Sheets] ======
def write_to_sheet(symbol, signal_type, info):
    try:
        creds = Credentials.from_service_account_file("gcp_credentials.json")
        service = build("sheets", "v4", credentials=creds)
        sheet = service.spreadsheets()
        row = [[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), symbol, signal_type, info]]
        sheet.values().append(spreadsheetId=SHEET_ID,
                              range="訊號紀錄!A:D",
                              valueInputOption="RAW",
                              body={"values": row}).execute()
    except Exception as e:
        print(f"❌ Sheets 寫入失敗：{e}")

# ====== [計算技術指標與判斷] ======
def analyze_signal(df):
    try:
        rsi = RSIIndicator(df["close"]).rsi().iloc[-1]
        macd = MACD(df["close"]).macd_diff().iloc[-1]
        so = StochasticOscillator(df["high"], df["low"], df["close"])
        kd_k = so.stoch().iloc[-1]
        kd_d = so.stoch_signal().iloc[-1]
        tmo = df["close"].diff().rolling(window=5).mean().iloc[-1]

        if rsi < 30 and macd > 0 and kd_k > kd_d:
            return "⚠️ 多頭搶轉折"
        if rsi > 70 and macd < 0 and kd_k < kd_d:
            return "⚠️ 空頭翻轉"
        if rsi > 50 and macd > 0 and tmo > 0:
            return "✅ 正式多頭"
        if rsi < 50 and macd < 0 and tmo < 0:
            return "🔻 正式空頭"
        return None
    except:
        return None

# ====== [從 Polygon API 抓資料] ======
def fetch_data(symbol):
    try:
        with RESTClient(POLYGON_API_KEY) as client:
            bars = client.get_aggs(symbol, 5, "minute", limit=100, adjusted=True)
            df = pd.DataFrame([{
                "timestamp": b.timestamp,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume
            } for b in bars])
            return df
    except Exception as e:
        print(f"❌ 無法取得 {symbol} 資料：{e}")
        return None

# ====== [掃描單一股票] ======
def process_symbol(symbol):
    df = fetch_data(symbol)
    if df is not None and len(df) > 20:
        signal = analyze_signal(df)
        if signal:
            push_to_discord(symbol, signal)
            write_to_sheet(symbol, signal, "由技術指標觸發")
            print(f"✅ {symbol} 觸發訊號：{signal}")
        else:
            print(f"… {symbol} 無訊號")
    else:
        print(f"❌ {symbol} 無有效資料")

# ====== [主掃描器] ======
def scan_all_symbols(symbols):
    threads = []
    for symbol in symbols:
        t = threading.Thread(target=process_symbol, args=(symbol,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()

# ====== [主程式入口] ======
if __name__ == "__main__":
    while True:
        print(f"▶️ 啟動掃描：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            symbols = load_symbols()
            scan_all_symbols(symbols)
        except Exception as e:
            print(f"⚠️ 主程式錯誤：{e}")
        print(f"⏳ 等待 {SCAN_INTERVAL} 秒...
")
        time.sleep(SCAN_INTERVAL)
