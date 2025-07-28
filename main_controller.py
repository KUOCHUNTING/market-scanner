# main_controller.py

# ✅ 先載入 .env 與 Webhook
from dotenv import load_dotenv
import os
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
if not WEBHOOK_URL or "discord.com" not in WEBHOOK_URL:
    print("❌ Webhook URL 無效或未載入，請確認 .env 檔與 load_dotenv() 是否正確！")
    exit(1)

# ✅ 再 import 其他模組（要用到 webhook）
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
# ✅ 正確時機再初始化（此時 .env 已就緒）
print(f"✅ DEBUG：使用的 webhook = {WEBHOOK_URL}")
pm = PositionManager(initial_capital=100000, webhook_url=WEBHOOK_URL, auto_reset=True)

sheet_url = os.getenv("GSHEET_URL")
key_base64 = os.getenv("GCP_KEY_BASE64")

# ✅ 初始化 Google Sheets 工作表
sheet = connect_with_base64_key(sheet_url, key_base64)
sheet_entry = sheet.worksheet("建倉記錄")
# ✅ 載入股票清單
stock_list = load_stock_list()

def main():
    print("🚀 啟動主控系統：scan_market + 出場排程")

    phase = get_market_phase()
    if phase != "open":
        print(f"⏰ 當前市場為 {phase} ➜ 暫停掃描與建倉")
        return

    from modules.controller.resonance_scan import run_sector_resonance
    import threading
    threading.Thread(target=run_sector_resonance, kwargs={"interval": 30}, daemon=True).start()

    try:
        scan_market(stock_list, sheet_entry, position_manager=pm)
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
