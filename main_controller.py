import time
import traceback
from dotenv import load_dotenv

from modules.config import stock_list
from modules.scan_market import scan_market
from modules.notify.check_exit_and_notify import schedule_exit_check
from modules.utils.market_time import is_us_market_open  # ⏰ 盤中判斷
from modules.utils.market_time import is_us_market_open, get_market_phase

def main():
    print("🚀 啟動主控系統：scan_market + 出場排程")

    # ✅ 判斷市場階段（盤前 / 盤中 / 盤後）
    phase = get_market_phase()
    print(f"🕒 當前市場階段：{phase}")

    # ✅ 非盤中跳過掃描（可根據 phase 寫不同邏輯）
    if phase != "盤中":
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
