def print_debug_summary(symbol, indicators, latest_price, score, rrov_score, trend_score, 
                        strategy_name=None, direction=None, strategy_hit=None,
                        trend_long=None, trend_short=None, 
                        rrov_long=None, rrov_short=None, 
                        mean_long=None, mean_short=None):

    rsi = indicators['rsi'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]
    obv = indicators['obv'].iloc[-1]
    zscore = indicators['zscore'].iloc[-1]
    obv_trend = "上升" if obv - indicators['obv'].iloc[-2] > 0 else "下降"
    vwap = indicators['vwap'].iloc[-1]
    vwap_diff = latest_price - vwap
    vwap_pct = (vwap_diff / vwap) * 100
    ema_relation = "EMA5 > EMA20" if ema5 > ema20 else "EMA5 < EMA20"

    print("───────────── 技術判斷摘要 ─────────────")
    print(f"📌 股票代號：{symbol}")
    print(f"🧠 技術信心：{score:.2f}")

    if trend_long is not None and trend_short is not None:
        print(f"🎯 命中率 ➜")
        print(f"　🔹 順勢：多 {trend_long:.2f}｜空 {trend_short:.2f}")
        print(f"　🔹 RROV：多 {rrov_long:.2f}｜空 {rrov_short:.2f}")
        print(f"　🔹 均值：多 {mean_long:.2f}｜空 {mean_short:.2f}")

    print(f"📈 收盤價：${latest_price:.2f}｜RSI：{rsi:.1f}｜Z-score：{zscore:.2f}")
    print(f"📉 {ema_relation}｜VWAP乖離：{vwap_pct:.2f}%｜OBV變化：{obv_trend}")

    if strategy_name:
        print(f"📊 策略：{strategy_name}｜方向：{direction}｜命中：{strategy_hit}")

    print("─────────────────────────────────────")
