
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
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
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

def main():
    if not is_market_open():
        print("非盤中，暫停掃描")
        return
    tick_val, tick_slope, tick_perc = get_tick_data()
    print(f"TICK 現值：{tick_val:.0f} | 斜率：{tick_slope:.1f} | 百分位：{tick_perc:.1f}%")
    symbols = get_all_us_symbols()
    
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=30) as executor:
        executor.map(lambda sym: check_signal(sym, tick_val, tick_slope, tick_perc), symbols)


if __name__ == "__main__":
    while True:
        main()
        time.sleep(300)
