from modules.compute_confidence_score import get_strategy_match_score

def get_trend_score(indicators):
    ema5 = indicators["ema_5"].iloc[-1]
    ema20 = indicators["ema_20"].iloc[-1]
    rsi = indicators["rsi"].iloc[-1]

    # === 做多邏輯 ===
    if ema5 > ema20 and rsi > 60:
        conditions = {
            "RSI 強勢": rsi > 60,
            "均線多頭": ema5 > ema20
        }
        return get_strategy_match_score("順勢 多頭", conditions)

    # === 做空邏輯 ===
    elif ema5 < ema20 and rsi < 40:
        conditions = {
            "RSI 弱勢": rsi < 40,
            "均線空頭": ema5 < ema20
        }
        return get_strategy_match_score("順勢 空頭", conditions)

    return 0.0
