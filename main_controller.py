from modules import *
import threading
import time
from modules import stock_list, scan_market
scan_market()
schedule_exit_check()

if __name__ == "__main__":
    print("🚀 啟動主控系統：scan_market + 出場排程")

    # ✅ 執行市場掃描與建倉
    try:
        scan_market()
    except Exception as e:
        print(f"[錯誤] scan_market 失敗：{e}")

    # ✅ 啟動排程出場檢查
    try:
        schedule_exit_check()
    except Exception as e:
        print(f"[錯誤] schedule_exit_check 啟動失敗：{e}")

    # ✅ 防止主程式結束（維持執行狀態）
    while True:
        time.sleep(60)
