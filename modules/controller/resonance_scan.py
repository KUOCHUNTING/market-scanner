 import sys
import os
import time
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# ✅ 加入上層目錄到系統路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# ✅ 載入 .env 環境變數
load_dotenv()
GSHEET_URL = os.getenv("GSHEET_URL")
GSHEET_TAB = os.getenv("GSHEET_TAB") or "共振紀錄"
GCP_KEY = os.getenv("GCP_KEY_BASE64")
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

# ✅ 模組匯入
from modules.data.sector_etf_map import sector_etf_map, get_etf_by_sector, get_chinese_by_sector
from modules.strategy.resonance_polygon import detect_sector_resonance
from modules.utils.gsheet_writer import write_resonance_to_sheet
from modules.data.loaders import load_stock_list, merge_stock_with_sector
from modules.notify.discord_push import send_discord_message  # ✅ 改為正確的模組

# ✅ 主執行函數（每 interval 秒掃描一次）
def run_sector_resonance(interval=30):
    stock_list = load_stock_list()
    df = merge_stock_with_sector(stock_list)

    if df.empty:
        print("❌ 股票分類資料為空，無法進行共振掃描")
        return

    # ✅ 建立板塊成分股對應表
    sector_stocks = {}
    for _, row in df.iterrows():
        sector = row.get("Standard_Sector")
        symbol = row.get("symbol")
        if sector in sector_etf_map:
            sector_stocks.setdefault(sector, []).append(symbol)

    while True:
        print("🔍 [板塊共振] 開始掃描…")
        for sector, symbols in sector_stocks.items():
            etf = get_etf_by_sector(sector)
            chinese = get_chinese_by_sector(sector)
            if not etf or not symbols:
                continue

            try:
                resonant, stocks = detect_sector_resonance(etf, symbols)
                if resonant:
                    print(f"✅ [共振] {chinese}（{etf}） → {len(stocks)} 檔")
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    content = (
                        f"📊 **[共振警報] {etf} - {chinese}**\n"
                        f"✅ **ETF 技術轉強**（RSI / OBV 轉為上升）\n"
                        f"✅ **共振成分股：{len(stocks)} 檔**\n"
                        f"📈 股票清單：`{', '.join(stocks[:10])}`\n"
                        f"🕒 {timestamp}"
                    )

                    # ✅ 改為傳入 webhook
                    send_discord_message(WEBHOOK_URL, content)

                    write_resonance_to_sheet(
                        timestamp=timestamp,
                        etf=etf,
                        sector_ch=chinese,
                        stock_list=stocks[:10],
                        sheet_url=GSHEET_URL,
                        sheet_name=GSHEET_TAB,
                        base64_key=GCP_KEY
                    )
                else:
                    print(f"❌ [無共振] {chinese}（{etf}）")
            except Exception as e:
                print(f"⚠️ 共振偵測錯誤：{chinese}｜{e}")

        print(f"⏳ 等待 {interval} 秒再掃描...\n")
        time.sleep(interval)
