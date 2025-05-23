
import pandas as pd
import os
import requests
from ta.momentum import RSIIndicator
from ta.trend import MACD

# Polygon API 抓資料
def fetch_stock_bars(symbol, multiplier=5, timespan="minute", limit=300, adjusted=True):
    api_key = os.getenv("POLYGON_API_KEY")
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/1"
    params = {
        "adjusted": str(adjusted).lower(),
        "sort": "desc",
        "limit": limit,
        "apiKey": api_key
    }
    print(f"🔍 嘗試抓取資料：{symbol}...")
    response = requests.get(url, params=params, timeout=10)
    if response.status_code != 200:
        print(f"❌ API 回傳錯誤：{response.status_code} - {response.text}")
        return None
    data = response.json().get("results", [])
    if not data:
        print("⚠️ 無資料")
        return None
    df = pd.DataFrame(data)
    df["t"] = pd.to_datetime(df["t"], unit="ms")
    df = df.rename(columns={"t": "datetime", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    df = df.sort_values("datetime")
    df.set_index("datetime", inplace=True)
    return df

# 主程式
def main():
    df = fetch_stock_bars("AAPL")
    if df is None or df.empty:
        print("❌ 無法取得股價資料")
        return

    print(f"✅ 成功取得資料，共 {len(df)} 筆")
    close = df["close"]

    try:
        df["RSI"] = RSIIndicator(close=close, window=14).rsi()
        macd_calc = MACD(close=close)
        df["MACD"] = macd_calc.macd()
        df["MACD_signal"] = macd_calc.macd_signal()
        print("✅ 技術指標計算成功")
        print(df[["close", "RSI", "MACD", "MACD_signal"]].tail())
    except Exception as e:
        print(f"❌ 技術分析錯誤：{e}")

if __name__ == "__main__":
    print("🚀 啟動極簡測試版腳本...")
    main()
