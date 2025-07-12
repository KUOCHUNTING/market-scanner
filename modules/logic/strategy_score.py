def get_all_strategy_scores(df, indicators, latest_price):
    """
    一次回傳所有策略分數（僅分數值，不含文字說明）
    格式：{ "trend": (0.7,), "mean": (0.4,), "rrov": (0.9,) }
    """
    return {
        "trend": (get_strategy_match_score(df, indicators, latest_price, "trend")[0],),
        "mean": (get_strategy_match_score(df, indicators, latest_price, "mean")[0],),
        "rrov": (get_strategy_match_score(df, indicators, latest_price, "rrov")[0],)
    }
    if len(df) < 60:
        return (0.0, "資料不足")

    try:
        rsi = indicators['rsi'].iloc[-1]
        zscore = indicators['zscore'].iloc[-1]
        ema5 = indicators['ema_5'].iloc[-1]
        ema20 = indicators['ema_20'].iloc[-1]
        vwap = indicators['vwap'].iloc[-1]
        roc = indicators['roc'].iloc[-1]
        close = df['close'].iloc[-1]
        upper = indicators['bb_upper'].iloc[-1]
        lower = indicators['bb_lower'].iloc[-1]
    except KeyError as e:
        return (0.0, f"指標缺失：{e}")

    # === 順勢策略 ===
    if strategy_type == "trend":
        score = 0
        if ema5 > ema20:
            score += 0.4
        if close > vwap:
            score += 0.3
        if rsi > 55:
            score += 0.3
        return (round(min(score, 1.0), 2), "順勢策略得分")

    # === 均值回歸策略 ===
    elif strategy_type == "mean":
        score = 0
        if rsi < 35 or rsi > 70:
            score += 0.4
        if zscore < -1.5 or zscore > 1.5:
            score += 0.3
        if close < lower or close > upper:
            score += 0.3
        return (round(min(score, 1.0), 2), "均值回歸策略得分")

    # === RROV 策略（突破） ===
    elif strategy_type == "rrov":
        score = 0
        recent_high = df['high'].iloc[-10:].max()
        recent_low = df['low'].iloc[-10:].min()

        if close > recent_high:
            score += 0.5  # 多單突破
        elif close < recent_low:
            score += 0.5  # 空單跌破

        if abs(close - vwap) > 0.03 * close:
            score += 0.2
        if rsi > 60 or rsi < 40:
            score += 0.2
        if abs(roc) > 2:
            score += 0.1

        return (round(min(score, 1.0), 2), "RROV 策略得分")

    # === 其他 ===
    return (0.0, f"未知策略：{strategy_type}")
