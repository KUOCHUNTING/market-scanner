import pandas as pd
import math

def log_invalid_indicator(message):
    try:
        with open("invalid_indicators_log.txt", "a") as f:
            f.write(f"{message}\n")
    except Exception as e:
        print(f"[Log 錯誤] 無法寫入 log：{e}")

def is_invalid(indicators):
    if indicators is None or not isinstance(indicators, dict):
        print("[指標錯誤] indicators 為 None 或不是字典")
        log_invalid_indicator("indicators 無效格式")
        return True

    for key, val in indicators.items():
        if val is None:
            print(f"[指標錯誤] {key} 是 None ➜ 無效")
            log_invalid_indicator(f"{key} = None")
            return True

        # 若為 Series，只檢查最後一筆是否為 NaN
        if isinstance(val, pd.Series):
            if len(val) == 0 or pd.isna(val.iloc[-1]):
                print(f"[指標錯誤] {key} 尾端是 NaN ➜ 無效")
                log_invalid_indicator(f"{key} 尾端是 NaN")
                return True

        # 若為 float/int，直接檢查是否為 NaN
        elif isinstance(val, (float, int)):
            if math.isnan(val):
                print(f"[指標錯誤] {key} 是 NaN ➜ 無效")
                log_invalid_indicator(f"{key} 是 NaN")
                return True

    return False
