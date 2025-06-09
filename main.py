# === 技術指標 ===
from ta.volume import OnBalanceVolumeIndicator, MFIIndicator
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator

# === 基本功能套件 ===
import requests
import pandas as pd
import random
import time
from polygon import RESTClient
from datetime import datetime, timedelta, time
from pytz import timezone

# === Google Sheets 套件 ===
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials

# === API / SDK ===
from dotenv import load_dotenv
from alpaca.data.timeframe import TimeFrame

import os
import base64
import json
import gspread
from google.oauth2.service_account import Credentials
# Polygon（抓 TICK）
POLYGON_API_KEY = "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"
client = RESTClient(api_key=POLYGON_API_KEY)

def get_gspread_client_from_env():
    encoded_key = os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")
    if not encoded_key:
        raise ValueError("找不到 GOOGLE_SERVICE_ACCOUNT_BASE64 環境變數")
    key_json = base64.b64decode(encoded_key).decode("utf-8")
    key_data = json.loads(key_json)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(key_data, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def init_sheets():
    # ✅ 使用環境變數方式建立 client
    client = get_gspread_client_from_env()
    
    # ✅ 使用環境變數讀取試算表 ID
    sheet_id = os.getenv("GOOGLE_SPREADSHEET_ID")
    if not sheet_id:
        raise ValueError("找不到 GOOGLE_SPREADSHEET_ID 環境變數")

    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.sheet1

    # ✅ 寫入表頭
    headers = [
        '時間', '股票代號', '方向', '價格', '進場時間', '出場時間',
        '報酬率', '持倉時間（秒）', 'TICK%', 'TRIN', 'TMO', 'VWAP偏離',
        '成交量倍數', 'RSI', 'MACD', 'OBV方向', 'ROC', '策略版本', '信心分數'
    ]
    worksheet.clear()
    worksheet.append_row(headers)
    print("[INFO] ✅ 已初始化 Google Sheets 欄位")

def write_to_sheet_by_type(data_dict, type="交易紀錄"):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_file(
            "gsheet_key.json", scopes=scopes
        )
        gc = gspread.authorize(credentials)
        spreadsheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/")
        worksheet = spreadsheet.worksheet(type)

        # 依據類型排序欄位
        header_map = {
            "交易紀錄": ["日期", "股票代號", "進場時間", "出場時間", "持倉時間", "方向", "進場價格", "出場價格", "報酬率", "資金投入", "剩餘資金", "訊號類型", "是否TICK共振", "TICK 百分位", "TRIN 值", "TMO 值", "TMO 斜率", "RSI 值", "MACD 狀態", "VWAP 乖離", "成交量倍數", "OBV 方向", "策略版本", "信心分數"],
            "潛伏訊號紀錄": ["時間", "股票代號", "價格", "RSI", "TMO", "VWAP 乖離", "成交量倍數", "OBV", "當時盤勢情緒", "是否推播", "預警類型"],
            "TICK共振紀錄": ["時間", "TICK 值", "TICK 百分位", "TICK 斜率", "TRIN 值", "共振股票代號"]
        }

        if type not in header_map:
            print(f"[WARNING] 不支援的類型：{type}")
            return

        row = [data_dict.get(col, "") for col in header_map[type]]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"[SHEET] ✅ 寫入成功：{type} → {data_dict.get('股票代號', '')}")
    except Exception as e:
        print(f"[ERROR] Google Sheets 寫入失敗：{e}")

def generate_daily_summary():
    try:
        # Google Sheets 連線
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Trading Log").worksheet("交易紀錄")

        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        today_str = datetime.now(timezone("US/Eastern")).strftime("%Y-%m-%d")
        df_today = df[df["entry_time"].str.startswith(today_str)]

        if df_today.empty:
            return f"📊 **[今日績效速報]**\n🗓️ 日期：{today_str}\n⚠️ 今日尚無任何交易紀錄。"

        total_trades = len(df_today)
        wins = len(df_today[df_today["return_rate"] > 0])
        losses = len(df_today[df_today["return_rate"] <= 0])
        win_rate = (wins / total_trades) * 100
        total_return = df_today["return_rate"].sum() * 100
        capital_used = df_today["capital_used"].sum()
        capital_left = df_today["capital_left"].iloc[-1]

        return (
            f"📊 **[今日績效速報]**\n"
            f"🗓️ 日期：{today_str}\n"
            f"💼 總進場筆數：{total_trades}\n"
            f"✅ 勝場：{wins}｜❌ 敗場：{losses}\n"
            f"📈 勝率：{win_rate:.1f}%\n"
            f"💰 總報酬率：{total_return:.2f}%\n"
            f"💸 今日投入資金：${capital_used:,.0f}\n"
            f"💼 剩餘資金：${capital_left:,.0f}"
        )
    except Exception as e:
        return f"[ERROR] 產生績效摘要失敗：{e}"
 
    def init_sheets():
        print("[DEBUG] 開始執行 init_sheets()")
    try:
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME)

        pages = {
            "交易紀錄": ["日期", "股票代號", "進場時間", "出場時間", "持倉時間", "方向", "進場價格", "出場價格", "報酬率", "資金投入", "剩餘資金", "訊號類型", "是否TICK共振", "TICK 百分位", "TRIN 值", "TMO 值", "TMO 斜率", "RSI 值", "MACD 狀態", "VWAP 乖離", "成交量倍數", "OBV 方向", "策略版本", "信心分數"],
            "每日績效統計": ["日期", "勝場數", "負場數", "勝率", "總交易次數", "總投入資金", "總損益金額", "總報酬率", "最大獲利", "最大虧損", "平均持倉時間", "策略版本", "機器學習最佳策略"],
            "每日盤前情緒紀錄": ["日期", "TICK 百分位", "TICK 均值", "TICK 斜率", "TRIN 值", "VIX 值", "VIX 變化率", "當日預判方向"],
            "TICK共振紀錄": ["時間", "TICK 值", "TICK 百分位", "TICK 斜率", "TRIN 值", "共振股票代號"],
            "每日最佳參數": ["日期", "RSI 低點門檻", "TMO 金叉值門檻", "VWAP 乖離門檻", "ROC 濾網", "成交量倍數閾值", "VWAP 漲幅停利閾值", "選用策略名稱", "模型準確率"],
            "潛伏訊號紀錄": ["時間", "股票代號", "價格", "RSI", "TMO", "VWAP 乖離", "成交量倍數", "OBV", "當時盤勢情緒", "是否推播", "預警類型"]
        }
        # 尚未含自動建表程式（下一段可補）
    except Exception as e:
        print(f"[ERROR] 初始化 Sheets 失敗：{e}")

def check_exit_and_notify_dynamic(symbol, latest_price, entry_price, entry_time, direction, reason=None):
    holding_time = (datetime.now() - entry_time).total_seconds()
    profit_pct = (latest_price - entry_price) / entry_price * 100 if direction == "多" else (entry_price - latest_price) / entry_price * 100

    # === 判斷出場條件（浮動停利／停損） ===
    exit_flag = False
    exit_note = ""

    if profit_pct <= -2:
        exit_flag = True
        exit_note = "❌ 停損 -2%"
    elif profit_pct >= 8:
        exit_flag = True
        exit_note = "✅ 全數停利 +8%"
    elif profit_pct >= 5:
        exit_flag = True
        exit_note = "✅ 停利階段 +5%"
    elif profit_pct >= 3:
        exit_flag = True
        exit_note = "✅ 停利階段 +3%"

    if exit_flag:
        msg = (
            f"📤 **[出場通知 - {direction}單]** {symbol}\n"
            f"📈 出場價格：${latest_price:.2f}｜進場：${entry_price:.2f}\n"
            f"💰 報酬率：{profit_pct:.2f}%｜持倉時間：{holding_time:.0f} 秒\n"
            f"📌 出場原因：{exit_note if reason is None else reason}"
        )
        send_to_discord(msg)

        write_to_sheet([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol,
            latest_price,
            round(profit_pct, 2),
            holding_time,
            "空" if direction == "空" else "多",
            "出場",
            exit_note
        ])

        if symbol in positions:
            del positions[symbol]

# === 資料來源與系統狀態 ===
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."  # ✅ 請改為你自己的 Webhook URL

capital_left = 1_000_000     # 初始資金
report_sent = False          # 是否已推播今日績效報告
positions = {}               # 持倉記錄
entered_positions = {}       # 已進場紀錄
observed_candidates = {}     # 潛伏觀察名單（預警階段）

def calculate_tmo(df, short_window=2, long_window=8):
    close = df['close']
    short_ema = close.ewm(span=short_window).mean()
    long_ema = close.ewm(span=long_window).mean()
    tmo_line = short_ema - long_ema
    return tmo_line

# === 🔁 處理觀察名單中的潛伏爆量個股 ===
now = datetime.now()
def check_abnormal_reversal_entry(symbol, df):
    try:
        if len(df) < 25:
            return

        latest_price = df['close'].iloc[-1]
        avg_volume = df['volume'].iloc[-9:-1].mean()
        latest_volume = df['volume'].iloc[-1]
        if latest_volume < avg_volume * 5:
            return  # ❌ 未達爆量門檻

        # === 技術指標 ===
        rsi = RSIIndicator(close=df['close'], window=6).rsi()
        tmo = calculate_tmo(df)
        obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        latest_vwap = vwap.iloc[-1]
        vwap_deviation = (latest_price - latest_vwap) / latest_vwap

        # === 起跌轉折條件（不是死叉，也不是跌破） ===
        is_rsi_weakening = rsi.iloc[-2] > 70 and rsi.iloc[-1] < rsi.iloc[-2]
        is_tmo_rolling_over = tmo.iloc[-1] > 0 and tmo.iloc[-1] < tmo.iloc[-2]
        is_vwap_near = latest_price >= latest_vwap * 0.985  # 尚未明顯跌破
        is_obv_falling = obv.iloc[-1] < obv.iloc[-2] < obv.iloc[-3]
        is_red_candle = df['close'].iloc[-1] < df['open'].iloc[-1]

        if all([is_rsi_weakening, is_tmo_rolling_over, is_vwap_near, is_obv_falling, is_red_candle]):

            # === 推播通知 ===
            msg = (
                f"🐻 **[爆量觸頂反轉 - 空方起點]** 🐻 {symbol}\n"
                f"📉 價格：${latest_price:.2f}｜VWAP：{latest_vwap:.2f}｜乖離：{vwap_deviation:.2%}\n"
                f"📊 RSI：{rsi.iloc[-1]:.1f} ↘️｜TMO：{tmo.iloc[-1]:.2f} ↘️｜OBV：下降｜成交量：{latest_volume:,} 股\n"
                f"🕯️ 當前 K 棒：紅K｜時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            send_to_discord(msg)

            # === Google Sheets 寫入 ===
            write_to_sheet([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                symbol,
                latest_price,
                round(rsi.iloc[-1], 2),
                round(tmo.iloc[-1], 2),
                round(vwap_deviation, 4),
                round(latest_volume / avg_volume, 2),
                "下降",
                "偏空",
                "✅",
                "爆量空頭起點"
            ])

            # ✅ 建倉邏輯
            trigger_entry(symbol, direction="空", df=df, signal_type="🐻 爆量轉折（起點）")
            if symbol in observed_candidates:
                del observed_candidates[symbol]

    except Exception as e:
        print(f"[ERROR] 檢查爆量反轉錯誤：{symbol} → {e}")

for symbol, info in list(observed_candidates.items()):
    duration = (now - info['start_time']).total_seconds()

    # 超過 30 分鐘自動移除觀察
    if duration > 30 * 60:
        del observed_candidates[symbol]
        continue

    # 嘗試抓最新資料
    df = fetch_stock_data(symbol)
    if df is None or len(df) < 30:
        continue

    # 檢查是否符合爆量反轉進場條件
    check_abnormal_reversal_entry(symbol, df)

# === 🔁 檢查已建倉部位是否該出場 ===
for symbol in list(positions.keys()):
    entry_info = positions[symbol]
    entry_price = entry_info['entry_price']
    entry_time = entry_info['entry_time']
    direction = entry_info['direction']

    df = fetch_stock_data(symbol)
    if df is None or len(df) < 10:
        continue

    latest_price = df['close'].iloc[-1]
    check_exit_and_notify_dynamic(symbol, latest_price, entry_price, entry_time, direction)



# ✅ Discord 推播函數
def send_to_discord(message):
    try:
        payload = {"content": message}
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"[推播失敗] Discord 發送錯誤：{e}")

def get_tick_series(minutes=30):
    try:
        est = pytz.timezone("US/Eastern")
        now = datetime.now(est)
        start_time = now - timedelta(minutes=minutes)

        client = RESTClient(api_key=POLYGON_API_KEY)
        aggs = client.get_aggs(
            ticker="TICK",
            multiplier=1,
            timespan="minute",
            from_=start_time.isoformat(),  # ✅ 建議用 ISO 8601 格式
            to=end_time.isoformat(),
            limit=minutes,
            adjusted=True
        )

        # ✅ 若支援 .df，直接使用
        if hasattr(aggs, "df"):
            df = aggs.df.rename(columns={
                "o": "open", "h": "high", "l": "low",
                "c": "close", "v": "volume", "t": "timestamp"
            })
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
            df.set_index("timestamp", inplace=True)
            return df if not df.empty else None

        # ✅ 手動解析 bars（備援路徑）
        bars = aggs.results if hasattr(aggs, 'results') else aggs if isinstance(aggs, list) else []
        if not bars:
            print("[ERROR] TICK bars 結構無效")
            return None

        cleaned = []
        for bar in bars:
            b = vars(bar) if hasattr(bar, '__dict__') else bar
            if all(k in b for k in ["t", "o", "h", "l", "c", "v"]):
                cleaned.append({
                    "timestamp": pd.to_datetime(b["t"], unit='ms'),
                    "open": b["o"], "high": b["h"],
                    "low": b["l"], "close": b["c"], "volume": b["v"]
                })

        df = pd.DataFrame(cleaned)
        df.set_index("timestamp", inplace=True)
        return df if not df.empty else None

    except Exception as e:
        print(f"[ERROR] get_tick_series 錯誤：{e}")
        return None
    
def run_scanner():
    # ✅ 這是主要的掃描邏輯（你之前應該寫好了）
    for symbol in stock_list:
        if not is_valid_symbol(symbol):
            continue
        df = fetch_stock_data(symbol)
        if df is None or len(df) < 25:
            continue
        check_abnormal_reversal_entry(symbol, df)

    # ✅ 檢查持倉是否要出場
    for symbol in list(positions.keys()):
        entry_info = positions[symbol]
        latest_price = fetch_stock_data(symbol)['close'].iloc[-1]
        check_exit_and_notify_dynamic(symbol, latest_price, entry_info['entry_price'], entry_info['entry_time'], entry_info['direction'])
    
# === 出場風控參數 ===
TRAIL_TRIGGER = 0.03       # +3% 啟動追蹤停利
TRAIL_MARGIN = 0.015       # 回落 1.5% 就出場
DEFAULT_STOP_LOSS = 0.02   # 停損 2%
DEFAULT_TAKE_PROFIT = 0.05 # 停利 5%

# ✅ 出場判斷函數（支援浮動停利、風控共振、階段性出場）
def check_exit_and_notify_dynamic(symbol, latest_price, now, df):
    global capital_left

    if symbol not in positions:
        return

    entry_data = positions[symbol]
    entry_price = entry_data['entry_price']
    direction = entry_data['direction']
    capital_used = entry_data['capital_used']
    entry_time = entry_data['entry_time']
    holding_time = int((now - entry_time).total_seconds())

    return_rate = (
        (latest_price - entry_price) / entry_price
        if direction == "多" else
        (entry_price - latest_price) / entry_price
    )

    # === 出場條件 ===
    PHASE_1_PROFIT = 0.03   # +3%
    PHASE_2_PROFIT = 0.05   # +5%
    PHASE_3_PROFIT = 0.08   # +8%
    STOP_LOSS = -0.02       # -2% 停損

    exit_ratio = 0.0
    stage_note = ""
    signal_emoji = ""

    # ✅ 階段性出場判斷
    if direction == "多":
        if return_rate >= PHASE_3_PROFIT:
            exit_ratio = 1.0
            stage_note = "🚀 第3段鎖利（+8%）"
        elif return_rate >= PHASE_2_PROFIT:
            exit_ratio = 0.75
            stage_note = "✅ 第2段鎖利（+5%）"
        elif return_rate >= PHASE_1_PROFIT:
            exit_ratio = 0.5
            stage_note = "🔒 第1段鎖利（+3%）"
        elif return_rate <= STOP_LOSS:
            exit_ratio = 1.0
            stage_note = "🛑 固定停損（-2%）"

    elif direction == "空":
        if return_rate >= PHASE_3_PROFIT:
            exit_ratio = 1.0
            stage_note = "📉🚀 第3段鎖利（+8%）"
        elif return_rate >= PHASE_2_PROFIT:
            exit_ratio = 0.75
            stage_note = "📉✅ 第2段鎖利（+5%）"
        elif return_rate >= PHASE_1_PROFIT:
            exit_ratio = 0.5
            stage_note = "📉🔒 第1段鎖利（+3%）"
        elif return_rate <= STOP_LOSS:
            exit_ratio = 1.0
            stage_note = "📉🛑 固定停損（-2%）"

    # ✅ 市場風控出場（TRIN / TICK 共振）
    tick_value = get_latest_tick()
    trin_value = get_trin_value()
    if direction == "多" and trin_value >= 1.5 and tick_value < -1000:
        exit_ratio = 1.0
        stage_note = "⚠️ 市場風控出場（空頭）"
    elif direction == "空" and trin_value <= 0.8 and tick_value > 1000:
        exit_ratio = 1.0
        stage_note = "⚠️ 市場風控出場（多頭）"

    # ✅ 執行出場
    if exit_ratio > 0:
        capital_left += capital_used * exit_ratio
        entry_data['holding_ratio'] -= exit_ratio
        entry_data['holding_ratio'] = max(0, entry_data['holding_ratio'])

        signal_emoji = "📈" if direction == "多" else "📉"
        profit_percent = return_rate * 100

        # ✅ 推播通知
        push_to_discord(
            f"{signal_emoji} {stage_note} | {symbol}\n"
            f"📉 出場價格：${latest_price:.2f}｜進場：${entry_price:.2f}\n"
            f"💰 報酬率：{profit_percent:.2f}%｜持倉時間：{holding_time}秒"
        )

        # ✅ 寫入 Google Sheets
        write_to_sheet(
            symbol=symbol,
            direction=direction,
            pnl=return_rate,
            entry_price=entry_price,
            exit_price=latest_price,
            volume_ratio=entry_data.get("volume_ratio", 1.0),
            obv=entry_data.get("obv", 0),
            rsi=entry_data.get("rsi", 50),
            tmo=entry_data.get("tmo", 0),
            candle_type="陽線" if latest_price > entry_price else "陰線",
            remark=stage_note,
            holding_time=holding_time,
            vwap=entry_data.get("vwap", 0),
            ema_cross=entry_data.get("ema_cross", ""),
            kd_status=entry_data.get("kd_status", ""),
            tick_percentile=entry_data.get("tick_percentile", 50),
            tick_slope=entry_data.get("tick_slope", 0),
            trin_value=trin_value,
            strategy_version="v1.0",
            confidence_score=entry_data.get("confidence_score", 0.8),
            signal_type="出場"
        )

        print(f"[出場] {symbol} | 報酬率：{return_rate:.2%} | 出場比例：{exit_ratio:.0%}")

        if entry_data['holding_ratio'] <= 0.01:
            del positions[symbol]

    else:
        entry_data['max_gain'] = max(entry_data.get("max_gain", 0), return_rate)

def get_tick_percentile(tick_series):
    """回傳目前 TICK 值在歷史序列中的百分位位置"""
    if tick_series is None or tick_series.empty:
        print("[WARNING] tick_series 是空的，無法計算百分位")
        return None

    current_tick = tick_series.iloc[-1]
    sorted_series = tick_series.sort_values()
    rank = sorted_series[sorted_series <= current_tick].count()
    percentile = rank / len(sorted_series) * 100
    return round(percentile, 2)

def write_to_sheet(symbol, direction, pnl, entry_price, exit_price,
                   volume_ratio, obv, rsi, tmo, candle_type, remark,
                   holding_time, vwap, ema_cross, kd_status,
                   tick_percentile, tick_slope,
                   trin_value, strategy_version, confidence_score, signal_type):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Trading Log").worksheet("交易紀錄")
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        symbol,
        direction,
        signal_type,
        f"{entry_price:.2f}",
        f"{exit_price:.2f}",
        f"{pnl * 100:.2f}%",
        holding_time,
        f"{rsi:.1f}" if rsi is not None else "",
        f"{tmo:.1f}" if tmo is not None else "",
        f"{vwap:.2f}" if vwap is not None else "",
        f"{volume_ratio:.2f}" if volume_ratio is not None else "",
        f"{obv:.2f}" if obv is not None else "",
        ema_cross,
        kd_status,
        candle_type,
        f"{tick_percentile:.1f}" if tick_percentile is not None else "",
        f"{tick_slope:.1f}" if tick_slope is not None else "",
        f"{trin_value:.2f}" if trin_value is not None else "",
        strategy_version,
        confidence_score,
        remark
    ]

    append_row_safe(sheet, row)

def is_valid_symbol(symbol: str) -> bool:
    symbol = symbol.upper()

    if symbol.endswith("F") or symbol.endswith("Q"):
        print(f"[FILTER] ❌ {symbol} 為 OTC 股票，排除")
        return False

    if "ETF" in symbol:
        print(f"[FILTER] ❌ {symbol} 為 ETF，排除")
        return False

    return True  # ✅ 通過過濾

def filter_stock_conditions(symbol, price, market_cap, avg_volume_10d, atr_3d):
    if price < 1 or price > 5:
        print(f"[FILTER] ❌ {symbol} 價格不符：{price}")
        return False

    if market_cap is not None and market_cap < 100_000_000:
        print(f"[FILTER] ❌ {symbol} 市值過低：{market_cap}")
        return False

    if avg_volume_10d is not None and avg_volume_10d < 500_000:
        print(f"[FILTER] ❌ {symbol} 平均量過低：{avg_volume_10d}")
        return False

    if atr_3d is not None and (atr_3d / price) < 0.02:
        print(f"[FILTER] ❌ {symbol} 波動不足：ATR={atr_3d:.2f}, Price={price:.2f}")
        return False

    return True

def add_to_observed_candidates(symbol, price, reason):
    now = datetime.now()
    observed_candidates[symbol] = {
        "start_time": now,
        "last_push_time": now,
        "entry_price": price,
        "reason": reason,
        "notified_expiring": False
    }
    print(f"[OBSERVE] 📌 已加入觀察名單：{symbol}（原因：{reason}）")

def check_abnormal_volume_with_direction(symbol, df):
    try:
        # 1. 取得成交量與 VWAP / OBV 狀態
        avg_volume_20 = df['volume'].iloc[-21:-1].mean()
        latest_volume = df['volume'].iloc[-1]
        latest_price = df['close'].iloc[-1]

        if latest_volume < avg_volume_20 * 5:
            return  # ❌ 沒有異常爆量

        # 2. VWAP 斜率與 OBV 方向判斷
        obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()
        obv_direction = "上升" if obv.iloc[-1] > obv.iloc[-3] else "下滑"

        vwap_series = (df['volume'] * df['close']).cumsum() / df['volume'].cumsum()
        vwap_slope_up = vwap_series.iloc[-1] > vwap_series.iloc[-3]
        vwap_deviation = abs(latest_price - vwap_series.iloc[-1]) / vwap_series.iloc[-1]

        direction = "偏多" if obv_direction == "上升" and vwap_slope_up else "偏空"

        # 3. 寫入觀察名單與 Sheets
        add_to_observed_candidates(symbol, latest_price, "異常爆量")

        write_to_sheet_by_type({
            "時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "股票代號": symbol,
            "價格": latest_price,
            "RSI": None,
            "TMO": None,
            "VWAP 乖離": round(vwap_deviation, 4),
            "成交量倍數": round(latest_volume / avg_volume_20, 2),
            "OBV": obv_direction,
            "當時盤勢情緒": direction,
            "是否推播": "✅",
            "預警類型": "異常爆量"
        }, type="潛伏訊號紀錄")

        # 4. 推播通知
        signal_note = (
            f"⚠️ **[💣異常爆量警告💣]** {symbol}\n"
            f"📈 價格：${latest_price:.2f}｜成交量：{latest_volume:,} 股\n"
            f"🧪 平均量：{avg_volume_20:,.0f} 股｜倍數：{latest_volume / avg_volume_20:.1f}x\n"
            f"📊 OBV：{obv_direction}｜VWAP：{'上升↗️' if vwap_slope_up else '下滑↘️'}｜方向：{direction}\n"
            f"📌 已加入觀察名單，隨時注意追蹤"
        )
        push_to_discord(symbol, signal_note)

    except Exception as e:
        print(f"[ERROR] 檢查爆量失敗：{e}")

def detect_latent_signal(df, rsi, tmo, obv, latest_price, latest_vwap):
    print(f"[DEBUG] 呼叫 detect_latent_signal 用參數：price={latest_price:.2f}, vwap={latest_vwap:.2f}")
    print(f"[DEBUG] 傳入參數：rsi={rsi:.2f}, tmo={tmo:.2f}, obv={obv.iloc[-1]:.2f}")

    auto_entry = False
    direction = None
    signal_note = None

    price = latest_price
    symbol = df['symbol'].iloc[-1]
    ema5 = df['close'].ewm(span=5, adjust=False).mean().iloc[-1]

def detect_latent_signal(df, rsi, tmo, obv, latest_price, latest_vwap):
    candle_type = "陽線" if df['close'].iloc[-1] > df['open'].iloc[-1] else "陰線"
    obv_direction = "上升" if obv.iloc[-1] > obv.iloc[-3] else "下滑"
    now = datetime.now()
    symbol = df['symbol'].iloc[-1]
    price = latest_price
    ema5 = df['close'].ewm(span=5).mean().iloc[-1]

    auto_entry = False
    direction = None
    signal_note = None

    # === 潛伏多頭轉折 ===
    if price < ema5 and rsi.iloc[-1] > rsi.iloc[-2] and tmo.iloc[-1] > tmo.iloc[-2]:
        add_to_observed_candidates(symbol, price, "RSI 回升 + TMO 金叉")
        signal_note = (
            f"⚠️ **[{symbol}] 潛伏 - 多頭轉折**\n"
            f"📈 價格雖跌，但動能轉強\n"
            f"📊 RSI：{rsi.iloc[-1]:.1f} ↗️｜TMO：{tmo.iloc[-1]:.2f} ↗️｜VWAP：下方｜🕯️ {candle_type}\n"
            f"📌 加入觀察名單，等待正式啟動"
        )
        push_to_discord(symbol, signal_note)
        direction = "long"

        # ✅ 寫入 Sheets
        write_to_sheet_by_type({
            "時間": now.strftime("%Y-%m-%d %H:%M:%S"),
            "股票代號": symbol,
            "價格": price,
            "RSI": rsi.iloc[-1],
            "TMO": tmo.iloc[-1],
            "VWAP 乖離": (price - latest_vwap) / latest_vwap,
            "成交量倍數": df['volume'].iloc[-1] / df['volume'].iloc[-20:-1].mean(),
            "OBV": obv_direction,
            "當時盤勢情緒": "偏多",
            "是否推播": "✅",
            "預警類型": "潛伏多頭"
        }, type="潛伏訊號紀錄")

    # === 潛伏空頭轉折 ===
    elif price > ema5 and rsi.iloc[-1] < rsi.iloc[-2] and tmo.iloc[-1] < tmo.iloc[-2]:
        add_to_observed_candidates(symbol, price, "RSI 過熱 + TMO 死叉")
        signal_note = (
            f"⚠️ **[{symbol}] 潛伏 - 空頭轉折**\n"
            f"📉 價格雖漲，但技術轉弱\n"
            f"📊 RSI：{rsi.iloc[-1]:.1f} ↘️｜TMO：{tmo.iloc[-1]:.2f} ↘️｜VWAP：上方｜🕯️ {candle_type}\n"
            f"📌 加入觀察名單，等待正式啟動"
        )
        push_to_discord(symbol, signal_note)
        direction = "short"

        # ✅ 寫入 Sheets
        write_to_sheet_by_type({
            "時間": now.strftime("%Y-%m-%d %H:%M:%S"),
            "股票代號": symbol,
            "價格": price,
            "RSI": rsi.iloc[-1],
            "TMO": tmo.iloc[-1],
            "VWAP 乖離": (price - latest_vwap) / latest_vwap,
            "成交量倍數": df['volume'].iloc[-1] / df['volume'].iloc[-20:-1].mean(),
            "OBV": obv_direction,
            "當時盤勢情緒": "偏空",
            "是否推播": "✅",
            "預警類型": "潛伏空頭"
        }, type="潛伏訊號紀錄")

    # ✅ 正式建倉（多頭）
    if (
        df['close'].iloc[-1] < df['close'].iloc[-3] and
        rsi.iloc[-1] > rsi.iloc[-2] and rsi.iloc[-2] < 30 and
        tmo.iloc[-1] > tmo.iloc[-2] and tmo.iloc[-2] < 0 and
        obv.iloc[-1] > obv.iloc[-2] > obv.iloc[-3] and
        price > df['close'].iloc[-2] and
        abs(price - latest_vwap) / latest_vwap < 0.01 and
        df['close'].iloc[-1] > df['open'].iloc[-1]
    ):
        if symbol in observed_candidates:
            first = observed_candidates[symbol]
            price_diff = abs(price - first["price"]) / first["price"]
            time_diff = (now - first["time"]).total_seconds() / 60

            if price_diff <= 0.02 and time_diff <= 30:
                del observed_candidates[symbol]
                direction = "long"
                vwap_status = "上穿" if price > latest_vwap else "下方"

                signal_note = (
                    f"🐮 **潛伏多頭（正式建倉）** 🐮 {symbol}\n"
                    f"📈 價格：${price:.2f}｜K棒：陽線｜動能轉強\n"
                    f"📊 RSI：{rsi.iloc[-1]:.1f} ⬆️｜TMO：{tmo.iloc[-1]:.2f} ⬆️｜OBV：連續上升\n"
                    f"📏 VWAP 偏離：{abs(price - latest_vwap) / latest_vwap:.2%}（貼近主力成本）\n"
                    f"📌 技術面低檔翻揚，進場時機成立\n"
                    f"🕒 時間：{now.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                # ✅ 安全條件
                if not is_safe_entry(rsi.iloc[-1], price, latest_vwap, direction="long", symbol=symbol):
                    return


                # ✅ 正式建倉與紀錄
                if symbol not in entered_positions:
                    entered_positions[symbol] = {
                        "price": price, "direction": direction, "entry_time": now
                    }
                    positions[symbol] = {
                        "entry_price": price,
                        "capital_used": 10000,
                        "entry_time": now,
                        "direction": direction,
                        "max_gain": 0,
                        "holding_ratio": 1.0,
                        "sell_stage": 0
                    }

                    # ✅ 建倉成功推播
                    send_to_discord(signal_note)

    # ✅ 正式建倉（空頭）
    if (
        df['close'].iloc[-1] > df['close'].iloc[-3] and
        rsi.iloc[-2] > 70 and rsi.iloc[-1] < rsi.iloc[-2] and
        tmo.iloc[-2] > 0 and tmo.iloc[-1] < tmo.iloc[-2] and
        obv.iloc[-1] < obv.iloc[-2] < obv.iloc[-3] and
        df['close'].iloc[-1] < df['close'].iloc[-2] and
        abs(df['close'].iloc[-1] - latest_vwap) / latest_vwap < 0.01 and
        df['close'].iloc[-1] < df['open'].iloc[-1]
    ):
        if symbol in observed_candidates:
            first = observed_candidates[symbol]
            price_diff = abs(price - first["price"]) / first["price"]
            time_diff = (now - first["time"]).total_seconds() / 60

            if price_diff <= 0.02 and time_diff <= 30:
                del observed_candidates[symbol]
                direction = "short"

                signal_note = (
                    f"🐻 **潛伏空頭（正式建倉）** 🐻{symbol}\n"
                    f"📉 價格：${latest_price:.2f}｜K棒：{candle_type}\n"
                    f"📊 RSI：{rsi:.1f}｜TMO：{tmo:.2f}｜OBV：{obv_direction}\n"
                    f"📏 VWAP 偏離：{abs(df['close'].iloc[-1] - latest_vwap) / latest_vwap:.2%}\n"
                    f"📌 技術面確認空頭啟動，建倉時機已到\n"
                    f"🕒 時間：{now.strftime('%Y-%m-%d %H:%M:%S')}"
                )

                if not is_safe_entry(rsi.iloc[-1], latest_price, latest_vwap, direction="short", symbol=symbol):
                    return

                if symbol not in entered_positions:
                    entered_positions[symbol] = {
                        "price": price, "direction": direction, "entry_time": now
                    }
                    positions[symbol] = {
                        "entry_price": price,
                        "capital_used": 10000,
                        "entry_time": now,
                        "direction": direction,
                        "max_gain": 0,
                        "holding_ratio": 1.0,
                        "sell_stage": 0
                    }

                    send_to_discord(signal_note)

est = timezone("US/Eastern")
now_est = datetime.now(est)

market_open = est.localize(datetime.combine(now_est.date(), time(9, 30)))
market_close = est.localize(datetime.combine(now_est.date(), time(16, 0)))

if now_est < market_open or now_est > market_close:
    print("[INFO] 非美股盤中時間，跳過掃描")
    exit()

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

def write_to_sheet(
    symbol, direction, signal_type, tick_percentile, trin, latest_rsi,
    latest_tmo, tmo_slope, vwap_diff, volume_ratio,
    kd_status, candle_type,
    entry_price, exit_price, holding_time_sec, return_rate,
    capital_used, capital_left, session, strategy_version, confidence_score, remark
):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Trading Log").worksheet("交易紀錄")

        row_data = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol, direction, signal_type,
            f"{tick_percentile:.2f}%", entry_price, exit_price,
            f"{return_rate:.2%}", holding_time_sec,
            capital_used, capital_left,
            f"RSI: {latest_rsi:.1f}", f"TMO: {latest_tmo:.2f}", f"Slope: {tmo_slope:.2f}",
            f"VWAP乖離: {vwap_diff:.2%}", f"量能倍數: {volume_ratio:.2f}",
            kd_status, candle_type,
            session, strategy_version, f"{confidence_score:.2f}", remark
        ]

        sheet.append_row(row_data)

    except Exception as e:
        print(f"[ERROR] 寫入 Sheets 失敗：{e}")

def load_stock_list(filepath):
    try:
        df = pd.read_csv(filepath)
        return df['symbol'].tolist()
    except Exception as e:
        print(f"[ERROR] 無法讀取股票清單：{e}")
        return []

stock_list = load_stock_list("filtered_us_stocks_common_only.csv")

def fetch_stock_data(symbol):
    try:
        from polygon import RESTClient
        import pytz
        est = pytz.timezone("US/Eastern")
        now_est = datetime.now(est)
        end_time = now_est - timedelta(minutes=15)
        start_time = end_time - timedelta(hours=2)

        market_open = est.localize(datetime.combine(now_est.date(), time(9, 30)))
        market_close = est.localize(datetime.combine(now_est.date(), time(16, 0)))

        if now_est < market_open or now_est > market_close:
            print(f"[SKIP] {symbol} 不在交易時段（{now_est.strftime('%H:%M:%S')}），跳過")
            return None

        client = RESTClient(api_key=POLYGON_API_KEY)

        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=5,
            timespan="minute",
            from_=start_time.isoformat(),
            to=end_time.isoformat(),
            limit=100,
            adjusted=True
        )

        # ✅ 嘗試使用 .df（新版 SDK）
        if hasattr(aggs, "df"):
            df = aggs.df.rename(columns={
                "o": "open", "h": "high", "l": "low",
                "c": "close", "v": "volume", "t": "timestamp"
            })
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            return df if not df.empty else None

        # ✅ 若 .df 不存在，用備援方式解析
        bars = aggs.results if hasattr(aggs, 'results') else []
        if not bars:
            print(f"[警告] {symbol} 無法取得有效 K 線資料")
            return None

        cleaned = []
        for bar in bars:
            cleaned.append({
                "timestamp": pd.to_datetime(bar["t"], unit='ms'),
                "open": bar["o"], "high": bar["h"],
                "low": bar["l"], "close": bar["c"], "volume": bar["v"]
            })

        df = pd.DataFrame(cleaned)
        df.set_index("timestamp", inplace=True)
        return df if not df.empty else None

    except Exception as e:
        print(f"[錯誤] {symbol} 抓資料時發生錯誤：{e}")
        return None
    
def analyze_stock_data(symbol, bars, tick_value, trin_value):
    try:
        df = pd.DataFrame(bars)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        if len(df) < 25 or 'close' not in df.columns or df['close'].isnull().all():
            print(f"[WARNING] {symbol} 資料不足或收盤價異常")
            return None

        latest_price = df['close'].iloc[-1]
        print(f"[DATA] {symbol} 最新收盤價：{latest_price:.2f}")

        # === 價格與量能 ===
        latest_open = df['open'].iloc[-1]
        latest_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(8).mean().iloc[-1]
        volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0
        candle_type = detect_candle_pattern(df)

        # === RSI ===
        rsi = RSIIndicator(close=df['close'], window=6).rsi()
        latest_rsi = rsi.iloc[-1]

        # === VWAP ===
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        latest_vwap = vwap.iloc[-1] if not pd.isna(vwap.iloc[-1]) else 0
        vwap_deviation = abs(latest_price - latest_vwap) / latest_vwap if latest_vwap != 0 else 0

        # === TMO ===
        tmo = calculate_tmo(df)
        latest_tmo = tmo.iloc[-1]
        tmo_slope = tmo.diff().iloc[-1]

        # === OBV ===
        obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()
        obv_direction = "上升" if obv.iloc[-1] > obv.iloc[-2] else "下降"

        # === EMA ===
        ema5 = EMAIndicator(close=df['close'], window=2).ema_indicator()
        ema20 = EMAIndicator(close=df['close'], window=8).ema_indicator()
        ema_cross = "✅" if ema5.iloc[-1] > ema20.iloc[-1] else "❌"

        # === KD ===
        kd = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=5)
        k_value = kd.stoch().iloc[-1]
        d_value = kd.stoch_signal().iloc[-1]
        kd_status = "金叉" if k_value > d_value else "死叉" if k_value < d_value else "中性"

        # === 顯示資訊 ===
        print(f"[INFO] {symbol} 最新收盤：{latest_price:.2f}")
        print(f"📊 RSI：{latest_rsi:.1f}｜TMO：{latest_tmo:.2f}（斜率：{tmo_slope:.2f}）｜VWAP：{latest_vwap:.2f}")
        print(f"📈 倍量：{volume_ratio:.2f}｜EMA交叉：{ema_cross}｜OBV：{obv_direction}｜KD：{kd_status}｜K棒：{candle_type}")

        # === 基本方向判斷 ===
        direction = None
        if latest_rsi < 30 and latest_tmo > 0:
            direction = "多"
        elif latest_rsi > 70 and latest_tmo < 0:
            direction = "空"

        # === TRIN / TICK 風控 ===
        if direction == "多" and trin_value >= 1.5 and tick_value < -1000:
            msg = f"⛔ **[風控 - 禁止多單進場]** ⛔ {symbol}\n📊 TRIN：{trin_value:.2f}｜TICK：{tick_value}"
            push_to_discord(msg)
            return None

        if direction == "空" and trin_value <= 0.8 and tick_value > 1000:
            msg = f"⛔ **[風控 - 禁止空單進場]** ⛔ {symbol}\n📊 TRIN：{trin_value:.2f}｜TICK：{tick_value}"
            push_to_discord(msg)
            return None

        # === 多空訊號判斷與建倉 ===
        now = datetime.now()
        tick_percentile = 50  # ← 預設值，可替換為外部傳入
        tick_slope = 0
        confidence_score = 0.75

        if (
            latest_rsi < 35 and
            tmo_slope > 0 and
            obv.iloc[-1] > obv.iloc[-3] and
            candle_type in ['hammer', 'bullish_engulfing']
        ):
            signal_note = (
                f"🐮**[觀察 - 多頭進場]** 🐮{symbol}\n"
                f"📈 價格：${latest_price:.2f}｜距離 VWAP 僅 {vwap_deviation:.2%}\n"
                f"📊 RSI：{latest_rsi:.1f} ↗️｜TMO：{latest_tmo:.2f} ↗️｜OBV：上升\n"
                f"💥 VWAP 尚未站上但貼近｜📈 Volume：{volume_ratio:.2f}x｜🕯️ K棒：{candle_type}\n"
                f"🟢 多項轉強訊號共振，多頭建倉時機形成"
            )

            if not is_safe_entry(latest_rsi, latest_price, latest_vwap, direction="long", symbol=symbol):
                return


            push_to_discord(symbol, signal_note)

            capital_used = capital_left * 0.05
            positions[symbol] = {
                'entry_price': latest_price,
                'capital_used': capital_used,
                'entry_time': now,
                'direction': '多',
                'holding_ratio': 1.0,
                'sell_stage': 0,
                'max_gain': 0,
                'volume_ratio': volume_ratio,
                'obv': obv.iloc[-1],
                'rsi': latest_rsi,
                'tmo': latest_tmo,
                'vwap': latest_vwap,
                'ema_cross': ema_cross,
                'kd_status': kd_status,
                'tick_percentile': tick_percentile,
                'tick_slope': tick_slope,
                'trin_value': trin_value,
                'confidence_score': confidence_score,
            }
            capital_left -= capital_used
            print(f"[建倉紀錄] {symbol} 建倉於 {latest_price:.2f}｜投入資金 ${capital_used:.2f}")

        elif (
            latest_rsi > 60 and
            rsi.iloc[-2] > rsi.iloc[-1] and
            tmo.iloc[-2] > 0 and latest_tmo < tmo.iloc[-2] and
            vwap_deviation < 0.03 and latest_price > latest_vwap and tmo_slope < 0 and
            volume_ratio > 1.5 and
            obv.iloc[-1] < obv.iloc[-3] and
            candle_type in ['shooting_star', 'bearish_engulfing']
        ):
            signal_note = (
                f"🐻**[觀察 - 空頭進場]** 🐻{symbol}\n"
                f"📉 價格：${latest_price:.2f}｜距離 VWAP 僅 {vwap_deviation:.2%}\n"
                f"📊 RSI：{latest_rsi:.1f} ↘️｜TMO：{latest_tmo:.2f} ↘️｜OBV：下滑\n"
                f"💥 VWAP 尚未跌破但貼近｜📈 Volume：{volume_ratio:.2f}x｜🕯️ K棒：{candle_type}\n"
                f"🛑 多項轉弱訊號共振，空頭建倉時機形成"
            )

            if not is_safe_entry(latest_rsi, latest_price, latest_vwap, direction="short", symbol=symbol):
                return

            push_to_discord(symbol, signal_note)
            # 如果有空單建倉邏輯，可以放在這裡

        return {
            "price": latest_price,
            "rsi": latest_rsi,
            "tmo": latest_tmo,
            "tmo_slope": tmo_slope,
            "vwap": latest_vwap,
            "volume_ratio": volume_ratio,
            "obv_direction": obv_direction,
            "kd_status": kd_status,
            "candle_type": candle_type,
            "ema_cross": ema_cross
        }

    except Exception as e:
        print(f"[ERROR] analyze_stock_data 發生錯誤：{e}")
        return None

    push_to_discord(symbol, signal_note)

    capital_used = capital_left * 0.05
    positions[symbol] = {
        'entry_price': latest_price,
        'capital_used': capital_used,
        'entry_time': now,
        'direction': '空',
        'holding_ratio': 1.0,
        'sell_stage': 0,
        'max_gain': 0,
        'volume_ratio': volume_ratio,
        'obv': obv.iloc[-1],
        'rsi': latest_rsi,
        'tmo': latest_tmo,
        'vwap': latest_vwap,
        'ema_cross': ema_cross,
        'kd_status': kd_status,
        'tick_percentile': tick_percentile,
        'tick_slope': tick_slope,
        'trin_value': trin_value,
        'confidence_score': confidence_score,
    }
    capital_left -= capital_used
    print(f"[建倉紀錄] {symbol} 建倉於 {latest_price:.2f}｜投入資金 ${capital_used:.2f}")

if __name__ == "__main__":
    init_sheets()  # ⬅️ 自動建立 Google Sheets 所需欄位
    run_scanner()  # ✅ 執行主程式

    while True:
        now_est = datetime.now(timezone("US/Eastern"))

        # ✅ 每日下午 15:30 自動推播績效報告
        if now_est.strftime("%H:%M") == "15:30" and not report_sent:
            summary = generate_daily_summary()
            send_to_discord(summary)
            report_sent = True

        # ✅ 抓取 TICK 指標
        tick_series = get_tick_series()
        tick_percentile = get_tick_percentile(tick_series)
        tick_slope = get_tick_slope(tick_series)
        current_tick = tick_series.iloc[-1] if len(tick_series) > 0 else None
        trin_value = get_trin_value()

        # ✅ 推播市場風向預測
        if tick_percentile is not None and tick_slope is not None and trin_value is not None:
            if tick_percentile > 50 and tick_slope > 0 and trin_value < 1.0:
                send_to_discord(f"📊 **[大盤潛伏多頭]**\nTICK 百分位：{tick_percentile:.1f}｜斜率：+{tick_slope:.0f}｜TRIN：{trin_value:.2f}\n大盤動能轉強，觀察多方機會")
            if tick_percentile < 5 and tick_slope < 0 and trin_value > 1.0:
                send_to_discord(f"📉 **[大盤潛伏空頭]**\nTICK 百分位：{tick_percentile:.1f}｜斜率：{tick_slope:.0f}｜TRIN：{trin_value:.2f}\n大盤動能轉弱，觀察空方壓力")
            if current_tick > 1000:
                send_to_discord(f"🚀 **[TICK 極端多頭]**\nTICK 當前值：{current_tick}｜斜率：{tick_slope}｜百分位：{tick_percentile}")
            if current_tick < -1000:
                send_to_discord(f"⚠️ **[TICK 極端空頭]**\nTICK 當前值：{current_tick}｜斜率：{tick_slope}｜百分位：{tick_percentile}")

            write_tick_to_sheet(current_tick, tick_percentile, tick_slope, trin_value)

        # ✅ 執行主掃描器
        try:
            success_count, fail_count = run_scanner(tick_series)
            efficiency = round(success_count / (success_count + fail_count + 1e-6) * 100, 2)
            print(f"\n[統計] ✅ 成功 {success_count} 檔，❌ 失敗 {fail_count} 檔，有效率：{efficiency}%")
        except Exception as e:
            print(f"[ERROR] run_scanner 發生錯誤：{e}")

        print("[INFO] 等待 60 秒再執行下一輪...")
        time.sleep(60)

