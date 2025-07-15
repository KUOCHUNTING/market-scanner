import pandas as pd
from datetime import datetime
from modules.connect_to_gsheet import connect_to_gsheet

def analyze_exit_stats():
    try:
        # === 連線與讀取資料 ===
        client = connect_to_gsheet()
        sheet_exit = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit") \
                          .worksheet("出場紀錄")
        df = pd.DataFrame(sheet_exit.get_all_records())

        df["出場時間"] = pd.to_datetime(df["出場時間"], errors="coerce")
        df["進場時間"] = pd.to_datetime(df["進場時間"], errors="coerce")
        df["報酬率"] = df["報酬率"].str.replace("%", "").astype(float)
        df["損益"] = df["損益"].str.replace("$", "").astype(float)
        df["持倉時間"] = pd.to_numeric(df["持倉時間"], errors="coerce")

        df = df.dropna(subset=["報酬率", "損益"])

        latest_date = df["出場時間"].dt.date.max()
        today_df = df[df["出場時間"].dt.date == latest_date]

        if today_df.empty:
            print("⚠️ 今日無出場資料")
            return

        # === 📊 總體統計 ===
        total_trades = len(today_df)
        avg_return = today_df["報酬率"].mean()
        win_rate = (today_df["報酬率"] > 0).mean() * 100
        total_pnl = today_df["損益"].sum()
        avg_holding = today_df["持倉時間"].mean()

        long_df = today_df[today_df["方向"].str.contains("多")]
        short_df = today_df[today_df["方向"].str.contains("空")]
        long_win = (long_df["報酬率"] > 0).mean() * 100 if not long_df.empty else 0
        short_win = (short_df["報酬率"] > 0).mean() * 100 if not short_df.empty else 0

        # === 📝 寫入「出場績效統計」分頁 ===
        sheet_stats = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit") \
                            .worksheet("出場績效統計")

        row = [
            latest_date.strftime("%Y-%m-%d"),
            total_trades,
            round(avg_return, 2),
            round(win_rate, 2),
            round(total_pnl, 2),
            round(avg_holding, 1),
            round(long_win, 2),
            round(short_win, 2)
        ]
        sheet_stats.append_row(row)
        print(f"✅ 寫入出場績效：{latest_date}｜出場 {total_trades} 筆｜勝率 {win_rate:.2f}%｜總損益 ${total_pnl:.2f}")

    except Exception as e:
        print(f"❌【出場績效分析失敗】{e}")
