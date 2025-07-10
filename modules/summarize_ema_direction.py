def summarize_ema_direction(ema_series):
    results = []
    prev_direction = None
    start_time = None

    for i in range(len(ema_series)):
        direction = ema_series.iloc[i]
        time = ema_series.index[i]

        if direction != prev_direction:
            if prev_direction is not None:
                results.append((start_time, prev_time, prev_direction))
            start_time = time
        prev_direction = direction
        prev_time = time

    # 補上最後一段
    if prev_direction is not None:
        results.append((start_time, prev_time, prev_direction))

    # 格式化輸出
    summary = []
    for start, end, direction in results:
        count = len(ema_series[(ema_series.index >= start) & (ema_series.index <= end)])
        summary.append(f"{start.strftime('%m/%d %H:%M')} ～ {end.strftime('%H:%M')}：{direction}（{count}根）")

    return summary