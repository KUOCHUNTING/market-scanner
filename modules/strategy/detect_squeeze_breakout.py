import pandas as pd
from modules.fetch_stock_data import fetch_stock_data
from modules.config import POLYGON_API_KEY
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

def detect_squeeze_breakout(symbol):
    df = fetch_stock_data(symbol, api_key=POLYGON_API_KEY)
    if df is None or len(df) < 60:
        print(f"[擠壓] {symbol} ➜ 資料不足")
        return None

    if 'close' not in df.columns:
        print(f"[擠壓錯誤] {symbol} 缺少欄位：close")
        return None

    # === 計算布林通道寬度 ===
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['stddev'] = df['close'].rolling(window=20).std()
    df['upper'] = df['MA20'] + (2 * df['stddev'])
    df['lower'] = df['MA20'] - (2 * df['stddev'])
    df['band_width'] = df['upper'] - df['lower']

    # === 判斷是否進入擠壓狀態 ===
    recent_bandwidth = df['band_width'].iloc[-5:]
    historical_avg = df['band_width'].rolling(window=50).mean().iloc[-1]
    squeeze = recent_bandwidth.mean() < historical_avg * 0.5

    if not squeeze:
        return None

    print(f"[擠壓策略] {symbol} ➜ 進入擠壓狀態")

    # === 技術指標補充（用於推播與策略判斷） ===
    df['rsi'] = RSIIndicator(close=df['close']).rsi()
    df['ema_5'] = EMAIndicator(close=df['close'], window=5).ema_indicator()
    df['ema_20'] = EMAIndicator(close=df['close'], window=20).ema_indicator()

    close = df['close'].iloc[-1]
    rsi = df['rsi'].iloc[-1]
    ema_5 = df['ema_5'].iloc[-1]
    ema_20 = df['ema_20'].iloc[-1]

    # === 簡易邏輯判斷突破方向（做多 or 做空） ===
    direction = "做多" if ema_5 > ema_20 and rsi > 50 else "做空"

    # 命中條件
    matched = []
    if ema_5 > ema_20:
        matched.append("EMA 多頭")
    else:
        matched.append("EMA 空頭")

    if rsi > 55:
        matched.append("RSI 強勢")
    elif rsi < 45:
        matched.append("RSI 弱勢")

    return {
        "symbol": symbol,
        "strategy_name": "擠壓策略",
        "direction": direction,
        "score": len(matched),
        "conditions_met": matched,
        "close": close,           # ✅ 關鍵欄位：推播會用到
        "rsi": rsi,
        "ema_5": ema_5,
        "ema_20": ema_20
    }
