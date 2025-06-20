# === 📦 系統與網路套件 ===
import os
import random
import requests

# === 📊 資料處理 ===
import pandas as pd
from datetime import datetime
from datetime import datetime, time
from datetime import datetime, timedelta, time as dtime

# === 📈 技術指標（ta-lib 套件）===
from ta.momentum import RSIIndicator, ROCIndicator
from ta.volume import OnBalanceVolumeIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands

# === 📡 Polygon API 套件 ===
from polygon import RESTClient

# === 🧾 Google Sheets 套件 ===
import gspread
from oauth2client.service_account import ServiceAccountCredentials

import pytz
est = pytz.timezone("US/Eastern")
now_est = datetime.now(est)

# ✅ 補上開盤與收盤時間的定義
market_open = est.localize(datetime.combine(now_est.date(), time(9, 30)))
market_close = est.localize(datetime.combine(now_est.date(), time(16, 0)))
# 只在開盤期間運行
if now_est < market_open or now_est > market_close:
    print("[INFO] 非美股盤中時間，跳過掃描")
    exit()

API_KEY = os.getenv("POLYGON_API_KEY") or "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"
STOCK_LIST_CSV = "filtered_us_stocks_common_only.csv"


WEBHOOK_URL = "https://discord.com/api/webhooks/1372956363235393536/2bELr_6LwGlk2K7G4B3d3J0MBD5iv04IwC33pQaWxAHcRbgn6sBVtkvI_65FfmC4Um5f"
# === 🧠 交易資金設定 ===
TOTAL_CAPITAL = 1000000         # 初始總資金（單位：美元）
POSITION_SIZE = 0.05            # 每次進場資金佔比（5%）
capital_left = TOTAL_CAPITAL   # 剩餘可用資金
positions = {}                  # 持倉記錄：symbol -> {'entry_price', 'shares', 'entry_time'}

# === 🛡️ 出場風控參數（含三段鎖利）===
TRAIL_TRIGGER = 0.03            # +3% 啟動移動停利
TRAIL_MARGIN = 0.015            # 回落 1.5% 停利出場
DEFAULT_STOP_LOSS = 0.02        # -2% 強制停損
DEFAULT_TAKE_PROFIT = 0.05      # +5% 預設停利

def load_stock_list(filepath="filtered_us_stocks_common_only.csv"):
    try:
        df = pd.read_csv(filepath)
        return df['symbol'].tolist()
    except Exception as e:
        print(f"[ERROR] 無法讀取股票清單：{e}")
        return []

# ✅ 呼叫時就可以簡單這樣
symbol_list = load_stock_list()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

def fetch_stock_data(symbol, api_key):

    est = pytz.timezone("US/Eastern")
    now_est = datetime.now(est)

    # 設定當天的交易時段（09:30～16:00）
    market_open = est.localize(datetime.combine(now_est.date(), dtime(9, 30)))
    market_close = est.localize(datetime.combine(now_est.date(), dtime(16, 0)))

    est = pytz.timezone("US/Eastern")
    now = datetime.now(est)  # ✅ 要補這行

    # 然後你才能寫：
    end_time = now
    start_time = now - timedelta(minutes=5 * 50)

    # ✅ 如果現在是收盤後，直接抓今天完整盤中
    if now_est > market_close:
        start_time = market_open
        end_time = market_close

    # ✅ 如果現在是開盤前或資料區間跨開盤前，就抓昨天完整盤中
    elif now_est < market_open:
        print(f"[補資料] 當前資料不足，改抓昨日盤中")
        yesterday = now_est.date() - timedelta(days=1)
        start_time = est.localize(datetime.combine(yesterday, dtime(9, 30)))
        end_time = est.localize(datetime.combine(yesterday, dtime(16, 0)))

    # 其餘狀況（盤中）則維持預設抓法

    from_ts = int(start_time.timestamp() * 1000)
    to_ts = int(end_time.timestamp() * 1000)

    print(f"[DEBUG] 抓取 {symbol} 15 分K：{from_ts} → {to_ts}")
    print(f"[DEBUG] 抓取 {symbol} 15 分K：{start_time} → {end_time}")

    try:
        client = RESTClient(api_key=api_key)

        bars = client.get_aggs(
            ticker=symbol,
            multiplier=5,
            timespan="minute",
            from_=from_ts,
            to=to_ts,
            limit=100,
            adjusted=True
        )

        if not bars:
            print(f"[❌錯誤] {symbol} 無 bars 資料")
            return None

        df = pd.DataFrame([{
            "timestamp": bar.timestamp,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        } for bar in bars])

        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)

        return df

    except Exception as e:
        print(f"[❌錯誤] 抓取 {symbol} 失敗：{e}")
        return None
        
def detect_mean_reversion_signals(df, symbol):
    global capital_left  # ⚠️ 確保這個變數在主程式有定義
    signal_note = None

    if len(df) < 30:
        return None

    ind = calculate_indicators(df)
    latest_price = df['close'].iloc[-1]
    latest_rsi = ind['rsi'].iloc[-1]
    prev_rsi = ind['rsi'].iloc[-2]
    zscore = ind['zscore'].iloc[-1]
    ema5 = ind['ema_5'].iloc[-1]
    ema20 = ind['ema_20'].iloc[-1]
    lower_band = ind['lower_band'].iloc[-1]
    upper_band = ind['upper_band'].iloc[-1]

    # ✅ 多單條件
    if (
        latest_price < lower_band and
        latest_rsi > prev_rsi and
        latest_rsi < 35 and
        zscore < -2 and
        ema5 > ema20
    ):
        signal_note = "📈 多單均值回歸：跌破布林下緣 + RSI 回升 + Z-score 偏低 + EMA多方\n🔎 大盤盤整中，啟動均值回歸判斷"
        # === 推播
        push_entry_to_discord(
            symbol=symbol,
            direction="多",
            price=latest_price,
            signal_note=signal_note,
            zscore=zscore,
            rsi=latest_rsi
        )

        # === 建倉記錄
        capital_used = TOTAL_CAPITAL * POSITION_SIZE
        quantity = int(capital_used // latest_price)

        positions[symbol] = {
            "direction": "多",
            "entry_price": latest_price,
            "shares": quantity,
            "entry_time": datetime.now(),
            "capital_used": capital_used,
            "sell_stage": 0,        # 初始為 0（未鎖利）
            "max_gain": 0.0,        # 初始最大報酬率為 0
            "strategy": "均值回歸"   # ✅ 用英文引號包住中文字
        }

        capital_left -= capital_used
        return signal_note

    # ✅ 空單條件
    elif (
        latest_price > upper_band and
        latest_rsi < prev_rsi and
        latest_rsi > 65 and
        zscore > 2 and
        ema5 < ema20
    ):
        signal_note = "📉 空單均值回歸：突破布林上緣 + RSI 轉弱 + Z-score 偏高 + EMA空方\n🔎 大盤盤整中，啟動均值回歸判斷"

        # === 推播
        push_entry_to_discord(
            symbol=symbol,
            direction="空",
            price=latest_price,
            signal_note=signal_note,
            zscore=zscore,
            rsi=latest_rsi
        )

        # === 建倉記錄
        capital_used = TOTAL_CAPITAL * POSITION_SIZE
        quantity = int(capital_used // latest_price)

        positions[symbol] = {
            "direction": "空",
            "entry_price": latest_price,
            "quantity": quantity,
            "entry_time": datetime.now(),
            "capital_used": capital_used,
            "sell_stage": 0,         # 初始鎖利階段
            "max_gain": 0.0,         # 初始最大報酬率
            "strategy": "均值回歸"    # 策略類型（可用於出場推播標示）
        }

        capital_left -= capital_used
        return signal_note

    return None

# === 2. 技術指標計算函數 ===

def calculate_indicators(df):
    if len(df) < 30:
        print("[警告] 技術指標計算時資料不足，跳過")
        return None
    
    close = df['close']
    volume = df['volume']

    # === RSI（14）===
    rsi = RSIIndicator(close=close, window=14).rsi()

    # === ROC（9）===
    roc = ROCIndicator(close=close, window=9).roc()

    # === OBV ===
    obv = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

    # === Z-score（20）===
    rolling_mean = close.rolling(20).mean()
    rolling_std = close.rolling(20).std()
    zscore = (close - rolling_mean) / rolling_std

    # === Bollinger Bands（20, 2x）===
    bb = BollingerBands(close=close, window=20, window_dev=2)
    lower_band = bb.bollinger_lband()
    upper_band = bb.bollinger_hband()
    mid_band = bb.bollinger_mavg()

    # === VWAP（成交量加權平均價）===
    df['cum_vol'] = volume.cumsum()
    df['cum_vwap'] = (close * volume).cumsum()
    vwap = df['cum_vwap'] / df['cum_vol']

    # === EMA（5日與 20日）===
    ema_5 = EMAIndicator(close=close, window=5).ema_indicator()
    ema_20 = EMAIndicator(close=close, window=20).ema_indicator()

    return {
        'rsi': rsi,
        'roc': roc,
        'obv': obv,
        'zscore': zscore,
        'lower_band': lower_band,
        'upper_band': upper_band,
        'mid_band': mid_band,
        'vwap': vwap,
        'ema_5': ema_5,
        'ema_20': ema_20
    }

# === 3. 訊號判斷邏輯（多空建倉，無預警） ===

def detect_trading_signal(symbol, df, indicators):
    latest_price = df['close'].iloc[-1]
    rsi = indicators['rsi'].iloc[-1]
    roc = indicators['roc'].iloc[-1]
    obv = indicators['obv'].iloc[-1]
    vwap = indicators['vwap'].iloc[-1]

    # 排除 RSI 半山腰
    in_neutral_zone = 45 <= rsi <= 65
    if in_neutral_zone:
        return None, None

    signal_type = None
    signal_note = None

    # === 🟢 多單建倉條件（原本的預警條件，現在視為正式建倉）
    if (
        rsi < 35 and rsi > indicators['rsi'].iloc[-2] and
        roc < 0 and roc > indicators['roc'].iloc[-2] and
        obv > indicators['obv'].iloc[-2] and
        abs(latest_price - vwap) / vwap < 0.05
    ):
        signal_type = "BUY"
        signal_note = "🐸 多單建倉：RSI回升 + ROC翻揚 + OBV上升 + 貼近VWAP"

    # === 🔴 空單建倉條件（原本的預警條件，現在視為正式建倉）
    elif (
        rsi > 65 and rsi < indicators['rsi'].iloc[-2] and
        roc > 0 and roc < indicators['roc'].iloc[-2] and
        obv < indicators['obv'].iloc[-2] and
        abs(latest_price - vwap) / vwap < 0.05
    ):
        signal_type = "SELL"
        signal_note = "🐶 空單建倉：RSI轉弱 + ROC下滑 + OBV下降 + 貼近VWAP"

    return signal_type, signal_note

# === 5. 推播模組（Discord） ===

def push_entry_to_discord(symbol, direction, price, signal_note, zscore=None, rsi=None):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    emoji = "🐸" if direction == "多" else "🐶"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    capital_used = TOTAL_CAPITAL * POSITION_SIZE
    quantity = int(capital_used // price)

    content = f"{emoji} **[建倉訊號 - {direction}單]** {symbol}\n" \
              f"💵 價格：${price:.2f}｜方向：{direction}\n" \
              f"📈 資金投入：${capital_used:.2f}｜股數：約 {quantity} 股\n"

    if zscore is not None:
        content += f"📊 Z-score：{zscore:.2f}（{'超跌' if zscore < -2 else '超漲' if zscore > 2 else '偏離中'}）\n"
    if rsi is not None:
        content += f"📉 RSI：{rsi:.1f}\n"

    content += f"📌 條件說明：{signal_note}\n" \
               f"🕒 時間：{time_str}"

    try:
        requests.post(webhook_url, json={"content": content})
    except Exception as e:
        print(f"[EXCEPTION] Discord 推播錯誤：{e}")

def enter_position(symbol, price, direction, signal_note):
    global capital_left

    # 🧮 計算資金與股數
    capital_used = TOTAL_CAPITAL * POSITION_SIZE
    quantity = int(capital_used // price)
    positions[symbol] = {
        "direction": direction,
        "entry_price": price,
        "shares": quantity,
        "entry_time": datetime.now(),
        "capital_used": capital_used,
        "sell_stage": 0,
        "max_gain": 0.0,
        "strategy": "均值回歸"
    }
    capital_left -= capital_used

    print(f"[ENTRY] 建倉 {symbol} {direction}單，價格={price:.2f}，股數={quantity}，投入資金=${capital_used:.2f}")

def push_exit_to_discord(symbol, direction, entry_price, exit_price, return_rate, shares, reason):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"""📤**[出場 - {direction}單]**📤 {symbol}
📈 出場價格：${exit_price:.2f}
📉 進場價格：${entry_price:.2f}
📊 報酬率：{return_rate:.2%}
📦 股數：{shares}
🔄 出場原因：{reason}
📆 時間：{now}"""
    requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})

# === 4. 出場邏輯模組（三段鎖利 + 停損） ===

def check_exit_and_notify(symbol, latest_price):
    global capital_left

    if symbol not in positions:
        return

    pos = positions[symbol]
    entry_price = pos["entry_price"]
    direction = pos["direction"]
    capital_used = pos["capital_used"]
    quantity = pos["quantity"]
    sell_stage = pos["sell_stage"]
    max_gain = pos["max_gain"]

    # 🧮 報酬率計算（多單 / 空單）
    return_rate = (latest_price - entry_price) / entry_price if direction == "多" else (entry_price - latest_price) / entry_price

    # ⬆️ 更新最高報酬（用於追蹤停利）
    if return_rate > max_gain:
        pos["max_gain"] = return_rate
        max_gain = return_rate

    # 🧠 停損：虧損超過 -2%
    if return_rate <= -DEFAULT_STOP_LOSS:
        reason = f"🔻 停損觸發：報酬率 {return_rate*100:.2f}%"
        exit_ratio = 1.0
        sell_stage = -1

    # ✅ 第一段：+5% 鎖利 → 出場一半
    elif return_rate >= DEFAULT_TAKE_PROFIT and sell_stage == 0:
        reason = f"🔒 第一段鎖利：報酬率 {return_rate*100:.2f}%"
        exit_ratio = 0.5
        sell_stage = 1

    # ✅ 第二段：+8% 全部出場
    elif return_rate >= 0.08 and sell_stage <= 1:
        reason = f"🔒 第二段鎖利：報酬率 {return_rate*100:.2f}%"
        exit_ratio = 1.0
        sell_stage = 2

    # ✅ 第三段：+3% 後回落超過 1.5%
    elif max_gain >= TRAIL_TRIGGER and (max_gain - return_rate) >= TRAIL_MARGIN and sell_stage <= 1:
        reason = f"🔃 追蹤停利觸發（回落 {((max_gain - return_rate)*100):.2f}%）"
        exit_ratio = 1.0
        sell_stage = 3

    else:
        return  # 尚未達出場條件

    # 🧾 出場執行
    exit_qty = int(quantity * exit_ratio)
    profit_dollar = exit_qty * (latest_price - entry_price) if direction == "多" else exit_qty * (entry_price - latest_price)

    # ✅ 回收資金
    capital_left += latest_price * exit_qty
    pos["quantity"] -= exit_qty
    pos["sell_stage"] = sell_stage



    # ✅ 推播出場訊息
    emoji = "✅" if return_rate >= 0 else "⚠️"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ✅ 🔽 插在這裡！
    strategy_name = pos.get("strategy", "一般策略")

    content = (
        f"{emoji} **[出場通知 - {strategy_name}｜{direction}單]** {symbol}\n"
        f"📈 出場價格：${latest_price:.2f} ｜ 數量：{exit_qty} 股\n"
        f"📊 報酬率：{return_rate * 100:.2f}% ｜ 獲利金額：${profit_dollar:.2f}\n"
        f"🔄 原因：{reason}\n"
        f"🕒 時間：{time_str}"
    )

    requests.post(DISCORD_WEBHOOK_URL, json={"content": content})

    # ✅ 若剩餘股數為 0 → 移除持倉
    if pos["quantity"] <= 0:
        del positions[symbol]

def scan_market(symbol_list):
    for symbol in symbol_list:
        try:
            print(f"📡 掃描中：{symbol}")

            df = fetch_stock_data(symbol, POLYGON_API_KEY)
            if df is None or len(df) < 30:
                continue

            indicators = calculate_indicators(df)
            signal_type, signal_note = detect_trading_signal(symbol, df, indicators)
            latest_price = df['close'].iloc[-1]

            if signal_type == "BUY":
                direction = "多"
                enter_position(symbol, latest_price, direction, signal_note)
                push_entry_to_discord(symbol, direction, latest_price, signal_note)

            elif signal_type == "SELL":
                direction = "空"
                enter_position(symbol, latest_price, direction, signal_note)
                push_entry_to_discord(symbol, direction, latest_price, signal_note)

            # ✅ 出場條件判斷（若已建倉）
            if symbol in positions:
                check_exit_and_notify(symbol, latest_price)

        except Exception as e:
            print(f"[ERROR] {symbol} 掃描錯誤：{e}")


def push_to_discord(symbol, price, rsi, tmo, vwap, volume_ratio, ema_cross, kd_status, candle_type, signal_note):
    try:
        vwap_text = f"{vwap:.2f}" if vwap is not None and not pd.isna(vwap) else "無"
        message = (
            f"📣 **[訊號]** {symbol}\n"
            f"💰 價格：${price:.2f} | RSI：{rsi:.1f} | TMO：{tmo:.2f}\n"
            f"📊 VWAP：{vwap_text} | 倍量：{volume_ratio:.2f}x\n"
            f"📈 EMA：{ema_cross} | KD：{kd_status} | K棒：{candle_type}\n"
            f"🔔 **訊號類型**：{signal_note}"
        )
        payload = {"content": message}
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code != 204:
            print(f"[WARNING] Discord 推播失敗：{response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] 發送 Discord 推播失敗：{e}")
    except Exception as e:
        print(f"[ERROR] {e}")

def analyze_stock_data(symbol, df):
    signal_note = detect_mean_reversion_signals(df)
    if signal_note:
        latest_price = df['close'].iloc[-1]
        rsi = RSIIndicator(close=df['close'], window=14).rsi().iloc[-1]
        zscore = ((df['close'] - df['close'].rolling(20).mean()) / df['close'].rolling(20).std()).iloc[-1]

        direction = "多" if "多單" in signal_note else "空"

        push_entry_to_discord(
            symbol=symbol,
            direction=direction,
            price=latest_price,
            signal_note=signal_note,
            zscore=zscore,
            rsi=rsi
        )
        return True
    return False
    
def main_loop():
    while True:
        symbol_list = load_stock_list()  # 確保這是回傳股票代碼清單的函數
        scan_market(symbol_list)
        time.sleep(60)


# ✅ 主程式區（放最外層）
if __name__ == "__main__":
    main_loop()
