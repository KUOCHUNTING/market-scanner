
import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from polygon.rest import RESTClient
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

POLYGON_API_KEY = "sRnfK4Nqsa8xTHXC0gBeNE3uh11_Q4ln"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
SHEET_ID = "14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko"
SCAN_INTERVAL = 60

def send_discord_message(title, message):
    try:
        data = {
            "content": f"**{title}**\n{message}"
        }
        response = requests.post(DISCORD_WEBHOOK, json=data)
        if response.status_code != 204:
            print(f"[ERROR] Discord 發送失敗：{response.text}")
    except Exception as e:
        print(f"[ERROR] Discord 發送失敗：{e}")

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
        print(f"[ERROR] {symbol} 技術指標錯誤：{e}")
        return None

def fetch_5min_bars(symbol):
    try:
        client = RESTClient(POLYGON_API_KEY)
        end = datetime.utcnow()
        start = end - timedelta(days=2)
        aggs = client.get_aggs(symbol, 5, "minute", start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        bars = [{"timestamp": a.timestamp, "open": a.open, "high": a.high, "low": a.low, "close": a.close, "volume": a.volume} for a in aggs]
        return pd.DataFrame(bars)
    except Exception as e:
        print(f"[ERROR] 無法取得 {symbol} 資料：{e}")
        return None

def scan_all_symbols():
    print("[INFO] 開始載入股票清單...")
    df = pd.read_csv("filtered_us_stocks_common_only.csv")
    if 'symbol' not in df.columns:
        print("[ERROR] 找不到 symbol 欄位")
        return
    symbols = df['symbol'].tolist()
    print(f"[INFO] 共載入 {len(symbols)} 檔股票，開始掃描...")

    for i, symbol in enumerate(symbols):
        print(f"[TRACE] 掃描第 {i+1} 檔：{symbol}")
        df_bars = fetch_5min_bars(symbol)
        if df_bars is None or df_bars.empty:
            continue
        signal = analyze_signal(symbol, df_bars)
        if signal:
            print(f"[ALERT] {symbol} 觸發訊號：{signal}")
            send_discord_message(f"{symbol} 訊號出現", f"{signal}，請留意走勢")
        else:
            print(f"[TRACE] {symbol} 無訊號")

def main():
    print("✅ [INFO] 腳本啟動成功，進入主流程...")
    while True:
        print(f"▶️ [TRACE] 新一輪掃描開始於 {datetime.now().strftime('%H:%M:%S')}...")
        scan_all_symbols()
        print(f"⏳ [TRACE] 等待 {SCAN_INTERVAL} 秒後進行下一輪...
")
        time.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    main()
