def get_rrov_score_short(indicators, latest_price):
    return get_strategy_match_score('RROV-空', {
        "跌破支撐": latest_price < indicators['bb_lower'].iloc[-1],
        "量能放大": indicators['curr_volume'] > indicators['avg_volume'] * 1.2,
        "短期弱勢": latest_price < indicators['ema_5'].iloc[-1]
    })

def get_trend_score_short(indicators):
    return get_strategy_match_score('順勢策略-空', {
        "RSI弱勢": indicators['rsi'].iloc[-1] < 40,
        "均線空頭": indicators['ema_5'].iloc[-1] < indicators['ema_20'].iloc[-1],
    })

def get_mean_score_short(indicators, latest_price):
    return get_strategy_match_score('均值回歸-空', {
        "Z-score高": indicators['zscore'].iloc[-1] > 1.0,
        "接近上軌": latest_price > indicators['bb_upper'].iloc[-1] * 0.98
    })
