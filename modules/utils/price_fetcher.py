# modules/utils/price_fetcher.py

import requests
import os

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")  # 從 .env 載入

def get_latest_price(symbol):
    """
    從 Polygon.io 抓取最新成交價（Last Trade Price）
    """
    url = f"https://api.polygon.io/v2/last/trade/{symbol}?apiKey={POLYGON_API_KEY}"
    try:
        res = requests.get(url)
        data = res.json()
        return data['results']['p']
    except Exception as e:
        print(f"❌ 抓取 {symbol} 最新成交價失敗：{e}")
        return None
