# main_controller.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import time
import traceback
from dotenv import load_dotenv

# === 設定與功能模組 ===
from modules.scan_market import scan_market
from modules.notify.check_exit_and_notify import schedule_exit_check
from modules.utils.market_time import get_market_phase  # ⏰ 盤前/盤中/盤後 判斷
from modules.data.loaders import load_stock_list  # ✅ 改用載入函數
stock_list = load_stock_list()
# ✅ 載入 .env 環境變數
load_dotenv()

print("✅ GCP_KEY_BASE64:", os.getenv("GCP_KEY_BASE64"))

def main():
    print("🚀 啟動主控系統：scan_market + 出場排程")

    # ✅ 市場時段判斷
    phase = get_market_phase()
    if phase != "open":
        print(f"⏰ 當前市場為 {phase} ➜ 暫停掃描與建倉")
        return

    from modules.controller.resonance_scan import run_sector_resonance
    import threading
    threading.Thread(target=run_sector_resonance, kwargs={"interval": 30}, daemon=True).start()

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
