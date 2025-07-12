import requests
import pandas as pd

def get_fundamentals(symbol, polygon_api_key, df=None):
    try:
        url = f"https://api.polygon.io/v3/reference/tickers/{symbol}?apiKey={polygon_api_key}"
        res = requests.get(url)
        data = res.json().get("results", {})

        avg_volume_api = float(data.get("average_volume", 0))
        avg_volume_fallback = 0

        if avg_volume_api == 0 and df is not None and "volume" in df.columns:
            avg_volume_fallback = df["volume"].tail(60).mean()  # ✅ 用近 60 根 K 計算，約等於 3 日均量

        avg_volume = avg_volume_api if avg_volume_api > 0 else avg_volume_fallback

        return {
            "market_cap": float(data.get("market_cap", 0)),
            "avg_volume": avg_volume,
            "price": float(data.get("last_close", {}).get("price", 0)),
            "is_otc": data.get("market", "").lower() == "otc",
            "is_delisted": not data.get("active", True),
            "is_recent_earning": False
        }

    except Exception as e:
        print(f"[❌ 基本面抓取失敗] {symbol} ➜ {e}")
        return {
            "market_cap": 0,
            "avg_volume": 0,
            "price": 0,
            "is_otc": True,
            "is_delisted": True,
            "is_recent_earning": True
        }
