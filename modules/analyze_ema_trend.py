# analyze_ema_trend.py
def analyze_ema_trend(df):
    """
    分析過去 20 根 K 線的 EMA 趨勢：上彎 / 下彎
    回傳統計結果文字
    """
    try:
        ema5 = df["ema_5"]
        ema20 = df["ema_20"]
        trend_list = []

        for i in range(-20, 0):
            if ema5.iloc[i] > ema20.iloc[i]:
                trend_list.append("上彎")
            elif ema5.iloc[i] < ema20.iloc[i]:
                trend_list.append("下彎")
            else:
                trend_list.append("持平")

        up = trend_list.count("上彎")
        down = trend_list.count("下彎")
        bias = "偏多" if up > down else "偏空" if down > up else "盤整"
        return f"EMA 趨勢：上彎 {up} 次｜下彎 {down} 次（{bias}）"
    except Exception as e:
        return f"分析失敗：{e}"
