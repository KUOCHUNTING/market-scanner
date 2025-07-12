def evaluate_signal_and_score(symbol, df, indicators, latest_price):
    from modules.logic.detect_trading_signal import detect_trading_signal
    from modules.compute_confidence_score import compute_confidence_score, get_strategy_match_score

    # ➤ 三策略得分
    scores = get_strategy_match_score(df, indicators, latest_price)
    rrov_score = scores['rrov'][0]
    trend_score = scores['trend'][0]
    mean_score = scores['mean'][0]

    # ➤ 判斷哪個策略命中
    if trend_score >= 1.0:
        direction = "多" if indicators["ema_5"].iloc[-1] > indicators["ema_20"].iloc[-1] else "空"
        strategy_name = f"順勢{direction}單"
        signal_type = "順勢"
    elif mean_score >= 1.0:
        direction = "多" if indicators["rsi"].iloc[-1] < 35 else "空"
        strategy_name = f"均值{direction}單"
        signal_type = "均值"
    elif rrov_score >= 1.0:
        direction = "多" if indicators["rsi"].iloc[-1] > 60 else "空"
        strategy_name = f"突破{direction}單"
        signal_type = "RROV"
    else:
        return None, None, None, None, None, rrov_score, trend_score, mean_score

    # ➤ 技術分數與摘要
    confidence_score = compute_confidence_score(
        rsi=indicators['rsi'].iloc[-1],
        roc=indicators['roc'].iloc[-1],
        obv=indicators['obv'].iloc[-1],
        vwap_deviation=indicators['vwap'].iloc[-1] - df['close'].iloc[-1],
        zscore=indicators['zscore'].iloc[-1],
        bb_deviation=(df['close'].iloc[-1] - indicators['bb_lower'].iloc[-1]) /
                     (indicators['bb_upper'].iloc[-1] - indicators['bb_lower'].iloc[-1] + 1e-6)
    )

    signal_note = "策略條件命中，符合建倉邏輯"

    return signal_type, strategy_name, signal_note, direction, confidence_score, rrov_score, trend_score, mean_score
