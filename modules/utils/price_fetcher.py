import requests
import os
import datetime

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

def get_latest_price(symbol):
    url = f"https://api.polygon.io/v2/last/trade/{symbol}?apiKey={POLYGON_API_KEY}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        
        price = data['results']['p']
        timestamp_ns = data['results']['t']  # 時間是 nanosecond 格式
        ts = datetime.datetime.fromtimestamp(timestamp_ns / 1e9)  # 轉換為 datetime 物件

        print(f"✅ {symbol} 最新成交價：${price}｜時間：{ts}")
        return price  # 你可改回 return price, ts 如果要時間也回傳
    except Exception as e:
        print(f"❌ 抓取 {symbol} 最新成交價失敗：{e}")
        return None
