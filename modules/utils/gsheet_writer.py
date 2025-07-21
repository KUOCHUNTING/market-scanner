import os
from datetime import datetime
from modules.utils.connect_to_gsheet import connect_to_gsheet
from modules.utils.format import to_serializable

# ✅ 建倉資料寫入
def write_entry_to_sheet(entry: dict, sheet, shares: int = 0):
    entry["shares"] = shares
    entry_time = entry.get("entry_time")
    if isinstance(entry_time, datetime):
        entry_time = entry_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        entry_time = str(entry_time)

    row = [
        to_serializable(entry_time),
        to_serializable(entry.get("symbol", "")),
        to_serializable(entry.get("direction", "")),
        to_serializable(entry.get("price", "")),
        to_serializable(entry.get("shares", "")),
        to_serializable(entry.get("capital_used", "")),
        to_serializable(entry.get("strategy_name", "")),
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

    print(f"[DEBUG] ✅ 寫入建倉 row：{row}")
    sheet.append_row(row, value_input_option="USER_ENTERED")


# ✅ 出場資料寫入
def write_exit_to_sheet(exit_info: dict, sheet):
    exit_time = exit_info.get("exit_time")
    if isinstance(exit_time, datetime):
        exit_time = exit_time.strftime("%Y-%m-%d %H:%M:%S")
    else:
        exit_time = str(exit_time)

    row = [
        to_serializable(exit_info.get("symbol", "")),
        to_serializable(exit_info.get("entry_time", "")),
        to_serializable(exit_time),
        to_serializable(exit_info.get("return_rate", "")),
        to_serializable(exit_info.get("profit_loss", "")),
        to_serializable(exit_info.get("holding_minutes", "")),
        to_serializable(exit_info.get("exit_price", "")),
        to_serializable(exit_info.get("rsi", "")),
        to_serializable(exit_info.get("zscore", "")),
        to_serializable(exit_info.get("roc", "")),
        to_serializable(exit_info.get("obv", "")),
        to_serializable(exit_info.get("vwap", "")),
        to_serializable(exit_info.get("ema5", "")),
        to_serializable(exit_info.get("ema20", "")),
        to_serializable(exit_info.get("strategy_name", ""))
    ]

    print(f"[DEBUG] ✅ 寫入出場 row：{row}")
    sheet.append_row(row, value_input_option="USER_ENTERED")


# ✅ 共振掃描資料寫入
def write_resonance_to_sheet(resonance_data: list, sheet):
    if not resonance_data:
        print("⚠️ 無共振資料可寫入")
        return

    # 清空原有內容並寫入標題
    headers = list(resonance_data[0].keys())
    sheet.clear()
    sheet.append_row(headers, value_input_option="USER_ENTERED")

    for item in resonance_data:
        row = [to_serializable(item.get(col, "")) for col in headers]
        sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"[✅] 寫入共振 row：{row}")
