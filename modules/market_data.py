# modules/market_data.py

def get_latest_price(symbol):
    """
    回傳最新股價，可根據你的資料來源修改邏輯
    """
    import requests
    from modules.config import POLYGON_API_KEY

    url = f"https://api.polygon.io/v1/last/stocks/{symbol}?apiKey={POLYGON_API_KEY}"
    try:
        res = requests.get(url)
        data = res.json()
        return data["last"]["price"]
    except Exception as e:
        print(f"[錯誤] 取得 {symbol} 最新價格失敗：{e}")
        return None
