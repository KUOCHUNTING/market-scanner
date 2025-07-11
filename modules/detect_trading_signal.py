import pandas as pd
import numpy as np

def detect_trading_signal(symbol, df, indicators, debug=False, force_test=False):
    if 'volume' not in df.columns:
        print(f"[跳過] {symbol} 缺少 volume 欄位")
        return None, None, None, None, df, indicators, None, 0.0, 0.0, 0.0

    if len(df) < 60:
        if debug:
            print(f"[跳過] {symbol} 資料不足（僅 {len(df)} 筆）")
        return None, None, None, None, df, indicators, None, 0.0, 0.0, 0.0

    if 'close' not in df.columns or df['close'].isnull().all():
        print(f"[跳過] {symbol} ➜ close 欄位無效")
        return None, None, None, None, df, indicators, None, 0.0, 0.0, 0.0

    latest_price = df['close'].iloc[-1]
    prev_close = df['close'].iloc[-2]
    if pd.isna(latest_price) or latest_price <= 0:
        print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
        return None, None, None, None, df, indicators, None, 0.0, 0.0, 0.0

    # === 技術指標抽出 ===
    rsi = indicators['rsi'].iloc[-1]
    rsi_prev = indicators['rsi'].iloc[-2]
    roc = indicators['roc'].iloc[-1]
    roc_prev = indicators['roc'].iloc[-2]
    obv = indicators['obv'].iloc[-1]
    obv_prev = indicators['obv'].iloc[-2]
    vwap = indicators['vwap'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]
    lower_band = indicators['bb_lower'].iloc[-1]
    upper_band = indicators['bb_upper'].iloc[-1]

    mean = df['close'].rolling(window=20).mean().iloc[-1]
    std = df['close'].rolling(window=20).std().iloc[-1]
    zscore = (latest_price - mean) / std if std and not pd.isna(std) else 0
    vwap_deviation = (latest_price - vwap) / vwap if vwap else 0
    price_change = abs(latest_price - prev_close) / prev_close

    signal_type = signal_note = direction = strategy_name = None
    rrov_score = trend_score = mean_score = 0.0

    # === 策略判斷 ===
    if (
        rsi < 35 and rsi > rsi_prev and
        roc < 0 and roc > roc_prev and
        obv > obv_prev and
        abs(latest_price - vwap) / vwap < 0.05 and
        price_change < 0.01
    ):
        signal_type = "BUY"
        signal_note = "🐸 多單建倉（RROV）：RSI回升 + ROC翻揚 + OBV上升 + VWAP貼近"
        direction = "多"
        strategy_name = "RROV 主策略"
        rrov_score = 1.0

    elif (
        rsi > 50 and rsi > rsi_prev and
        roc > 0 and roc > roc_prev and
        obv > obv_prev and
        latest_price > vwap and
        ema5 > ema20 and
        price_change < 0.015
    ):
        signal_type = "BUY"
        signal_note = "🐸 多單建倉（順勢）：RSI轉強、VWAP上方、EMA 多頭排列"
        direction = "多"
        strategy_name = "順勢多單"
        trend_score = 1.0

    elif (
        latest_price < lower_band and
        rsi < 35 and rsi > rsi_prev and
        zscore < -2 and
        ema5 > ema20
    ):
        signal_type = "BUY"
        signal_note = "🐸 多單建倉（均值回歸）：跌破布林 + RSI回升 + Z-score超跌"
        direction = "多"
        strategy_name = "均值回歸"
        mean_score = 1.0

    elif (
        rsi > 65 and rsi < rsi_prev and
        roc > 0 and roc < roc_prev and
        obv < obv_prev and
        abs(latest_price - vwap) / vwap < 0.05 and
        price_change < 0.01
    ):
        signal_type = "SELL"
        signal_note = "🐶 空單建倉（RROV）：RSI轉弱 + ROC下滑 + OBV下降 + VWAP貼近"
        direction = "空"
        strategy_name = "RROV 主策略"
        rrov_score = 1.0

    elif (
        rsi < 50 and rsi < rsi_prev and
        roc < 0 and roc < roc_prev and
        obv < obv_prev and
        latest_price < vwap and
        ema5 < ema20 and
        price_change < 0.015
    ):
        signal_type = "SELL"
        signal_note = "🐶 空單建倉（順勢）：RSI轉弱、VWAP下方、EMA死叉"
        direction = "空"
        strategy_name = "順勢空單"
        trend_score = 1.0

    elif (
        latest_price > upper_band and
        rsi > 65 and rsi < rsi_prev and
        zscore > 2 and
        ema5 < ema20
    ):
        signal_type = "SELL"
        signal_note = "🐶 空單建倉（均值回歸）：突破布林 + RSI轉弱 + Z-score過熱"
        direction = "空"
        strategy_name = "均值回歸"
        mean_score = 1.0

    # === 回傳完整 10 項
    return signal_type, strategy_name, signal_note, direction, df, indicators, latest_price, rrov_score, trend_score, mean_score
