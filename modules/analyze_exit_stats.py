import pandas as pd
from modules.connect_to_gsheet import connect_to_gsheet

def analyze_exit_stats():
    try:
        # ✅ 連線並讀取出場紀錄
        client = connect_to_gsheet()
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit") \
                      .worksheet("出場紀錄")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        # ✅ 轉換欄位格式
        df["出場時間"] = pd.to_datetime(df["出場時間"], errors="coerce")
        df["進場時間"] = pd.to_datetime(df["進場時間"], errors="coerce")
        df["報酬率"] = df["報酬率"].str.replace("%", "").astype(float)
        df["損益"] = df["損益"].str.replace("$", "").astype(float)
        df["持倉時間"] = pd.to_numeric(df["持倉時間"], errors="coerce")

        df = df.dropna(subset=["報酬率", "損益"])

        # ✅ 最新一天的出場資料
        latest_date = df["出場時間"].dt.date.max()
        daily_df = df[df["出場時間"].dt.date == latest_date]

        if daily_df.empty:
            print("⚠️ 今日無出場紀錄")
            return

        # ✅ 統計績效
        total_trades = len(daily_df)
        win_rate = (daily_df["報酬率"] > 0).mean() * 100
        avg_return = daily_df["報酬率"].mean()
        total_pnl = daily_df["損益"].sum()
        avg_duration = daily_df["持倉時間"].mean()

        long_df = daily_df[daily_df["方向"].str.contains("多")]
        short_df = daily_df[daily_df["方向"].str.contains("空")]
        long_win = (long_df["報酬率"] > 0).mean() * 100 if not long_df.empty else 0
        short_win = (short_df["報酬率"] > 0).mean() * 100 if not short_df.empty else 0

        print(f"📊【{latest_date} 出場績效統計】")
        print(f"📈 出場總數：{total_trades}｜平均報酬率：{avg_return:.2f}%")
        print(f"🎯 勝率：{win_rate:.2f}%｜總損益：${total_pnl:.2f}")
        print(f"⏱️ 平均持倉時間：{avg_duration:.1f} 分鐘")
        print(f"📈 做多勝率：{long_win:.2f}%｜📉 做空勝率：{short_win:.2f}%")

        # ✅ 各策略統計
        print("\n📌 各策略績效：")
        by_strategy = daily_df.groupby("策略名稱").agg({
            "報酬率": ["mean", lambda x: (x > 0).mean() * 100, "count"]
        })
        by_strategy.columns = ["平均報酬率", "勝率(%)", "次數"]
        print(by_strategy.round(2))

    except Exception as e:
        print(f"❌ [統計失敗] ➜ {e}")
