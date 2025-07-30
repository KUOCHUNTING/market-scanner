# modules/utils/price_fetcher.py

import os
import requests
from datetime import datetime

# modules/utils/price_fetcher.py

import os
import requests
from datetime import datetime
import yfinance as yf

def get_latest_price(symbol: str):
    api_key = os.getenv("POLYGON_API_KEY")
    url = f"https://api.polygon.io/v2/last/trade/{symbol}?apiKey={api_key}"

    try:
        response = requests.get(url)
        data = response.json()

        if "results" not in data:
            print(f"⚠️ Polygon 無法取得 {symbol}：{data.get('message', '未知錯誤')} ➜ 改用 yfinance")
            raise Exception("Polygon 降級")

        price = data["results"]["p"]
        ts_ms = data["results"]["t"]
        ts_str = datetime.fromtimestamp(ts_ms / 1000).strftime("%H:%M:%S")
        return price, ts_str

    except Exception as e:
        # 🟡 改用 yfinance 延遲價格
        try:
            ticker = yf.Ticker(symbol)
            price = ticker.info.get("regularMarketPrice")
            ts_str = "延遲"
            print(f"✅ yfinance 補上 {symbol} 價格：{price}")
            return price, ts_str
        except Exception as e2:
            print(f"❌ yfinance 抓不到 {symbol} 價格：{e2}")
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
