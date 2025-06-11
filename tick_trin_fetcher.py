import os
import requests
from datetime import datetime, timedelta

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

# === 抓取最新 TICK / TRIN 值（延遲15分鐘資料）
def fetch_tick_and_trin():
    try:
        now = datetime.utcnow() - timedelta(minutes=15)
        to_time = now.strftime("%Y-%m-%d")
        url = f"https://api.polygon.io/v2/aggs/ticker/TICK/prev?adjusted=true&apiKey={POLYGON_API_KEY}"
        tick_res = requests.get(url, timeout=10).json()

        trin_url = f"https://api.polygon.io/v2/aggs/ticker/TRIN/prev?adjusted=true&apiKey={POLYGON_API_KEY}"
        trin_res = requests.get(trin_url, timeout=10).json()

        tick_value = tick_res['results'][0]['c'] if 'results' in tick_res else None
        trin_value = trin_res['results'][0]['c'] if 'results' in trin_res else None

        if tick_value is None or trin_value is None:
            raise ValueError("TICK 或 TRIN 無法取得")

        return float(tick_value), float(trin_value)
    except Exception as e:
        print(f"[錯誤] 無法取得 TICK / TRIN：{e}")
        return None, None
