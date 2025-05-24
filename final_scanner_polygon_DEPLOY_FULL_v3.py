
# final_scanner_polygon_DEPLOY_FULL_v3.py
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import threading

API_KEY = "sRnfK4Nqsa8xTHXC0gBeNE3uh11_Q4ln"

def load_symbols(csv_path="filtered_us_stocks_common_only.csv"):
    try:
        df = pd.read_csv(csv_path)
        return df["symbol"].dropna().unique().tolist()
    except:
        return ["AAPL", "MSFT"]

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
            return None
    except:
        return None

def compute_indicators(df):
    df["rsi"] = compute_rsi(df["close"])
    df["macd"], df["macd_signal"] = compute_macd(df["close"])
    df["atr"] = compute_atr(df)
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

def compute_atr(df, period=14):
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def scan_symbol(symbol):
    df = fetch_5min_bars(symbol)
    if df is None or len(df) < 50:
        return

    df = compute_indicators(df)
    latest = df.iloc[-1]
    rsi, macd_diff, atr = latest["rsi"], latest["macd"] - latest["macd_signal"], latest["atr"]

    if rsi < 30 and macd_diff > 0 and atr > 0.5:
        print(f"✅ [正式進場訊號] {symbol} RSI={rsi:.1f}, MACD差={macd_diff:.2f}, ATR={atr:.2f}")
    elif rsi < 35:
        print(f"🟡 [預警] {symbol} RSI={rsi:.1f}, MACD差={macd_diff:.2f}")
    else:
        print(f"📉 {symbol} 無訊號")

def main():
    print(f"▶️ 啟動全市場掃描（{datetime.now()}）")
    symbols = load_symbols("filtered_us_stocks_common_only.csv")
    threads = []

    for symbol in symbols:
        t = threading.Thread(target=scan_symbol, args=(symbol,))
        threads.append(t)
        t.start()
        time.sleep(0.2)  # 控制頻率避免被限速

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
