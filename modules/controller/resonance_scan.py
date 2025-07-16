import sys
import os

# ✅ 加入上層目錄到系統路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import time
import pandas as pd
import requests
from datetime import datetime

from modules.data.sector_etf_map import sector_etf_map, get_etf_by_sector, get_chinese_by_sector
from modules.strategy.resonance_polygon import detect_sector_resonance
from modules.connect_to_gsheet import write_resonance_to_sheet

GSHEET_URL = os.getenv("GSHEET_URL")
GSHEET_TAB = os.getenv("GSHEET_TAB") or "共振紀錄"
GCP_KEY = os.getenv("GCP_KEY_BASE64")

# ✅ 讀取 Discord Webhook
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK") or "https://your-webhook-url"

# ✅ Discord 推播函數
def send_discord_message(content: str):
    try:
        payload = {"content": content}
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code != 204:
            print(f"⚠️ Discord 推播失敗：{response.text}")
    except Exception as e:
        print(f"❌ Discord 發送錯誤：{e}")

# ✅ 主執行函數（每 interval 秒掃描一次）
def run_sector_resonance(interval=30, csv_path="data/stocks_with_sector.csv"):
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌ 無法讀取股票分類檔案：{e}")
        return

    # 建立板塊成分股對應表
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

                    # ✅ 推播到 Discord
                    send_discord_message(content)

                    # ✅ 寫入 Google Sheets
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
