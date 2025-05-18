import pandas as pd
import yfinance as yf
import requests
import time
from datetime import datetime
import pytz

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
positions = {}

# === 市場狀態 ===
def is_market_open():
    eastern = pytz.timezone("US/Eastern")
    now_est = datetime.now(eastern)
    if now_est.weekday() >= 5:
        return False
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, microsecond=0)
    return market_open <= now_est <= market_close

# === 股票清單 ===
def get_all_us_symbols():
    url = "https://raw.githubusercontent.com/ldavis44/stock-symbol-list/master/all/all_tickers.txt"
    try:
        r = requests.get(url)
        return [s.strip().replace(".", "-") for s in r.text.splitlines() if s.strip()]
    except:
        return []

# === TICK 值 + 斜率 + 百分位
def get_tick_data():
    try:
        df = yf.download("^TICK", period="1d", interval="1m", progress=False)
        df.dropna(inplace=True)
        latest = df["Close"].iloc[-1]
        slope = df["Close"].diff().tail(3).mean()
        percentile = (df["Close"] < latest).sum() / len(df["Close"]) * 100
        return latest, slope, percentile
    except Exception as e:
        print(f"TICK 抓取錯誤：{e}")
        return 0, 0, 50

# === 推播
def send_to_discord(message):
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        print(f"推播失敗：{e}")

# === 技術指標
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

# === 判斷個股進出場條件 ===
def check_signal(symbol, tick_val, tick_slope, tick_perc):
    try:
        df = yf.download(symbol, period="1d", interval="5m", progress=False)
        if df is None or df.empty or len(df) < 30:
            return
        df = calc_indicators(df)
        latest = df.iloc[-1]
        if latest["Close"] < 1 or latest["Close"] > 10:
            return

        # TICK 共振判斷
        bull_tick = tick_val > 300 and tick_slope > 30 and tick_perc > 90
        bear_tick = tick_val < -300 and tick_slope < -30 and tick_perc < 10

        # 個股條件
        longCond = (
            latest["Close"] > latest["Upper"] and
            latest["TMO"] > latest["TMO_signal"] and
            latest["MACD_hist"] > 0 and
            latest["Volume"] > latest["VolAvg"] * 1.2 and
            latest["Close"] > latest["VWAP"] and
            bull_tick
        )
        shortCond = (
            latest["Close"] < latest["Lower"] and
            latest["TMO"] < latest["TMO_signal"] and
            latest["MACD_hist"] < 0 and
            latest["Volume"] > latest["VolAvg"] * 1.2 and
            latest["Close"] < latest["VWAP"] and
            bear_tick
        )

        longPre = (
            latest["Close"] > latest["Basis"] and
            latest["TMO"] > latest["TMO_signal"] and
            latest["MACD_line"] > 0 and
            latest["Close"] > latest["VWAP"] and
            bull_tick
        )
        shortPre = (
            latest["Close"] < latest["Basis"] and
            latest["TMO"] < latest["TMO_signal"] and
            latest["MACD_line"] < 0 and
            latest["Close"] < latest["VWAP"] and
            bear_tick
        )

        # 出場邏輯
        if symbol in positions:
            entry = positions[symbol]
            if entry["type"] == "long":
                if latest["Close"] >= entry["price"] + 5:
                    send_to_discord(f"[出場] {symbol} 多單停利，現價 {latest['Close']:.2f}")
                    del positions[symbol]
                elif latest["Low"] <= entry["price"] - 2:
                    send_to_discord(f"[出場] {symbol} 多單停損，現價 {latest['Close']:.2f}")
                    del positions[symbol]
            elif entry["type"] == "short":
                if latest["Close"] <= entry["price"] - 5:
                    send_to_discord(f"[出場] {symbol} 空單停利，現價 {latest['Close']:.2f}")
                    del positions[symbol]
                elif latest["High"] >= entry["price"] + 2:
                    send_to_discord(f"[出場] {symbol} 空單停損，現價 {latest['Close']:.2f}")
                    del positions[symbol]

        # 推播訊號
        if longCond and symbol not in positions:
            positions[symbol] = {"price": latest["Close"], "type": "long"}
            send_to_discord(f"[進場] {symbol} 多單成立，價格 {latest['Close']:.2f}｜TICK={tick_val:.0f} 百分位={tick_perc:.1f}%")
        elif shortCond and symbol not in positions:
            positions[symbol] = {"price": latest["Close"], "type": "short"}
            send_to_discord(f"[進場] {symbol} 空單成立，價格 {latest['Close']:.2f}｜TICK={tick_val:.0f} 百分位={tick_perc:.1f}%")
        elif longPre:
            send_to_discord(f"[預警] {symbol} 多頭預警｜TICK={tick_val:.0f} 百分位={tick_perc:.1f}%")
        elif shortPre:
            send_to_discord(f"[預警] {symbol} 空頭預警｜TICK={tick_val:.0f} 百分位={tick_perc:.1f}%")

    except Exception as e:
        print(f"{symbol} 發生錯誤：{e}")

# === 主程式 ===
def main():
    if not is_market_open():
        print("非盤中，暫停掃描")
        return
    tick_val, tick_slope, tick_perc = get_tick_data()
    print(f"TICK 現值：{tick_val:.0f} | 斜率：{tick_slope:.1f} | 百分位：{tick_perc:.1f}%")
    if tick_perc < 10 or tick_perc > 90:
        symbols = get_all_us_symbols()
        for symbol in symbols:
            check_signal(symbol, tick_val, tick_slope, tick_perc)
    else:
        print("TICK 未極端偏多／偏空，共振不足，略過本輪。")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(300)