import time
import traceback
from dotenv import load_dotenv

from modules.config import stock_list
from modules.scan_market import scan_market
from modules.notify.check_exit_and_notify import schedule_exit_check
from modules.utils.market_time import is_us_market_open  # ⏰ 盤中判斷

# ✅ 載入 .env 環境變數
load_dotenv()

def main():
    print("🚀 啟動主控系統：scan_market + 出場排程")

    # ✅ 若非盤中 ➜ 直接跳出
    if not is_us_market_open():
        print("⏰ 非美股盤中時間 ➜ 跳過掃描")
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

    # ✅ 持續執行主程式
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
