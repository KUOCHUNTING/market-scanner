def get_strategy_match_score(symbol, df, indicators, strategy_type):
    if strategy_type == "順勢":
        # 多方條件
        long_score = 0
        if indicators["ema_5"].iloc[-1] > indicators["ema_20"].iloc[-1]:
            long_score += 1
        if indicators["rsi"].iloc[-1] > 55:
            long_score += 1

        # 空方條件
        short_score = 0
        if indicators["ema_5"].iloc[-1] < indicators["ema_20"].iloc[-1]:
            short_score += 1
        if indicators["rsi"].iloc[-1] < 45:
            short_score += 1

        return round(long_score / 2, 2), round(short_score / 2, 2)

    elif strategy_type == "RROV":
        long_score = 0
        if df["close"].iloc[-1] > df["open"].iloc[-1] * 1.01:
            long_score += 1
        if indicators["obv"].iloc[-1] > indicators["obv"].iloc[-2]:
            long_score += 1

        short_score = 0
        if df["close"].iloc[-1] < df["open"].iloc[-1] * 0.99:
            short_score += 1
        if indicators["obv"].iloc[-1] < indicators["obv"].iloc[-2]:
            short_score += 1

        return round(long_score / 2, 2), round(short_score / 2, 2)

    elif strategy_type == "均值":
        z = indicators["zscore"].iloc[-1]
        rsi = indicators["rsi"].iloc[-1]
        bb_lower = indicators.get("bb_lower", df["close"]).iloc[-1]
        bb_upper = indicators.get("bb_upper", df["close"]).iloc[-1]
        close = df["close"].iloc[-1]

        long_score = 0
        if z < -1.2:
            long_score += 1
        if rsi < 35:
            long_score += 1
        if close < bb_lower:
            long_score += 1

        short_score = 0
        if z > 1.2:
            short_score += 1
        if rsi > 65:
            short_score += 1
        if close > bb_upper:
            short_score += 1

        return round(long_score / 3, 2), round(short_score / 3, 2)

    return 0.0, 0.0

def select_best_strategy(df, indicators):
    # 三策略命中率（long / short）
    trend_long, trend_short = get_strategy_match_score(df, indicators, "順勢")
    rrov_long, rrov_short   = get_strategy_match_score(df, indicators, "RROV")
    mean_long, mean_short   = get_strategy_match_score(df, indicators, "均值")

    candidates = [
        ("順勢", "多", trend_long),
        ("順勢", "空", trend_short),
        ("RROV", "多", rrov_long),
        ("RROV", "空", rrov_short),
        ("均值", "多", mean_long),
        ("均值", "空", mean_short)
    ]

    # 取滿分策略中分數最高的（先找 == 1.0）
    full_score_strategies = [c for c in candidates if c[2] == 1.0]
    if full_score_strategies:
        # ✅ 策略命中（滿分）
        best = full_score_strategies[0]  # 或 max(full_score_strategies, key=lambda x: x[2])
        return best[0], best[1], best[2]
    
    # ❌ 沒有策略達到滿分
    return None, None, 0.0
