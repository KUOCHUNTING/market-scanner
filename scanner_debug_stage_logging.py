
import os
import time
import pandas as pd
from datetime import datetime

print("✅ [STAGE 1] 腳本開始執行", flush=True)

try:
    print("🔍 [STAGE 2] 嘗試讀取環境變數", flush=True)
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
    if not POLYGON_API_KEY:
        raise ValueError("❌ 未提供 POLYGON_API_KEY 環境變數")
    print(f"✅ [STAGE 2] API Key 已讀取（前 6 碼）：{POLYGON_API_KEY[:6]}***", flush=True)
except Exception as e:
    print(f"❌ [STAGE 2 ERROR] API KEY 錯誤：{e}", flush=True)

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

def main():
    print("✅ [STAGE 4] 進入主程式", flush=True)
    print(f"🕒 啟動時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

    if not symbols:
        print("⚠️ [STAGE 4] 無有效股票，主程式結束", flush=True)
        return

    for idx, symbol in enumerate(symbols[:5]):  # 減少測試數量
        try:
            print(f"🔁 掃描第 {idx+1} 檔：{symbol}", flush=True)
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ [STAGE 4 ERROR] {symbol} 掃描錯誤：{e}", flush=True)

    print("✅ [STAGE 4] 主程式完成", flush=True)

if __name__ == "__main__":
    try:
        print("✅ [STAGE 5] 執行 main()", flush=True)
        main()
    except Exception as e:
        print(f"❌ [STAGE 5 ERROR] 主程式崩潰：{e}", flush=True)
