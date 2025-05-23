
import pandas as pd
import os
import requests
from ta.momentum import RSIIndicator
from ta.trend import MACD

# Polygon API 抓資料（使用合法的日期區間）
def fetch_stock_bars(symbol, multiplier=5, timespan="minute", from_date="2024-05-01", to_date="2024-05-23", adjusted=True):
    api_key = os.getenv("POLYGON_API_KEY")
    print(f"🔐 目前使用的 API KEY：{api_key}")
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
    params = {
        "adjusted": str(adjusted).lower(),
        "sort": "asc",
        "apiKey": api_key
    }
    print(f"🌐 發送請求網址：{url}?adjusted={params['adjusted']}&sort={params['sort']}&apiKey={params['apiKey']}")
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
    print("🚀 啟動修正版測試腳本（正確網址格式）...")
    main()
