from modules.enter_position import enter_position

def execute_entry(symbol, price, direction, score, strategy_name, indicators, capital_left):
    shares, capital_used, capital_left = enter_position(
        symbol=symbol,
        price=price,
        direction=direction,
        signal_note=f"{strategy_name} 訊號",
        rsi=indicators['rsi'].iloc[-1],
        zscore=indicators['zscore'].iloc[-1],
        strategy_name=strategy_name,
        ema5=indicators['ema_5'].iloc[-1],
        ema20=indicators['ema_20'].iloc[-1],
        roc=indicators['roc'].iloc[-1],
        obv=indicators['obv'].iloc[-1],
        vwap=indicators['vwap'].iloc[-1],
        confidence_score=score,
        strategy_display=strategy_name,
        match_score=None,
        ema_trend=None,
        up_count=0,
        down_count=0
    )
    return shares, capital_used, capital_left  # ✅ 加入 capital_left 回傳
