
# final_scanner_polygon_INTEGRATED_FULL_v1.py
# 整合版：Polygon API + 技術指標 + 共振條件 + 推播 + Sheets

import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

API_KEY = "sRnfK4Nqsa8xTHXC0gBeNE3uh11_Q4ln"
SYMBOLS = ["AAPL", "MSFT", "GOOGL"]

def fetch_5min_bars(symbol, days=2):
    end = int(datetime.now().timestamp()) * 1000
    start = int((datetime.now() - timedelta(days=days)).timestamp()) * 1000
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/5/minute/{start}/{end}?adjusted=true&sort=desc&limit=1000&apiKey={API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json().get("results", [])
            if not data:
                return None
            df = pd.DataFrame(data)
            df["t"] = pd.to_datetime(df["t"], unit="ms")
            df.set_index("t", inplace=True)
            df = df.sort_index()
            df.rename(columns={"c": "close", "h": "high", "l": "low", "o": "open", "v": "volume"}, inplace=True)
            return df[["open", "high", "low", "close", "volume"]]
        else:
            print(f"[{symbol}] 回應碼錯誤：{r.status_code}")
            return None
    except Exception as e:
        print(f"[{symbol}] 擷取失敗：{str(e)}")
        return None

def calculate_indicators(df):
    df["rsi"] = compute_rsi(df["close"])
    df["macd"], df["macd_signal"] = compute_macd(df["close"])
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / (avg_loss + 1e-6)
    return 100 - (100 / (1 + rs))

def compute_macd(series, short=12, long=26, signal=9):
    short_ema = series.ewm(span=short, adjust=False).mean()
    long_ema = series.ewm(span=long, adjust=False).mean()
    macd = short_ema - long_ema
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def main():
    print("▶️ 啟動：整合版掃描器（Polygon API + 技術分析）")
    for symbol in SYMBOLS:
        print(f"🔍 掃描：{symbol}")
        df = fetch_5min_bars(symbol)
        if df is None or len(df) < 50:
            print(f"⚠️ {symbol} 資料不足或擷取失敗")
            continue
        df = calculate_indicators(df)

        rsi_now = df["rsi"].iloc[-1]
        macd_now = df["macd"].iloc[-1]
        macd_sig = df["macd_signal"].iloc[-1]

        print(f"📊 {symbol} RSI={rsi_now:.1f}, MACD差值={macd_now - macd_sig:.2f}")

        if rsi_now < 30 and macd_now > macd_sig:
            print(f"🚨 [{symbol}] 出現技術性多頭訊號（RSI低檔＋MACD金叉）")
        time.sleep(1)

if __name__ == "__main__":
    main()
