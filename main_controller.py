import os
import time
import traceback
from datetime import datetime
from dotenv import load_dotenv

# ✅ 載入環境變數（最一開始執行）
load_dotenv()

# ✅ 載入功能模組
from modules.utils.market_time import is_us_market_open
from modules.config import stock_list
from modules.scan_market import scan_market
from modules.notify.check_exit_and_notify import schedule_exit_check

def main():
    print(f"🚀 啟動主控系統：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ✅ 檢查盤中時間
    if not is_us_market_open():
        print("[⏰ 跳過] 非美股盤中時間，掃描已跳過")
        return

    # ✅ 掃描市場並建倉
    try:
        scan_market(stock_list)
    except Exception as e:
        print(f"[錯誤] scan_market 失敗：{e}")
        traceback.print_exc()

    # ✅ 啟動出場排程
    try:
        schedule_exit_check()
    except Exception as e:
        print(f"[錯誤] schedule_exit_check 啟動失敗：{e}")
        traceback.print_exc()

    # ✅ 持續運行（未來可整合 websocket / 即時監控）
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
