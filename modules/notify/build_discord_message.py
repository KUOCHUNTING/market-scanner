def build_entry_message(
    symbol, direction, signal_note, latest_price, score,
    strategy_name, rsi, zscore, shares, capital_used,
    capital_left, rrov_score, trend_score, mean_score
):
    direction_label = "多單" if direction == "多" else "空單"
    signal_type_label = f"【 {direction_label} 技術策略 訊號】{symbol}"

    message = f"{signal_type_label}\n"
    message += f"類型：{direction}（方向：{direction}）\n"
    message += f"命中率 ➜ 順勢：{trend_score:.2f}｜RROV：{rrov_score:.2f}｜均值：{mean_score:.2f}\n"
    message += f"技術信心：{score:.2f}\n"
    message += f"收盤價：${latest_price:.2f}｜RSI：{rsi:.1f}｜Z-score：{zscore:.2f}\n"
    message += f"訊號摘要：{signal_note}\n"
    message += f"策略名稱：{strategy_name}\n"
    message += f"股數：{shares} 股｜進場資金：${capital_used:.0f}｜剩餘資金：${capital_left:,.0f}"
    return message
