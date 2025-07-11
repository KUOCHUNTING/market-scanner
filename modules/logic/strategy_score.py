def get_strategy_match_score(symbol, df, indicators, strategy_type):
    if strategy_type == "順勢":
        long_score = 1.0 if indicators["ema_5"].iloc[-1] > indicators["ema_20"].iloc[-1] and indicators["rsi"].iloc[-1] > 55 else 0.4
        short_score = 1.0 if indicators["ema_5"].iloc[-1] < indicators["ema_20"].iloc[-1] and indicators["rsi"].iloc[-1] < 45 else 0.4
        return long_score, short_score

    elif strategy_type == "RROV":
        long_k = df["close"].iloc[-1] > df["open"].iloc[-1] * 1.01
        obv_up = indicators["obv"].iloc[-1] > indicators["obv"].iloc[-2]
        short_k = df["close"].iloc[-1] < df["open"].iloc[-1] * 0.99
        obv_down = indicators["obv"].iloc[-1] < indicators["obv"].iloc[-2]
        long_score = 0.8 if long_k and obv_up else 0.3
        short_score = 0.8 if short_k and obv_down else 0.3
        return long_score, short_score

    elif strategy_type == "均值":
        z = indicators["zscore"].iloc[-1]
        return (1.0 if z < -1.5 else 0.4), (1.0 if z > 1.5 else 0.4)

    return 0.0, 0.0
