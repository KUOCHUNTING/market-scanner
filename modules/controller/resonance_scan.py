# controller/resonance_scan.py

import time
import pandas as pd
from modules.data.sector_etf_map import sector_etf_map, get_etf_by_sector, get_chinese_by_sector
from modules.strategy.resonance_detector import detect_sector_resonance

def run_sector_resonance(interval=30, csv_path="data/stocks_with_sector.csv"):
    """持續掃描板塊共振狀況，每 interval 秒執行一次"""
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

    # 持續掃描
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
                    print(f"✅ [共振訊號] {chinese}（{etf}）→ 共振股：{len(stocks)}")
                    print("　📈 股票：", ", ".join(stocks[:10]))
                else:
                    print(f"❌ [無共振] {chinese}（{etf}）")
            except Exception as e:
                print(f"⚠️ 共振偵測錯誤｜{chinese}：{e}")

        print(f"⏳ 等待 {interval} 秒再掃描...\n")
        time.sleep(interval)