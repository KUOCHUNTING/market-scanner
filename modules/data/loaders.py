# modules/data/loaders.py

import os
import pandas as pd
import requests
from datetime import datetime

# ✅ 抓取個股 15 分鐘線資料（Polygon API）
def fetch_stock_data(symbol, api_key, multiplier=15, timespan="minute", limit=1000):
    """
    從 Polygon 抓取歷史資料，回傳 DataFrame（收盤價欄為 close）
    """
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
        
# ✅ 載入股票清單（預設 CSV）
def load_stock_list(filepath="stocks_with_sector.csv"):
    """
    載入股票清單 CSV，回傳 symbol list
    """
    base_path = os.path.dirname(__file__)
    file_path = os.path.join(base_path, filepath)

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
    從 modules/data/ 載入股票分類檔案（symbol, sector, industry）
    """
    try:
        base_path = os.path.dirname(__file__)
        filepath = os.path.join(base_path, "stocks_with_sector.csv") 
        df = pd.read_csv(filepath)

        if "symbol" not in df.columns:
            raise ValueError("❌ 檔案缺少 'symbol' 欄位")
        return df
    except Exception as e:
        print(f"❌ 無法讀取股票分類檔案：{e}")
        return pd.DataFrame()

# ✅ 建立 symbol ➜ sector 對應表
def load_sector_mapping(filename="stocks_with_sector.csv"):
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_path, filename)
        df = pd.read_csv(file_path)

        # ✅ 檢查正確欄位名稱
        if "symbol" not in df.columns or "Standard_Sector" not in df.columns:
            raise ValueError("❌ 檔案缺少必要欄位（symbol 或 Standard_Sector）")

        return dict(zip(df["symbol"], df["Standard_Sector"]))  # ✅ 改這裡
    except Exception as e:
        print(f"❌ 無法讀取股票分類檔案：{e}")
        print("⚠️ sector mapping 資料缺失，回傳空字典")
        return {}
