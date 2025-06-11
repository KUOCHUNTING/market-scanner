# === 系統與基本套件 ===
import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
import pytz
from pytz import timezone
from dotenv import load_dotenv
from datetime import datetime, time
# === 載入 .env 檔案 ===
load_dotenv()
# ✅ 確認 Polygon API Key 是否正確載入
print(f"[DEBUG] Polygon Key = {os.getenv('POLYGON_API_KEY')}")
# === 技術指標相關套件 ===
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volume import OnBalanceVolumeIndicator
from ta.volatility import AverageTrueRange

# === 外部工具（像 Discord、Sheets 等） ===
import requests
from polygon import RESTClient

# === Google Sheets 套件 ===
import gspread
from google.oauth2.service_account import Credentials

# === 環境變數讀取 ===
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
GOOGLE_SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
GOOGLE_SERVICE_ACCOUNT_BASE64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")

# ✅ 防呆：檢查是否成功取得
if not GOOGLE_SPREADSHEET_ID:
    raise ValueError("❌ GOOGLE_SPREADSHEET_ID 環境變數沒有正確設定")

if not GOOGLE_SERVICE_ACCOUNT_BASE64:
    raise ValueError("❌ GOOGLE_SERVICE_ACCOUNT_BASE64 環境變數沒有正確設定")

if not GOOGLE_SHEET_NAME:
    raise ValueError("❌ GOOGLE_SHEET_NAME 環境變數沒有設定")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
import base64
import json

key_b64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")
key_dict = json.loads(base64.b64decode(key_b64))
credentials = Credentials.from_service_account_info(key_dict, scopes=SCOPES)

import os
import base64
import json
import gspread
from google.oauth2.service_account import Credentials

def get_gspread_client_from_env():
    encoded_key = os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")
    key_json = base64.b64decode(encoded_key).decode("utf-8")
    service_account_info = json.loads(key_json)

    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    return gspread.authorize(credentials)

# ✅ 使用函數取得 client 並開啟試算表
gc = get_gspread_client_from_env()
spreadsheet = gc.open_by_key(GOOGLE_SPREADSHEET_ID)
worksheets = spreadsheet.worksheets()

# ✅ 清理掉多餘空白、換行字元
worksheet_titles = [ws.title.strip() for ws in worksheets]

# ✅ 印出名稱列表供檢查
print("📋 工作表名稱列表：", worksheet_titles)

worksheet_trades = spreadsheet.worksheet("交易紀錄")
worksheet_stats = spreadsheet.worksheet("每日統計")
worksheet_tick = spreadsheet.worksheet("TICK紀錄")
worksheet_mood = spreadsheet.worksheet("每日盤前情緒紀錄")

spreadsheet = gc.open_by_key(GOOGLE_SPREADSHEET_ID)

worksheet = None
for attempt in range(3):
    try:
        worksheet = gc.open_by_key(GOOGLE_SPREADSHEET_ID).worksheet(GOOGLE_SHEET_NAME)
        break
    except gspread.exceptions.APIError as e:
        print(f"[警告] 第 {attempt+1}/3 次：Google Sheets API 錯誤，3 秒後重試...：{e}")
        time.sleep(3)

if worksheet is None:
    raise RuntimeError("❌ 無法連線到 Google Sheets，請稍後再試或檢查網路/API 狀態。")

# === 推播設定 ===
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "你的 Discord webhook URL")

# === 全域持倉與紀錄 ===
open_positions = {}
closed_trades = []

# === 訊號分類與觀察名單 === ✅ 你這段放這裡正確
observed_candidates = {}
watch_duration_limit = 30 * 60  # 單位：秒（30 分鐘

# === 資金管理設定（可自訂） ===
CAPITAL = 100_0000           # 總資金：100 萬
POSITION_SIZE = 0.05         # 每筆投入資金比例：5%
MAX_POSITION_PER_TRADE = 6_000  # 每筆最多投入金額上限（防爆倉）

# === 時區與交易時間設定 ===
EST = timezone("US/Eastern")
MARKET_OPEN = datetime.now(EST).replace(hour=9, minute=30, second=0, microsecond=0)
MARKET_CLOSE = datetime.now(EST).replace(hour=16, minute=0, second=0, microsecond=0)

def is_us_market_open_now():
    est = pytz.timezone("US/Eastern")
    now_est = datetime.now(est)
    market_open = time(9, 30)
    market_close = time(16, 0)
    is_weekday = now_est.weekday() < 5  # 週一～週五
    return is_weekday and market_open <= now_est.time() <= market_close

# ✅ 程式開頭就判斷一次
if not is_us_market_open_now():
    print("⏸️ 非美股開盤時間，跳過掃描。")
    sys.exit(0)  # 或 return / break / pass 視程式架構而定

# === 抓取 K 線資料（延遲 15 分鐘） ===
def fetch_15min_stock_data(symbol, include_yesterday=True):
    from polygon import RESTClient
    from datetime import datetime, timedelta, time as dtime
    import pytz
    import pandas as pd

    client = RESTClient(api_key=POLYGON_API_KEY)

    try:
        est = pytz.timezone("US/Eastern")
        now_est = datetime.now(est)

        # ✅ 取得今天的盤中起訖時間
        market_open = est.localize(datetime.combine(now_est.date(), dtime(9, 30)))
        market_close = est.localize(datetime.combine(now_est.date(), dtime(16, 0)))

        # ✅ 計算結束時間：延遲 15 分鐘並對齊到整數 15 分鐘
        end_time = now_est - timedelta(minutes=15)
        end_time = end_time.replace(minute=(end_time.minute // 15) * 15, second=0, microsecond=0)

        # ✅ 計算開始時間
        if include_yesterday:
            start_day = now_est - timedelta(days=1)
            start_time = est.localize(datetime.combine(start_day.date(), dtime(9, 30)))
        else:
            start_time = market_open

        # ✅ 防呆：確保時間範圍合理
        if end_time <= start_time:
            print(f"[SKIP] {symbol} 時間範圍無效（{start_time} → {end_time}）")
            return None

        from_ts = int(start_time.timestamp())
        to_ts = int(end_time.timestamp())

        print(f"[DEBUG] 抓取 15 分K {symbol}：{start_time} → {end_time}")

        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=15,
            timespan="minute",
            from_=from_ts,
            to=to_ts,
            limit=1000  # ✅ 跨日建議設高一點
        )

        if not aggs or not hasattr(aggs, "results") or len(aggs.results) == 0:
            print(f"[⚠️警告] {symbol} 沒有抓到 15 分圖資料（results 為空）")
            return None

        df = pd.DataFrame(aggs.results)
        df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df['symbol'] = symbol

        return df

    except Exception as e:
        print(f"[錯誤] 抓取 15 分K {symbol} 發生錯誤：{e}")
        return None
    
    # === 套用技術指標並回傳計算結果 ===
def apply_indicators(df):
    if df is None or df.empty:
        return None

    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    # === RSI（相對強弱指標）===
    rsi = RSIIndicator(close=close).rsi()

    # === MACD 柱狀圖（差離值）===
    macd = MACD(close=close).macd_diff()

    # === OBV（能量方向）===
    obv = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

    # === ATR（波動率）===
    atr = AverageTrueRange(high=high, low=low, close=close).average_true_range()

    # === VWAP（成交量加權平均價格）===
    df['cum_vol'] = volume.cumsum()
    df['cum_vol_x_price'] = (close * volume).cumsum()
    vwap = df['cum_vol_x_price'] / df['cum_vol']

    # === ROC（變動率）===
    df['roc'] = close.pct_change(periods=5) * 100

    # === TMO（Traders Momentum Oscillator）你後面會補進來用 ===
    # 這裡預留空間，可插入 tmo = calculate_tmo(df)

    return {
        'rsi': rsi,
        'macd': macd,
        'obv': obv,
        'atr': atr,
        'vwap': vwap,
        'roc': df['roc']
    }

# === 從 Polygon API 取得 TICK.US 的延遲 TICK 值 ===
def get_tick_data_from_polygon(api_key, window=20):
    from polygon import RESTClient
    from datetime import datetime, timedelta, time as dtime
    import pytz
    import pandas as pd

    try:
        client = RESTClient(api_key=api_key)

        est = pytz.timezone("US/Eastern")
        now = datetime.now(est)

        # ✅ 盤中限制
        market_open = est.localize(datetime.combine(now.date(), dtime(9, 30)))
        market_close = est.localize(datetime.combine(now.date(), dtime(16, 0)))
        if now < market_open or now > market_close:
            print(f"[SKIP] 現在是 {now.strftime('%H:%M')}，不在盤中，TICK 不抓")
            return None, []

        # ✅ 時間範圍
        end_time = now - timedelta(minutes=1)
        end_time = end_time.replace(second=0, microsecond=0)  # ✅ 對齊整分鐘
        start_time = end_time - timedelta(minutes=window * 1.5)

        from_ts = int(start_time.timestamp())
        to_ts = int(end_time.timestamp())

        aggs = client.get_aggs(
            ticker="TICK",
            multiplier=1,
            timespan="minute",
            from_=from_ts,
            to=to_ts,
            limit=window
        )

        if not aggs or not hasattr(aggs, "results") or len(aggs.results) == 0:
            print("[TICK] ❌ 無法取得 TICK 數據（results 為空）")
            return None, []

        df = pd.DataFrame(aggs.results)
        df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
        df.set_index('timestamp', inplace=True)
        tick_series = df['c'].tolist()  # ✅ 'c' 為收盤價欄位（TICK值）
        tick_now = tick_series[-1] if tick_series else None

        return tick_now, tick_series

    except Exception as e:
        print(f"[TICK] ❌ 發生錯誤：{e}")
        return None, []

# === 市場情緒共振邏輯（TICK） ===
def check_tick_resonance():
    try:
        tick_now, tick_series = get_tick_data_from_polygon(POLYGON_API_KEY)

        if tick_now is None or len(tick_series) < 5:
            return None

        tick_percentile = get_tick_percentile(tick_series, tick_now)
        tick_slope = get_tick_slope(tick_series)

        print(f"[TICK] 百分位：{tick_percentile}｜斜率：{tick_slope}")

        if tick_percentile > 95 and tick_slope > 0:
            return "BULLISH"
        elif tick_percentile < 5 and tick_slope < 0:
            return "BEARISH"
        else:
            return None
    except Exception as e:
        print(f"[TICK 判斷錯誤] {e}")
        return None

import numpy as np

# ✅ 假設你已有 tick_series（list 或 array），可從 API / CSV / Sheets 載入
# 這邊先用模擬版本建立模組框架，等你接上資料就能直接運作

# === 計算目前 TICK 百分位位置 ===
def get_tick_percentile(tick_series, current_tick):
    if not tick_series:
        return 50  # 沒資料時預設中性
    return np.round(np.sum(np.array(tick_series) < current_tick) / len(tick_series) * 100, 2)

# === 計算 TICK 的最近斜率（線性趨勢）===
def get_tick_slope(tick_series):
    if len(tick_series) < 5:
        return 0
    x = np.arange(len(tick_series))
    y = np.array(tick_series)
    slope = np.polyfit(x, y, 1)[0]  # 取得線性斜率
    return round(slope, 2)

# === 多空訊號分類模組 ===
def classify_signal(df, symbol):
    indicators = apply_indicators(df)
    if indicators is None:
        return None, None

    rsi = indicators['rsi']
    macd = indicators['macd']
    obv = indicators['obv']
    vwap = indicators['vwap']
    roc = indicators['roc']
    price = df['close'].iloc[-1]
    volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].rolling(20).mean().iloc[-1]

    # === 潛伏多頭（尚未爆量） ===
    if (
        rsi.iloc[-1] < 35 and rsi.iloc[-1] > rsi.iloc[-2] and
        macd.iloc[-1] > 0 and
        price > vwap.iloc[-1] and
        volume < avg_volume * 2
    ):
        return "潛伏多頭", f"⚠️ **[{symbol}] 潛伏 - 多頭轉折**"

    # === 潛伏空頭（尚未爆量） ===
    if (
        rsi.iloc[-1] > 65 and rsi.iloc[-1] < rsi.iloc[-2] and
        macd.iloc[-1] < 0 and
        price < vwap.iloc[-1] and
        volume < avg_volume * 2
    ):
        return "潛伏空頭", f"⚠️ **[{symbol}] 潛伏 - 空頭轉折**"

    # === 爆量異常（可進觀察名單） ===
    if volume > avg_volume * 5:
        return "爆量觀察", f"💣 **[{symbol}] 爆量異常**（{volume:,} 股）"

    return None, None

# === 評估是否產生交易訊號 ===
def evaluate_signal(symbol, df, mode="trade"):
    indicators = apply_indicators(df)
    if indicators is None:
        return None

    rsi = indicators['rsi']
    macd = indicators['macd']
    obv = indicators['obv']
    atr = indicators['atr']
    vwap = indicators['vwap']
    roc = indicators['roc']
    price = df['close'].iloc[-1]

    # === 半山腰過濾：避免 RSI 在 45～65 的震盪區間 ===
    if 45 < rsi.iloc[-1] < 65:
        return None

    # === 多單進場條件（短線搶轉折）===
    if (
        rsi.iloc[-1] < 30 and rsi.iloc[-1] > rsi.iloc[-2] and         # RSI 極端翻揚
        macd.iloc[-1] > macd.iloc[-2] and macd.iloc[-1] > 0 and       # MACD 柱狀翻正
        obv.iloc[-1] > obv.iloc[-2] > obv.iloc[-3] and                # OBV 多頭
        price > vwap.iloc[-1] and                                     # 在 VWAP 上方
        abs(price - vwap.iloc[-1]) / vwap.iloc[-1] < 0.03 and         # 沒離 VWAP 太遠
        roc.iloc[-1] > 0                                              # 有加速跡象
    ):
        return "BUY"

    # === 空單進場條件（短線轉弱）===
    if (
        rsi.iloc[-1] > 70 and rsi.iloc[-1] < rsi.iloc[-2] and         # RSI 過熱轉弱
        macd.iloc[-1] < macd.iloc[-2] and macd.iloc[-1] < 0 and       # MACD 柱狀轉負
        obv.iloc[-1] < obv.iloc[-2] < obv.iloc[-3] and                # OBV 空頭
        price < vwap.iloc[-1] and                                     # 在 VWAP 下方
        abs(price - vwap.iloc[-1]) / vwap.iloc[-1] < 0.03 and         # 沒偏離太遠
        roc.iloc[-1] < 0                                              # 有跌勢
    ):
        return "SELL"

    # === 預警（潛伏訊號）模式 ===
    if mode == "watch":
        if rsi.iloc[-1] < 35 or rsi.iloc[-1] > 65:
            return "WATCH"

    return None

# === 推播訊息到 Discord 頻道 ===
def push_to_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("[警告] 沒有設定 Discord Webhook，跳過推播")
        return

    payload = {
        "content": message
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code != 204:
            print(f"[推播失敗] 狀態碼：{response.status_code} - {response.text}")
    except Exception as e:
        print(f"[推播錯誤] {e}")

# === 自動建倉模組（正式建倉） ===
def enter_position(symbol, direction, price, confidence=1.0):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ✅ 進場資金計算（限制最大投入）
    position_cap = min(CAPITAL * POSITION_SIZE * confidence, MAX_POSITION_PER_TRADE)
    shares = int(position_cap // price)

    if shares == 0:
        print(f"[⚠️ 警告] {symbol} 價格過高，資金不足建倉")
        return

    msg = (
        f"🚀 **[建倉 - {direction}]** {symbol}\n"
        f"💰 價格：${price:.2f}｜數量：{shares:,} 股｜投入：${position_cap:,.0f}\n"
        f"📈 信心分數：{confidence:.2f}｜時間：{now}"
    )
    push_to_discord(msg)

    # ✅ 寫入進場紀錄（準備接入 Sheets）
    trade = {
        'symbol': symbol,
        'direction': direction,
        'entry_price': price,
        'entry_time': now,
        'shares': shares,
        'position_cap': position_cap,
        'confidence': confidence,
        'status': 'open'
    }

    # 放入全域持倉列表（之後再追蹤出場）
    open_positions[symbol] = trade

    check_exit_and_notify_dynamic(symbol, latest_price=price, current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# === 出場模組（浮動停利 + 停損機制） ===
def check_exit_and_notify_dynamic(symbol, latest_price, current_time):
    if symbol not in open_positions:
        return

    position = open_positions[symbol]
    entry_price = position['entry_price']
    shares = position['shares']
    direction = position['direction']
    confidence = position.get('confidence', 1.0)

    # ✅ 計算報酬率（正負都可以）
    pct_return = (latest_price - entry_price) / entry_price if direction == "多單" else (entry_price - latest_price) / entry_price

    # ✅ 進場金額
    position_value = shares * entry_price
    pnl = pct_return * position_value

    # === 停利 / 停損 條件 ===
    TAKE_PROFIT = 0.05   # +5%
    STOP_LOSS = -0.02    # -2%
    TRAIL_TRIGGER = 0.03 # 浮動停利觸發點
    TRAIL_MARGIN = 0.01  # 漲超 3% 回跌 1% 就出

    # === 漲幅追蹤 ===
    if 'max_gain' not in position:
        position['max_gain'] = pct_return
    else:
        position['max_gain'] = max(position['max_gain'], pct_return)

    # ✅ 停利
    if pct_return >= TAKE_PROFIT:
        exit_reason = "🎯 停利"
    # ✅ 停損
    elif pct_return <= STOP_LOSS:
        exit_reason = "🛑 停損"
    # ✅ 浮動停利：超過 3%，但跌回 1% 就出場
    elif position['max_gain'] >= TRAIL_TRIGGER and (position['max_gain'] - pct_return) >= TRAIL_MARGIN:
        exit_reason = "🔁 漲後回跌 - 浮動停利"
    else:
        return  # 尚未觸發出場條件

    # === 出場通知 ===
    msg = (
        f"💸 **[平倉 - {direction}]** {symbol}\n"
        f"{exit_reason}｜價格：${latest_price:.2f}\n"
        f"📈 報酬率：{pct_return:.2%}｜損益：${pnl:,.0f}\n"
        f"📊 信心分數：{confidence:.2f}｜時間：{current_time}"
    )
    push_to_discord(msg)

    # ✅ 寫入紀錄
    position['exit_price'] = latest_price
    position['exit_time'] = current_time
    position['return'] = pct_return
    position['pnl'] = pnl
    position['status'] = 'closed'

    closed_trades.append(position)
    del open_positions[symbol]  # 移除持倉

# === 寫入單筆交易紀錄到 Google Sheets ===
def write_to_google_sheets(trade):
    try:
        row = [
            trade['symbol'],
            trade['direction'],
            trade['entry_time'],
            trade.get('exit_time', ''),
            trade['entry_price'],
            trade.get('exit_price', ''),
            trade.get('shares', ''),
            trade.get('position_cap', ''),
            trade.get('return', ''),
            trade.get('pnl', ''),
            trade.get('confidence', ''),
            trade.get('status', '')
        ]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"[寫入成功] ✅ {trade['symbol']} 已記錄至 Google Sheets")
    except Exception as e:
        print(f"[寫入錯誤] ❌ {e}")

# === 每日績效統計寫入（勝率 / 總損益 / 筆數） ===
def write_daily_summary_to_sheets():
    try:
        if not closed_trades:
            print("[總結] 📭 今日無交易，不寫入績效統計")
            return

        today_str = datetime.now().strftime("%Y-%m-%d")
        total_trades = len(closed_trades)
        wins = sum(1 for t in closed_trades if t['return'] > 0)
        losses = sum(1 for t in closed_trades if t['return'] <= 0)
        total_pnl = sum(t['pnl'] for t in closed_trades)

        win_rate = wins / total_trades if total_trades > 0 else 0
        avg_return = sum(t['return'] for t in closed_trades) / total_trades

        row = [
            today_str,
            total_trades,
            wins,
            losses,
            f"{win_rate:.2%}",
            f"{avg_return:.2%}",
            f"${total_pnl:,.0f}"
        ]

        sheet_name = "每日績效總表"
        summary_ws = gc.open_by_key(GOOGLE_SHEET_ID).worksheet(sheet_name)
        summary_ws.append_row(row, value_input_option="USER_ENTERED")

        print(f"[寫入成功] 🧾 已寫入 {today_str} 績效總表：{total_trades} 筆交易")
        
    except Exception as e:
        print(f"[績效統計錯誤] ❌ {e}")

# === 主控邏輯 ===
def main():
    # ✅ 你可以手動列清單，或未來從 CSV 載入
    stock_list = ['AAPL', 'TSLA', 'AMD']

    for symbol in stock_list:
        df = fetch_15min_stock_data(symbol)
        if df is None:
            continue

        # === 若有預警訊號，推播並加入觀察名單 ===
        if signal_type:
            push_to_discord(message)
            observed_candidates[symbol] = {
                'start_time': datetime.now(),
                'last_push_time': datetime.now(),
                'reason': signal_type,
                'entry_price': df['close'].iloc[-1]
            }
        # === 加在每檔股票分析的最前面（通常在 evaluate_signal() 前） ===
        signal_type, message = classify_signal(df, symbol)

        if signal_type:
            push_to_discord(message)  # ✅ 這行是觸發推播
            observed_candidates[symbol] = {
                'start_time': datetime.now(),
                'last_push_time': datetime.now(),
                'reason': signal_type,
                'entry_price': df['close'].iloc[-1]
            }

        signal = evaluate_signal(symbol, df)
        price = df['close'].iloc[-1]

        # ✅ 插入這段「30分鐘共振過濾器」⬇️⬇️⬇️
        if signal in ["BUY", "SELL"]:
            confirm = confirm_30min_resonance(symbol)
            if confirm != signal:
                print(f"[共振] ❌ {symbol} 方向不一致，跳過正式建倉")
                continue

        # ✅ 加在正式訊號確認前（可搭配 30 分鐘共振）
        tick_view = check_tick_resonance()
        if signal == "BUY" and tick_view != "BULLISH":
            print(f"[TICK] ❌ 市場未共振多頭，跳過建倉：{symbol}")
            continue
        elif signal == "SELL" and tick_view != "BEARISH":
            print(f"[TICK] ❌ 市場未共振空頭，跳過建倉：{symbol}")
            continue

        if signal == "BUY":
            push_to_discord(f"🐸 **[進場 - 多單]** {symbol} 價格：${df['close'].iloc[-1]:.2f}")
        elif signal == "SELL":
            push_to_discord(f"🐻 **[進場 - 空單]** {symbol} 價格：${df['close'].iloc[-1]:.2f}")
        elif signal == "WATCH":
            push_to_discord(f"👀 **[觀察 - 潛伏訊號]** {symbol}")

        # ✅ 出場檢查
        check_exit_and_notify_dynamic(
            symbol,
            latest_price=price,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

# ✅ 執行主程式
if __name__ == "__main__":
    main()


