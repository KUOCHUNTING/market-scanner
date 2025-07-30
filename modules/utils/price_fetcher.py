# modules/utils/price_fetcher.py

import requests
import os
import datetime

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

def get_latest_price(symbol):
    """
    從 Polygon 抓取即時成交價與時間戳記
    回傳: (價格: float, 時間: datetime) 或 (None, None)
    """
    url = f"https://api.polygon.io/v2/last/trade/{symbol}?apiKey={POLYGON_API_KEY}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()

        price = data['results']['p']
        timestamp_ns = data['results']['t']
        ts = datetime.datetime.fromtimestamp(timestamp_ns / 1e9)

        return price, ts
    except Exception as e:
        print(f"❌ 抓取 {symbol} 最新成交價失敗：{e}")
        return None, None
