import os
import pandas as pd
import requests
from datetime import datetime

# ✅ 抓取個股 15 分鐘線資料（Polygon API）
def fetch_stock_data(symbol, api_key, multiplier=15, timespan="minute", limit=1000):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/2023-01-01/2025-12-31"
    params = {
        "adjusted": "true",
        "sort": "desc",
        "limit": limit,
        "apiKey": api_key
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if "results" not in data:
            print(f"[❌] 沒有結果：{symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(data["results"])
        df["timestamp"] = pd.to_datetime(df["t"], unit="ms")
        df.rename(columns={"c": "close", "o": "open", "h": "high", "l": "low", "v": "volume"}, inplace=True)
        return df[["timestamp", "open", "high", "low", "close", "volume"]]

    except Exception as e:
        print(f"[❌] 抓取資料失敗：{symbol} ➜ {e}")
        return pd.DataFrame()

# ✅ 載入股票清單（symbol list）
def load_stock_sector_csv():
    base_path = os.path.dirname(os.path.dirname(__file__))  # 取得模組上層資料夾
    file_path = os.path.join(base_path, "data", "stocks_with_sector.csv")

    try:
        df = pd.read_csv(file_path)
        if "symbol" not in df.columns:
            raise ValueError("❌ 缺少 symbol 欄位")
        return df
    except Exception as e:
        print(f"❌ 無法讀取股票分類檔案：{e}")
        return pd.DataFrame()

# ✅ 載入股票分類表（完整 DataFrame）
def load_sector_file(filename="stocks_with_sector.csv"):
    try:
        base_path = os.path.dirname(__file__)
        file_path = os.path.join(base_path, filename)
        df = pd.read_csv(file_path)

        if "symbol" not in df.columns:
            raise ValueError("❌ 檔案缺少 'symbol' 欄位")

        return df
    except Exception as e:
        print(f"❌ 無法讀取股票分類檔案：{e}")
        return pd.DataFrame()

# ✅ 建立 symbol ➜ sector 對應表（dict）
def load_stock_list(filepath="data/filtered_us_stocks_common_only.csv"):
    """
    從 CSV 檔讀取股票代碼清單，預設檔案為 data/filtered_us_stocks_common_only.csv
    """
    try:
        base_path = os.path.dirname(os.path.dirname(__file__))
        file_path = os.path.join(base_path, filepath)
        df = pd.read_csv(file_path)

        if "symbol" not in df.columns:
            raise ValueError("❌ CSV 檔案缺少 symbol 欄位")
        
        return df["symbol"].dropna().tolist()
    except Exception as e:
        print(f"❌ 股票清單讀取失敗：{e}")
        print("✅ 改用預設測試股票清單")
        return ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]

def load_stock_sector_csv(filename="stocks_with_sector.csv"):
    try:
        base_path = os.path.dirname(__file__)
        file_path = os.path.join(base_path, filename)
        df = pd.read_csv(file_path)

        if "symbol" not in df.columns:
            raise ValueError("❌ 檔案缺少 'symbol' 欄位")

        return df
    except Exception as e:
        print(f"❌ 無法讀取股票分類檔案：{e}")
        return pd.DataFrame()

