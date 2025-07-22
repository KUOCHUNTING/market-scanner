# modules/data/loaders.py

import os
import pandas as pd

# ✅ 載入股票清單（預設 CSV）
def load_stock_list(filepath="filtered_us_stocks_common_only.csv"):
    """
    載入股票清單 CSV，若讀取失敗則直接拋出錯誤，不使用預設清單。
    """
    base_path = os.path.dirname(__file__)
    file_path = os.path.join(base_path, filepath)  # ✅ 不再加 ../../data

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ 找不到檔案：{file_path}")

    df = pd.read_csv(file_path)
    if "symbol" not in df.columns:
        raise ValueError("❌ 檔案中缺少 'symbol' 欄位")

    symbols = df["symbol"].dropna().tolist()
    if len(symbols) == 0:
        raise ValueError("❌ 股票清單為空")

    return symbols
# ✅ 載入 stocks_with_sector.csv（完整 DataFrame）
def load_stock_sector_csv(filename="stocks_with_sector.csv"):
    """
    從 data/ 載入股票分類檔案（symbol, sector, industry）
    """
    try:
        base_path = os.path.dirname(__file__)
        filepath = os.path.join(base_path, "..", "..", "data", filename)
        df = pd.read_csv(filepath)

        if "symbol" not in df.columns:
            raise ValueError("❌ 檔案缺少 'symbol' 欄位")
        return df
    except Exception as e:
        print(f"❌ 無法讀取股票分類檔案：{e}")
        return pd.DataFrame()

# ✅ 建立 symbol ➜ sector 對應表
def load_sector_mapping():
    """
    回傳 symbol ➜ sector 的對應字典，用於板塊分類。
    """
    df = load_stock_sector_csv()
    if df.empty or "symbol" not in df or "sector" not in df:
        print("⚠️ sector mapping 資料缺失，回傳空字典")
        return {}

    return dict(zip(df["symbol"], df["sector"]))
