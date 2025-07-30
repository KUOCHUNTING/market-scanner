import os
import sys
import time
import traceback
from dotenv import load_dotenv

# ✅ 載入 .env
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)

# ✅ 環境變數
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
GSHEET_URL = os.getenv("GSHEET_URL")
GSHEET_TAB = os.getenv("GSHEET_TAB") or "建倉記錄"
GCP_KEY_BASE64 = os.getenv("GCP_KEY_BASE64")
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

try:
    CAPITAL_LEFT = float(os.getenv("CAPITAL_LEFT", 100000))
except ValueError:
    print("❌ CAPITAL_LEFT 無法轉成 float，請檢查 .env 設定")
    exit(1)

MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", 0.2))

# ✅ DEBUG 印出設定
print(f"[DEBUG] ✅ Webhook URL：{WEBHOOK_URL}")
print(f"[DEBUG] ✅ Google Sheet：{GSHEET_URL} ➜ {GSHEET_TAB}")
print(f"[DEBUG] ✅ 資金 = {CAPITAL_LEFT}，單筆上限 = {MAX_POSITION_PCT * 100:.1f}%")

# ❌ 檢查必要變數
if not WEBHOOK_URL or "discord.com" not in WEBHOOK_URL:
    print("❌ Webhook URL 無效")
    exit(1)
if not GSHEET_URL or not GCP_KEY_BASE64:
    print("❌ Google Sheets 金鑰未載入")
    exit(1)

# ✅ 匯入模組
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from modules.scan_market import scan_market
from modules.notify.check_exit_and_notify import set_positions_ref, schedule_exit_check
from modules.utils.market_time import get_market_phase
from modules.data.loaders import load_stock_list
from modules.entry.position_manager import PositionManager
from modules.utils.connect_to_gsheet import connect_with_base64_key

def main():
    print("🚀 啟動主控系統：scan_market + 出場排程")

    # ✅ 初始化資金與持倉管理器
    pm = PositionManager(
        initial_capital=CAPITAL_LEFT,
        max_position_pct=MAX_POSITION_PCT,
        webhook_url=WEBHOOK_URL,
        auto_reset=False
    )

    # ✅ 測試持倉直接插入（避免 scan_market 沒建倉你無法測）
    from datetime import datetime, timedelta
    pm.positions["AAPL"] = {
        "symbol": "AAPL",
        "entry_time": datetime.now() - timedelta(minutes=5),
        "entry_price": 100.0,
        "price": 110.0,
        "direction": "做多",
        "shares": 10,
        "quantity": 10,
        "capital_used": 1000.0,
        "strategy_name": "測試策略",
        "sell_stage": 0,
        "max_gain": 0.0,
        "rsi": 55,
        "zscore": 0.2,
        "roc": 1.5,
        "obv": 100000,
        "vwap": 105,
        "ema5": 107,
        "ema20": 104
    }
    print("✅ [測試] AAPL 持倉已加入")

    # ✅ 連接 Google Sheet
    sheet_entry = connect_with_base64_key(GSHEET_URL, GSHEET_TAB, GCP_KEY_BASE64)
    if not sheet_entry:
        print("❌ 無法取得 Google Sheet 分頁，請檢查金鑰")
        exit(1)
    else:
        print(f"✅ 成功連接 Google Sheet ➜ {GSHEET_TAB}")

    # ✅ 載入股票清單
    stock_list = load_stock_list()

    # ✅ 時段檢查
    phase = get_market_phase()
    print(f"[DEBUG] 市場時段 = {phase}")
    # 強制測試時執行，不跳出
    # if phase != "open":
    #     print(f"⏰ 非開盤時段 ➜ 跳過")
    #     return

    # ✅ 建倉掃描
    try:
        scan_market(stock_list, sheet_entry, position_manager=pm)
    except Exception as e:
        print(f"[錯誤] scan_market 執行錯誤：{e}")
        traceback.print_exc()

    # ✅ 出場排程流程
    print(f"🟡 傳入持倉：{len(pm.positions)} 檔")
    for p in pm.positions:
        print(f"▶️ {p.get('symbol')} @ {p.get('entry_price')}，方向={p.get('direction')}")

    set_positions_ref(pm.positions)
    print("✅ set_positions_ref() 完成")

    try:
        print("✅ schedule_exit_check() 執行中...")
        schedule_exit_check()
    except Exception as e:
        print(f"❌ schedule_exit_check 啟動失敗：{e}")
        traceback.print_exc()

    # ✅ 測試排程期間等候
    print("⏳ 等待 30 秒觀察出場掃描輸出...")
    time.sleep(30)

if __name__ == "__main__":
    main()
