# === 基本功能套件 ===
import requests
import pandas as pd
import random
import os
from polygon import RESTClient
import time                         # 用於 time.sleep()
from datetime import datetime, time  # 這個 time 是 class，可用於 time(9, 30)
from datetime import time
from datetime import time as dtime
import pytz
import pandas as pd
# === Google Sheets 套件 ===
import gspread
from oauth2client.service_account import ServiceAccountCredentials

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1381592286932238336/8TLHxMcoAxGEydMVrLeTrhoirnzplM3myRoaozF_7bxoFcK4g236KLnd075NogP25Gak"  # 記得換成自己的

# 🧠 交易資金設定
TOTAL_CAPITAL = 1000000       # 初始資金（可調整）
POSITION_SIZE = 0.05          # 每筆資金投入比例（5%）
capital_left = TOTAL_CAPITAL  # 剩餘可用資金
positions = {}                # 持倉紀錄（symbol: entry info）

# ✅ 出場風控參數（含三段鎖利）
TRAIL_TRIGGER = 0.03          # +3% 啟動追蹤停利
TRAIL_MARGIN  = 0.015         # 回落超過 1.5% 停利出場
DEFAULT_STOP_LOSS = 0.02      # -2% 停損
DEFAULT_TAKE_PROFIT = 0.05    # +5% 預設停利

import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

def detect_mean_reversion_signals(df):
    signal_note = None
    if len(df) < 30:
        return None  # 避免資料不足

    close = df['close']
    volume = df['volume']

    # ========== 計算指標 ==========
    rsi = RSIIndicator(close=close, window=14).rsi()

    bb = BollingerBands(close=close, window=20, window_dev=2)
    lower_band = bb.bollinger_lband()
    upper_band = bb.bollinger_hband()
    mid_band = bb.bollinger_mavg()

    rolling_mean = close.rolling(20).mean()
    rolling_std = close.rolling(20).std()
    z_score = (close - rolling_mean) / rolling_std

    latest_price = close.iloc[-1]
    latest_rsi = rsi.iloc[-1]
    prev_rsi = rsi.iloc[-2]
    latest_z = z_score.iloc[-1]

    # ========== 多單均值回歸條件 ==========
    if (
        latest_price < lower_band.iloc[-1] and
        latest_rsi > prev_rsi and
        latest_rsi < 35 and
        latest_z < -2
    ):
        signal_note = "📈 多單均值回歸：跌破布林下緣 + RSI 回升 + Z-score 偏低"

    # ========== 空單均值回歸條件 ==========
    elif (
        latest_price > upper_band.iloc[-1] and
        latest_rsi < prev_rsi and
        latest_rsi > 65 and
        latest_z > 2
    ):
        signal_note = "📉 空單均值回歸：突破布林上緣 + RSI 轉弱 + Z-score 偏高"

    return signal_note

# === 2. 技術指標計算函數 ===

def calculate_indicators(df):
    close = df['close']
    volume = df['volume']

    # RSI（預設 14）
    rsi = RSIIndicator(close=close, window=14).rsi()

    # ROC（預設 9）
    roc = ROCIndicator(close=close, window=9).roc()

    # EMA（5日 & 20日）
    ema_5 = EMAIndicator(close=close, window=5).ema_indicator()
    ema_20 = EMAIndicator(close=close, window=20).ema_indicator()

    # OBV（On-Balance Volume）
    obv = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

    # VWAP（成交量加權平均價格）
    df['cum_vol'] = df['volume'].cumsum()
    df['cum_vwap'] = (df['close'] * df['volume']).cumsum()
    vwap = df['cum_vwap'] / df['cum_vol']

    return {
        'rsi': rsi,
        'roc': roc,
        'ema_5': ema_5,
        'ema_20': ema_20,
        'obv': obv,
        'vwap': vwap
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

def push_entry_to_discord(symbol, direction, price, signal_note):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    emoji = "🐸" if direction == "多" else "🐶"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # === 自動計算投入資金與股數 ===
    capital_used = TOTAL_CAPITAL * POSITION_SIZE
    quantity = int(capital_used // price)  # 向下取整股數

    content = f"{emoji} **[建倉訊號 - {direction}單]** {symbol}\n" \
              f"💵 價格：${price:.2f}｜方向：{direction}\n" \
              f"📈 資金投入：${capital_used:.2f}｜股數：約 {quantity} 股\n" \
              f"📌 條件說明：{signal_note}\n" \
              f"🕒 時間：{time_str}"

    data = {"content": content}
    try:
        response = requests.post(webhook_url, json=data)
        if response.status_code != 204:
            print(f"[ERROR] Discord 推播失敗：{response.status_code}")
    except Exception as e:
        print(f"[EXCEPTION] Discord 推播錯誤：{e}")

def enter_position(symbol, price, direction, signal_note):
    global capital_left

    # 🧮 計算資金與股數
    capital_used = TOTAL_CAPITAL * POSITION_SIZE
    quantity = int(capital_used // price)

    # 💾 建立持倉紀錄
    positions[symbol] = {
        "entry_price": price,
        "direction": direction,
        "capital_used": capital_used,
        "quantity": quantity,
        "entry_time": datetime.now(),
        "signal_note": signal_note,
        "sell_stage": 0,            # 用於三段鎖利
        "max_gain": 0.0             # 用於追蹤停利
    }

    # 💰 扣除可用資金
    capital_left -= capital_used

    print(f"[ENTRY] 建倉 {symbol} {direction}單，價格={price:.2f}，股數={quantity}，投入資金=${capital_used:.2f}")

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

    # 推播出場訊息
    emoji = "✅" if return_rate >= 0 else "⚠️"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"{emoji} **[出場通知 - {direction}單]** {symbol}\n" \
              f"📉 出場價格：${latest_price:.2f}｜數量：{exit_qty} 股\n" \
              f"💰 報酬率：{return_rate*100:.2f}%｜獲利金額：${profit_dollar:.2f}\n" \
              f"📌 原因：{reason}\n" \
              f"🕒 時間：{time_str}"

    requests.post(os.getenv("DISCORD_WEBHOOK_URL"), json={"content": content})

    # ✅ 若剩餘股數為 0 → 移除持倉
    if pos["quantity"] <= 0:
        del positions[symbol]

def scan_market(symbol_list):
    for symbol in symbol_list:
        try:
            df = get_recent_data(symbol)
            if df is None or len(df) < 30:
                continue

            indicators = calculate_indicators(df)
            signal_type, signal_note = detect_trading_signal(symbol, df, indicators)

            if signal_type == "BUY":
                direction = "多"
                enter_position(symbol, df['close'].iloc[-1], direction, signal_note)
                push_entry_to_discord(symbol, direction, df['close'].iloc[-1], signal_note)

            elif signal_type == "SELL":
                direction = "空"
                enter_position(symbol, df['close'].iloc[-1], direction, signal_note)
                push_entry_to_discord(symbol, direction, df['close'].iloc[-1], signal_note)

            # ✅ 出場條件判斷（無論是否新訊號）
            if symbol in positions:
                check_exit_and_notify(symbol, df['close'].iloc[-1])

        except Exception as e:
            print(f"[ERROR] {symbol} 掃描錯誤：{e}")

# ✅ 補上開盤與收盤時間的定義
est = pytz.timezone("US/Eastern")
now_est = datetime.now(est)
market_open = est.localize(datetime.combine(now_est.date(), time(9, 30)))
market_close = est.localize(datetime.combine(now_est.date(), time(16, 0)))
# 只在開盤期間運行
if now_est < market_open or now_est > market_close:
    print("[INFO] 非美股盤中時間，跳過掃描")
    exit()

API_KEY = os.getenv("POLYGON_API_KEY") or "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"
STOCK_LIST_CSV = "filtered_us_stocks_common_only.csv"


WEBHOOK_URL = "https://discord.com/api/webhooks/1372956363235393536/2bELr_6LwGlk2K7G4B3d3J0MBD5iv04IwC33pQaWxAHcRbgn6sBVtkvI_65FfmC4Um5f"

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

def load_stock_list(filepath):
    try:
        df = pd.read_csv(filepath)
        return df['symbol'].tolist()
    except Exception as e:
        print(f"[ERROR] 無法讀取股票清單：{e}")
        return []
stock_list = load_stock_list("filtered_us_stocks_common_only.csv")

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

def fetch_stock_data(symbol, api_key):
    from polygon import RESTClient
    from datetime import datetime, timedelta, time as dtime
    import pytz
    import pandas as pd

    est = pytz.timezone("US/Eastern")
    now_est = datetime.now(est)

    # 設定當天的交易時段（09:30～16:00）
    market_open = est.localize(datetime.combine(now_est.date(), dtime(9, 30)))
    market_close = est.localize(datetime.combine(now_est.date(), dtime(16, 0)))

    now = datetime.now(est)  # ✅ 補上 now

    # 預設抓最近 50 根 5分鐘K
    end_time = now
    start_time = now - timedelta(minutes=5 * 50)

    # ✅ 補資料：收盤後改抓當天完整盤中
    if now_est > market_close:
        start_time = market_open
        end_time = market_close

    # ✅ 補資料：開盤前或區間跨盤前，改抓昨天
    elif now_est < market_open or start_time < market_open:
        print(f"[補資料] 當前資料不足，改抓昨日盤中")
        yesterday = now_est.date() - timedelta(days=1)
        start_time = est.localize(datetime.combine(yesterday, dtime(9, 30)))
        end_time = est.localize(datetime.combine(yesterday, dtime(16, 0)))

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
            limit=100
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


# ✅ 主程式區（放最外層）
if __name__ == "__main__":
    main_loop()
