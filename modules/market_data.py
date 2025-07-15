import pandas as pd
from modules.fetch_stock_data import fetch_stock_data
from modules.config import POLYGON_API_KEY

# ✅ 取得最新收盤價（Polygon API 或快取）
def get_latest_price(symbol):
    try:
        df = fetch_stock_data(symbol, api_key=POLYGON_API_KEY)
        if df is None or df.empty or "close" not in df.columns:
            print(f"[⚠️ 無法取得最新價格] {symbol}")
            return None
        return df["close"].iloc[-1]
    except Exception as e:
        print(f"[錯誤] 無法取得 {symbol} 最新價格：{e}")
        return None
