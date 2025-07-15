# ✅ 擠壓策略建倉處理
def handle_squeeze_entry(symbol, squeeze_result, enter_position, send_discord_message, build_breakout_message, webhook_url):
    msg = build_breakout_message(squeeze_result)
    send_discord_message(webhook_url, msg)

    shares, capital_used, _ = enter_position(
        symbol=symbol,
        price=squeeze_result["close"],
        direction=squeeze_result["direction"],
        score=squeeze_result["score"],
        strategy_name=squeeze_result["strategy_name"],
        rsi=squeeze_result.get("rsi"),
        ema5=squeeze_result.get("ema_5"),
        ema20=squeeze_result.get("ema_20"),
        signal_note="Squeeze OFF + 技術條件命中"
    )
    return shares, capital_used