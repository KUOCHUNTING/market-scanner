import time
from modules.config import stock_list
from modules.scan_market import scan_market
from modules.notify.check_exit_and_notify import schedule_exit_check  # ← ✅ 加這行
from dotenv import load_dotenv
load_dotenv()

if __name__ == "__main__":
    print("🚀 啟動主控系統：scan_market + 出場排程")

    # ✅ 執行市場掃描與建倉
    try:
        scan_market(stock_list)  # ← 傳入股票清單
    except Exception as e:
        print(f"[錯誤] scan_market 失敗：{e}")

    # ✅ 啟動排程出場檢查
    try:
        schedule_exit_check()
    except Exception as e:
        print(f"[錯誤] schedule_exit_check 啟動失敗：{e}")

    # ✅ 維持主程式執行
    while True:
        time.sleep(60)
