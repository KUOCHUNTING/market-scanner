# modules/utils/price_fetcher.py

import os
import requests
from datetime import datetime

def get_latest_price(symbol: str):
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("❌ POLYGON_API_KEY 未設定")
        return None, "N/A"

    url = f"https://api.polygon.io/v2/last/trade/{symbol}?apiKey={api_key}"

    try:
        response = requests.get(url)
        data = response.json()
        print(f"[DEBUG] {symbol} 回傳資料：{data}")

        if "results" not in data:
            print(f"❌ Symbol {symbol} 回傳結果無 'results' 欄位：{data}")
            return None, "N/A"

        price = data["results"]["p"]
        ts_ms = data["results"]["t"]
        ts_str = datetime.fromtimestamp(ts_ms / 1000).strftime("%H:%M:%S")

        return price, ts_str

    except Exception as e:
        print(f"❌ 抓取 {symbol} 價格錯誤：{e}")
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
