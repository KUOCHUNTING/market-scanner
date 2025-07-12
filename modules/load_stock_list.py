import pandas as pd
import os

def load_stock_list(filepath="filtered_us_stocks_common_only.csv"):
    try:
        df = pd.read_csv(filepath)
        if "symbol" in df.columns:
            return df["symbol"].dropna().tolist()
        else:
            print("❌ 缺少 'symbol' 欄位")
            return []
    except Exception as e:
        print(f"❌ 載入失敗：{e}")
        return []
