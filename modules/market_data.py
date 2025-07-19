# modules/market_data.py

import requests
from modules.config import POLYGON_API_KEY

def get_latest_price(symbols, api_key=POLYGON_API_KEY):
    """
    支援單一或多檔股票最新收盤價查詢
    回傳：
    - symbols 為 str 時：float（單一收盤價）
    - symbols 為 list 時：dict {symbol: price}
    """
    if isinstance(symbols, str):
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbols}/prev?adjusted=true&apiKey={api_key}"
        try:
            response = requests.get(url)
            data = response.json()
            return data['results'][0]['c'] if 'results' in data and data['results'] else None
        except Exception as e:
            print(f"[❌錯誤] 無法取得 {symbols} 最新價格：{e}")
            return None

    elif isinstance(symbols, list):
        prices = {}
        for symbol in symbols:
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={api_key}"
            try:
                response = requests.get(url)
                data = response.json()
                close_price = data['results'][0]['c'] if 'results' in data and data['results'] else None
                prices[symbol] = close_price
            except Exception as e:
                print(f"[❌錯誤] 無法取得 {symbol} 最新價格：{e}")
                prices[symbol] = None
        return prices

    else:
        raise TypeError("請傳入股票代碼（str）或股票清單（list）")
