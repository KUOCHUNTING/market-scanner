import requests
import pandas as pd
import os

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

def fetch_stock_bars(symbol, multiplier=5, timespan="minute", limit=300, adjusted=True):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/1"
    params = {
        "adjusted": str(adjusted).lower(),
        "sort": "desc",
        "limit": limit,
        "apiKey": POLYGON_API_KEY
    }
    response = requests.get(url, params=params, timeout=10)
    if response.status_code != 200:
        raise Exception(f"Polygon API 回傳錯誤：{response.status_code} - {response.text}")

    data = response.json().get("results", [])
    if not data:
        raise Exception("無法取得股價資料")

    df = pd.DataFrame(data)
    df["t"] = pd.to_datetime(df["t"], unit="ms")
    df = df.rename(columns={"t": "datetime", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    df = df.sort_values("datetime")
    df.set_index("datetime", inplace=True)
    return df
