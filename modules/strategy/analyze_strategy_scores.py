def analyze_strategy_scores(indicators, latest_price):
    from modules.strategy.strategy_score import (
        get_rrov_scores, get_trend_scores, get_mean_scores
    )
    rrov_long, rrov_short = get_rrov_scores(indicators, latest_price)
    trend_long, trend_short = get_trend_scores(indicators)
    mean_long, mean_short = get_mean_scores(indicators, latest_price)

    return {
        "rrov": (rrov_long, rrov_short),
        "trend": (trend_long, trend_short),
        "mean": (mean_long, mean_short)
    }
