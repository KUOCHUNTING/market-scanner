
import os
import requests
import datetime

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

def fetch_stock_bars(symbol, interval="5", days=5):
    """
    從 Polygon 抓取指定股票的歷史 K 線資料。
    :param symbol: 股票代碼，例如 AAPL
    :param interval: K 線間隔，支援 1、5、15、30、day、week、month
    :param days: 抓過去幾天的資料
    :return: JSON 資料（list of bars），或 None（若失敗）
    """
    if not POLYGON_API_KEY:
        print("❌ 未設定 POLYGON_API_KEY")
        return None

    end_date = datetime.datetime.now().date()
    start_date = end_date - datetime.timedelta(days=days)

    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{interval}/minute/"
        f"{start_date}/{end_date}?adjusted=true&sort=asc&limit=5000&apiKey={POLYGON_API_KEY}"
    )

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and data['results']:
                return data['results']
            else:
                print(f"⚠️ {symbol} 沒有返回任何 K 線資料")
                return None
        else:
            print(f"❌ {symbol} API 錯誤回應：{response.status_code}")
            return None
    except Exception as e:
        print(f"❌ {symbol} 抓取過程出錯：{e}")
        return None
