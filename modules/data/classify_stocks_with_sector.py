# modules/data/classify_stocks_with_sector.py

import os
import pandas as pd
import yfinance as yf
from tqdm import tqdm

# === 中文板塊對照表 ===
sector_cn_map = {
    "Technology": "資訊科技",
    "Healthcare": "醫療保健",
    "Financial Services": "金融服務",
    "Consumer Cyclical": "非必需消費",
    "Consumer Defensive": "必需消費",
    "Industrials": "工業",
    "Energy": "能源",
    "Basic Materials": "原物料",
    "Utilities": "公用事業",
    "Communication Services": "通訊服務",
    "Real Estate": "房地產"
}

# === 路徑設定 ===
input_path = "data/filtered_us_stocks_common_only.csv"
output_path = "data/stocks_with_sector.csv"

# === 建立資料夾
os.makedirs("data", exist_ok=True)

# === 讀入股票清單
df = pd.read_csv(input_path)
if "symbol" not in df.columns:
    raise ValueError("輸入 CSV 檔缺少 symbol 欄位")

results = []

print("📊 開始抓取股票板塊與產業分類...")

for symbol in tqdm(df["symbol"].dropna().unique()):
    try:
        info = yf.Ticker(symbol).info
        sector = info.get("sector", None)
        industry = info.get("industry", None)
        sector_cn = sector_cn_map.get(sector, "未分類")
        results.append({
            "symbol": symbol,
            "sector": sector,
            "sector_cn": sector_cn,
            "industry": industry
        })
    except Exception as e:
        print(f"⚠️ {symbol} 讀取失敗：{e}")
        results.append({
            "symbol": symbol,
            "sector": None,
            "sector_cn": "讀取失敗",
            "industry": None
        })

# === 輸出結果
result_df = pd.DataFrame(results)
result_df.to_csv(output_path, index=False, encoding="utf-8-sig")
print(f"✅ 匯出完成：{output_path}")
