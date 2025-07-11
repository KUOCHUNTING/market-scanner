# modules/strategy/strategy_score.py

from modules.compute_confidence_score import get_strategy_match_score

def get_rrov_scores(indicators, latest_price):
    long_score = get_strategy_match_score('RROV', {
        "突破壓力": latest_price > indicators['bb_upper'].iloc[-1],
        "量能放大": indicators['curr_volume'] > indicators['avg_volume'] * 1.2,
        "短期強勢": latest_price > indicators['ema_5'].iloc[-1]
    })
    short_score = get_strategy_match_score('RROV', {
        "跌破支撐": latest_price < indicators['bb_lower'].iloc[-1],
        "量能放大": indicators['curr_volume'] > indicators['avg_volume'] * 1.2,
        "短期弱勢": latest_price < indicators['ema_5'].iloc[-1]
    })
    return long_score, short_score

def get_trend_scores(indicators):
    long_score = get_strategy_match_score('順勢策略', {
        "RSI強勢": indicators['rsi'].iloc[-1] > 60,
        "均線多頭": indicators['ema_5'].iloc[-1] > indicators['ema_20'].iloc[-1]
    })
    short_score = get_strategy_match_score('順勢策略', {
        "RSI弱勢": indicators['rsi'].iloc[-1] < 40,
        "均線空頭": indicators['ema_5'].iloc[-1] < indicators['ema_20'].iloc[-1]
    })
    return long_score, short_score

def get_mean_scores(indicators, latest_price):
    long_score = get_strategy_match_score('均值回歸', {
        "Z-score低": indicators['zscore'].iloc[-1] < -1.0,
        "接近下軌": latest_price < indicators['bb_lower'].iloc[-1] * 1.02
    })
    short_score = get_strategy_match_score('均值回歸', {
        "Z-score高": indicators['zscore'].iloc[-1] > 1.0,
        "接近上軌": latest_price > indicators['bb_upper'].iloc[-1] * 0.98
    })
    return long_score, short_score
