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
