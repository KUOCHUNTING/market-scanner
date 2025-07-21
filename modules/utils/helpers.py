def get_last_value(series):
    """
    取得指標的最後一筆非空值
    """
    try:
        if series is not None and len(series) > 0:
            return float(series[-1])
    except:
        pass
    return None
