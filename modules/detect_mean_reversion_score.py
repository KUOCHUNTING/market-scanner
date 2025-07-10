def detect_mean_reversion_score(df, symbol):
    if len(df) < 60:
        return 0.0

    indicators = calculate_indicators(df)
    required_keys = ['rsi', 'zscore', 'ema_5', 'ema_20', 'bb_lower', 'bb_upper', 'vwap', 'obv']
    for key in required_keys:
        if key not in indicators or indicators[key].isna().iloc[-1]:
            return 0.0

    latest_price = df['close'].iloc[-1]
    latest_rsi = indicators['rsi'].iloc[-1]
    prev_rsi = indicators['rsi'].iloc[-2]
    zscore = indicators['zscore'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]
    lower_band = indicators['bb_lower'].iloc[-1]
    upper_band = indicators['bb_upper'].iloc[-1]

    score = 0.0

    # 多單方向評分
    if latest_price < lower_band:
        score += 0.25
    if latest_rsi > prev_rsi and latest_rsi < 40:
        score += 0.25
    if zscore < -1:
        score += 0.25
    if ema5 > ema20:
        score += 0.25

    # 空單方向評分（可選擇是否納入）
    if latest_price > upper_band:
        score += 0.25
    if latest_rsi < prev_rsi and latest_rsi > 60:
        score += 0.25
    if zscore > 1:
        score += 0.25
    if ema5 < ema20:
        score += 0.25

    return round(score, 2)