import requests
from modules.config import POLYGON_API_KEY
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ✅ 抓取最新收盤價（支援單檔或多檔）
def fetch_latest_price(symbols, api_key=POLYGON_API_KEY):
    """
    支援單一股票或多股票最新收盤價查詢
    回傳：
    - 單檔：float（收盤價）
    - 多檔：dict {symbol: price}
    """
    # === 單一股票 ===
    if isinstance(symbols, str):
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbols}/prev?adjusted=true&apiKey={api_key}"
        try:
            response = requests.get(url)
            data = response.json()
            result = data['results'][0]['c'] if 'results' in data and data['results'] else None
            return result
        except Exception as e:
            print(f"[錯誤] 無法取得 {symbols} 最新價格：{e}")
            return None

    # === 多檔股票 ===
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
                print(f"[錯誤] 無法取得 {symbol} 最新價格：{e}")
                prices[symbol] = None
        return prices

    else:
        raise TypeError("請傳入股票代碼（str）或股票清單（list）")
