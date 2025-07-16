import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

# ✅ 讀取 Polygon API 金鑰
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY") or "your-api-key"

# ✅ 抓取 Polygon 歷史價格資料（回傳 DataFrame）
def fetch_polygon_ohlc(symbol, days=30):
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days * 2)  # 多抓一點保險

    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 5000,
        "apiKey": POLYGON_API_KEY
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise ValueError(f"Polygon API 回應錯誤：{response.text}")

    data = response.json().get("results", [])
    if not data or len(data) < days:
        raise ValueError(f"{symbol} 資料不足（僅取得 {len(data)} 筆）")

    df = pd.DataFrame(data)
    df["t"] = pd.to_datetime(df["t"], unit="ms")
    df.set_index("t", inplace=True)
    df.rename(columns={"c": "close", "v": "volume"}, inplace=True)
    return df[["close", "volume"]].tail(days)

# ✅ 計算 RSI（14）
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ✅ 計算 OBV
def calculate_obv(close, volume):
    obv = [0]
    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            obv.append(obv[-1] + volume[i])
        elif close[i] < close[i - 1]:
            obv.append(obv[-1] - volume[i])
        else:
            obv.append(obv[-1])
    return pd.Series(obv, index=close.index)

# ✅ 主邏輯：板塊共振偵測
def detect_sector_resonance(etf_symbol, stock_list, min_confirmed=3):
    try:
        # ✅ 抓 ETF 資料
        df_etf = fetch_polygon_ohlc(etf_symbol)
        rsi_etf = calculate_rsi(df_etf["close"])
        obv_etf = calculate_obv(df_etf["close"].values, df_etf["volume"].values)

        # ✅ 判斷 ETF 是否轉強（RSI > 50 且 OBV 上升）
        etf_rsi_value = rsi_etf.iloc[-1]
        etf_obv_up = obv_etf.iloc[-1] > obv_etf.iloc[-5]
        etf_is_strong = (etf_rsi_value > 50) and etf_obv_up

        if not etf_is_strong:
            return False, []

        # ✅ 掃描成分股是否共振
        resonant_stocks = []
        for symbol in stock_list:
            try:
                df = fetch_polygon_ohlc(symbol)
                rsi = calculate_rsi(df["close"])
                obv = calculate_obv(df["close"].values, df["volume"].values)
                rsi_val = rsi.iloc[-1]
                obv_up = obv.iloc[-1] > obv.iloc[-5]
                if rsi_val > 50 and obv_up:
                    resonant_stocks.append(symbol)
            except Exception as e:
                print(f"⚠️ {symbol} 資料錯誤：{e}")

        return len(resonant_stocks) >= min_confirmed, resonant_stocks

    except Exception as e:
        print(f"❌ 共振檢查失敗：{e}")
        return False, []
