def execute_entry(symbol, latest_price, direction, score, strategy_name, indicators, capital_left):
    from modules.enter_position import enter_position
    result = enter_position(symbol, latest_price, direction, score, strategy_name)
    if result is None:
        return None, None, None

    shares, capital_used = result[:2]
    ema_trend = "多頭" if indicators['ema_5'].iloc[-1] > indicators['ema_20'].iloc[-1] else "空頭"
    return shares, capital_used, ema_trend
