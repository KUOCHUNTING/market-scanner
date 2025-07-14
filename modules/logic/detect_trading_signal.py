from modules.strategy.detect_squeeze_breakout import detect_squeeze_breakout
from modules.strategy.strategy_score import get_rrov_score, get_trend_score, get_mean_score
from modules.compute_confidence_score import compute_confidence_score

def detect_trading_signal(symbol, df, indicators, latest_price):
    """
    策略判斷模組（自動選擇最強策略）
    回傳：
    - signal_type: "rrov", "trend", "mean", "squeeze_breakout"
    - strategy_name: 策略名稱
    - signal_note: 技術摘要說明
    - direction: "做多" / "做空"
    - extra: 擠壓策略 dict（或 None）
    """

    candidates = []

    # === 1️⃣ 擠壓突破策略 ===
    squeeze_result = detect_squeeze_breakout(symbol)
    if squeeze_result:
        score = squeeze_result.get("score", 1.0)  # 若無則預設滿分
        candidates.append((
            score,
            "squeeze_breakout",
            squeeze_result["strategy_name"],
            "Squeeze OFF + 技術條件命中",
            squeeze_result["direction"],
            squeeze_result
        ))

    # === 2️⃣ RROV 策略（突破 / 跌破）===
    rrov_score = get_rrov_score(indicators, latest_price)
    if rrov_score >= 0.7:
        if latest_price > indicators['bb_upper'].iloc[-1]:
            candidates.append((
                rrov_score,
                "rrov",
                "壓力突破（多頭）",
                "價格突破 BB 上軌 + 放量 + EMA 多頭排列",
                "做多",
                None
            ))
        elif latest_price < indicators['bb_lower'].iloc[-1]:
            candidates.append((
                rrov_score,
                "rrov",
                "支撐跌破（空頭）",
                "價格跌破 BB 下軌 + 放量 + EMA 空頭排列",
                "做空",
                None
            ))

    # === 3️⃣ 順勢策略 ===
    trend_score = get_trend_score(indicators)
    if trend_score >= 0.7:
        direction = "做多" if indicators['ema_5'].iloc[-1] > indicators['ema_20'].iloc[-1] else "做空"
        candidates.append((
            trend_score,
            "trend",
            "順勢策略",
            "EMA 趨勢明確 + RSI 動能支撐",
            direction,
            None
        ))

    # === 4️⃣ 均值回歸策略 ===
    mean_score = get_mean_score(indicators, latest_price)
    if mean_score >= 0.7:
        z = indicators['zscore'].iloc[-1]
        direction = "做多" if z < -1.5 else "做空" if z > 1.5 else None
        if direction:
            candidates.append((
                mean_score,
                "mean",
                "均值回歸",
                f"Z-score = {z:.2f} 過度乖離",
                direction,
                None
            ))

    # === 無策略命中 ===
    if not candidates:
        return None, None, None, None, None

    # === 選擇分數最高策略 ===
    candidates.sort(reverse=True, key=lambda x: x[0])
    _, signal_type, strategy_name, signal_note, direction, extra = candidates[0]
    return signal_type, strategy_name, signal_note, direction, extra
