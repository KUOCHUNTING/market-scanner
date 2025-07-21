import os
import pandas as pd

def load_stock_sector_csv(filename="stocks_with_sector.csv"):
    """
    從 /data 資料夾讀取 stocks_with_sector.csv，回傳 DataFrame
    """
    base_path = os.path.dirname(__file__)
    filepath = os.path.join(base_path, "..", "data", filename)  # ../data/stocks_with_sector.csv
    try:
        df = pd.read_csv(filepath)
        if "symbol" not in df.columns:
            raise ValueError("❌ 檔案缺少 'symbol' 欄位")
        return df
    except Exception as e:
        print(f"❌ 無法讀取股票分類檔案：{e}")
        return pd.DataFrame()

def load_sector_mapping():
    """
    載入 symbol ➜ sector 對應 dict，用於板塊分類顯示。
    """
    df = load_stock_sector_csv()
    if df.empty or "symbol" not in df or "sector" not in df:
        print("⚠️ sector mapping 資料缺失，回傳空字典")
        return {}
    return dict(zip(df["symbol"], df["sector"]))
