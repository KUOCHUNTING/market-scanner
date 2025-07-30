# modules/utils/price_fetcher.py

import os
import requests

def get_latest_price(symbol: str) -> float:
    """
    從 Polygon API 取得即時價格
    """
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("❌ POLYGON_API_KEY 未設定")
        return None

    url = f"https://api.polygon.io/v2/last/trade/{symbol}?apiKey={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        return data["results"]["p"]
    except Exception as e:
        print(f"[❌] 抓取 {symbol} 即時價錯誤：{e}")
        return None

def get_latest_price_with_time(symbol: str):
    """
    回傳 (價格, 時間字串)，如 ("345.60", "15:42:31")
    """
    api_key = os.getenv("POLYGON_API_KEY")
    url = f"https://api.polygon.io/v2/last/trade/{symbol}?apiKey={api_key}"

    try:
        response = requests.get(url)
        data = response.json()
        price = data["results"]["p"]
        timestamp_ms = data["results"]["t"]  # UNIX timestamp in milliseconds
        from datetime import datetime
        time_str = datetime.fromtimestamp(timestamp_ms / 1000).strftime("%H:%M:%S")
        return price, time_str
    except Exception as e:
        print(f"[❌] 無法取得 {symbol} 即時價與時間：{e}")
        return None, "N/A"
