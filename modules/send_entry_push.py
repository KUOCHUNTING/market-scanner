def send_entry_push(symbol, direction, strategy_name, strategy_emoji, confidence_score, roc, latest_price, capital_used, capital_left, shares, rsi, ema5, ema20, zscore, vwap, bb_upper, bb_lower, volume_ratio, obv_change_text, trend_note, emoji_trend, trend_score, rrov_score, mean_score):
    # ✅ 技術指標整合推播內容
    tech_info = (
        f"[技術傾向] {emoji_trend} 技術{trend_note}（僅供參考）|{symbol} ➜\n"
        f"RSI={safe_round(rsi)}｜EMA5={safe_round(ema5)}｜EMA20={safe_round(ema20)}｜"
        f"Z-score={safe_round(zscore)}｜VWAP={safe_round(vwap)}｜ROC={safe_round(roc)}\n"
        f"布林通道：上={safe_round(bb_upper)} / 下={safe_round(bb_lower)}｜"
        f"量比={safe_round(volume_ratio)}｜OBV變化：{obv_change_text}"
    )

    # ✅ 組合完整推播內容
    message = (
        f"{tech_info}\n\n"
        f"[策略診斷] {symbol} ➜ 順勢={trend_score:.2f}｜RROV={rrov_score:.2f}｜均值回歸={mean_score:.2f}\n"
        f"[策略選擇] {symbol} ➜ 使用{strategy_name}（命中 {int(max(trend_score, rrov_score, mean_score) * 100)}%）\n"
        f"[✅紀錄] 已建倉：{symbol} @ ${latest_price:.2f}|方向：{direction}|股數：{shares}|策略：{strategy_emoji}"
    )

    # ✅ 發送 Discord 推播
    try:
        requests.post(WEBHOOK_URL, json={"content": message})
        print(f"[✅推播成功] {symbol} 建倉通知已送出")
    except Exception as e:
        print(f"[❌推播失敗] {symbol} ➜ {e}")