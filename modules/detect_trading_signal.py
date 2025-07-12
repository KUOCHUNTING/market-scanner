import pandas as pd
import numpy as np

def detect_trading_signal(symbol, df, indicators, latest_price=None, debug=False):
    if 'volume' not in df.columns:
        print(f"[跳過] {symbol} 缺少 volume 欄位")
        return None, None, None, None

    if len(df) < 60:
        if debug:
            print(f"[跳過] {symbol} 資料不足（僅 {len(df)} 筆）")
        return None, None, None, None

    if 'close' not in df.columns or df['close'].isnull().all():
        print(f"[跳過] {symbol} ➜ close 欄位無效")
        return None, None, None, None

    if latest_price is None:
        latest_price = df['close'].iloc[-1]

    prev_close = df['close'].iloc[-2]
    if pd.isna(latest_price) or latest_price <= 0:
        print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
        return None, None, None, None

    price_change = abs(latest_price - prev_close) / prev_close

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

    signal_type = signal_note = direction = strategy_name = None

    # === 🟢 多單策略 ===
    if (
        rsi < 35 and rsi > rsi_prev and
        roc < 0 and roc > roc_prev and
        obv > obv_prev and
        abs(latest_price - vwap) / vwap < 0.05 and
        price_change < 0.01
    ):
        return "BUY", "🐸 多單建倉（RROV）：RSI回升 + ROC翻揚 + OBV上升 + VWAP貼近", "多", "RROV 主策略"

    if (
        rsi > 50 and rsi > rsi_prev and
        roc > 0 and roc > roc_prev and
        obv > obv_prev and
        latest_price > vwap and
        ema5 > ema20 and
        price_change < 0.015
    ):
        return "BUY", "🐸 多單建倉（順勢）：RSI轉強、VWAP上方、EMA 多頭排列", "多", "順勢多單"

    if debug:
        print(f"[DEBUG] {symbol} ➜ Zscore={zscore:.2f}, RSI={rsi:.1f}, EMA5>EMA20={ema5 > ema20}, latest_price={latest_price:.2f}, lower_band={lower_band:.2f}")
    if (
        latest_price < lower_band and
        rsi < 35 and rsi > rsi_prev and
        zscore < -2 and
        ema5 > ema20
    ):
        return "BUY", "🐸 多單建倉（均值回歸）：跌破布林 + RSI回升 + Z-score超跌", "多", "均值回歸"

    # === 🔴 空單策略 ===
    if (
        rsi > 65 and rsi < rsi_prev and
        roc > 0 and roc < roc_prev and
        obv < obv_prev and
        abs(latest_price - vwap) / vwap < 0.05 and
        price_change < 0.01
    ):
        return "SELL", "🐶 空單建倉（RROV）：RSI轉弱 + ROC下滑 + OBV下降 + VWAP貼近", "空", "RROV 主策略"

    if (
        rsi < 50 and rsi < rsi_prev and
        roc < 0 and roc < roc_prev and
        obv < obv_prev and
        latest_price < vwap and
        ema5 < ema20 and
        price_change < 0.015
    ):
        return "SELL", "🐶 空單建倉（順勢）：RSI轉弱、VWAP下方、EMA死叉", "空", "順勢空單"

    if debug:
        print(f"[DEBUG] {symbol} ➜ Zscore={zscore:.2f}, RSI={rsi:.1f}, EMA5<EMA20={ema5 < ema20}, latest_price={latest_price:.2f}, upper_band={upper_band:.2f}")
    if (
        latest_price > upper_band and
        rsi > 65 and rsi < rsi_prev and
        zscore > 2 and
        ema5 < ema20
    ):
        return "SELL", "🐶 空單建倉（均值回歸）：突破布林 + RSI轉弱 + Z-score過熱", "空", "均值回歸"

    # === ⚠️ 爆量預警 ===
    curr_volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].rolling(20).mean().iloc[-1]
    volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1.0

    if volume_ratio >= 5 and (rsi < 40 or latest_price < lower_band * 1.02):
        return "ALERT_VOLUME_SPIKE_LONG", f"⚠️ [低檔爆量] ➜ 量比={volume_ratio:.1f}x，RSI={rsi:.1f}", "多", "爆量預警"

    elif volume_ratio >= 5 and (rsi > 70 or latest_price > upper_band * 0.98):
        return "ALERT_VOLUME_SPIKE_SHORT", f"⚠️ [高檔爆量] ➜ 量比={volume_ratio:.1f}x，RSI={rsi:.1f}", "空", "爆量預警"

    # === 無效訊號 ===
    if debug:
        print(f"[未達條件] {symbol} ➜ 無訊號，RSI={rsi:.1f}、Z-score={zscore:.2f}、VWAP乖離={vwap_deviation:.2%}")
    return None, None, None, None
