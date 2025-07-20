# main_controller.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import time
import traceback
from dotenv import load_dotenv
from modules.utils.connect_to_gsheet import connect_to_gsheet
# === 設定與功能模組 ===
from modules.scan_market import scan_market
from modules.notify.check_exit_and_notify import schedule_exit_check
from modules.utils.market_time import get_market_phase  # ⏰ 盤前/盤中/盤後 判斷
from modules.data.loaders import load_stock_list  # ✅ 改用載入函數
# ✅ 載入 .env 環境變數
load_dotenv()
sheet_url = os.getenv("GSHEET_URL")
key_base64 = os.getenv("GCP_KEY_BASE64")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

print(f"✅ 目前讀取的 Discord Webhook：{WEBHOOK_URL}")

if not WEBHOOK_URL or "discord.com" not in WEBHOOK_URL:
    print("❌ Webhook URL 無效或未載入，請確認 .env 檔與 load_dotenv() 是否正確！")
    exit(1)
# ✅ 初始化 Google Sheets 工作表
sheet_entry = connect_to_gsheet(sheet_url, "建倉記錄", key_base64)

# ✅ 載入股票清單
stock_list = load_stock_list()

# ✅ 開始掃描，並傳入 Google Sheet 工作表
scan_market(stock_list, sheet_entry)

def main():
    print("🚀 啟動主控系統：scan_market + 出場排程")

    phase = get_market_phase()
    if phase != "open":
        print(f"⏰ 當前市場為 {phase} ➜ 暫停掃描與建倉")
        return

    from modules.controller.resonance_scan import run_sector_resonance
    import threading
    threading.Thread(target=run_sector_resonance, kwargs={"interval": 30}, daemon=True).start()

    # ✅ 修正這行
    try:
        scan_market(stock_list, sheet_entry)  # ✅ 改成傳兩個參數
    except Exception as e:
        print(f"[錯誤] scan_market 失敗：{e}")
        traceback.print_exc()

    try:
        schedule_exit_check()
    except Exception as e:
        print(f"[錯誤] schedule_exit_check 啟動失敗：{e}")
        traceback.print_exc()

    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
