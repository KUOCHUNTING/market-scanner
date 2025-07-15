from modules.compute_confidence_score import get_strategy_match_score

def get_mean_score(indicators, latest_price):
    zscore = indicators["zscore"].iloc[-1]
    bb_upper = indicators["bb_upper"].iloc[-1]
    bb_lower = indicators["bb_lower"].iloc[-1]

    # 做多條件
    if zscore < -1.5 and latest_price < bb_lower * 1.02:
        conditions = {
            "Z-score 過低": zscore < -1.5,
            "接近下軌": latest_price < bb_lower * 1.02
        }
        return get_strategy_match_score("均值回歸 多頭", conditions)

    # 做空條件
    if zscore > 1.5 and latest_price > bb_upper * 0.98:
        conditions = {
            "Z-score 過高": zscore > 1.5,
            "接近上軌": latest_price > bb_upper * 0.98
        }
        return get_strategy_match_score("均值回歸 空頭", conditions)

    return 0.0
