# === 引入模組 ===
import numpy as np

# === TICK 三重共振模組 ===
def get_tick_data():
    try:
        df = yf.download("^TICK", interval="1m", period="30m", progress=False)
        if df is None or df.empty:
            return None
        return df['Close']
    except Exception as e:
        print(f"TICK 資料抓取錯誤: {e}")
        return None

def check_tick_triple_confluence(tick_series):
    try:
        if len(tick_series) < 10:
            return False
        latest = tick_series.iloc[-1]
        history = tick_series[:-1]
        perc_rank = np.sum(history < latest) / len(history)
        slope = tick_series.diff().rolling(5).mean().iloc[-1]
        avg_bias = tick_series.tail(10).mean()
        return (
            (perc_rank >= 0.95 or perc_rank <= 0.05) and
            abs(slope) > 50 and
            (avg_bias > 600 or avg_bias < -600)
        )
    except Exception as e:
        print(f"TICK 共振判斷錯誤: {e}")
        return False

# === 15分鐘共振 ===
def detect_15min_entry(symbol):
    try:
        df = yf.download(tickers=symbol, interval='15m', period='2d', progress=False, prepost=True)
        if df is None or df.empty or len(df) < 10:
            return False
        close = df['Close']
        volume = df['Volume']
        rsi = ta.rsi(close, length=14)
        macd_line, macd_signal, _ = ta.macd(close, fast=12, slow=26, signal=9)
        vwma = ta.vwma(close, volume, length=20)
        tmo = ta.ema(close.diff(), length=5)
        conds = [
            rsi.iloc[-1] > 50,
            macd_line.iloc[-2] < macd_signal.iloc[-2] and macd_line.iloc[-1] > macd_signal.iloc[-1],
            close.iloc[-1] > vwma.iloc[-1],
            tmo.iloc[-1] > 0 and tmo.iloc[-2] <= 0,
            volume.iloc[-1] > volume.rolling(20).mean().iloc[-1] * 1.2
        ]
        return sum(conds) >= 3
    except Exception as e:
        print(f"[15分鐘多頭判斷錯誤] {symbol}: {e}")
        return False


# === 15分鐘空頭共振判斷 ===
def detect_15min_short_entry(symbol):
    try:
        df = yf.download(tickers=symbol, interval='15m', period='2d', progress=False, prepost=True)
        if df is None or df.empty or len(df) < 10:
            return False
        close = df['Close']
        volume = df['Volume']
        rsi = ta.rsi(close, length=14)
        macd_line, macd_signal, _ = ta.macd(close, fast=12, slow=26, signal=9)
        vwma = ta.vwma(close, volume, length=20)
        tmo = ta.ema(close.diff(), length=5)
        conds = [
            rsi.iloc[-1] < 50,
            macd_line.iloc[-2] > macd_signal.iloc[-2] and macd_line.iloc[-1] < macd_signal.iloc[-1],
            close.iloc[-1] < vwma.iloc[-1],
            tmo.iloc[-1] < 0 and tmo.iloc[-2] >= 0,
            volume.iloc[-1] > volume.rolling(20).mean().iloc[-1] * 1.2
        ]
        return sum(conds) >= 3
    except Exception as e:
        print(f"[15分鐘空頭判斷錯誤] {symbol}: {e}")
        return False

# === 爆量啟動預警模組（多空共用）===
def detect_early_explosion(df, symbol):
    try:
        close = df['Close']
        volume = df['Volume']
        high = df['High']
        low = df['Low']
        rsi = ta.rsi(close, length=14)
        vwma = ta.vwma(close, volume, length=20)
        tmo = ta.ema(close.diff(), length=5)
        vol_avg = volume.rolling(20).mean()

        # 上漲啟動條件
        breakout_up = close.iloc[-1] > high.shift(1).rolling(10).max().iloc[-1]
        strong_volume = volume.iloc[-1] > vol_avg.iloc[-1] * 2
        momentum_up = (rsi.iloc[-1] > 50 and tmo.iloc[-1] > 0 and close.iloc[-1] > vwma.iloc[-1])

        # 下跌啟動條件
        breakout_down = close.iloc[-1] < low.shift(1).rolling(10).min().iloc[-1]
        momentum_down = (rsi.iloc[-1] < 50 and tmo.iloc[-1] < 0 and close.iloc[-1] < vwma.iloc[-1])

        if breakout_up and strong_volume and momentum_up:
            send_to_discord(f"🔔 爆量上漲預警：${symbol} 啟動中（突破高點 + 放量）")
        elif breakout_down and strong_volume and momentum_down:
            send_to_discord(f"🔻 爆量下跌預警：${symbol} 下殺中（跌破低點 + 放量）")
    except Exception as e:
        print(f"[爆量啟動預警錯誤] {symbol}: {e}")


# === 共振觀察訊號（提前預警）===
def detect_watch_signal_with_15min_tick(symbol, df):
    try:
        close = df['Close']
        volume = df['Volume']
        rsi = ta.rsi(close, length=14)
        macd_line, macd_signal, _ = ta.macd(close, fast=12, slow=26, signal=9)
        vwma = ta.vwma(close, volume, length=20)
        tmo = ta.ema(close.diff(), length=5)
        vol_avg = volume.rolling(20).mean()

        conds = [
            rsi.iloc[-1] > 45,
            macd_line.iloc[-2] < macd_signal.iloc[-2] and macd_line.iloc[-1] > macd_signal.iloc[-1],
            close.iloc[-1] > vwma.iloc[-1],
            tmo.iloc[-1] > 0 and tmo.iloc[-2] <= 0,
            volume.iloc[-1] > vol_avg.iloc[-1] * 1.5
        ]

        if sum(conds) >= 3:
            if detect_15min_entry(symbol):
                tick_series = get_tick_data()
                if tick_series is not None and check_tick_triple_confluence(tick_series):
                    send_to_discord(f"🔍【共振觀察】${symbol}（5分 + 15分 + TICK）")
                    write_to_gsheet_tab(symbol, "🔍 共振觀察", close.iloc[-1], "-", "-", "-")
    except Exception as e:
        print(f"[共振觀察錯誤] {symbol}: {e}")

import pandas as pd
import yfinance as yf
import requests
import time
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
positions = {}

def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/gcp_cred.json", scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key("1MkjggPDw1t_sTDLoMYH1E7CFOYrv0CkxTROpj-9NAHw")

        if "共振進場" in signal_type:
            tab = "共振進場"
        elif "共振預警" in signal_type:
            tab = "共振預警"
        elif "正式進場" in signal_type:
            tab = "正式進場"
        elif "預警" in signal_type:
            tab = "預警訊號"
        elif "出場" in signal_type:
            tab = "出場紀錄"
        else:
            tab = "其他"

        try:
            sheet = spreadsheet.worksheet(tab)
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=tab, rows="1000", cols="10")
            sheet.append_row(["時間", "股票代碼", "訊號類型", "價格", "勝率", "報酬率", "持倉時間"], value_input_option="USER_ENTERED")

        row = [now, stock_code, signal_type, price, win_rate, return_pct, holding_time]
        sheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        print(f"寫入 Google Sheets 失敗：{e}")

def send_to_discord(message):
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": message})
    except:
        pass

def is_market_open():
    eastern = pytz.timezone("US/Eastern")
    now_est = datetime.now(eastern)
    if now_est.weekday() >= 5:
        return False
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, microsecond=0)
    return market_open <= now_est <= market_close


def get_all_us_symbols():
    url = "https://raw.githubusercontent.com/ldavis44/stock-symbol-list/master/all/all_tickers.txt"
    try:
        r = requests.get(url)
        all_symbols = [s.strip().replace(".", "-") for s in r.text.splitlines() if s.strip()]
        # 過濾掉 OTC / ETF 類型（簡單篩掉常見 ETF / OTC 標記）
        filtered = [s for s in all_symbols if not any(tag in s.upper() for tag in ['ETF', '-U', '.PK', '.OB', 'OTC'])]
        return filtered
    except:
        return []

    url = "https://raw.githubusercontent.com/ldavis44/stock-symbol-list/master/all/all_tickers.txt"
    try:
        r = requests.get(url)
        return [s.strip().replace(".", "-") for s in r.text.splitlines() if s.strip()]
    except:
        return []

def get_tick_data():
    try:
        df = yf.download("^TICK", period="1d", interval="1m", progress=False)
        df.dropna(inplace=True)
        latest = df["Close"].iloc[-1]
        slope = df["Close"].diff().tail(3).mean()
        percentile = (df["Close"] < latest).sum() / len(df["Close"]) * 100
        return latest, slope, percentile
    except:
        return 0, 0, 50

def calc_indicators(df):
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["STD"] = df["Close"].rolling(20).std()
    df["Upper"] = df["SMA20"] + 2 * df["STD"]
    df["Lower"] = df["SMA20"] - 2 * df["STD"]
    df["Basis"] = df["SMA20"]
    rsi = df["Close"].rolling(21).apply(lambda x: 100 - (100 / (1 + (x.pct_change().dropna() > 0).sum() / max((x.pct_change().dropna() < 0).sum(), 1))), raw=False)
    tmo = rsi.rolling(5).mean().rolling(3).mean()
    signal = tmo.rolling(3).mean()
    df["TMO"] = tmo
    df["TMO_signal"] = signal
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal_macd = macd.ewm(span=9, adjust=False).mean()
    df["MACD_line"] = macd
    df["MACD_signal"] = signal_macd
    df["MACD_hist"] = macd - signal_macd
    df["TP"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["Cum_TPV"] = (df["TP"] * df["Volume"]).cumsum()
    df["Cum_Vol"] = df["Volume"].cumsum()
    df["VWAP"] = df["Cum_TPV"] / df["Cum_Vol"]
    df["VolAvg"] = df["Volume"].rolling(16).mean()
    return df

def enhanced_exit(symbol, direction, latest):
    try:
        entry = positions[symbol]
        entry_price = entry["price"]
        entry_time = entry["entry_time"]
        exit_price = latest["Close"]
        exit_time = datetime.now()
        pnl = exit_price - entry_price if direction == "long" else entry_price - exit_price
        return_pct = (pnl / entry_price) * 100
        return_pct_str = f"{return_p