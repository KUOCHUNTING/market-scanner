# modules/logic/detect_trading_signal.py

from modules.strategy.detect_squeeze_breakout import detect_squeeze_breakout
from modules.strategy.strategy_score import get_rrov_score, get_trend_score, get_mean_score
from modules.compute_confidence_score import compute_confidence_score

def detect_trading_signal(symbol, df, indicators, latest_price):
    """
    統一策略判斷模組
    回傳：
    - signal_type: "rrov", "trend", "mean", "squeeze_breakout"
    - strategy_name: 策略名稱
    - signal_note: 技術摘要說明
    - direction: "做多" / "做空"
    - extra: 擠壓策略 dict（或 None）
    """

    # === 1️⃣ 擠壓突破策略（多空雙向）
    squeeze_result = detect_squeeze_breakout(symbol)
    if squeeze_result:
        return (
            "squeeze_breakout",
            squeeze_result["strategy_name"],
            "Squeeze OFF + 技術條件命中",
            squeeze_result["direction"],
            squeeze_result
        )

    # === 2️⃣ RROV 策略（突破壓力 / 跌破支撐）
    rrov_score = get_rrov_score(indicators, latest_price)

    # 🟢 做多：突破 BB 上軌
    if rrov_score >= 0.9 and latest_price > indicators['bb_upper'].iloc[-1]:
        return (
            "rrov",
            "壓力突破（多頭）",
            "價格突破 BB 上軌 + 放量 + EMA 多頭排列",
            "做多",
            None
        )

    # 🔴 做空：跌破 BB 下軌
    if rrov_score >= 0.9 and latest_price < indicators['bb_lower'].iloc[-1]:
        return (
            "rrov",
            "支撐跌破（空頭）",
            "價格跌破 BB 下軌 + 放量 + EMA 空頭排列",
            "做空",
            None
        )

    # === 3️⃣ 順勢策略（EMA 趨勢 + RSI 強弱）
    trend_score = get_trend_score(indicators)
    if trend_score >= 0.9:
        direction = "做多" if indicators['ema_5'].iloc[-1] > indicators['ema_20'].iloc[-1] else "做空"
        return (
            "trend",
            "順勢策略",
            "EMA 趨勢明確 + RSI 動能支撐",
            direction,
            None
        )

    # === 4️⃣ 均值回歸策略（Z-score 過度偏離）
    mean_score = get_mean_score(indicators, latest_price)
    if mean_score >= 0.9:
        z = indicators['zscore'].iloc[-1]
        direction = "做多" if z < -1.5 else "做空" if z > 1.5 else None
        if direction:
            return (
                "mean",
                "均值回歸",
                f"Z-score = {z:.2f} 過度乖離",
                direction,
                None
            )

    # === 無訊號
    return None, None, None, None, None
