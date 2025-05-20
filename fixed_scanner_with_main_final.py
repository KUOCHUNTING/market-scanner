
# === 模組補充 ===
import pandas as pd
import yfinance as yf
import requests
import time
import json
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === TICK 三重共振判斷 ===
def check_tick_triple_confluence():
    # 模擬回傳 true 為符合共振（實際邏輯請按需設計）
    return True

# === Google Sheets 寫入函數 ===
def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/")
        tab = sheet.worksheet(signal_type)
        tab.append_row([now, stock_code, price, win_rate, return_pct, holding_time])
    except Exception as e:
        print(f"❌ Sheets 寫入錯誤：{e}")

# === Discord 推播函數 ===
def send_discord_alert(message):
    try:
        payload = {"content": message}
        r = requests.post(DISCORD_WEBHOOK, json=payload)
        if r.status_code != 204:
            print(f"❌ Discord 推播失敗：{r.status_code}")
    except Exception as e:
        print(f"❌ Discord 傳送錯誤：{e}")

# === 出場記錄函數 ===
def record_exit(symbol, exit_type, exit_price):
    entry_data = positions.get(symbol)
    if not entry_data:
        return
    entry_price = entry_data["entry"]
    entry_time = entry_data["time"]
    return_pct = round((exit_price - entry_price) / entry_price * 100, 2)
    holding_time = (datetime.now() - entry_time).total_seconds() / 60
    holding_str = f"{round(holding_time, 1)} 分鐘"
    win_rate = "WIN" if return_pct > 0 else "LOSS"
    print(f"⏹️ 出場紀錄 {symbol} | {exit_type} | 報酬 {return_pct}% | 持倉時間 {holding_str}")
    write_to_gsheet_tab(symbol, "正式出場", exit_price, win_rate, return_pct, holding_str)
    send_discord_alert(f"⏹️ 出場 [{symbol}] | {exit_type.upper()} | 報酬：{return_pct}% | 持倉：{holding_str}")
    del positions[symbol]



# === 讀取股票清單 CSV ===
def load_symbols():
    df = pd.read_csv('filtered_us_stocks_common_only.csv')
    return df['symbol'].tolist() if 'symbol' in df.columns else df.iloc[:, 0].tolist()

# === 資金控管設定 ===
capital = 100000  # 本金 10 萬
position_size_pct = 0.05  # 每筆投入 5%
max_stocks_held = 5
positions = {}  # 持倉紀錄：{symbol: {'entry': 價格, 'time': 時間}}

# === 判斷是否出場（停利/停損） ===
def check_exit_conditions(symbol, current_price):
    if symbol not in positions:
        return None
    entry = positions[symbol]['entry']
    gain = (current_price - entry) / entry * 100
    if gain >= 5:
        return 'take_profit'
    elif gain <= -2:
        return 'stop_loss'
    return None
# === 引入模組 ===
import numpy as np
print("✅ 腳本啟動成功，開始執行市場掃描器")


from datetime import datetime
import pytz

# 判斷美東時間是否為盤前 / 盤中 / 盤後
def get_market_session():
    eastern = pytz.timezone("US/Eastern")
    now_et = datetime.now(eastern).time()
    if now_et >= datetime.strptime("04:00", "%H:%M").time() and now_et < datetime.strptime("09:30", "%H:%M").time():
        return "pre"
    elif now_et >= datetime.strptime("09:30", "%H:%M").time() and now_et < datetime.strptime("16:00", "%H:%M").time():
        return "regular"
    elif now_et >= datetime.strptime("16:00", "%H:%M").time() and now_et < datetime.strptime("20:00", "%H:%M").time():
        return "post"
    else:
        return "closed"

# 範例推播（可與正式邏輯整合）
session = get_market_session()
print(f"⏰ 現在時段：{session}")

if session == "pre":
    send_discord_message("⚠️ [盤前異動] 偵測啟動中...")
elif session == "post":
    send_discord_message("⚠️ [盤後異動] 偵測啟動中...")
else:
    print("➡️ 非盤前盤後時段，不推播盤前/盤後訊息")


def send_discord_message(content):
    try:
        response = requests.post(DISCORD_WEBHOOK, json={"content": content})
        if response.status_code == 204:
            print(f"✅ 推播成功：{content}")
        else:
            print(f"❌ 推播失敗，狀態碼: {response.status_code}，回應: {response.text}")
    except Exception as e:
        print(f"❌ 發送 Discord 推播時錯誤：{e}")


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
        return_pct_str = f"{return_pct:.2f}%"
        result = "Win" if return_pct > 0 else "Loss"
        holding_minutes = (exit_time - entry_time).total_seconds() / 60
        holding_str = f"{int(holding_minutes)}分鐘"
        exit_type = f"出場-{'多單' if direction == 'long' else '空單'}"
        send_to_discord(f"[{exit_type}] {symbol}｜現價 {exit_price:.2f}｜報酬率 {return_pct_str}｜{result}")
        write_to_gsheet_tab(symbol, exit_type, exit_price, result, return_pct_str, holding_str)
        del positions[symbol]
    except Exception as e:
        print(f"{symbol} 出場錯誤：{e}")

def check_signal(symbol, tick_val, tick_slope, tick_perc):
    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)
        if df is None or df.empty or len(df) < 30:
            return
        df = calc_indicators(df)
        latest = df.iloc[-1]
        if latest["Close"] < 1 or latest["Close"] > 10:
            return

        bull_tick = tick_val > 300 and tick_slope > 30 and tick_perc > 90
        bear_tick = tick_val < -300 and tick_slope < -30 and tick_perc < 10
        long_general = latest["TMO"] > latest["TMO_signal"] and latest["MACD_line"] > 0 and latest["Close"] > latest["VWAP"]
        short_general = latest["TMO"] < latest["TMO_signal"] and latest["MACD_line"] < 0 and latest["Close"] < latest["VWAP"]
        long_strong = latest["Close"] > latest["Upper"] and latest["TMO"] > latest["TMO_signal"] and latest["MACD_hist"] > 0 and latest["Volume"] > latest["VolAvg"] * 1.2 and latest["Close"] > latest["VWAP"]
        short_strong = latest["Close"] < latest["Lower"] and latest["TMO"] < latest["TMO_signal"] and latest["MACD_hist"] < 0 and latest["Volume"] > latest["VolAvg"] * 1.2 and latest["Close"] < latest["VWAP"]

        if symbol in positions:
            entry = positions[symbol]
            if entry["type"] == "long" and (latest["Close"] >= entry["price"] + 5 or latest["Low"] <= entry["price"] - 2):
                enhanced_exit(symbol, "long", latest)
            elif entry["type"] == "short" and (latest["Close"] <= entry["price"] - 5 or latest["High"] >= entry["price"] + 2):
                enhanced_exit(symbol, "short", latest)

        if long_strong and bull_tick:
            send_to_discord(f"[🚨共振進場] {symbol} 多單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "共振進場-多單", latest["Close"], "N/A", "N/A", "0秒")
            positions[symbol] = {"price": latest["Close"], "type": "long", "entry_time": datetime.now()}
        elif short_strong and bear_tick:
            send_to_discord(f"[🚨共振進場] {symbol} 空單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "共振進場-空單", latest["Close"], "N/A", "N/A", "0秒")
            positions[symbol] = {"price": latest["Close"], "type": "short", "entry_time": datetime.now()}
        elif long_strong:
            send_to_discord(f"[✅正式進場] {symbol} 多單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "正式進場-多單", latest["Close"], "N/A", "N/A", "0秒")
            positions[symbol] = {"price": latest["Close"], "type": "long", "entry_time": datetime.now()}
        elif short_strong:
            send_to_discord(f"[✅正式進場] {symbol} 空單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "正式進場-空單", latest["Close"], "N/A", "N/A", "0秒")
            positions[symbol] = {"price": latest["Close"], "type": "short", "entry_time": datetime.now()}
        elif long_general and bull_tick:
            send_to_discord(f"[⚡️共振預警] {symbol} 多單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "共振預警-多單", latest["Close"], "N/A", "N/A", "尚未進場")
        elif short_general and bear_tick:
            send_to_discord(f"[⚡️共振預警] {symbol} 空單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "共振預警-空單", latest["Close"], "N/A", "N/A", "尚未進場")
        elif long_general:
            send_to_discord(f"[⚠️預警] {symbol} 多單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "預警-多單", latest["Close"], "N/A", "N/A", "尚未進場")
        elif short_general:
            send_to_discord(f"[⚠️預警] {symbol} 空單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "預警-空單", latest["Close"], "N/A", "N/A", "尚未進場")
    except Exception as e:
        print(f"{symbol} 發生錯誤：{e}")


def run_daily_report():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1MkjggPDw1t_sTDLoMYH1E7CFOYrv0CkxTROpj-9NAHw")
        ws = sheet.worksheet("出場紀錄")
        records = ws.get_all_values()[1:]

        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        today_records = [r for r in records if r[0].startswith(today)]
        if not today_records:
            print("今天無出場資料")
            return
        wins = [r for r in today_records if "Win" in r[4]]
        losses = [r for r in today_records if "Loss" in r[4]]
        win_rate = round(len(wins) / len(today_records) * 100, 2)
        avg_return = round(sum([float(r[5].replace("%", "")) for r in today_records]) / len(today_records), 2)
        avg_hold = round(sum([int(r[6].replace("分鐘", "")) for r in today_records]) / len(today_records), 2)
        stat_sheet = sheet.worksheet("統計報表") if "統計報表" in [ws.title for ws in sheet.worksheets()] else sheet.add_worksheet(title="統計報表", rows="100", cols="10")
        stat_sheet.append_row([today, len(today_records), f"{win_rate}%", f"{avg_return}%", f"{avg_hold}分鐘"], value_input_option="USER_ENTERED")
        print("今日統計報表已寫入")
    except Exception as e:
        print("統計報表錯誤：", e)
# === 資金控管設定 ===
INITIAL_CAPITAL = 100000
POSITION_SIZE_PCT = 0.05
MAX_POSITION_PER_TRADE = 6000
MAX_ACTIVE_POSITIONS = 5
current_positions = {}  # 儲存目前持股狀態 {symbol: {"entry_price": .., "entry_time": .., "amount": ..}}

def can_enter_new_trade():
    return len(current_positions) < MAX_ACTIVE_POSITIONS

def calculate_position_amount(price):
    capital_to_use = min(INITIAL_CAPITAL * POSITION_SIZE_PCT, MAX_POSITION_PER_TRADE)
    shares = capital_to_use // price
    return shares, capital_to_use

def record_entry(symbol, price):
    shares, invested = calculate_position_amount(price)
    current_positions[symbol] = {
        "entry_price": price,
        "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "amount": invested,
        "shares": shares
    }
    print(f"✅ 進場：{symbol} @ ${price}, 金額 = ${invested}, 張數 = {shares}")

def record_exit(symbol, exit_price):
    if symbol in current_positions:
        entry = current_positions[symbol]
        profit = (exit_price - entry["entry_price"]) * entry["shares"]
        return_pct = profit / entry["amount"] * 100
        holding_time = f'{datetime.now() - datetime.strptime(entry["entry_time"], "%Y-%m-%d %H:%M:%S")}'
        print(f"📤 出場：{symbol} @ ${exit_price}, 報酬 = {return_pct:.2f}%, 持倉時間 = {holding_time}")
        del current_positions[symbol]
        return return_pct, holding_time
    return None, None




# === 停利 / 停損 設定 ===
TAKE_PROFIT_PCT = 5.0
STOP_LOSS_PCT = -2.0

def check_exit_conditions(symbol, current_price):
    if symbol in current_positions:
        entry = current_positions[symbol]
        entry_price = entry["entry_price"]
        change_pct = (current_price - entry_price) / entry_price * 100
        if change_pct >= TAKE_PROFIT_PCT or change_pct <= STOP_LOSS_PCT:
            return True, change_pct
    return False, 0.0








# === Discord 推播函式 ===
def send_discord_alert(message):
    try:
        payload = {"content": message}
        requests.post(DISCORD_WEBHOOK, json=payload)
    except Exception as e:
        print("❌ Discord 推播失敗:", e)



# === Google Sheets 寫入函式 ===
def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/").worksheet("正式進場")
        sheet.append_row([now, stock_code, signal_type, price, win_rate, return_pct, holding_time])
    except Exception as e:
        print("❌ Google Sheets 寫入失敗:", e)



def main():
    print("▶️ 啟動主流程...")
    symbols = load_symbols()
    print(f"✅ 共載入 {len(symbols)} 檔股票")
    print("開始掃描中...")

    for symbol in symbols[:20]:
        try:
            data = yf.download(symbol, period="5d", interval="5m")
            if len(data) < 20:
                continue

            # === 技術指標計算 ===
            data["returns"] = data["Close"].pct_change()
            data["rsi"] = ta.rsi(data["Close"], length=14)
            data["vol_avg"] = data["Volume"].rolling(window=20).mean()
            data["vol_spike"] = data["Volume"] > data["vol_avg"] * 2

            latest = data.iloc[-1]
            price_change_pct = (latest["Close"] - data["Close"].iloc[-6]) / data["Close"].iloc[-6] * 100
            rsi_val = latest["rsi"]
            is_vol_spike = latest["vol_spike"]

            # === 判斷訊號條件 ===
            if price_change_pct > 3 and rsi_val > 70 and is_vol_spike:
                print(f"🚀 訊號成立：{symbol} 價格漲幅 + RSI + 放量 共振")
            
        except Exception as e:
            print(f"❌ {symbol} 資料抓取失敗：", e)




# === 每 30 秒執行一次主程式 ===
if __name__ == "__main__":
    import time
    while True:
        main()
        time.sleep(30)



# === 主程式 ===
def main():
    print("🚀 開始掃描市場 ...")
    all_symbols = load_symbols()
    session = get_market_session()
    active_count = 0

    for symbol in all_symbols:
        try:
            df = yf.download(tickers=symbol, interval='5m', period='2d', prepost=True, progress=False)
            if df is None or df.empty or len(df) < 10:
                continue

            current_price = df['Close'].iloc[-1]
            exit_type = check_exit_conditions(symbol, current_price)
            if exit_type:
                record_exit(symbol, exit_type, current_price)
                continue

            # 僅允許新進場時做以下偵測
            if len(positions) >= max_stocks_held:
                continue

            if detect_15min_entry(symbol):
                entry_amount = capital * position_size_pct
                positions[symbol] = {
                    "entry": current_price,
                    "time": datetime.now()
                }
                print(f"✅ 進場 [{symbol}] 價格: {current_price}")
                write_to_gsheet_tab(symbol, "正式進場", current_price, "-", "-", "-")
                send_discord_alert(f"✅ 正式進場 [{symbol}] | 價格：{current_price}")
        except Exception as e:
            print(f"⚠️ 錯誤處理 {symbol}：{e}")

    print("✅ 本輪掃描結束")

# === 每日績效報表統計 ===
def run_daily_report():
    try:
        print("📊 執行每日報表統計 ...")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/")
        tab = sheet.worksheet("正式出場")
        records = tab.get_all_values()
        returns = []
        for row in records[1:]:
            try:
                pct = float(row[4])
                returns.append(pct)
            except:
                continue
        win_count = len([r for r in returns if r > 0])
        total = len(returns)
        win_rate = round(win_count / total * 100, 2) if total > 0 else 0
        avg_return = round(sum(returns) / total, 2) if total > 0 else 0
        print(f"📈 總筆數：{total}｜勝率：{win_rate}%｜平均報酬：{avg_return}%")
    except Exception as e:
        print(f"❌ 報表錯誤：{e}")

# 自動執行主程式
if __name__ == "__main__":
    while True:
        main()
        time.sleep(30)  # 每 30 秒掃描一次
