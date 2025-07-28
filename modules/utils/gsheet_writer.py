import os
from datetime import datetime
from modules.utils.connect_to_gsheet import connect_to_gsheet
from modules.utils.format import to_serializable

# ✅ 建倉資料寫入
def write_entry_to_sheet(entry: dict, sheet, shares: int = 0):
    """
    將建倉資訊寫入 Google Sheets（建倉記錄）
    """

    entry_time = entry.get("entry_time")
    if isinstance(entry_time, datetime):
        entry_time = entry_time.strftime("%Y-%m-%d %H:%M:%S")

    row = [
        to_serializable(entry_time),                  # A 建倉時間
        to_serializable(entry.get("symbol", "")),     # B 股票代號
        to_serializable(entry.get("direction", "")),  # C 方向
        to_serializable(entry.get("entry_price", "")),# D 建倉價格
        to_serializable(entry.get("shares", shares)), # E 股數
        to_serializable(entry.get("capital_used", "")),   # F 建倉金額
        to_serializable(entry.get("strategy_name", "")),  # G 策略名稱
        to_serializable(entry.get("confidence_score", "")), # H 信心分數
        to_serializable(entry.get("signal_note", "")),     # I 訊號摘要
        to_serializable(entry.get("rsi", "")),         # J RSI
        to_serializable(entry.get("zscore", "")),      # K Z-score
        to_serializable(entry.get("roc", "")),         # L ROC
        to_serializable(entry.get("obv", "")),         # M OBV
        to_serializable(entry.get("vwap", "")),        # N VWAP
        to_serializable(entry.get("ema5", "")),        # O EMA5
        to_serializable(entry.get("ema20", "")),       # P EMA20
        to_serializable(entry.get("bb_upper", "")),    # Q BB上軌
        to_serializable(entry.get("bb_lower", "")),    # R BB下軌
        to_serializable(entry.get("trend_score", "")), # S 順勢分數
        to_serializable(entry.get("rrov_score", "")),  # T RROV分數
        to_serializable(entry.get("mean_score", "")),  # U 均值分數
        to_serializable(entry.get("strategy_type", "")), # V 類型（如 trend）
    ]

    sheet.append_row(row)


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
def write_resonance_to_sheet(resonance_data: list, sheet, timestamp=None):
    if not resonance_data:
        print("⚠️ 無共振資料可寫入")
        return

    # 清空原有內容並寫入標題
    headers = list(resonance_data[0].keys())
    sheet.clear()
    sheet.append_row(headers, value_input_option="USER_ENTERED")

    for item in resonance_data:
        row = [to_serializable(item.get(col, "")) for col in headers]
        if timestamp:
            row.append(to_serializable(timestamp))  # ✅ 加上時間欄
        sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"[✅] 寫入共振 row：{row}")
