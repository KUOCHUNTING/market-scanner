
import os
import requests

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

def test_polygon_api():
    if not POLYGON_API_KEY:
        print("❌ 沒有設定 POLYGON_API_KEY 環境變數")
        return

    url = f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&limit=1&apiKey={POLYGON_API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("✅ 成功連線 Polygon API")
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                print("✅ 成功取得股票資料範例：", data['results'][0])
            else:
                print("⚠️ 連線成功但沒有取得股票資料（可能資料為空）")
        else:
            print(f"❌ API 回傳錯誤狀態碼：{response.status_code}")
            print("回應內容：", response.text)
    except Exception as e:
        print(f"❌ 連線 Polygon API 失敗：{e}")

if __name__ == "__main__":
    test_polygon_api()
