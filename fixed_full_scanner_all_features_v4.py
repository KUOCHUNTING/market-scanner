import pandas as pd
import yfinance as yf
import requests
import time
import threading
import pytz
import os
from datetime import datetime
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands
from ta.volume import OnBalanceVolumeIndicator
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === 參數設定 ===
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
capital = 100000
max_positions = 5
position_pct = 0.05
max_per_position = 6000
positions = {}
tz = pytz.timezone("US/Eastern")

# === 股票清單讀取 ===
def load_stock_list():
    filename = "filtered_us_stocks_common_only.csv"
    if not os.path.exists(filename):
        print("【警告】找不到股票清單")
        return []
    with open(filename, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

# === Discord 通知 ===
def send_discord(message):
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        print("推播失敗:", e)

# === Google Sheets 分類寫入 ===
def write_to_gsheet_tab(symbol, signal_type, price, win_rate, return_pct, holding_time):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/")
        ws = sheet.worksheet(signal_type)
        now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        ws.append_row([now, symbol, price, win_rate, return_pct, holding_time])
    except Exception as e:
        print("寫入 Sheets 失敗:", e)

# === 真實 TICK 共振邏輯（多頭與空頭） ===
def get_tick_data():
    try:
        df = yf.download("^TICK", interval="1m", period="1d", prepost=False)
        if df is None or df.empty:
            return None
        return df['Close']
    except:
        return None

def check_tick_confluence():
    tick_data = get_tick_data()
    if tick_data is None or len(tick_data) < 30:
        return None
    latest_tick = tick_data.iloc[-1]
    percentile = (tick_data < latest_tick).sum() / len(tick_data)
    slope = tick_data.diff().rolling(5).mean().iloc[-1]
    if percentile > 0.95 and slope > 0:
        return "bullish"
    elif percentile < 0.05 and slope < 0:
        return "bearish"
    return None

def analyze_stock(symbol):
    try:
        df = yf.download(tickers=symbol, interval='5m', period='2d', prepost=True)
        if df is None or df.empty or len(df) < 30:
            return

        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume']
        now_price = close.iloc[-1]

        rsi = RSIIndicator(close).rsi()
        macd = MACD(close).macd_diff()
        adx = ADXIndicator(high=high, low=low, close=close).adx()
        ema = EMAIndicator(close, window=20).ema_indicator()
        bb = BollingerBands(close)
        upper_bb = bb.bollinger_hband()
        lower_bb = bb.bollinger_lband()

        tick_signal = check_tick_confluence()

        # 預警
        if (
            rsi.iloc[-1] > 50 and
            macd.iloc[-1] > 0 and
            adx.iloc[-1] > 20 and
            now_price > ema.iloc[-1]
        ):
            send_discord(f"⚠️ [預警] {symbol} 出現多頭預警 | 現價：{now_price:.2f}")
            write_to_gsheet_tab(symbol, "預警試單", now_price, "", "", "")
            if tick_signal == "bullish":
                send_discord(f"⚡️ [共振預警] {symbol} + TICK 多頭共振 | 現價：{now_price:.2f}")
                write_to_gsheet_tab(symbol, "共振預警", now_price, "", "", "")

        # 正式進場
        if (
            rsi.iloc[-1] > 60 and
            macd.iloc[-1] > 0 and
            adx.iloc[-1] > 25 and
            now_price > ema.iloc[-1] and
            volume.iloc[-1] > volume.mean()
        ):
            send_discord(f"✅ [進場] {symbol} 多頭正式進場 | 現價：{now_price:.2f}")
            write_to_gsheet_tab(symbol, "正式進場", now_price, "", "", "")
            positions[symbol] = {"entry_price": now_price, "entry_time": datetime.now(tz)}

            if tick_signal == "bullish":
                send_discord(f"🚨 [共振進場] {symbol} 多頭正式 + TICK 共振 | 現價：{now_price:.2f}")
                write_to_gsheet_tab(symbol, "共振進場", now_price, "", "", "")

        # 出場
        if symbol in positions:
            entry_price = positions[symbol]["entry_price"]
            holding_time = (datetime.now(tz) - positions[symbol]["entry_time"]).total_seconds() / 60
            return_pct = (now_price - entry_price) / entry_price
            if return_pct >= 0.05 or return_pct <= -0.02:
                win = 1 if return_pct > 0 else 0
                send_discord(f"【出場】{symbol} {'停利' if win else '停損'} | 報酬：{return_pct:.2%} | 時間：{holding_time:.1f}分")
                write_to_gsheet_tab(symbol, "正式出場", now_price, win, return_pct, holding_time)
                del positions[symbol]

    except Exception as e:
        print(f"{symbol} 錯誤：", e)

def main_loop():
    stock_list = load_stock_list()
    if not stock_list:
        print("未載入股票清單")
        return
    print(f"掃描中，共 {len(stock_list)} 檔")
    while True:
        threads = []
        for symbol in stock_list:
            if symbol in positions:
                continue
            t = threading.Thread(target=analyze_stock, args=(symbol,))
            threads.append(t)
            t.start()
            if len(threads) >= 30:
                for t in threads:
                    t.join()
                threads = []
        time.sleep(30)

if __name__ == "__main__":
    main_loop()

# === 空頭邏輯與 15分鐘共振檢查 ===
def analyze_stock(symbol):
    try:
        df_5m = yf.download(tickers=symbol, interval='5m', period='2d', prepost=True)
        df_15m = yf.download(tickers=symbol, interval='15m', period='2d', prepost=True)
        if df_5m is None or df_5m.empty or len(df_5m) < 30:
            return

        close = df_5m['Close']
        high = df_5m['High']
        low = df_5m['Low']
        volume = df_5m['Volume']
        now_price = close.iloc[-1]

        rsi = RSIIndicator(close).rsi()
        macd = MACD(close).macd_diff()
        adx = ADXIndicator(high=high, low=low, close=close).adx()
        ema = EMAIndicator(close, window=20).ema_indicator()
        bb = BollingerBands(close)
        upper_bb = bb.bollinger_hband()
        lower_bb = bb.bollinger_lband()

        tick_signal = check_tick_confluence()
        fifteen_match = confirm_15m_confluence(df_15m)

        # 多頭進場
        if (
            rsi.iloc[-1] > 60 and macd.iloc[-1] > 0 and adx.iloc[-1] > 25 and
            now_price > ema.iloc[-1] and volume.iloc[-1] > volume.mean()
        ):
            send_discord(f"✅ [進場] {symbol} 多頭進場 | 現價：{now_price:.2f}")
            write_to_gsheet_tab(symbol, "正式進場", now_price, "", "", "")
            positions[symbol] = {"entry_price": now_price, "entry_time": datetime.now(tz)}

            if tick_signal == "bullish" and fifteen_match == "bullish":
                send_discord(f"🚨 [共振進場] {symbol} 多頭 + TICK + 15分共振 | {now_price:.2f}")
                write_to_gsheet_tab(symbol, "共振進場", now_price, "", "", "")

        # 空頭進場
        if (
            rsi.iloc[-1] < 40 and macd.iloc[-1] < 0 and adx.iloc[-1] > 25 and
            now_price < ema.iloc[-1] and volume.iloc[-1] > volume.mean()
        ):
            send_discord(f"✅ [空頭進場] {symbol} 空單成立 | 現價：{now_price:.2f}")
            write_to_gsheet_tab(symbol, "空頭進場", now_price, "", "", "")
            positions[symbol] = {"entry_price": now_price, "entry_time": datetime.now(tz), "short": True}

            if tick_signal == "bearish" and fifteen_match == "bearish":
                send_discord(f"🚨 [空頭共振進場] {symbol} 空單共振成立 | 現價：{now_price:.2f}")
                write_to_gsheet_tab(symbol, "共振空頭進場", now_price, "", "", "")

        # 出場邏輯（多空雙向）
        if symbol in positions:
            entry_price = positions[symbol]["entry_price"]
            holding_time = (datetime.now(tz) - positions[symbol]["entry_time"]).total_seconds() / 60
            return_pct = (now_price - entry_price) / entry_price if not positions[symbol].get("short") else (entry_price - now_price) / entry_price
            if return_pct >= 0.05 or return_pct <= -0.02:
                win = 1 if return_pct > 0 else 0
                send_discord(f"【出場】{symbol} {'停利' if win else '停損'} | 報酬：{return_pct:.2%} | 持倉：{holding_time:.1f} 分")
                write_to_gsheet_tab(symbol, "正式出場", now_price, win, return_pct, holding_time)
                log_ml_parameters(symbol, return_pct, win, holding_time)
                del positions[symbol]

    except Exception as e:
        print(f"{symbol} 錯誤：", e)

# === 15分鐘共振確認邏輯 ===
def confirm_15m_confluence(df):
    try:
        close = df['Close']
        macd = MACD(close).macd_diff()
        rsi = RSIIndicator(close).rsi()
        ema = EMAIndicator(close, window=20).ema_indicator()
        if close.iloc[-1] > ema.iloc[-1] and macd.iloc[-1] > 0 and rsi.iloc[-1] > 50:
            return "bullish"
        if close.iloc[-1] < ema.iloc[-1] and macd.iloc[-1] < 0 and rsi.iloc[-1] < 50:
            return "bearish"
    except:
        pass
    return None

# === 機器學習最佳參數紀錄（每日 retrain 模擬） ===
def log_ml_parameters(symbol, return_pct, win_flag, holding_time):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/")
        ws = sheet.worksheet("每日最佳參數")
        now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        ws.append_row([now, symbol, return_pct, win_flag, holding_time])
    except Exception as e:
        print("紀錄 ML 模組參數錯誤：", e)
