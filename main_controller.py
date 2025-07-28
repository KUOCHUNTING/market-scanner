# ✅ 載入 .env 與 Webhook 設定
from dotenv import load_dotenv
import os

dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
print(f"[DEBUG] 載入的 Webhook：{WEBHOOK_URL}")

if not WEBHOOK_URL or "discord.com" not in WEBHOOK_URL:
    print("❌ Webhook URL 無效或未載入，請確認 .env 檔與 load_dotenv() 是否正確！")
    exit(1)

# ✅ 再 import 其他模組（需先載入 webhook）
import sys
import time
import traceback
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.scan_market import scan_market
from modules.notify.check_exit_and_notify import schedule_exit_check
from modules.utils.market_time import get_market_phase
from modules.data.loaders import load_stock_list
from modules.entry.position_manager import PositionManager
from modules.utils.connect_to_gsheet import connect_with_base64_key

# ✅ 初始化資金與推播
pm = PositionManager(initial_capital=100000, webhook_url=WEBHOOK_URL, auto_reset=True)

# ✅ 讀取 Google Sheets 連線資訊
sheet_url = os.getenv("GSHEET_URL")
key_base64 = os.getenv("GCP_KEY_BASE64")

if not sheet_url or not key_base64:
    print("❌ GSHEET_URL 或 GCP_KEY_BASE64 未正確載入，請確認 .env 檔")
    exit(1)

# ✅ 初始化建倉紀錄工作表（sheet_name = 建倉記錄）
sheet_entry = connect_with_base64_key(sheet_url, "建倉記錄", key_base64)

if not sheet_entry:
    print("❌ 無法取得 Google Sheet 分頁，請檢查金鑰與網址是否正確！")
    exit(1)
else:
    print("✅ 成功連接 Google Sheet ➜ 建倉記錄")

# ✅ 載入股票清單
stock_list = load_stock_list()

def main():
    print("🚀 啟動主控系統：scan_market + 出場排程")

    # ✅ 檢查市場時段是否為開盤
    phase = get_market_phase()
    if phase != "open":
        print(f"⏰ 當前市場為 {phase} ➜ 暫停掃描與建倉")
        return

    # ✅ 背景執行類股共振掃描
    from modules.controller.resonance_scan import run_sector_resonance
    import threading
    threading.Thread(target=run_sector_resonance, kwargs={"interval": 30}, daemon=True).start()

    # ✅ 執行建倉邏輯
    try:
        scan_market(stock_list, sheet_entry, position_manager=pm)
    except Exception as e:
        print(f"[錯誤] scan_market 失敗：{e}")
        traceback.print_exc()

    # ✅ 啟動出場排程
    try:
        schedule_exit_check()
    except Exception as e:
        print(f"[錯誤] schedule_exit_check 啟動失敗：{e}")
        traceback.print_exc()

    # ✅ 主迴圈持續執行
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
