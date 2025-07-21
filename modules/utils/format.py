import numpy as np
import pandas as pd


def clean_string(s: str) -> str:
    """
    清洗字串內容，移除控制符號與不可列印字元
    """
    return ''.join(c for c in str(s) if c.isprintable()).strip()

def to_serializable(value):
    import numpy as np
    import pandas as pd

    if value is None:
        return ""
    elif isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value if v is not None)
    elif isinstance(value, (np.int64, np.int32, int)):
        return int(value)
    elif isinstance(value, (np.float64, np.float32, float)):
        if np.isnan(value) or np.isinf(value):
            return ""
        return round(float(value), 4)  # ✅ 保留最多 4 位小數
    elif isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(value)
    elif isinstance(value, bool):
        return str(value)
    elif isinstance(value, str):
        try:
            value.encode("utf-8")
            return ''.join(c for c in value if c.isprintable())
        except UnicodeEncodeError:
            return "[非法字元]"
    else:
        try:
            return str(value)
        except:
            return "[無法序列化]"

def safe_float(value, decimals=2, prefix="", suffix="", fill="--"):
    """
    安全格式化浮點數（防止 NoneType、格式錯誤），可補空白或固定填充字元
    """
    try:
        f = round(float(value), decimals)
        return f"{prefix}{f:.{decimals}f}{suffix}"
    except Exception:
        return fill

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

def safe_symbol(symbol):
    """
    安全格式化 symbol 名稱，避免 None / 空字串 造成 Discord 推播錯誤
    """
    try:
        s = str(symbol).strip()
        return s if s else "未知代號"
    except Exception:
        return "未知代號"
