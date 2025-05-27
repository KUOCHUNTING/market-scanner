import os
import time
import pandas as pd
from datetime import datetime, timedelta
from pytz import timezone
from polygon import RESTClient
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD

API_KEY = os.getenv("POLYGON_API_KEY") or "YOUR_API_KEY"
SCAN_INTERVAL = 60

import requests
from datetime import datetime, timedelta
from pytz import timezone
import pandas as pd

API_KEY = "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"

def fetch_stock_data(symbol):
    try:
        est = timezone("US/Eastern")
        end = datetime.now(est)
        start = end - timedelta(minutes=35)
        date_str = end.strftime("%Y-%m-%d")

        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/5/minute/{date_str}/{date_str}"
        params = {
            "adjusted": "true",
            "include_pre_post": "true",  # ✅ 支援盤前盤後
            "sort": "asc",
            "limit": 5000,
            "apiKey": YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"[ERROR] 無法獲取 {symbol} 資料：{response.status_code} - {response.text}")
            return None

        data = response.json().get("results", [])
        if not data:
            print(f"[WARNING] 無資料 {symbol}")
            return None

        df = pd.DataFrame([{
            "timestamp": pd.to_datetime(bar["t"], unit='ms'),
            "open": bar["o"],
            "high": bar["h"],
            "low": bar["l"],
            "close": bar["c"],
            "volume": bar["v"]
        } for bar in data])

        df.set_index("timestamp", inplace=True)
        return df

    except Exception as e:
        print(f"[ERROR] 抓取資料失敗 {symbol}: {e}")
        return None

def analyze_signal(symbol, df):
    try:
        close = df["close"]
        if len(close) < 35:
            return None
        rsi = RSIIndicator(close).rsi().iloc[-1]
        macd = MACD(close).macd_diff().iloc[-1]
        kd = StochasticOscillator(high=df["high"], low=df["low"], close=close)
        k = kd.stoch().iloc[-1]
        d = kd.stoch_signal().iloc[-1]

        if rsi < 30 and macd > 0 and k > d:
            return "多頭訊號"
        elif rsi > 70 and macd < 0 and k < d:
            return "空頭訊號"
        return None
    except Exception as e:
        print(f"[ERROR] 訊號分析錯誤 {symbol}: {e}")
        return None

import time

SCAN_INTERVAL = 60  # ✅ 一定要定義

def main():
    symbols = ["AAPL"]
    for symbol in symbols:
        df = fetch_stock_data(symbol)
        if df is not None:
            signal = analyze_signal(symbol, df)
            if signal:
                print(f"[SIGNAL] {symbol}: {signal}")
        time.sleep(1)

if __name__ == "__main__":
    print("=== ✅ 開始掃描 (無 include_pre_post) ===")
    while True:
        try:
            main()
        except Exception as e:
            print(f"[ERROR] 主程式錯誤：{e}")
        print(f"⏳ 等待 {SCAN_INTERVAL} 秒...")
        time.sleep(SCAN_INTERVAL)
