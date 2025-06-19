# === 基本功能套件 ===
import requests
import pandas as pd
import random
import os
from polygon import RESTClient
import time                         # 用於 time.sleep()
from datetime import datetime, time  # 這個 time 是 class，可用於 time(9, 30)
from datetime import time
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

# === 7. 主迴圈執行區（從 CSV 載入） ===

import time

# === 6. Polygon 資料抓取模組（5分鐘K） ===
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
    elif now_est < market_open or start_time < market_open:
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

# === 7. 主掃描流程與自動執行 ===
def get_symbol_list():
    try:
        df = pd.read_csv("stock_list.csv")
        return df["symbol"].dropna().tolist()
    except Exception as e:
        print(f"[ERROR] 載入股票清單失敗：{e}")
        return []

def fetch_stock_data(symbol, api_key):
    from polygon import RESTClient
    from datetime import datetime, timedelta, time as dtime
    import pytz
    import pandas as pd

    # 取得美東時間 now
    est = pytz.timezone("US/Eastern")
    now = datetime.now(est)

    # 設定今日開盤 / 收盤時間
    market_open = est.localize(datetime.combine(now.date(), dtime(9, 30)))
    market_close = est.localize(datetime.combine(now.date(), dtime(16, 0)))

    # 預設抓 50 根 5分鐘線（大約4小時）
    end_time = now
    start_time = now - timedelta(minutes=5 * 50)

    # 若已收盤，抓當天完整盤中
    if now > market_close:
        start_time = market_open
        end_time = market_close

    # 若尚未開盤或早上太早，抓昨天完整盤中
    elif now < market_open or start_time < market_open:
        print(f"[補資料] 現在是盤前，抓取昨日資料")
        yesterday = now.date() - timedelta(days=1)
        start_time = est.localize(datetime.combine(yesterday, dtime(9, 30)))
        end_time = est.localize(datetime.combine(yesterday, dtime(16, 0)))

    # 時間戳轉為毫秒
    from_ts = int(start_time.timestamp() * 1000)
    to_ts = int(end_time.timestamp() * 1000)

    print(f"[DEBUG] 抓取 {symbol}：{start_time} → {end_time}")

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
            print(f"[❌錯誤] {symbol} 沒有資料")
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
        print(f"[❌錯誤] {symbol} 抓取失敗：{e}")
        return None

def scan_market(symbol_list, api_key):
    for symbol in symbol_list:
        df = fetch_stock_data(symbol, api_key)
        if df is None or len(df) < 30:
            continue
        indicators = calculate_indicators(df)
        signal_type, signal_note = detect_trading_signal(symbol, df, indicators)
        if signal_type == "BUY":
            enter_position(symbol, df['close'].iloc[-1], "多", signal_note)
            push_entry_to_discord(symbol, "多", df['close'].iloc[-1], signal_note)
        elif signal_type == "SELL":
            enter_position(symbol, df['close'].iloc[-1], "空", signal_note)
            push_entry_to_discord(symbol, "空", df['close'].iloc[-1], signal_note)
        if symbol in positions:
            check_exit_and_notify(symbol, df['close'].iloc[-1])

def is_market_open():
    est = pytz.timezone("US/Eastern")
    now = datetime.now(est).time()
    market_open = dtime(9, 30)
    market_close = dtime(16, 0)
    return market_open <= now <= market_close

def main_loop():
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise Exception("❌ 找不到 Polygon API 金鑰，請確認環境變數是否正確設定")
    while True:
        if not is_market_open():
            print("⏰ 非盤中，等待60秒...")
            time.sleep(60)
            continue
        symbol_list = get_symbol_list()
        if not symbol_list:
            print("⚠️ 股票清單為空")
            time.sleep(60)
            continue
        scan_market(symbol_list, api_key)
        print("✅ 本輪結束，等待60秒...")
        time.sleep(60)

if __name__ == "__main__":
    main_loop()
