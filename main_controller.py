import time
import traceback
from dotenv import load_dotenv

# ✅ 載入設定與功能模組
from modules.config import stock_list
from modules.scan_market import scan_market
from modules.notify.check_exit_and_notify import schedule_exit_check

# ✅ 載入環境變數
load_dotenv()

def main():
    print("🚀 啟動主控系統：scan_market + 出場排程")

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

    # ✅ 維持主程式執行
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
