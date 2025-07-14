# modules/utils/format.py

def safe_float(val, digits=2, prefix="$", suffix=""):
    """
    安全格式化浮點數：
    - val 為 None 時回傳 'N/A'
    - digits 控制小數位數
    - 可選擇加上 $、%、等符號
    """
    if val is None:
        return "N/A"
    try:
        return f"{prefix}{val:.{digits}f}{suffix}"
    except:
        return "N/A"
