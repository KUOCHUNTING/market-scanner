import os
from dotenv import load_dotenv
from polygon import RESTClient
from datetime import datetime, timedelta

# 載入 .env 環境變數
load_dotenv()
API_KEY = os.getenv("POLYGON_API_KEY")

print(f"[DEBUG] API KEY：{API_KEY}")

# 如果沒有讀到 API Key，直接報錯
if not API_KEY:
    print("[ERROR] 沒有成功讀取 API KEY，請檢查 .env 檔案或 Render 環境變數設定")
    exit()

# 初始化 Polygon API Client
try:
    client = RESTClient(api_key=API_KEY)
    now = datetime.now()
    start = (now - timedelta(minutes=30)).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")

    # 測試抓取 AAPL 的 5 分鐘 K 線資料
    aggs = client.get_aggs(
        ticker="AAPL",
        multiplier=5,
        timespan="minute",
        from_=start,
        to=end,
        limit=5
    )

    if aggs:
        print("[SUCCESS] 成功連接 Polygon API，資料如下：")
        for bar in aggs:
            print(f"- {bar['t']} / Close: {bar['c']}")
    else:
        print("[WARNING] 成功連接 API，但無資料（可能是假日或非交易時間）")

except Exception as e:
    print(f"[ERROR] API 測試失敗：{e}")
