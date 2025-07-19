import os
import pandas as pd
from datetime import datetime
from modules.utils.connect_to_gsheet import connect_to_gsheet

def summarize_exit_stats():
    key_base64 = os.getenv("GCP_KEY_BASE64")
    sheet_url = os.getenv("GSHEET_URL")

    # 讀取出場紀錄分頁
    sheet = connect_to_gsheet(sheet_url, "出場記錄", key_base64)
    records = sheet.get_all_records()
    if not records:
        print("❗ 出場記錄為空")
        return

    df = pd.DataFrame(records)

    # 清洗資料格式
    df["報酬率"] = df["報酬率"].astype(str).str.replace('%', '').astype(float)
    df["損益"] = pd.to_numeric(df["損益"], errors='coerce')
    df["持倉時間"] = pd.to_numeric(df["持倉時間"], errors='coerce')
    df["方向"] = df["進場價格"] < df["出場價格"]

    # 核心統計
    total_trades = len(df)
    avg_return = df["報酬率"].mean()
    win_rate = (df["損益"] > 0).sum() / total_trades * 100
    total_pnl = df["損益"].sum()
    avg_holding = df["持倉時間"].mean()

    # 做多 / 做空 勝率
    long_df = df[df["方向"] == True]
    short_df = df[df["方向"] == False]

    long_win_rate = (long_df["損益"] > 0).sum() / len(long_df) * 100 if len(long_df) > 0 else 0
    short_win_rate = (short_df["損益"] > 0).sum() / len(short_df) * 100 if len(short_df) > 0 else 0

    # ✅ 寫入到《出場績效統計》分頁
    stat_sheet = connect_to_gsheet(sheet_url, "出場績效統計", key_base64)
    today_str = datetime.now().strftime("%Y-%m-%d")
    row = [
        today_str,
        total_trades,
        round(avg_return, 2),
        round(win_rate, 2),
        round(total_pnl, 2),
        round(avg_holding, 1),
        round(long_win_rate, 2),
        round(short_win_rate, 2)
    ]
    stat_sheet.append_row(row, value_input_option="USER_ENTERED")

    print("✅ 已寫入出場績效統計！")