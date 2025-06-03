import requests
import pandas as pd
from datetime import datetime, timedelta
from pytz import timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === 設定區 ===
POLYGON_API_KEY = "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1372956363235393536/2bELr_6LwGlk2K7G4B3d3J0MBD5iv04IwC33pQaWxAHcRbgn6sBVtkvI_65FfmC4Um5f"

# Google Sheets 設定
SHEET_NAME = "Trading Log"
WORKSHEET_NAME = "每日盤前情緒紀錄"
CREDS_FILE = "credentials.json"  # 放置你的 JSON 金鑰

# === 功能區 ===

def fetch_vix_data():
    today = datetime.now().strftime('%Y-%m-%d')
    start = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    url = f"https://api.polygon.io/v2/aggs/ticker/^VIX/range/1/day/{start}/{today}?adjusted=true&sort=desc&limit=2&apiKey={POLYGON_API_KEY}"
    res = requests.get(url)
    data = res.json().get("results", [])
    if len(data) < 2:
        return None, None, None, "❓ 無足夠資料"
    vix_today = data[-1]["c"]
    vix_yesterday = data[-2]["c"]
    change = (vix_today - vix_yesterday) / vix_yesterday * 100
    if vix_today > 30:
        level = "⚠️ 極度恐慌"
    elif vix_today > 25:
        level = "⚠️ 高度恐慌"
    elif vix_today > 20:
        level = "🔶 謹慎觀察"
    else:
        level = "✅ 正常"
    return vix_today, change, level, None

def fetch_tick_series(minutes=30):
    est = timezone("US/Eastern")
    now = datetime.now(est)
    start = now - timedelta(minutes=minutes)
    from_time = start.strftime("%Y-%m-%dT%H:%M:%S")
    to_time = now.strftime("%Y-%m-%dT%H:%M:%S")
    url = f"https://api.polygon.io/v2/aggs/ticker/TICK/range/1/minute/{from_time}/{to_time}?adjusted=true&sort=asc&limit=1000&apiKey={POLYGON_API_KEY}"
    res = requests.get(url)
    raw = res.json()
    bars = raw.get("results", [])
    values = [bar["c"] for bar in bars if "c" in bar]
    return pd.Series(values)

def analyze_tick(tick_series):
    if tick_series.empty:
        return None, None, "❓ 無資料"
    slope = tick_series.iloc[-1] - tick_series.iloc[0]
    percentile = sum(tick_series < tick_series.iloc[-1]) / len(tick_series) * 100
    sentiment = "偏多" if percentile > 80 and slope > 0 else "偏空" if percentile < 20 and slope < 0 else "中性"
    return percentile, slope, sentiment

def fetch_trin_value():
    est = timezone("US/Eastern")
    now = datetime.now(est)
    start = now - timedelta(minutes=15)
    url = f"https://api.polygon.io/v2/aggs/ticker/TRIN/range/1/minute/{start.strftime('%Y-%m-%dT%H:%M:%S')}/{now.strftime('%Y-%m-%dT%H:%M:%S')}?adjusted=true&sort=desc&limit=10&apiKey={POLYGON_API_KEY}"
    res = requests.get(url)
    bars = res.json().get("results", [])
    if not bars:
        return None, "❓ 無資料"
    trin_value = bars[0]["c"]
    structure = "偏空" if trin_value > 1 else "偏多" if trin_value < 1 else "中性"
    return trin_value, structure

def push_to_discord(message):
    data = {"content": message}
    requests.post(DISCORD_WEBHOOK_URL, json=data)

def write_to_sheets(date_str, vix, change, tick_pct, tick_slope, trin, summary):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
    sheet.append_row([date_str, vix, change, tick_pct, tick_slope, trin, summary])

# === 主流程 ===

def main():
    now = datetime.now(timezone("US/Eastern")).strftime("%Y-%m-%d %H:%M")

    vix, vix_change, vix_level, vix_err = fetch_vix_data()

    try:
        tick_series = fetch_tick_series()
        tick_pct, tick_slope, tick_status = analyze_tick(tick_series)
    except Exception as e:
        print(f"[ERROR] TICK 抓取失敗：{e}")
        tick_pct, tick_slope, tick_status = None, None, "❓ 無資料"

    trin_value, trin_status = fetch_trin_value()

    if vix_err or tick_status == "❓ 無資料" or trin_status == "❓ 無資料":
        push_to_discord("⚠️ 開盤前市場偵測失敗，請手動確認 API 資料來源")
        return

    summary = (
        f"📊 **[開盤前市場情緒預判]**\n"
        f"VIX：{vix:.2f}（{vix_change:+.2f}%）｜風險：{vix_level}\n"
        f"TICK 百分位：{tick_pct:.1f}｜斜率：{tick_slope:.1f}｜情緒：{tick_status}\n"
        f"TRIN：{trin_value:.2f}｜結構：{trin_status}"
    )

    if vix > 25 or tick_pct < 5 or trin_value > 1.2:
        summary += (
            "\n⚠️ 今日盤前預警：\n"
            f"TICK 百分位過低或 TRIN 偏高，建議開盤觀望，注意開盤震盪與風險控管。"
        )

    push_to_discord(summary)
    write_to_sheets(now, vix, vix_change, tick_pct, tick_slope, trin_value, tick_status)

    print("[DEBUG] vix_err =", vix_err)
    print("[DEBUG] tick_status =", tick_status)
    print("[DEBUG] trin_status =", trin_status)

if __name__ == "__main__":
    main()
    print("[INFO] 開盤前市場偵測完成 ✅")
