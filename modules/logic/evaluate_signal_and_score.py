def evaluate_signal_and_score(symbol, df, indicators, latest_price):
    from modules.detect_trading_signal import detect_trading_signal
    from modules.compute_confidence_score import compute_confidence_score
    from modules.logic.strategy_score import get_strategy_match_score
    
    signal_type, strategy_name, signal_note, direction, df, indicators, latest_price, \
        rrov_score, trend_score, mean_score = detect_trading_signal(symbol, df, indicators)

    score = compute_confidence_score(
        rsi=indicators['rsi'].iloc[-1],
        roc=indicators['roc'].iloc[-1],
        obv=indicators['obv'].iloc[-1],
        vwap_deviation=indicators['vwap'].iloc[-1] - latest_price,
        zscore=indicators['zscore'].iloc[-1],
        bb_deviation=(latest_price - indicators['bb_lower'].iloc[-1]) /
                     (indicators['bb_upper'].iloc[-1] - indicators['bb_lower'].iloc[-1] + 1e-6),
        ema5=indicators['ema_5'].iloc[-1],
        ema20=indicators['ema_20'].iloc[-1]
    )

    return signal_type, strategy_name, signal_note, direction, score, rrov_score, trend_score, mean_score
