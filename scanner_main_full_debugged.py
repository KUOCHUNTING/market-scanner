
import os
import time
import pandas as pd
import requests
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import MACD

print("✅ [STAGE 1] 腳本開始執行", flush=True)

try:
    print("🔍 [STAGE 2] 嘗試讀取環境變數", flush=True)
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
    if not POLYGON_API_KEY:
        raise ValueError("❌ 未提供 POLYGON_API_KEY 環境變數")
    print(f"✅ [STAGE 2] API Key 已讀取（前 6 碼）：{POLYGON_API_KEY[:6]}***", flush=True)
except Exception as e:
    print(f"❌ [STAGE 2 ERROR] API KEY 錯誤：{e}", flush=True)
    POLYGON_API_KEY = None

try:
    print("🔍 [STAGE 3] 嘗試讀取股票清單 CSV...", flush=True)
    df = pd.read_csv("filtered_sp500_list.csv")
    if df.empty:
        raise ValueError("⚠️ 股票清單為空")
    symbols = df["symbol"].tolist()
    print(f"✅ [STAGE 3] 成功讀取 {len(symbols)} 檔股票", flush=True)
except Exception as e:
    print(f"❌ [STAGE 3 ERROR] 無法讀取股票清單：{e}", flush=True)
    symbols = []

def fetch_data(symbol):
    try:
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/minute/2024-01-01/2024-01-02?adjusted=true&limit=50&apiKey={POLYGON_API_KEY}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"⚠️ [API] {symbol} 回應異常：{r.status_code}", flush=True)
            return None
        # 模擬假資料
        return pd.DataFrame({
            "Close": [10 + i * 0.1 for i in range(60)],
            "Volume": [1000000 + i * 1000 for i in range(60)]
        })
    except Exception as e:
        print(f"❌ [API ERROR] {symbol} 抓資料失敗：{e}", flush=True)
        return None

def process_symbol(symbol, idx):
    try:
        print(f"🔁 掃描第 {idx+1} 檔：{symbol}", flush=True)
        df = fetch_data(symbol)
        if df is None or df.empty:
            print(f"⚠️ {symbol} 無資料，略過", flush=True)
            return

        close = df["Close"]
        rsi = RSIIndicator(close=close, window=14).rsi()
        macd = MACD(close=close, window_fast=12, window_slow=26, window_sign=9)
        if rsi.iloc[-1] < 30 and macd.macd().iloc[-1] > macd.macd_signal().iloc[-1]:
            print(f"📈 多頭訊號：{symbol}", flush=True)
        time.sleep(0.2)
    except Exception as e:
        print(f"❌ [技術指標錯誤] {symbol}：{e}", flush=True)

def main():
    print("✅ [STAGE 4] 進入主程式", flush=True)
    print("🕒 啟動時間：", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), flush=True)

    if not symbols:
        print("⚠️ [STAGE 4] 無有效股票，結束執行", flush=True)
        return

    for idx, symbol in enumerate(symbols[:10]):
        process_symbol(symbol, idx)

    print("✅ [STAGE 4] 掃描結束", flush=True)

if __name__ == "__main__":
    try:
        print("✅ [STAGE 5] 執行 main()", flush=True)
        main()
    except Exception as e:
        print(f"❌ [STAGE 5 ERROR] 主程式錯誤：{e}", flush=True)
