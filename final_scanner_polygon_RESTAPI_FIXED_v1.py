
import requests
import time

API_KEY = "sRnfK4Nqsa8xTHXC0gBeNE3uh11_Q4ln"
TICKERS = ["AAPL", "MSFT", "GOOGL"]  # 可替換為你自己的清單

def fetch_prev_close(symbol):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"[成功] {symbol}: 收盤價 = {data['results'][0]['c']}")
        else:
            print(f"[失敗] {symbol} 回應碼：{response.status_code}，訊息：{response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[錯誤] {symbol} 請求錯誤：{str(e)}")
    except Exception as e:
        print(f"[例外] {symbol} 資料處理錯誤：{str(e)}")

def main():
    print("▶️ 啟動 Polygon 抓取測試（REST API）")
    for symbol in TICKERS:
        print(f"🔍 正在處理：{symbol}")
        fetch_prev_close(symbol)
        time.sleep(1)  # 避免太快觸發限速

if __name__ == "__main__":
    main()
