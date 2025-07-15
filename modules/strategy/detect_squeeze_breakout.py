import pandas as pd
from modules.fetch_stock_data import fetch_stock_data
from modules.calculate_indicators import calculate_indicators
from modules.config import POLYGON_API_KEY

def detect_squeeze_breakout(symbol):
    try:
        # === 抓取資料與指標 ===
        df = fetch_stock_data(symbol, POLYGON_API_KEY)
        if df is None or len(df) < 60:
            return None

        indicators = calculate_indicators(df)
        if indicators is None:
            return None

        close = df['close'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        curr_volume = df['volume'].iloc[-1]

        ema_5 = indicators['ema_5'].iloc[-1]
        ema_20 = indicators['ema_20'].iloc[-1]
        bb_upper = indicators['bb_upper'].iloc[-1]
        bb_lower = indicators['bb_lower'].iloc[-1]
        rsi = indicators['rsi'].iloc[-1]

        # === 做多條件 ===
        long_conditions = {
            "突破布林上軌": close > bb_upper,
            "放量": curr_volume > avg_volume * 1.2,
            "短線轉強（EMA5 > EMA20）": ema_5 > ema_20,
        }
        long_score = sum(long_conditions.values())

        if long_score >= 2:
            return {
                "symbol": symbol,
                "direction": "做多",
                "score": long_score,
                "conditions_met": [k for k, v in long_conditions.items() if v],
                "close": close,
                "rsi": rsi,
                "ema_5": ema_5,
                "ema_20": ema_20,
                "strategy_name": "擠壓突破"
            }

        # === 做空條件 ===
        short_conditions = {
            "跌破布林下軌": close < bb_lower,
            "放量下殺": curr_volume > avg_volume * 1.2,
            "短線轉弱（EMA5 < EMA20）": ema_5 < ema_20,
        }
        short_score = sum(short_conditions.values())

        if short_score >= 2:
            return {
                "symbol": symbol,
                "direction": "做空",
                "score": short_score,
                "conditions_met": [k for k, v in short_conditions.items() if v],
                "close": close,
                "rsi": rsi,
                "ema_5": ema_5,
                "ema_20": ema_20,
                "strategy_name": "擠壓跌破"
            }

        return None

    except Exception as e:
        print(f"[錯誤] 擠壓策略偵測失敗：{symbol} ➜ {e}")
        return None
