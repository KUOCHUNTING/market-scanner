from modules.strategy.rrov import get_rrov_score
from modules.strategy.trend import get_trend_score
from modules.strategy.mean_reversion import get_mean_score
from modules.strategy.squeeze_breakout import detect_squeeze_breakout
from modules.config.strategy_thresholds import THRESHOLDS

def detect_trading_signal(symbol, df, indicators, latest_price):
    candidates = []

    # ✅ 擠壓策略（需 df 參與）
    squeeze_result = detect_squeeze_breakout(symbol, indicators, df)
    if squeeze_result:
        score = squeeze_result.get("score", 1.0)
        candidates.append((
            score,
            "squeeze_breakout",
            squeeze_result["strategy_name"],
            "Squeeze OFF + 技術條件命中",
            squeeze_result["direction"],
            squeeze_result
        ))

    # ✅ RROV 策略
    rrov_score = get_rrov_score(indicators, latest_price)
    if rrov_score >= THRESHOLDS["rrov"]:
        direction = "做多" if latest_price > indicators["bb_upper"].iloc[-1] else "做空"
        candidates.append((
            rrov_score,
            "rrov",
            f"RROV {direction}",
            "布林突破 + 放量 + 短線趨勢",
            direction,
            None
        ))

    # ✅ 順勢策略
    trend_score = get_trend_score(indicators)
    if trend_score >= THRESHOLDS["trend"]:
        ema5 = indicators["ema_5"].iloc[-1]
        ema20 = indicators["ema_20"].iloc[-1]
        rsi = indicators["rsi"].iloc[-1]
        if ema5 > ema20 and rsi > 60:
            direction = "做多"
        elif ema5 < ema20 and rsi < 40:
            direction = "做空"
        else:
            direction = None

        if direction:
            candidates.append((
                trend_score,
                "trend",
                f"順勢 {direction}",
                "EMA 趨勢排列 + RSI 支撐",
                direction,
                None
            ))

    # ✅ 均值回歸策略
    mean_score = get_mean_score(indicators, latest_price)
    if mean_score >= THRESHOLDS["mean"]:
        z = indicators["zscore"].iloc[-1]
        direction = "做多" if z < -1.5 else "做空" if z > 1.5 else None
        if direction:
            candidates.append((
                mean_score,
                "mean",
                f"均值回歸 {direction}",
                f"Z-score 過度乖離 ({z:.2f})",
                direction,
                None
            ))

    if not candidates:
        return None, None, None, None, None

    # ✅ 按分數高低排序
    candidates.sort(reverse=True, key=lambda x: x[0])
    return candidates[0]  # score, type, name, note, direction, extra
