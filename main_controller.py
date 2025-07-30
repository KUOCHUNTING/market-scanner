import os
from dotenv import load_dotenv
from modules.notify.check_exit_and_notify import schedule_exit_check

dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)

print(f"[DEBUG] ✅ DISCORD_WEBHOOK from .env = '{os.getenv('DISCORD_WEBHOOK')}'")
# ✅ 讀取環境變數
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
GSHEET_URL = os.getenv("GSHEET_URL")
GSHEET_TAB = os.getenv("GSHEET_TAB") or "建倉記錄"
GCP_KEY_BASE64 = os.getenv("GCP_KEY_BASE64")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
try:
    CAPITAL_LEFT = float(os.getenv("CAPITAL_LEFT", 100000))
except ValueError:
    print("❌ CAPITAL_LEFT 環境變數無法轉為 float，請檢查 Secrets 設定")
    exit(1)
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", 0.2))

# ✅ DEBUG 檢查
print(f"[DEBUG] Webhook URL：{WEBHOOK_URL}")
print(f"[DEBUG] Google Sheet URL：{GSHEET_URL}")
print(f"[DEBUG] Sheet Tab：{GSHEET_TAB}")
print(f"[DEBUG] 資金參數：資金={CAPITAL_LEFT}，單筆上限={MAX_POSITION_PCT * 100:.1f}%")

# ❌ 檢查必要變數
if not WEBHOOK_URL or "discord.com" not in WEBHOOK_URL:
    print("❌ Webhook URL 無效或未載入，請確認 .env 設定")
    exit(1)
if not GSHEET_URL or not GCP_KEY_BASE64:
    print("❌ GSHEET_URL 或 GCP_KEY_BASE64 未正確載入，請確認 .env 設定")
    exit(1)

# ✅ 再 import 其他模組
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

# ✅ 初始化資金與推播模組
pm = PositionManager(
    initial_capital=CAPITAL_LEFT,
    max_position_pct=MAX_POSITION_PCT,
    webhook_url=WEBHOOK_URL,
    auto_reset=False
)

# ✅ 連接 Google Sheets
sheet_entry = connect_with_base64_key(GSHEET_URL, GSHEET_TAB, GCP_KEY_BASE64)

if not sheet_entry:
    print("❌ 無法取得 Google Sheet 分頁，請檢查金鑰與網址是否正確！")
    exit(1)
else:
    print(f"✅ 成功連接 Google Sheet ➜ {GSHEET_TAB}")

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
        
    from modules.notify.check_exit_and_notify import set_positions_ref, schedule_exit_check
    set_positions_ref(pm.positions)  # ⬅️ 就放這裡！

    # ✅ 啟動出場排程
    try:
        print(f"[DEBUG] 持倉掃描啟動 ➜ 當前持倉數：{len(pm.positions)}")
        schedule_exit_check()
    except Exception as e:
        print(f"[錯誤] schedule_exit_check 啟動失敗：{e}")
        traceback.print_exc()

    # ✅ 主迴圈持續執行
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
