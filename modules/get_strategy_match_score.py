def get_strategy_match_score(symbol, df, indicators, strategy_type):
    # 根據每支股票的技術指標回傳該策略的命中率
    if strategy_type == "順勢":
        # 模擬：根據 EMA 趨勢與 RSI 判斷命中率
        long_score = 1.0 if indicators["ema_5"].iloc[-1] > indicators["ema_20"].iloc[-1] and indicators["rsi"].iloc[-1] > 55 else 0.4
        short_score = 1.0 if indicators["ema_5"].iloc[-1] < indicators["ema_20"].iloc[-1] and indicators["rsi"].iloc[-1] < 45 else 0.4
        return long_score, short_score

    elif strategy_type == "RROV":
        # 模擬：突破長紅 + OBV 上升為命中
        if (df["close"].iloc[-1] > df["open"].iloc[-1] * 1.01) and (indicators["obv"].iloc[-1] > indicators["obv"].iloc[-2]):
            return 0.8, 0.3
        else:
            return 0.3, 0.3

    elif strategy_type == "均值":
        # 模擬：Z-score 超出區間視為偏離，分數高
        z = indicators["zscore"].iloc[-1]
        return (1.0 if z < -1.5 else 0.4), (1.0 if z > 1.5 else 0.4)

    return 0.0, 0.0
