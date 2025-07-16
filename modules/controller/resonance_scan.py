# controller/resonance_scan.py

import time
import os
import pandas as pd
import requests
from datetime import datetime
from modules.data.sector_etf_map import sector_etf_map, get_etf_by_sector, get_chinese_by_sector
from modules.strategy.resonance_detector import detect_sector_resonance

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
                        f"📊 板塊共振訊號（{etf}｜{chinese})\n"
                        f"✅ ETF 技術指標轉強\n"
                        f"✅ 成分股 RSI + OBV 共振：{len(stocks)} 檔\n"
                        f"📈 股票：{', '.join(stocks[:10])}...\n"
                        f"🕒 {timestamp}"
                    )
                    send_discord_message(content)
                else:
                    print(f"❌ [無共振] {chinese}（{etf}）")
            except Exception as e:
                print(f"⚠️ 共振偵測錯誤：{chinese}｜{e}")

        print(f"⏳ 等待 {interval} 秒再掃描...\n")
        time.sleep(interval)
