from modules.compute_confidence_score import get_strategy_match_score

def get_rrov_score(indicators, latest_price):
    is_breakout = latest_price > indicators["bb_upper"].iloc[-1]
    is_breakdown = latest_price < indicators["bb_lower"].iloc[-1]
    volume_surge = indicators["curr_volume"] > indicators["avg_volume"] * 1.2
    ema5 = indicators["ema_5"].iloc[-1]
    ema20 = indicators["ema_20"].iloc[-1]

    # 做多邏輯
    if is_breakout and volume_surge and latest_price > ema5 and ema5 > ema20:
        conditions = {
            "突破壓力": is_breakout,
            "量能放大": volume_surge,
            "短期強勢": latest_price > ema5,
            "均線多頭": ema5 > ema20
        }
        return get_strategy_match_score("RROV 多頭", conditions)

    # 做空邏輯
    if is_breakdown and volume_surge and latest_price < ema5 and ema5 < ema20:
        conditions = {
            "跌破支撐": is_breakdown,
            "放量下殺": volume_surge,
            "短線轉弱": latest_price < ema5,
            "均線空頭": ema5 < ema20
        }
        return get_strategy_match_score("RROV 空頭", conditions)

    return 0.0
