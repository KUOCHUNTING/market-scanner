
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

# === ML 訓練資料寫入函式 ===
def write_to_ml_training_log(symbol, indicators, signal_type, return_pct, win_flag, holding_time):
        print("寫入 ML 訓練資料失敗：", e)

import joblib
import numpy as np
import os

# === 載入 ML 模型並預測勝率 ===
def predict_win_probability(indicators):
        print("ML 預測錯誤：", e)
        return 1.0  # 如果錯誤，預設都通過



def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        tab = "紀錄"
        try:
            sheet = spreadsheet.worksheet(tab)
        except:
            sheet = spreadsheet.add_worksheet(title=tab, rows="1000", cols="10")
            sheet.append_row(["時間", "股票代碼", "訊號類型", "價格", "勝率", "報酬率", "持倉時間"], value_input_option="USER_ENTERED")
        row = [now, stock_code, signal_type, price, win_rate, return_pct, holding_time]
        sheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        print(f"❌ Sheets 寫入錯誤：{e}")
def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
        print(f"❌ Sheets 寫入錯誤：{e}")

# === Discord 推播函數 ===
def send_discord_alert(message):
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
        print(f"❌ 發送 Discord 推播時錯誤：{e}")


# === TICK 三重共振模組 ===
def get_tick_data():
        print(f"TICK 資料抓取錯誤: {e}")
        return None

def check_tick_triple_confluence(tick_series):
        print(f"TICK 共振判斷錯誤: {e}")
        return False

# === 15分鐘共振 ===
def detect_15min_entry(symbol):
        print(f"[15分鐘多頭判斷錯誤] {symbol}: {e}")
        return False


# === 15分鐘空頭共振判斷 ===
def detect_15min_short_entry(symbol):
        print(f"[15分鐘空頭判斷錯誤] {symbol}: {e}")
        return False

# === 爆量啟動預警模組（多空共用）===
def detect_early_explosion(df, symbol):
        print(f"[爆量啟動預警錯誤] {symbol}: {e}")


# === 共振觀察訊號（提前預警）===
def detect_watch_signal_with_15min_tick(symbol, df):
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
def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        tab = "紀錄"
        try:
            sheet = spreadsheet.worksheet(tab)
        except:
            sheet = spreadsheet.add_worksheet(title=tab, rows="1000", cols="10")
            sheet.append_row(["時間", "股票代碼", "訊號類型", "價格", "勝率", "報酬率", "持倉時間"], value_input_option="USER_ENTERED")
        row = [now, stock_code, signal_type, price, win_rate, return_pct, holding_time]
        sheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        print(f"寫入 Google Sheets 失敗：{e}")
        pass
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

def get_all_us_symbols():
    # TODO: Implement real symbol loading logic
    return []


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
        print(f"{symbol} 出場錯誤：{e}")

def check_signal(symbol, tick_val, tick_slope, tick_perc):
        print(f"{symbol} 發生錯誤：{e}")


def run_daily_report():
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
        print("❌ Discord 推播失敗:", e)



# === Google Sheets 寫入函式 ===
def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
        print("❌ Google Sheets 寫入失敗:", e)



def main():
    print("▶️ 啟動主流程...")
    symbols = load_symbols()
    print(f"✅ 共載入 {len(symbols)} 檔股票")
    print("開始掃描中...")

    for symbol in symbols[:20]:
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



# === 模組 ===
import pandas as pd
import yfinance as yf
import requests
import time
import numpy as np
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Discord 與 Sheets 設定 ===
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/xxx/yyy"
positions = {}
capital = 100000
position_size_pct = 0.05
max_stocks_held = 5

# === 股票清單 ===
def load_symbols():
    df = pd.read_csv('filtered_us_stocks_common_only.csv')
    return df['symbol'].tolist()

# === 判斷盤別 ===
def get_market_session():
    eastern = pytz.timezone("US/Eastern")
    now_et = datetime.now(eastern).time()
    if now_et >= datetime.strptime("04:00", "%H:%M").time() and now_et < datetime.strptime("09:30", "%H:%M").time():
        return "pre"
    elif now_et >= datetime.strptime("09:30", "%H:%M").time() and now_et < datetime.strptime("16:00", "%H:%M").time():
        return "regular"
    elif now_et >= datetime.strptime("16:00", "%H:%M").time() and now_et < datetime.strptime("20:00", "%H:%M").time():
        return "post"
    return "closed"

# === 推播功能 ===
def send_discord_alert(message):
        pass

# === Sheets 寫入功能 ===
def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
        pass

# === 出場條件 ===
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

# === 出場紀錄 ===
def record_exit(symbol, exit_type, current_price):
    entry = positions[symbol]['entry']
    entry_time = positions[symbol]['time']
    pct = round((current_price - entry) / entry * 100, 2)
    hold = round((datetime.now() - entry_time).total_seconds() / 60, 1)
    win = "WIN" if pct > 0 else "LOSS"
    write_to_gsheet_tab(symbol, "正式出場", current_price, win, pct, hold)
    send_discord_alert(f"⏹️ 出場 [{symbol}]｜{exit_type}｜報酬 {pct}%｜持倉 {hold} 分鐘")
    del positions[symbol]

# === 預警邏輯 ===
def detect_warning_entry(symbol, df):
    close = df['Close']
    rsi = ta.rsi(close, 14)
    macd, macdsignal, _ = ta.macd(close)
    return rsi.iloc[-1] > 50 and macd.iloc[-1] > macdsignal.iloc[-1]

# === 正式進場邏輯（需自定） ===
def detect_15min_entry(symbol):
    return False  # 範例：你可以自行寫條件

# === TICK 共振（模擬） ===
def check_tick_triple_confluence():
    import random

def random_choice():
    return random.choice([True, False])

# === 多執行緒掃描單支股票 ===
def scan_symbol(symbol):
        print(f"⚠️ 錯誤 {symbol}: {e}")

# === 主程式（多執行緒） ===
def main():
    symbols = load_symbols()
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(scan_symbol, s) for s in symbols]
        for _ in as_completed(futures):
            pass
    print("✅ 掃描完畢")

# === 進入點 ===
if __name__ == "__main__":
    while True:
        main()
        time.sleep(30)
