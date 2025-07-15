def detect_trading_signal(symbol, df, indicators, latest_price=None):
    signal_type = None
    strategy_name = None
    signal_note = ""
    direction = None
    extra = {}

    # === 防呆取值 ===
    rsi = indicators.get("rsi", [None])[-1]
    zscore = indicators.get("zscore", [None])[-1]
    ema5 = indicators.get("ema_5", [None])[-1]
    ema20 = indicators.get("ema_20", [None])[-1]
    bb_upper = indicators.get("bb_upper", [None])[-1]
    bb_lower = indicators.get("bb_lower", [None])[-1]
    curr_volume = indicators.get("curr_volume", None)
    avg_volume = indicators.get("avg_volume", None)

    # === RROV 多單策略 ===
    if (
        latest_price is not None and
        bb_upper is not None and
        curr_volume is not None and
        avg_volume is not None and
        ema5 is not None and
        latest_price > bb_upper and
        curr_volume > avg_volume * 1.2 and
        latest_price > ema5
    ):
        signal_type = "技術策略"
        strategy_name = "RROV 策略"
        signal_note = "突破布林上軌 + 放量 + EMA 突破"
        direction = "做多"
        return signal_type, strategy_name, signal_note, direction, extra

    # === RROV 空單策略 ===
    if (
        latest_price is not None and
        bb_lower is not None and
        curr_volume is not None and
        avg_volume is not None and
        ema5 is not None and
        latest_price < bb_lower and
        curr_volume > avg_volume * 1.2 and
        latest_price < ema5
    ):
        signal_type = "技術策略"
        strategy_name = "RROV 策略"
        signal_note = "跌破布林下軌 + 放量 + EMA 跌破"
        direction = "做空"
        return signal_type, strategy_name, signal_note, direction, extra

    # === 順勢策略：多單 ===
    if (
        rsi is not None and
        ema5 is not None and
        ema20 is not None and
        rsi > 60 and
        ema5 > ema20
    ):
        signal_type = "技術策略"
        strategy_name = "順勢策略"
        signal_note = "EMA 趨勢明確 + RSI 動能支撐"
        direction = "做多"
        return signal_type, strategy_name, signal_note, direction, extra

    # === 順勢策略：空單 ===
    if (
        rsi is not None and
        ema5 is not None and
        ema20 is not None and
        rsi < 40 and
        ema5 < ema20
    ):
        signal_type = "技術策略"
        strategy_name = "順勢策略"
        signal_note = "EMA 空頭排列 + RSI 虛弱"
        direction = "做空"
        return signal_type, strategy_name, signal_note, direction, extra

    # === 均值回歸策略 ===
    if zscore is not None:
        if zscore < -1.5:
            signal_type = "技術策略"
            strategy_name = "均值回歸"
            signal_note = f"Z-score = {round(zscore, 2)} 過度乖離"
            direction = "做多"
            return signal_type, strategy_name, signal_note, direction, extra
        elif zscore > 1.5:
            signal_type = "技術策略"
            strategy_name = "均值回歸"
            signal_note = f"Z-score = {round(zscore, 2)} 過度乖離"
            direction = "做空"
            return signal_type, strategy_name, signal_note, direction, extra

    return None, None, None, None, None
