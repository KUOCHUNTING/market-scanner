import os
from datetime import datetime
import numpy as np
import pandas as pd
from modules.utils.connect_to_gsheet import connect_to_gsheet

# ✅ 安全轉換格式
def to_serializable(value):
    if value is None:
        return ""
    elif isinstance(value, list):
        return ", ".join(str(v) for v in value)
    elif isinstance(value, (np.int64, np.int32)):
        return int(value)
    elif isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return ""
    elif isinstance(value, (np.float64, np.float32)):
        return float(value)
    elif isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(value)
    elif isinstance(value, str):
        return ''.join(c for c in value if c.isprintable())
    else:
        return value

# ✅ 寫入建倉紀錄
def write_entry_to_sheet(entry: dict):
    key_base64 = os.getenv("GCP_KEY_BASE64")
    sheet_url = os.getenv("GSHEET_URL")
    if not key_base64 or not sheet_url:
        raise ValueError("❌ 環境變數 GCP_KEY_BASE64 或 GSHEET_URL 未設定")

    sheet = connect_to_gsheet(sheet_url, "建倉記錄", key_base64)

    entry_time = entry["entry_time"]
    if isinstance(entry_time, datetime):
        entry_time = entry_time.strftime("%Y-%m-%d %H:%M:%S")

    row = [
        to_serializable(entry_time),
        to_serializable(entry["symbol"]),
        to_serializable(entry["direction"]),
        to_serializable(entry["price"]),
        to_serializable(entry["shares"]),
        to_serializable(entry.get("capital_used", "")),
        to_serializable(entry["strategy_name"]),
        to_serializable(entry.get("confidence_score", "")),
        to_serializable(entry.get("signal_note", "")),
        to_serializable(entry.get("rsi", "")),
        to_serializable(entry.get("zscore", "")),
        to_serializable(entry.get("obv", "")),
        to_serializable(entry.get("vwap", "")),
        to_serializable(entry.get("ema5", "")),
        to_serializable(entry.get("ema20", "")),
        to_serializable(entry.get("bb_upper", "")),
        to_serializable(entry.get("bb_lower", "")),
        to_serializable(entry.get("trend_score", "")),
        to_serializable(entry.get("rrov_score", "")),
        to_serializable(entry.get("mean_score", ""))
    ]

    sheet.append_row(row, value_input_option="USER_ENTERED")

# ✅ 寫入出場紀錄
def write_exit_to_sheet(
    symbol,
    entry_time,
    exit_time,
    return_rate,
    pnl,
    holding_minutes,
    exit_price,
    rsi=None,
    zscore=None,
    roc=None,
    obv=None,
    vwap=None,
    ema5=None,
    ema20=None,
    strategy_name=None,
    confidence_score=None
):
    key_base64 = os.getenv("GCP_KEY_BASE64")
    sheet_url = os.getenv("GSHEET_URL")
    if not key_base64 or not sheet_url:
        raise ValueError("❌ GCP_KEY_BASE64 或 GSHEET_URL 未設定")

    sheet = connect_to_gsheet(sheet_url, "出場紀錄", key_base64)

    if isinstance(entry_time, datetime):
        entry_time = entry_time.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(exit_time, datetime):
        exit_time = exit_time.strftime("%Y-%m-%d %H:%M:%S")

    row = [
        to_serializable(symbol),
        to_serializable(entry_time),
        to_serializable(exit_time),
        to_serializable(f"{return_rate*100:.2f}%"),
        to_serializable(pnl),
        to_serializable(holding_minutes),
        to_serializable(exit_price),
        to_serializable(rsi),
        to_serializable(zscore),
        to_serializable(roc),
        to_serializable(obv),
        to_serializable(vwap),
        to_serializable(ema5),
        to_serializable(ema20),
        to_serializable(strategy_name)
    ]

    for i, val in enumerate(row):
        print(f"欄位{i}: {val}｜型別: {type(val)}")

    sheet.append_row(row, value_input_option="USER_ENTERED")
