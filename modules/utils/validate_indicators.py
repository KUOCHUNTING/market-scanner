# modules/utils/validate_indicators.py
import pandas as pd
import math

def log_invalid_indicator(message):
    with open("invalid_indicators_log.txt", "a") as f:
        f.write(f"{message}\n")

def is_invalid(indicators):
    for key, val in indicators.items():
        if val is None:
            print(f"[指標錯誤] {key} 是 None ➜ 無效")
            log_invalid_indicator(key)
            return True
        if isinstance(val, pd.Series):
            if val.isna().any():
                print(f"[指標錯誤] {key} 有 NaN 值 ➜ 無效")
                log_invalid_indicator(key)
                return True
        elif isinstance(val, (float, int)) and math.isnan(val):
            print(f"[指標錯誤] {key} 是 NaN ➜ 無效")
            log_invalid_indicator(key)
            return True
    return False