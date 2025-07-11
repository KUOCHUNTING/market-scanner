def send_entry_push(
    symbol,
    direction,
    strategy_name,
    strategy_emoji,
    confidence_score,
    roc,
    latest_price,
    capital_used,
    capital_left,
    shares,
    rsi,
    ema5,
    ema20,
    zscore,
    vwap,
    bb_upper,
    bb_lower,
    volume_ratio,
    obv_change_text,
    trend_note,
    emoji_trend,
    trend_score,
    rrov_score,
    mean_score
):
    # ✅ 技術摘要區塊
    tech_info = (
        f"📊【技術傾向】{emoji_trend} 技術{trend_note}\n"
        f"RSI：{safe_round(rsi)}｜ROC：{safe_round(roc)}｜Z-score：{safe_round(zscore)}\n"
        f"EMA5：{safe_round(ema5)}｜EMA20：{safe_round(ema20)}｜VWAP：{safe_round(vwap)}\n"
        f"布林帶：上={safe_round(bb_upper)} / 下={safe_round(bb_lower)}\n"
        f"量比：{safe_round(volume_ratio)}｜OBV變化：{obv_change_text}"
    )

    # ✅ 策略評分區塊
    score_info = (
        f"🧠【策略信心評估】\n"
        f"📈 順勢策略命中率：{trend_score:.2f}\n"
        f"📊 RROV 策略命中率：{rrov_score:.2f}\n"
        f"🔁 均值回歸策略命中率：{mean_score:.2f}\n"
        f"⭐ 最終策略：{strategy_emoji} {strategy_name}（信心分數：{confidence_score:.2f}）"
    )

    # ✅ 建倉資訊區塊
    entry_info = (
        f"📦【建倉資訊】{symbol} ➜ {direction.upper()}（方向）\n"
        f"📥 進場價格：${latest_price:.2f}｜股數：{shares} 股\n"
        f"💵 建場資金：${capital_used:.2f}\n"
        f"💰 剩餘資金：${capital_left:,.2f}"
    )

    # ✅ 組合最終訊息
    message = (
        f"🚀【技術策略 訊號】{symbol}\n\n"
        f"{tech_info}\n\n"
        f"{score_info}\n\n"
        f"{entry_info}"
    )

    # ✅ 發送 Discord 推播
    try:
        requests.post(WEBHOOK_URL, json={"content": message})
        print(f"[✅推播成功] {symbol} 建倉通知已送出")
    except Exception as e:
        print(f"[❌推播失敗] {symbol} ➜ {e}")
