# modules/utils/format.py

import numpy as np
import pandas as pd

def to_serializable(value):
    if value is None:
        return ""
    elif isinstance(value, (np.int64, np.int32)):
        return int(value)
    elif isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return ""
    elif isinstance(value, (np.float64, np.float32)):
        return float(value)
    elif isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(value)
    elif isinstance(value, str):
        # ✅ 移除控制字元、不能編碼的字元
        try:
            value.encode("utf-8")  # 測試是否能被 json 處理
            return ''.join(c for c in value if c.isprintable())
        except UnicodeEncodeError:
            return "[非法字元]"
    else:
        return value

def safe_float(value, decimals=2, prefix="", suffix=""):
    """
    安全格式化浮點數（防止 NoneType、格式錯誤）
    """
    try:
        f = round(float(value), decimals)
        return f"{prefix}{f:.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"

def safe_int(value, prefix="", suffix=""):
    """
    安全格式化整數
    """
    try:
        i = int(round(float(value)))
        return f"{prefix}{i}{suffix}"
    except (TypeError, ValueError):
        return "N/A"

def safe_percent(value, decimals=1):
    """
    安全格式化為百分比字串（乘 100 後加上 %）
    """
    try:
        percent = round(float(value) * 100, decimals)
        return f"{percent:.{decimals}f}%"
    except (TypeError, ValueError):
        return "N/A"

def get_last_value(series):
    if series is None or not hasattr(series, 'iloc'):
        return None
    if len(series) == 0:
        return None
    return series.iloc[-1]
