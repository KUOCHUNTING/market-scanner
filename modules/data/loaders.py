 modules/data/loaders.py

import os
import pandas as pd

def load_stock_list(filepath="filtered_us_stocks_common_only.csv"):
    """
    載入股票清單 CSV，若檔案不存在則回傳預設測試清單。
    """
    try:
        base_path = os.path.dirname(__file__)
        file_path = os.path.join(base_path, filepath)
        df = pd.read_csv(file_path)

        if "symbol" not in df.columns:
            raise ValueError("❌ 缺少 'symbol' 欄位")
        return df["symbol"].dropna().tolist()

    except Exception as e:
        print(f"[警告] 股票清單讀取失敗：{e}")
        print("[改用預設測試股票清單]")
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
            "NVDA", "META", "JPM", "UNH", "V",
            "XOM", "JNJ", "HD", "PG", "MA",
            "BAC", "KO", "AVGO", "PEP", "WMT"
        ]
