import os
import pandas as pd
import requests
from datetime import datetime

def load_stock_list(filepath="data/filtered_us_stocks_common_only.csv"):
    """
    載入股票清單（單欄 symbol），若無檔案則回傳預設清單
    """
    try:
        base_path = os.path.dirname(os.path.dirname(__file__))
        full_path = os.path.join(base_path, filepath)
        df = pd.read_csv(full_path)

        if "symbol" not in df.columns:
            raise ValueError("❌ CSV 缺少 symbol 欄位")
        
        return df["symbol"].dropna().unique().tolist()
    except Exception as e:
        print(f"❌ 股票清單讀取失敗：{e}")
        print("✅ 改用預設測試股票清單")
        return ["AAPL", "MSFT", "NVDA", "GOOGL", "TSLA"]

def load_stock_sector_csv(filepath="data/stocks_with_sector.csv"):
    """
    載入股票分類檔（含產業資訊）
    """
    try:
        base_path = os.path.dirname(os.path.dirname(__file__))
        full_path = os.path.join(base_path, filepath)
        df = pd.read_csv(full_path)

        if "symbol" not in df.columns or "Standard_Sector" not in df.columns:
            raise ValueError("❌ 檔案缺少必要欄位 symbol 或 Standard_Sector")
        
        return df
    except Exception as e:
        print(f"❌ 無法讀取分類檔案：{e}")
        return pd.DataFrame()

def merge_stock_with_sector(stock_list):
    """
    結合股票清單與分類資訊（共振掃描使用）
    """
    df_sector = load_stock_sector_csv()
    if df_sector.empty:
        print("⚠️ 無分類資料，回傳單純股票 DataFrame")
        return pd.DataFrame({"symbol": stock_list})
    
    df_sector["symbol"] = df_sector["symbol"].astype(str)
    df = pd.DataFrame({"symbol": stock_list})
    merged = pd.merge(df, df_sector, on="symbol", how="left")
    return merged

def load_sector_mapping(filepath="sector_mapping.csv"):
    import pandas as pd
    import os
    base_path = os.path.dirname(__file__)
    file_path = os.path.join(base_path, filepath)

    try:
        df = pd.read_csv(file_path)
        if "symbol" not in df.columns or "sector" not in df.columns:
            raise ValueError("❌ sector_mapping.csv 缺少必要欄位（symbol / sector）")
        return dict(zip(df["symbol"], df["sector"]))
    except Exception as e:
        print(f"❌ 讀取 sector_mapping.csv 錯誤：{e}")
        return {}

def fetch_stock_data(symbol, api_key, multiplier=15, timespan="minute", limit=1000):
    """
    從 Polygon API 抓取個股 15 分鐘線資料（或自訂區間）
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
        print(f"[錯誤] 抓取 {symbol} 時出錯：{e}")
        return pd.DataFrame()
