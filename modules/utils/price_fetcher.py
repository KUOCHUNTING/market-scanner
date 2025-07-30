# modules/utils/price_fetcher.py

import os
import requests
from datetime import datetime

def get_latest_price(symbol: str):
    """
    回傳 (價格, 時間字串)，即使錯誤也會回傳 (None, "N/A")
    """
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("❌ POLYGON_API_KEY 未設定")
        return None, "N/A"

    url = f"https://api.polygon.io/v2/last/trade/{symbol}?apiKey={api_key}"

    try:
        response = requests.get(url)
        data = response.json()

        price = data["results"]["p"]
        ts_ms = data["results"]["t"]
        ts_str = datetime.fromtimestamp(ts_ms / 1000).strftime("%H:%M:%S")

        return price, ts_str
    except Exception as e:
        print(f"❌ get_latest_price() 抓取失敗：{symbol} ➜ {e}")
        return None, "N/A"

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
