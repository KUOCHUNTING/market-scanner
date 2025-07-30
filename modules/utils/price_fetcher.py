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
