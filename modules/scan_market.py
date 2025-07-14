import pandas as pd
import traceback
import random
import math
from ta.momentum import RSIIndicator, ROCIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands
from ta.volume import OnBalanceVolumeIndicator

from modules.fetch_stock_data import fetch_stock_data
from modules.get_fundamentals import get_fundamentals
from modules.filter_fundamentals import filter_fundamentals
from modules.detect_trading_signal import detect_trading_signal
from modules.compute_confidence_score import compute_confidence_score
from modules.load_stock_list import load_stock_list
from modules.config import POLYGON_API_KEY, capital_left, WEBHOOK_URL
from modules.notify.discord_push import send_discord_message
from modules.enter_position import enter_position
from modules.strategy.strategy_score import get_rrov_score, get_trend_score, get_mean_score
from modules.notify.build_discord_message import build_entry_message, build_breakout_message
from modules.strategy.detect_squeeze_breakout import detect_squeeze_breakout

# ✅ 股票清單
stock_list = load_stock_list()

# ✅ 判斷指標是否無效
def is_invalid(indicators):
    for key, val in indicators.items():
        if val is None:
            print(f"[指標錯誤] {key} 是 None ➜ 無效")
            log_invalid_indicator(key)
            return True
        if isinstance(val, pd.Series):
            if val.isna().any():
                print(f"[指標錯誤] {key} 有 NaN 值 ➜ 無效")
                log_invalid_indicator(key)
                return True
        elif isinstance(val, (float, int)) and math.isnan(val):
            print(f"[指標錯誤] {key} 是 NaN ➜ 無效")
            log_invalid_indicator(key)
            return True
    return False

def log_invalid_indicator(message):
    with open("invalid_indicators_log.txt", "a") as f:
        f.write(f"{message}\n")

# ✅ 計算技術指標
def calculate_indicators(df):
    if df is None or len(df) < 60:
        print("[⚠️ 警告] 技術指標計算時資料不足（小於 60 筆），跳過")
        return None

    required_columns = ['close', 'volume', 'open', 'high', 'low']
    for col in required_columns:
        if col not in df.columns:
            print(f"⚠️ [警告] 缺少必要欄位：{col}，跳過")
            return None
        if df[col].isnull().all():
            print(f"⚠️ [警告] 欄位 {col} 全為空 ➜ 跳過")
            return None

    try:
        close = df['close']
        volume = df['volume']

        rsi = RSIIndicator(close=close, window=15).rsi()
        roc = ROCIndicator(close=close, window=10).roc()
        obv = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

        zscore = (close - close.rolling(21).mean()) / close.rolling(21).std()

        bb = BollingerBands(close=close, window=20, window_dev=2)
        lower_band = bb.bollinger_lband()
        upper_band = bb.bollinger_hband()
        mid_band = bb.bollinger_mavg()

        df['cum_vol'] = volume.cumsum()
        df['cum_vwap'] = (close * volume).cumsum()
        vwap = df['cum_vwap'] / df['cum_vol']

        ema_5 = EMAIndicator(close=close, window=5).ema_indicator()
        ema_20 = EMAIndicator(close=close, window=20).ema_indicator()

        ema_5_slope = ema_5.diff()
        ema_20_slope = ema_20.diff()
        ema_trend = []
        for i in range(len(ema_5_slope)):
            if ema_5_slope.iloc[i] > 0 and ema_20_slope.iloc[i] > 0:
                ema_trend.append("上彎")
            elif ema_5_slope.iloc[i] < 0 and ema_20_slope.iloc[i] < 0:
                ema_trend.append("下彎")
            else:
                ema_trend.append("糾結")

        curr_volume = volume.iloc[-1]
        avg_volume = volume.rolling(20).mean().iloc[-1]
        volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1.0
        ema_status = (ema_5 > ema_20).replace({True: "上穿", False: "下彎"})

        last_open = df['open'].iloc[-1]
        last_close = df['close'].iloc[-1]
        last_high = df['high'].iloc[-1]
        last_low = df['low'].iloc[-1]

        body_size = abs(last_close - last_open)
        upper_shadow = last_high - max(last_close, last_open)
        lower_shadow = min(last_close, last_open) - last_low

        if body_size < 0.1 * (last_high - last_low):
            candle_type = "十字線"
        elif last_close > last_open and lower_shadow > 2 * body_size:
            candle_type = "錘頭"
        elif last_close < last_open and upper_shadow > 2 * body_size:
            candle_type = "流星"
        elif last_close > last_open:
            candle_type = "陽線"
        else:
            candle_type = "陰線"

        # 防呆檢查
        key_checks = {
            "RSI": rsi,
            "Z-score": zscore,
            "EMA5": ema_5,
            "EMA20": ema_20,
            "BB上軌": upper_band,
            "OBV": obv
        }

        for name, series in key_checks.items():
            if series is None or series.dropna().empty or pd.isna(series.iloc[-1]):
                print(f"[❌ 錯誤] 指標 {name} ➜ 尾端無效值")
                log_invalid_indicator(f"{name} 無效")
                return None

        return {
            'rsi': rsi,
            'roc': roc,
            'obv': obv,
            'zscore': zscore,
            'bb_lower': lower_band,
            'bb_upper': upper_band,
            'bb_mid': mid_band,
            'vwap': vwap,
            'ema_5': ema_5,
            'ema_20': ema_20,
            'ema_trend': pd.Series(ema_trend, index=df.index),
            'curr_volume': curr_volume,
            'volume_ratio': volume_ratio,
            'avg_volume': avg_volume,
            'ema_status': ema_status,
            'candle_type': candle_type
        }

    except Exception as e:
        print(f"[❌ 例外] 技術指標計算失敗：{e}")
        log_invalid_indicator(f"Exception: {e}")
        return None
