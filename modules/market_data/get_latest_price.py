import requests
from modules.config import POLYGON_API_KEY

def get_latest_price(symbol):
    """
    使用 Polygon API 抓取最新報價
    """
    try:
        url = f"https://api.polygon.io/v2/last/trade/{symbol}?apiKey={POLYGON_API_KEY}"
        resp = requests.get(url)
        data = resp.json()

        if "results" in data and "p" in data["results"]:
            return data["results"]["p"]
        else:
            print(f"[❌ 無結果] {symbol} ➜ {data}")
            return None
    except Exception as e:
        print(f"[錯誤] 抓取 {symbol} 最新價格失敗 ➜ {e}")
        return None