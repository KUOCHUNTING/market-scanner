# modules/strategy/strategy_score.py

from modules.compute_confidence_score import get_strategy_match_score

def get_rrov_score(indicators, latest_price):
    return get_strategy_match_score('RROV', {
        "突破壓力": latest_price > indicators['bb_upper'].iloc[-1],
        "量能放大": indicators['curr_volume'] > indicators['avg_volume'] * 1.2,
        "短期強勢": latest_price > indicators['ema_5'].iloc[-1]
    })

def get_trend_score(indicators):
    return get_strategy_match_score('順勢策略', {
        "RSI強勢": indicators['rsi'].iloc[-1] > 60,
        "均線多頭": indicators['ema_5'].iloc[-1] > indicators['ema_20'].iloc[-1],
    })

def get_mean_score(indicators, latest_price):
    return get_strategy_match_score('均值回歸', {
        "Z-score低": indicators['zscore'].iloc[-1] < -1.0,
        "接近下軌": latest_price < indicators['bb_lower'].iloc[-1] * 1.02
    })
