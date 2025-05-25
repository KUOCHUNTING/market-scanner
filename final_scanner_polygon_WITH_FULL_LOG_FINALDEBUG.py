scan_index = 0
from concurrent.futures import ThreadPoolExecutor

import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD
# ===== 設定區 =====

def test_api_connection():
    test_url = f"https://api.polygon.io/v2/aggs/ticker/AAPL/prev?adjusted=true&apiKey={API_KEY}"
    try:
        r = requests.get(test_url, timeout=5)
        if r.status_code == 200:
            print("✅ Polygon API 連線成功")
        else:
            print(f"❌ Polygon API 回應錯誤碼：{r.status_code}")
    except Exception as e:
        print(f"❌ Polygon API 錯誤：{e}")

API_KEY = "sRnfK4Nqsa8xTHXC0gBeNE3uh11_Q4ln"
DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK"
SHEET_NAME = "交易紀錄總表"
TAB_NAME = "訊號紀錄"
CSV_FILE = "filtered_us_stocks_common_only.csv"

def load_symbols():
    df = pd.read_csv(CSV_FILE)
    return df["symbol"].dropna().unique().tolist()


from datetime import datetime, timedelta
import requests

def fetch_5min_bars(symbol, api_key):
    if '.' in symbol or '-' in symbol or any(suffix in symbol for suffix in ['.W', '.U', '.R']):
        print(f"⛔️ 跳過非普通股代碼：{symbol}")
        return []

    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=2)

    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/5/minute/"
        f"{start_date}/{end_date}?adjusted=true&limit=1000&apiKey={api_key}"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "results" in data and data["results"]:
            return data["results"]
        else:
            print(f"❌ 無資料：{symbol}")
            return []
    except Exception as e:
        print(f"⚠️ 抓取失敗 {symbol}：{str(e)}")
        return []
        print(f"❌ 程式啟動失敗：{e}")


# ========== 主流程入口 ==========
if __name__ == "__main__":
    print("▶️ 啟動主流程...")
    try:
        main()
    except Exception as e:
        print(f"❌ 主流程執行錯誤：{e}")
