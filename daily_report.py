import os
import json
import requests
import base64
import gspread
import pandas as pd
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials


def get_credentials_from_base64(env_var_name):
    encoded_key = os.getenv(env_var_name)
    key_dict = json.loads(base64.b64decode(encoded_key).decode("utf-8"))
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    return ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)


def fetch_today_trades(sheet_url, sheet_name="交易記錄"):
    creds = get_credentials_from_base64("GCP_KEY_BASE64")
    client = gspread.authorize(creds)
    ws = client.open_by_url(sheet_url).worksheet(sheet_name)
    rows = ws.get_all_records()
    today = datetime.now().strftime("%Y-%m-%d")
    return [r for r in rows if r["時間"].startswith(today)]


def calculate_and_format_report(rows):
    if not rows:
        return f"📊【每日績效報告】{datetime.now().strftime('%Y-%m-%d')}\n\n⚠️ 今日尚無任何交易記錄。"

    df = pd.DataFrame(rows)
    df["損益金額"] = pd.to_numeric(df["損益金額"], errors="coerce").fillna(0)
    df["策略"] = df["策略"].fillna("未知")

    total_trades = len(df)
    total_profit = df["損益金額"].sum()
    win_rate = round((df["損益金額"] > 0).sum() / total_trades * 100, 1)
    avg_profit = round(total_profit / total_trades)
    max_gain = int(df["損益金額"].max())
    max_loss = int(df["損益金額"].min())

    grouped = df.groupby("策略").agg(
        筆數=("損益金額", "count"),
        勝數=("損益金額", lambda x: (x > 0).sum()),
        總損益=("損益金額", "sum")
    ).reset_index()
    grouped["勝率"] = round(grouped["勝數"] / grouped["筆數"] * 100).astype(int)

    today_str = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"📊【每日績效報告】{today_str}",
        "",
        f"📈 今日總交易：{total_trades} 筆",
        f"✅ 勝率：{win_rate}%",
        f"💰 總損益：{f'+${int(total_profit)}' if total_profit >= 0 else f'-${abs(int(total_profit))}'}（平均每筆 {f'+${avg_profit}' if avg_profit >=0 else f'-${abs(avg_profit)}'}）",
        f"📉 最大虧損：{max_loss}，📈 最大獲利：{max_gain}",
        "",
        "🧠 策略分類："
    ]

    for _, row in grouped.iterrows():
        pnl_str = f"+{int(row['總損益'])}" if row["總損益"] >= 0 else str(int(row["總損益"]))
        lines.append(f"- {row['策略']}：{row['筆數']} 筆，勝率 {row['勝率']}%，總損益 {pnl_str}")

    lines.append("\n🕒 推播時間：15:30（EST）")
    return "\n".join(lines)


def push_to_discord(message, webhook_url):
    payload = {"content": message}
    try:
        res = requests.post(webhook_url, json=payload)
        print(f"[✅] Discord 回應：{res.status_code}")
    except Exception as e:
        print(f"[❌] 推播失敗：{e}")


# === ⏰ 程式執行區（可以排程在每日美東 15:30 執行） ===
if __name__ == "__main__":
    SHEET_URL = "https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit"
    DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1381592286932238336/8TLHxMcoAxGEydMVrLeTrhoirnzplM3myRoaozF_7bxoFcK4g236KLnd075NogP25Gak"

    rows = fetch_today_trades(SHEET_URL)
    msg = calculate_and_format_report(rows)
    push_to_discord(msg, DISCORD_WEBHOOK)
