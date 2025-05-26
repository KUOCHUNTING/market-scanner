
import os
import requests
import pandas as pd
import gspread
from datetime import datetime
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD
from ta.volatility import BollingerBands, AverageTrueRange
from polygon import RESTClient
from oauth2client.service_account import ServiceAccountCredentials
from concurrent.futures import ThreadPoolExecutor

API_KEY = os.getenv("POLYGON_API_KEY") or "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
SPREADSHEET_NAME = "MarketSignalLogs"
CSV_FILE = "filtered_us_stocks_common_only.csv"

def setup_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    return sheet

def fetch_stock_data(symbol):
    try:
        client = RESTClient(api_key=API_KEY)
        end = datetime(2025, 5, 22, 15, 59)
        start = end - pd.Timedelta(minutes=35)

        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=5,
            timespan="minute",
            from_=start.strftime("%Y-%m-%d"),
            to=end.strftime("%Y-%m-%d"),
            limit=100
        )

        if not aggs:
            return None

        data = [{
            "timestamp": pd.to_datetime(bar.timestamp, unit='ms'),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        } for bar in aggs]

        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        print(f"[錯誤] {symbol} 抓資料失敗：{e}")
        return None

def analyze_signal(symbol, df):
    try:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        if len(close) < 35:
            return None

        rsi = RSIIndicator(close).rsi().iloc[-1]
        macd = MACD(close).macd_diff().iloc[-1]
        kd = StochasticOscillator(high=high, low=low, close=close)
        k_value = kd.stoch().iloc[-1]
        d_value = kd.stoch_signal().iloc[-1]
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        vwap = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
        vwap_signal = close.iloc[-1] > vwap.iloc[-1]
        vol_spike = volume.iloc[-1] > volume.mean() * 2
        bb = BollingerBands(close)
        bb_signal = close.iloc[-1] > bb.bollinger_hband().iloc[-1] or close.iloc[-1] < bb.bollinger_lband().iloc[-1]
        atr = AverageTrueRange(high=high, low=low, close=close).average_true_range().iloc[-1]

        if (rsi < 35 and macd > 0 and k_value > d_value and vwap_signal and vol_spike and bb_signal):
            return "多頭進場訊號"
        elif (rsi > 70 and macd < 0 and k_value < d_value and not vwap_signal and vol_spike and bb_signal):
            return "空頭進場訊號"
        return None
    except Exception as e:
        print(f"[錯誤] {symbol} 分析失敗：{e}")
        return None

def send_to_discord(symbol, signal):
    payload = {"content": f"**{symbol}**\n觸發：`{signal}`"}
    try:
        requests.post(DISCORD_WEBHOOK, json=payload)
    except Exception as e:
        print(f"[推播失敗] {symbol}：{e}")

def write_to_sheet(sheet, symbol, signal):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [now, symbol, signal]
    try:
        sheet.append_row(row)
    except Exception as e:
        print(f"[寫入失敗] {symbol}：{e}")

def process_symbol(symbol, sheet):
    df = fetch_stock_data(symbol)
    if df is not None:
        signal = analyze_signal(symbol, df)
        if signal:
            print(f"{symbol} -> {signal}")
            send_to_discord(symbol, signal)
            write_to_sheet(sheet, symbol, signal)

def main():
    sheet = setup_google_sheets()
    symbols = pd.read_csv(CSV_FILE)["symbol"].tolist()
    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(lambda sym: process_symbol(sym, sheet), symbols)

if __name__ == "__main__":
    main()
