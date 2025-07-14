def build_entry_message(symbol, price, strategy_name, direction, confidence_score,
                        rsi=None, zscore=None,
                        ema5=None, ema20=None,
                        bb_upper=None, bb_lower=None, obv=None,
                        strategy_type=None,
                        trend_score=None, rrov_score=None, mean_score=None,
                        signal_note="", shares=None, capital_used=None, capital_left=None):
    
    direction_label = "多單" if direction == "多" else "空單"
    signal_type_label = f"【 {direction_label} 技術策略 訊號】{symbol}"

    message = f"{signal_type_label}\n"
    message += f"類型：{strategy_type or '未分類'}（方向：{direction}）\n"
    message += f"命中率 ➜ 順勢：{trend_score:.2f}｜RROV：{rrov_score:.2f}｜均值：{mean_score:.2f}\n"
    message += f"技術信心：{confidence_score:.2f}\n"
    message += f"收盤價：${price:.2f}｜RSI：{rsi:.1f if rsi is not None else 'N/A'}｜Z-score：{zscore:.2f if zscore is not None else 'N/A'}\n"
    message += f"訊號摘要：{signal_note}\n"
    message += f"策略名稱：{strategy_name}\n"
    message += f"股數：{shares} 股｜進場資金：${capital_used:,.0f}｜剩餘資金：${capital_left:,.0f}"
    
    return message
    
# ✅ 擠壓策略推播訊息（多空雙向皆可）
def build_breakout_message(result):
    symbol = result.get("symbol", "未知代號")
    direction = result.get("direction", "未知方向")
    score = result.get("score", 0)
    conditions = result.get("conditions_met", [])
    close = result.get("close", 0)
    rsi = result.get("rsi", None)
    ema_5 = result.get("ema_5", None)
    ema_20 = result.get("ema_20", None)
    strategy_name = result.get("strategy_name", "擠壓策略")

    emoji = "🚀" if direction == "做多" else "💥"

    message  = f"{emoji}【擠壓策略觸發】{symbol}｜{strategy_name}\n\n"
    message += f"📌 收盤價：${close:.2f}｜RSI：{rsi:.1f}\n"
    message += f"📈 EMA5：{ema_5:.2f}｜EMA20：{ema_20:.2f}\n"
    message += f"🎯 命中條件（{score}）項：\n"
    message += "\n".join([f"- {c}" for c in conditions]) + "\n\n"
    message += f"📊 判定方向：{direction}"

    return message
