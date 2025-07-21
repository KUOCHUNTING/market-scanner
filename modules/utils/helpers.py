def get_last_value(series):
    """
    安全取得 Series 的最後一筆數值（非空值）
    """
    try:
        if series is not None and len(series) > 0:
            return float(series.iloc[-1])  # ✅ 用 iloc[-1] 避開警告
    except:
        pass
    return None
