# === 技術指標 ===
from ta.volume import OnBalanceVolumeIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, ADXIndicator
from datetime import datetime, timedelta
from pytz import timezone
from ta.volume import OnBalanceVolumeIndicator
import numpy as np
# === 自訂函數 ===
from utils import detect_candle_pattern, calculate_tmo
import pandas as pd
import random
import requests
import requests
# === 資料來源 ===
from polygon import RESTClient 
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1372956363235393536/2bELr_6LwGlk2K7G4B3d3J0MBD5iv04IwC33pQaWxAHcRbgn6sBVtkvI_65FfmC4Um5f"  # 記得換成自己的

entered_positions = {}  # 全域變數記錄進場股票

def send_to_discord(message):  # ✅ 安全不會衝突
    try:
        payload = {"content": message}
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"[推播失敗] Discord 發送錯誤：{e}")
# === 技術工具函數 ===
def get_tick_series(minutes=30):
    """
    回傳最近 N 分鐘的 TICK.US 收盤值（用於斜率與百分位計算）
    """
    try:
        est = timezone("US/Eastern")
        now = datetime.now(est)
        start_time = now - timedelta(minutes=minutes)

        client = RESTClient(api_key=API_KEY)

        aggs = client.get_aggs(
            ticker="TICK",
            multiplier=1,
            timespan="minute",
            from_=start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            to=now.strftime("%Y-%m-%dT%H:%M:%S"),
            limit=minutes,
            adjusted=True
        )

        # 解析 bars
        if hasattr(aggs, 'results'):
            bars = aggs.results
        elif isinstance(aggs, list):
            bars = aggs
        else:
            print("[ERROR] 無效 TICK 結構")
            return pd.Series()

        tick_values = [bar['c'] for bar in bars if 'c' in bar]
        return pd.Series(tick_values)

    except Exception as e:
        print(f"[ERROR] 抓取 TICK 資料失敗：{e}")
        return pd.Series()

# 動態風控參數
TRAIL_TRIGGER = 0.03  # +3% 啟動追蹤停利
TRAIL_MARGIN = 0.015  # 回落超過 1.5% 即出場
DEFAULT_STOP_LOSS = 0.02
DEFAULT_TAKE_PROFIT = 0.05

# ✅ 出場判斷邏輯（可放在最前面）
def check_exit_and_notify_dynamic(symbol, latest_price, now):
    if symbol not in positions:
        return

    entry_data = positions[symbol]
    entry_price = entry_data['entry_price']
    direction = entry_data['direction']
    capital_used = entry_data['capital_used']
    entry_time = entry_data['entry_time']
    
    holding_time = int((now - entry_time).total_seconds())
    return_rate = (latest_price - entry_price) / entry_price if direction == "多" else (entry_price - latest_price) / entry_price

    # ✅ 停利停損條件判斷（含浮動停利）
    should_exit = False
    reason = ""

    drawdown = entry_data.get('max_gain', 0) - return_rate
    exit_ratio = 0.0

    # ✅ 報酬 >= 8%，直接全數出場
    if return_rate >= 0.08:
        should_exit = True
        exit_ratio = entry_data.get('holding_ratio', 1.0)
        entry_data['sell_stage'] = 100  # 標記為 +8% 全出

    # ✅ 報酬 >= 5%，出場一半
    elif return_rate >= 0.05 and entry_data['sell_stage'] < 98:
        should_exit = True
        exit_ratio = 0.5
        entry_data['sell_stage'] = 98  # 標記為 +5% 半出

    # ✅ 三段鎖利（需回落條件）
    elif entry_data['sell_stage'] == 0 and return_rate >= 0.03 and drawdown >= 0.01:
        should_exit = True
        exit_ratio = 0.5
        entry_data['sell_stage'] = 1

    elif entry_data['sell_stage'] == 1 and return_rate >= 0.06 and drawdown >= 0.015:
        should_exit = True
        exit_ratio = 0.3
        entry_data['sell_stage'] = 2

    elif entry_data['sell_stage'] == 2 and return_rate >= 0.10 and drawdown >= 0.02:
        should_exit = True
        exit_ratio = entry_data.get('holding_ratio', 1.0)
        entry_data['sell_stage'] = 3

    # ✅ 停損 -2%
    elif return_rate <= -0.02:
        should_exit = True
        exit_ratio = entry_data.get('holding_ratio', 1.0)
        entry_data['sell_stage'] = 4
    
    # === 執行出場 ===
    if should_exit:
        
        exit_price = latest_price
        capital_left += capital_used * exit_ratio
        entry_data['holding_ratio'] -= exit_ratio

        if entry_data['sell_stage'] == 0:
            signal_emoji = "🔒"
            stage_note = "第1段停利"
        elif entry_data['sell_stage'] == 1:
            signal_emoji = "🔒"
            stage_note = "第2段停利"
        elif entry_data['sell_stage'] == 2 or entry_data['sell_stage'] == 3:
            signal_emoji = "✅"
            stage_note = "最終鎖利出場"
        elif entry_data['sell_stage'] == 4:
            signal_emoji = "🛑"
            stage_note = "停損出場"
        elif entry_data['sell_stage'] == 98:
            signal_emoji = "📈"
            stage_note = "達 +5% 出場 50%"
        elif entry_data['sell_stage'] == 100:
            signal_emoji = "🚀"
            stage_note = "達 +8% 全數出場"
        else:
            signal_emoji = "📤"
            stage_note = "一般出場"

        send_to_discord(
            f"{signal_emoji} **[{stage_note}]** {symbol} @ ${exit_price:.2f}\n"
            f"📈 報酬：{return_rate*100:.2f}%｜回落：{drawdown*100:.2f}%\n"
            f"💰 出場：{exit_ratio*100:.0f}%｜剩餘：{entry_data['holding_ratio']*100:.0f}%"
        )

        # ✅ 寫入 Sheets（補上你的 write_to_sheet）
        # write_to_sheet(...)

        if entry_data['holding_ratio'] <= 0.01:
            del positions[symbol]

    # === 還沒出場，更新 max_gain
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

# ✅ 就貼在這區塊的下方
def write_tick_to_sheet(tick_value, tick_percentile, tick_slope, trin_value):
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        from datetime import datetime
        from pytz import timezone

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Trading Log").worksheet("TICK紀錄")

        now_est = datetime.now(timezone("US/Eastern")).strftime("%Y-%m-%d %H:%M:%S")
        row = [now_est, tick_value, tick_percentile, tick_slope, trin_value]
        sheet.append_row(row)
        print(f"[INFO] ✅ TICK 已寫入 Sheets：{now_est}")
    except Exception as e:
        print(f"[ERROR] TICK 寫入失敗：{e}")

# === 系統模組 ===
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from pytz import timezone

def write_to_sheet(symbol, direction, pnl, entry_price, exit_price, volume_ratio, rsi, tmo,
                   candle_type, remark, holding_time, vwap, ema_cross, kd_status,
                   adx, plus_di, minus_di, tick_percentile, tick_slope,
                   trin_value, strategy_version, confidence_score, signal_type):
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        from datetime import datetime

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Trading Log").worksheet("交易紀錄")

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol,
            direction,
            signal_type,
            entry_price,
            exit_price,
            round(pnl * 100, 2),
            holding_time,
            rsi,
            tmo,
            vwap,
            volume_ratio,
            ema_cross,
            kd_status,
            candle_type,
            adx,
            plus_di,
            minus_di,
            tick_percentile,
            tick_slope,
            trin_value,
            strategy_version,
            confidence_score,
            remark
        ]
        sheet.append_row(row)
    except Exception as e:
        print(f"[ERROR] 寫入交易紀錄失敗：{e}")
        
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        from datetime import datetime

        # ✅ 認證與連線設定
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)

        sheet = client.open("Trading Log").worksheet("交易紀錄")

        # ✅ 要寫入的資料列
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol,
            direction,
            signal_type,
            entry_price,
            exit_price,
            f"{pnl*100:.2f}%" if pnl is not None else "",
            holding_time,
            f"{rsi:.1f}" if rsi is not None else "",
            f"{tmo:.1f}" if tmo is not None else "",
            f"{vwap:.2f}" if vwap is not None else "",
            f"{volume_ratio:.2f}" if volume_ratio is not None else "",
            ema_cross,
            kd_status,
            candle_type,
            f"{adx:.1f}" if adx is not None else "",
            f"{plus_di:.1f}" if plus_di is not None else "",
            f"{minus_di:.1f}" if minus_di is not None else "",
            f"{tick_percentile:.1f}" if tick_percentile is not None else "",
            f"{tick_slope:.1f}" if tick_slope is not None else "",
            f"{trin_value:.2f}" if trin_value is not None else "",
            strategy_version,
            confidence_score,
            note
        ]

        # ✅ 寫入工作表
        sheet.append_row(row)

    except Exception as e:
        print(f"[寫入錯誤] Google Sheets 寫入失敗：{e}")

    entry_data = positions[symbol]
    entry_price = entry_data['entry_price']
    direction = entry_data['direction']
    capital_used = entry_data['capital_used']
    entry_time = entry_data['entry_time']
    holding_ratio = entry_data.get('holding_ratio', 1.0)
    sell_stage = entry_data.get('sell_stage', 0)

    # 持倉時間（秒轉分鐘）
    holding_time = int((now - entry_time).total_seconds())

    # 報酬率計算（多/空通用）
    if direction == "long":
        return_rate = (latest_price - entry_price) / entry_price
    elif direction == "short":
        return_rate = (entry_price - latest_price) / entry_price
    else:
        return_rate = 0

    # 更新歷史最大報酬
    entry_data['max_gain'] = max(entry_data.get('max_gain', 0), return_rate)
    drawdown = entry_data['max_gain'] - return_rate

    # === 三段鎖利條件判斷 ===
    should_exit = False
    exit_ratio = 0.0
    reason = ""

    if sell_stage == 0 and return_rate >= 0.03 and drawdown >= 0.01:
        exit_ratio = 0.5
        reason = f"🔒 第1段停利 +{return_rate*100:.2f}%，回落 -{drawdown*100:.2f}%"
        entry_data['sell_stage'] = 1
        should_exit = True

    elif sell_stage == 1 and return_rate >= 0.06 and drawdown >= 0.015:
        exit_ratio = 0.3
        reason = f"🔒 第2段停利 +{return_rate*100:.2f}%，回落 -{drawdown*100:.2f}%"
        entry_data['sell_stage'] = 2
        should_exit = True

    elif sell_stage == 2 and return_rate >= 0.10 and drawdown >= 0.02:
        exit_ratio = holding_ratio
        reason = f"✅ 最終鎖利 +{return_rate*100:.2f}%，全數出清"
        entry_data['sell_stage'] = 3
        should_exit = True        

observed_candidates = {}  # ⬅️ 全域觀察名單，用來追蹤第一次通知後的二次啟動

def detect_latent_signal(df, rsi, tmo, obv, adx, latest_price, latest_vwap):
    signal_note = detect_latent_signal(df, rsi, tmo, obv, adx, latest_price, latest_vwap)

    print(f"[DEBUG] 傳入參數：rsi={rsi:.2f}, tmo={tmo:.2f}, obv={obv.iloc[-1]:.2f}, adx={adx:.2f}, price={latest_price:.2f}, vwap={latest_vwap:.2f}")

    auto_entry = False
    direction = None

    price = latest_price
    symbol = df['symbol'].iloc[-1]
    ema5 = df['close'].ewm(span=5, adjust=False).mean().iloc[-1]
    candle_type = "陽線" if df['close'].iloc[-1] > df['open'].iloc[-1] else "陰線"
    obv_direction = "上升" if obv.iloc[-1] > obv.iloc[-3] else "下滑"
    now = datetime.now()

    # ✅ 半山腰過濾
    rsi_middle = 45 <= rsi.iloc[-1] <= 65
    vwap_bias = price > latest_vwap * 1.05 or price < latest_vwap * 0.95
    recent_high = df['high'].rolling(window=20).max().iloc[-2]
    not_breakout = df['high'].iloc[-1] < recent_high
    if vwap_bias or rsi_middle or not_breakout:
        print(f"[WARNING] {symbol} 疑似半山腰，跳過。")
        return None, auto_entry, direction

    # ✅ 第一次通知（預警 - 多空轉折）
    if price < ema5 and rsi.iloc[-1] > rsi.iloc[-2] and tmo.iloc[-1] > tmo.iloc[-2]:
        observed_candidates[symbol] = {"price": price, "time": now}
        signal_note = (
            f"⚠️ 潛伏 - 多頭轉折\n"
            f"價格雖跌，但動能轉強\n"
            f"📊 RSI：{rsi.iloc[-1]:.1f} ↗️｜TMO：{tmo.iloc[-1]:.2f} ↗️｜VWAP：下方｜🕯️ {candle_type}"
            f"📌 加入觀察名單，等待正式啟動"
        )
        direction = "long"

    elif price > ema5 and rsi.iloc[-1] < rsi.iloc[-2] and tmo.iloc[-1] < tmo.iloc[-2]:
        observed_candidates[symbol] = {"price": price, "time": now}
        signal_note = (
            f"⚠️ 潛伏 - 空頭轉折\n"
            f"價格雖漲，但技術線轉弱\n"
            f"📊 RSI：{rsi.iloc[-1]:.1f} ↘️｜TMO：{tmo.iloc[-1]:.2f} ↘️｜VWAP：上方｜🕯️ {candle_type}"
            f"📌 加入觀察名單，等待正式啟動"
        )
        direction = "short"

    # ✅ 第二次通知（正式建倉 - 多頭）
    elif (
        df['close'].iloc[-1] < df['close'].iloc[-3] and
        rsi.iloc[-1] > rsi.iloc[-2] and rsi.iloc[-2] < 30 and
        tmo.iloc[-1] > tmo.iloc[-2] and tmo.iloc[-2] < 0 and
        obv.iloc[-1] > obv.iloc[-3] and
        price > latest_vwap 
    ):
        if symbol in observed_candidates:
            first = observed_candidates[symbol]
            price_diff = abs(price - first["price"]) / first["price"]
            time_diff = (now - first["time"]).total_seconds() / 60
            if price_diff <= 0.01 and time_diff <= 20:
                del observed_candidates[symbol]
                signal_note = (
                    f"🌱 潛伏多頭（正式建倉）\n"
                    f"📊 RSI：{rsi.iloc[-1]:.1f} ↗️｜TMO：{tmo.iloc[-1]:.2f} ↗️｜OBV：{obv_direction}｜VWAP：突破｜ADX < 15｜🕯️ {candle_type}"
                    f"📌 確認多頭啟動，建倉時機已到"
                )
                auto_entry = True
                direction = "long"

                # ✅ 實際記錄建倉資訊（避免重複建倉）
                if symbol not in entered_positions:
                    entered_positions[symbol] = {
                        "price": price,
                        "direction": direction,
                        "entry_time": now
                    }

                    # ✅ 潛伏多頭建倉，也納入三段鎖利管理
                    positions[symbol] = {
                        'entry_price': price,
                        'capital_used': 10000,  # 若尚未接資金控管，暫用固定值
                        'entry_time': now,
                        'direction': "long",
                        'max_gain': 0,
                        'holding_ratio': 1.0,
                        'sell_stage': 0
                    }

    # ✅ 第二次通知（正式建倉 - 空頭）
    elif (
        df['close'].iloc[-1] > df['close'].iloc[-3] and
        rsi.iloc[-1] < rsi.iloc[-2] and rsi.iloc[-2] > 70 and
        tmo.iloc[-1] < tmo.iloc[-2] and tmo.iloc[-2] > 5 and
        obv.iloc[-1] < obv.iloc[-3] and
        price < latest_vwap
    ):
        if symbol in observed_candidates:
            first = observed_candidates[symbol]
            price_diff = abs(price - first["price"]) / first["price"]
            time_diff = (now - first["time"]).total_seconds() / 60
            if price_diff <= 0.01 and time_diff <= 20:
                del observed_candidates[symbol]
                signal_note = (
                    f"🌪 潛伏空頭（正式建倉）\n"
                    f"📊 RSI：{rsi.iloc[-1]:.1f} ↘️｜TMO：{tmo.iloc[-1]:.2f} ↘️｜OBV：{obv_direction}｜VWAP：跌破｜ADX < 15｜🕯️ {candle_type}"
                    f"📌 確認空頭啟動，建倉時機已到"
                )
                auto_entry = True
                direction = "short"

                # ✅ 建倉紀錄（避免重複）
                if symbol not in entered_positions:
                    entered_positions[symbol] = {
                        "price": price,
                        "direction": "short",
                        "entry_time": now
                    }

                    positions[symbol] = {
                        'entry_price': price,
                        'capital_used': 10000,  # 若尚未控資金，暫定固定值
                        'entry_time': now,
                        'direction': "short",
                        'max_gain': 0,
                        'holding_ratio': 1.0,
                        'sell_stage': 0
                    }


    return signal_note, auto_entry, direction



# 設定美東時間
est = timezone("US/Eastern")
now_est = datetime.now(est)
market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)

# 只在開盤期間運行
if now_est < market_open or now_est > market_close:
    print("[INFO] 非美股盤中時間，跳過掃描")
    exit()

API_KEY = os.getenv("POLYGON_API_KEY") or "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"
STOCK_LIST_CSV = "filtered_us_stocks_common_only.csv"

import requests

WEBHOOK_URL = "https://discord.com/api/webhooks/1372956363235393536/2bELr_6LwGlk2K7G4B3d3J0MBD5iv04IwC33pQaWxAHcRbgn6sBVtkvI_65FfmC4Um5f"

def push_to_discord(symbol, price, rsi, tmo, vwap, volume_ratio, ema_cross, kd_status, candle_type, adx, plus_di, minus_di, signal_note):
    try:
        vwap_text = f"{vwap:.2f}" if vwap is not None and not pd.isna(vwap) else "無"
        message = (
        f"📣 **[訊號]** {symbol}\n"
        f"💰 價格：${price:.2f} | RSI：{rsi:.1f} | TMO：{tmo:.2f}\n"
        f"📊 VWAP：{vwap_text} | 倍量：{volume_ratio:.2f}x\n"
        f"📈 EMA：{ema_cross} | KD：{kd_status} | K棒：{candle_type}\n"
        f"📐 ADX：{adx:.1f} | DI+: {plus_di:.1f} / DI-: {minus_di:.1f}\n"
        f"🔔 **訊號類型**：{signal_note}"
        )
        payload = {"content": message}
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code != 204:
            print(f"[WARNING] Discord 推播失敗：{response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] 發送 Discord 推播失敗：{e}")

# ✅ 2. Google Sheets 寫入函式（可放在 push_to_discord 下方）
def write_to_sheet(
    symbol, direction, signal_type, tick_percentile, trin, latest_rsi,
    latest_tmo, tmo_slope, vwap_diff, volume_ratio, latest_adx, 
    plus_di, minus_di, kd_status, candle_type,
    entry_price, exit_price, holding_time_sec, return_rate,
    capital_used, capital_left, session, strategy_version, confidence_score, remark
):
    try:
        from oauth2client.service_account import ServiceAccountCredentials
        import gspread
        from datetime import datetime

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Trading Log").worksheet("交易紀錄")

        row_data = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), symbol, direction, signal_type,
            "是" if tick_percentile else "否", entry_price, exit_price,
            return_rate, holding_time_sec, capital_used, capital_left,
            tick_percentile, trin, latest_rsi, latest_tmo, tmo_slope,
            vwap_diff, volume_ratio, latest_adx, 
            f"DI+: {plus_di} / DI-: {minus_di}",kd_status, candle_type, 
            session, strategy_version, confidence_score, remark
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

def fetch_stock_data(symbol):
    try:
        # ✅ 初始化
        client = RESTClient(api_key=API_KEY)
        est = timezone("US/Eastern")
        now = datetime.now(est)

        # ✅ 設定安全抓取時間（20～50 分鐘前）
        end_time = now - timedelta(minutes=20)
        start_time = end_time - timedelta(minutes=30)
        from_ts = int(start_time.timestamp())
        to_ts = int(end_time.timestamp())

        print(f"[INFO] 抓取時間範圍：{start_time} ~ {end_time}")
        print(f"[DEBUG] 處理中股票：{symbol}")

        # ✅ 呼叫 Polygon API
        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=1,
            timespan="minute",
            from_=from_ts,
            to=to_ts,
            adjusted=True
        )

        # ✅ 統一 bars 結構處理
        if hasattr(aggs, 'results'):
            bars = aggs.results
        elif isinstance(aggs, list):
            bars = aggs
        else:
            print(f"[ERROR] 無效 bars 結構：{symbol}")
            return None

        print(f"[DEBUG] {symbol} bars 筆數：{len(bars)}")

        if not bars:
            print(f"[WARNING] 無資料 bars：{symbol}")
            return None

        # ✅ 清洗資料
        cleaned_bars = []
        for bar in bars:
            if hasattr(bar, '__dict__'):
                bar = vars(bar)
            elif not isinstance(bar, dict):
                continue

            time_key = "timestamp" if "timestamp" in bar else ("t" if "t" in bar else None)
            if time_key is None or bar.get(time_key) is None:
                continue

            bar["timestamp"] = bar[time_key]

            required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
            if not all(field in bar and bar[field] is not None for field in required_fields):
                continue

            cleaned_bars.append(bar)

        if len(cleaned_bars) == 0:
            print(f"[WARNING] 無有效 K 棒資料：{symbol}")
            return None

        # ✅ 建立 DataFrame
        df = pd.DataFrame(cleaned_bars)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        if len(df) < 14:
            print(f"[WARNING] {symbol} K線不足（僅 {len(df)} 筆），跳過")
            return None

        return df

    except Exception as e:
        print(f"[ERROR] {symbol} 資料抓取失敗：{e}")
        return None
        
def analyze_stock_data(symbol, bars):
    try:
        df = pd.DataFrame(bars)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        if len(df) < 20:
            print(f"[WARNING] {symbol} 線數不足（僅 {len(df)} 筆），跳過")
            return None

        # ✅ 收盤價檢查
        if 'close' not in df.columns or df['close'].isnull().all():
            print(f"[WARNING] {symbol} 缺少有效收盤價")
            return None

        latest_price = df['close'].iloc[-1]
        print(f"[DATA] {symbol} 最新收盤價：{latest_price:.2f}")

        # === 技術指標 ===
        latest_price = df['close'].iloc[-1]

        # RSI
        rsi = RSIIndicator(close=df['close'], window=14).rsi().iloc[-1]

        # VWAP
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        latest_vwap = vwap.iloc[-1]

        # KD（K, D）
        kd = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=14)
        k_value = kd.stoch().iloc[-1]
        d_value = kd.stoch_signal().iloc[-1]

        # TMO（你自訂的函數）
        tmo_value = calculate_tmo(df)

        # 過濾 NaN
        if any(map(np.isnan, [latest_price, rsi, latest_vwap, k_value, d_value, tmo_value])):
            print(f"[WARNING] {symbol} 有 NaN 技術指標，跳過")
            return None

        # ✅ 顯示結果
        print(f"✅ {symbol} 收盤：{latest_price:.2f}｜RSI：{rsi:.1f}｜TMO：{tmo_value:.2f}｜VWAP：{latest_vwap:.2f}｜K：{k_value:.1f}｜D：{d_value:.1f}")

        return {
            "symbol": symbol,
            "price": latest_price,
            "rsi": rsi,
            "tmo": tmo_value,
            "vwap": latest_vwap,
            "k": k_value,
            "d": d_value
        }

    except Exception as e:
        print(f"[ERROR] {symbol} 技術分析失敗：{e}")
        return None
    
        
    candle_type = detect_candle_pattern(df)
    tmo_value = calculate_tmo(df)    


    # 技術指標
    rsi = RSIIndicator(close=df['close']).rsi()
    tmo = calculate_tmo(df['close'])  # ✅ 替代 MACD
    vwap = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
    ema5 = EMAIndicator(close=df['close'], window=5).ema_indicator()
    ema20 = EMAIndicator(close=df['close'], window=20).ema_indicator()
    adx = ADXIndicator(high=df['high'], low=df['low'], close=df['close']).adx()
    plus_di = ADXIndicator(high=df['high'], low=df['low'], close=df['close']).plus_di()
    minus_di = ADXIndicator(high=df['high'], low=df['low'], close=df['close']).minus_di()
    volume_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
    candle_type = detect_candle_pattern(df)  # 自訂：K棒型態判斷

    # 最新值
    latest_price = df['close'].iloc[-1]
    latest_open = df['open'].iloc[-1]
    latest_high = df['high'].iloc[-1]
    latest_low = df['low'].iloc[-1]
    latest_volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].rolling(20).mean().iloc[-1]
    volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0

    latest_rsi = rsi.iloc[-1]
    latest_tmo = tmo.iloc[-1]
    tmo_slope = tmo.diff().iloc[-1]
    latest_vwap = vwap.iloc[-1] if not pd.isna(vwap.iloc[-1]) else 0
    ema5_above_ema20 = ema5.iloc[-1] > ema20.iloc[-1]
    ema_cross = "✅" if ema5_above_ema20 else "❌"

    k_value = kd.stoch().iloc[-1]
    d_value = kd.stoch_signal().iloc[-1]
    kd_status = "金叉" if k_value > d_value else "死叉" if k_value < d_value else "中性"

    latest_adx = adx.iloc[-1]
    latest_plus_di = plus_di.iloc[-1]
    latest_minus_di = minus_di.iloc[-1]

    candle_type = detect_candle_pattern(df)  # K棒型態

    # ✅ 半山腰過濾條件：VWAP 偏離過大（避免追高追空）
    if latest_price > latest_vwap * 1.05 or latest_price < latest_vwap * 0.95:
        print(f"[WARNING] {symbol} 價格偏離 VWAP 過大，疑似半山腰，跳過。")
        return None

    # 顯示 Log
    print(f"[INFO] {symbol} 最新收盤價：{latest_price:.2f}")
    print(f"📊 RSI：{latest_rsi:.1f} | TMO：{latest_tmo:.2f}（斜率：{tmo_slope:.2f}）")
    print(f"📈 VWAP：{latest_vwap:.2f} | 均線交叉：{ema_cross}")
    print(f"🔍 成交量：{volume_ratio:.2f} 倍 | K棒型態：{candle_type}")
    print(f"📐 ADX：{latest_adx:.1f} | +DI：{latest_plus_di:.1f} | -DI：{latest_minus_di:.1f}")

    # VWAP 格式化
    vwap_str = "無" if latest_vwap is None or pd.isna(latest_vwap) else f"{latest_vwap:.2f}"

    # 格式化印出（改為 TMO / ADX / candle_type）
    print(f"[INFO] {symbol} | 價格: {latest_price:.2f} | RSI: {latest_rsi:.1f} | TMO: {latest_tmo:+.2f} | "
    f"VWAP: {vwap_str} | 量能: {volume_ratio:.1f}x | EMA5>EMA20: {ema_cross} | KD: {kd_status} | K棒: {candle_type}")
    print(f"📐 ADX: {latest_adx:.1f} | +DI: {latest_plus_di:.1f} | -DI: {latest_minus_di:.1f}")

    # 檢查 VWAP 是否為空值（避免除錯失敗）
    if latest_vwap is None or pd.isna(latest_vwap):
        print(f"[WARNING] VWAP 為 NaN，跳過：{symbol}")
        return None


def evaluate_breakout_signal(df):
    if df is None or len(df) < 30:
        return None

    close = df['close']
    volume = df['volume']

    # OBV
    obv = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()
    obv_slope = obv.diff().rolling(3).mean()

    # 布林帶
    bb = BollingerBands(close=close, window=20, window_dev=2)
    bb_width = bb.bollinger_hband() - bb.bollinger_lband()
    bb_width_sma = bb_width.rolling(5).mean()

    # 價格震盪範圍與判斷
    price_range = close.rolling(5).max() - close.rolling(5).min()
    price_sideways = price_range.iloc[-1] < close.iloc[-1] * 0.02
    bb_contracted = bb_width_sma.iloc[-1] < close.iloc[-1] * 0.03

    signal = None

    # 🔍 檢查 breakout 訊號
    breakout_signal = None
    if breakout_signal:
        print(f"[BREAKOUT] {symbol}: {breakout_signal}")
        # push_to_discord(symbol, signal_note=breakout_signal)  # 如需推播

    # ⚠️ 預警 - 多頭轉折（含 VWAP、OBV）
    elif (
        latest_rsi < 35 and rsi.iloc[-2] < rsi.iloc[-1] and
        tmo_slope > 0 and
     latest_price > latest_vwap and
        obv.iloc[-1] > obv.iloc[-3]
    ):
        signal_note = (
            f"⚠️ 預警 - 多頭轉折\n"
            f"📊 RSI：{latest_rsi:.1f} ↗️｜⚡ TMO：{latest_tmo:.2f} ↗️\n"
            f"📈 VWAP：已上穿｜💰 OBV：上升｜🕯️ K棒：{candle_type}"
        )

    # ⚠️ 預警 - 空頭轉折（含 VWAP、OBV）
    elif (
        latest_rsi > 65 and rsi.iloc[-2] > rsi.iloc[-1] and
        tmo_slope < 0 and
        latest_price < latest_vwap and
        obv.iloc[-1] < obv.iloc[-3]
    ):
        signal_note = (
            f"⚠️ 預警 - 空頭轉折\n"
            f"📊 RSI：{latest_rsi:.1f} ↘️｜⚡ TMO：{latest_tmo:.2f} ↘️\n"
            f"📉 VWAP：已跌破｜💰 OBV：下滑｜🕯️ K棒：{candle_type}"
        )

    # 🐸 多頭正式進場
    elif (
        latest_rsi > 30 and rsi.iloc[-2] < rsi.iloc[-1] and            # RSI 回升
        tmo.iloc[-2] < 0 and latest_tmo > 0 and tmo_slope > 0 and       # TMO 翻正
        latest_price > latest_vwap and                                  # 價格突破 VWAP
        volume_ratio > 1.5 and                                          # 放量
        ema5_above_20 and                                               # EMA5 上穿 EMA20
        latest_adx > 20 and latest_plus_di > latest_minus_di and        # ADX 趨勢強化
        candle_type in ['hammer', 'bullish_engulfing']                  # 多頭 K 棒
    ):
        signal_note = (
            f"🐸 正式進場 - 多頭\n"
            f"📊 RSI：{latest_rsi:.1f} ↗️｜⚡ TMO：{latest_tmo:.2f} ↗️\n"
            f"📈 VWAP：上穿｜📊 Volume：{volume_ratio:.2f}x｜🕯️ K棒：{candle_type}\n"
            f"📐 ADX：{latest_adx:.1f}｜DI+: {latest_plus_di:.1f} > DI-: {latest_minus_di:.1f}"
        )

    if symbol not in entry_price_dict and len(positions_held) < max_positions:
        allocated = total_capital * position_size_pct

        # 若資金不足，跳過
        if capital_left < allocated:
            print(f"[SKIP] 資金不足，無法進場：{symbol}")
        else:
            # 計算股數與真實投入金額
            shares = int(allocated / latest_price)
            actual_cost = shares * latest_price

            if shares == 0:
                print(f"[SKIP] 價格過高，無法整股購買：{symbol}")
            else:
                # 記錄已建倉股票，避免重複建倉
                if symbol not in entered_positions:
                    entered_positions[symbol] = {
                        "price": latest_price,
                        "direction": "long",  # 這裡是多頭進場
                        "entry_time": datetime.now()
                    }

                # 記錄資訊
                entry_price_dict[symbol] = latest_price
                positions_held[symbol] = actual_cost
                capital_left -= actual_cost
                entry_direction_dict[symbol] = 'long'
                entry_shares_dict[symbol] = shares
                entry_time_dict[symbol] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # ✅ 建立完整持倉資訊，用於多段鎖利
                positions[symbol] = {
                    'entry_price': latest_price,
                    'capital_used': allocated,
                    'entry_time': datetime.now(),
                    'direction': direction,
                    'max_gain': 0,
                    'holding_ratio': 1.0,
                    'sell_stage': 0
                }

                # 推播通知
                send_to_discord(
                    f"🟢 **[自動進場 - 多頭開倉]** {symbol} @ ${latest_price:.2f}｜{shares} 股\n"
                    f"📊 RSI: {latest_rsi:.1f} | TMO: {latest_tmo:.2f} | 倍量: {volume_ratio:.2f}x | K棒: {candle_type}\n"
                    f"📐 ADX: {latest_adx:.1f} | DI+: {latest_plus_di:.1f} / DI-: {latest_minus_di:.1f}\n"
                    f"💰 總投入：${actual_cost:.2f}｜剩餘資金：${capital_left:.2f}\n"
                    f"🕑 時間：{entry_time_dict[symbol]}"
                )
        
    # 🐶 空頭正式進場
    elif (
        latest_rsi < 70 and rsi.iloc[-2] > rsi.iloc[-1] and             # RSI 下滑
        tmo.iloc[-2] > 0 and latest_tmo < 0 and tmo_slope < 0 and       # TMO 翻負
        latest_price < latest_vwap and                                  # 價格跌破 VWAP
        volume_ratio > 1.5 and                                          # 放量
        ema5_below_20 and                                               # EMA5 跌破 EMA20
        latest_adx > 20 and latest_minus_di > latest_plus_di and        # 趨勢明顯轉弱
        candle_type in ['shooting_star', 'bearish_engulfing']          # 空頭 K 棒
    ):
        signal_note = (
            f"🐶 正式進場 - 空頭\n"
            f"📊 RSI：{latest_rsi:.1f} ↘️｜⚡ TMO：{latest_tmo:.2f} ↘️\n"
            f"📉 VWAP：跌破｜📊 Volume：{volume_ratio:.2f}x｜🕯️ K棒：{candle_type}\n"
            f"📐 ADX：{latest_adx:.1f}｜DI-: {latest_minus_di:.1f} > DI+: {latest_plus_di:.1f}"
        )

    if symbol not in entry_price_dict and len(positions_held) < max_positions:
        allocated = total_capital * position_size_pct

        if capital_left < allocated:
            print(f"[SKIP] 資金不足，無法進場：{symbol}")
        else:
            shares = int(allocated / latest_price)
            actual_cost = shares * latest_price

            if shares == 0:
                print(f"[SKIP] 價格過高，無法整股放空：{symbol}")
            else:
                # 記錄已建倉股票（避免重複）
                if symbol not in entered_positions:
                    entered_positions[symbol] = {
                        "price": latest_price,
                        "direction": "short",  # ⬅️ 空頭方向
                        "entry_time": datetime.now()
                    }
                    
                entry_price_dict[symbol] = latest_price
                positions_held[symbol] = actual_cost
                capital_left -= actual_cost
                entry_direction_dict[symbol] = 'short'
                entry_shares_dict[symbol] = shares
                entry_time_dict[symbol] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # ✅ 建立多段鎖利用的空單持倉資料
                positions[symbol] = {
                    'entry_price': latest_price,
                    'capital_used': allocated,
                    'entry_time': datetime.now(),
                    'direction': "short",  # ✅ 空單記得改這裡
                    'max_gain': 0,
                    'holding_ratio': 1.0,
                    'sell_stage': 0
                }

                send_to_discord(
                    f"🔴 **[自動進場 - 空頭開倉]** {symbol} @ ${latest_price:.2f}｜{shares} 股\n"
                    f"📊 RSI: {latest_rsi:.1f} | TMO: {latest_tmo:.2f} | 倍量: {volume_ratio:.2f}x | K棒: {candle_type}\n"
                    f"📐 ADX: {latest_adx:.1f} | DI+: {latest_plus_di:.1f} / DI-: {latest_minus_di:.1f}\n"
                    f"💰 總投入：${actual_cost:.2f}｜剩餘資金：${capital_left:.2f}\n"
                    f"🕑 時間：{entry_time_dict[symbol]}"
                )
    
    # 印出訊號（新版格式）
    if signal_note:
        print("-" * 60)
        print(f"[DATA] {symbol} 最新K棒：")
        print(f"開：{latest_open:.2f} | 高：{latest_high:.2f} | 低：{latest_low:.2f} | 收：{latest_price:.2f} | 量：{latest_volume:,}")
        print(f"[INDICATOR] RSI: {latest_rsi:.1f} | TMO: {latest_tmo:.2f} | VWAP: {latest_vwap:.2f} | 倍量: {volume_ratio:.2f}x")
        print(f"[TREND] EMA交叉: {ema_cross} | ADX: {latest_adx:.1f} | DI+: {latest_plus_di:.1f} | DI-: {latest_minus_di:.1f}")
        print(f"[KD] K: {k_value:.1f} | D: {d_value:.1f} | 狀態: {kd_status} | K棒: {candle_type}")
        print(f"[ALERT] {signal_note}：{symbol}")
        print("-" * 60)

        # ✅ 主訊號推播到 Discord（新版：使用 TMO + ADX）
        push_to_discord(
            symbol=symbol,
            price=latest_price,
            rsi=latest_rsi,
            tmo=latest_tmo,
            tmo_slope=tmo_slope,
            vwap=latest_vwap,
            volume_ratio=volume_ratio,
            ema_cross=ema_cross,
            kd_status=kd_status,
            candle_type=candle_type,
            adx=latest_adx,
            plus_di=latest_plus_di,
            minus_di=latest_minus_di,
            signal_note=signal_note
        )

import time
from datetime import datetime

entry_price_dict = {}
positions = {}  # 持倉記錄：{symbol: {...}}
total_capital = 1000000
position_size_pct = 0.05
max_positions = 15
capital_left = total_capital

def auto_trade_and_monitor(symbol, latest_price, signal_note, direction,
                           tick_percentile, trin, latest_rsi, latest_tmo, tmo_slope,
                           vwap_diff, volume_ratio, latest_adx, plus_di, minus_di,
                           kd_status, candle_type, session, strategy_version, confidence_score):
    global capital_left

    now = datetime.now()
    stop_loss_rate = 0.02
    take_profit_rate = 0.05
    # 自動跳過股價過高的股票（例如大於 100 美元）
    if latest_price < 1 or latest_price > 10:
        print(f"[SKIP] {symbol} 不在價格區間，跳過進場")
        return
    
    # ✅ 進場邏輯
    if symbol not in positions and len(positions) < max_positions:
        capital_used = total_capital * position_size_pct
        capital_left -= capital_used
        positions[symbol] = {
            'entry_price': latest_price,
            'entry_time': now,
            'direction': direction,
            'capital_used': capital_used,
            'strategy': strategy_version,
            'confidence': confidence_score
        }
        send_to_discord(f"🐸 **[自動進場]** {symbol} @ {latest_price:.2f} 方向：{direction}")
    
        print(f"[自動進場] {symbol} @ {latest_price} 方向：{direction}")
        return

    # ✅ 出場邏輯
    if symbol in positions:
        entry_data = positions[symbol]
        entry_price = entry_data['entry_price']
        holding_time_sec = int((now - entry_data['timestamp']).total_seconds())
        return_rate = (latest_price - entry_price) / entry_price if direction == "多" else (entry_price - latest_price) / entry_price

    if return_rate >= take_profit_rate or return_rate <= -stop_loss_rate:
        exit_price = latest_price
        capital_left += entry_data['capital_used']
        del positions[symbol]

        print(f"[出場] {symbol} @ {exit_price:.2f}，報酬率：{return_rate*100:.2f}%，持倉：{holding_time_sec} 秒")

        remark = "停利出場" if return_rate >= take_profit_rate else "停損出場"
        write_to_sheet(
            symbol=symbol,
            direction=direction,
            signal_type=signal_note,
            tick_percentile=tick_percentile,
            trin=trin,
            latest_rsi=latest_rsi,
            latest_tmo=latest_tmo,
            tmo_slope=tmo_slope,
            vwap_diff=vwap_diff,
            volume_ratio=volume_ratio,
            latest_adx=latest_adx,
            plus_di=plus_di,
            minus_di=minus_di,
            kd_status=kd_status,
            candle_type=candle_type,
            entry_price=entry_price,
            exit_price=exit_price,
            holding_time_sec=holding_time_sec,
            return_rate=return_rate,
            capital_used=entry_data['capital_used'],
            capital_left=capital_left,
            session=session,
            strategy_version=strategy_version,
            confidence_score=confidence_score,
            remark=remark
    )


# === 印出（有訊號才印TICK/TRIN） ===
def check_market_latent_signals(tick_percentile, tick_slope, trin_value):
    if tick_percentile > 50 and tick_slope > 0 and trin_value < 1.0:
        message = (
            "📊 **[大盤潛伏多頭]**\n"
            f"TICK 百分位：{tick_percentile:.1f}｜斜率：+{tick_slope:.2f}｜TRIN：{trin_value:.2f}\n"
            "大盤動能轉強，觀察個股多方機會"
        )
        send_to_discord(message)

    elif tick_percentile < 50 and tick_slope < 0 and trin_value > 1.0:
        message = (
            "📉 **[大盤潛伏空頭]**\n"
            f"TICK 百分位：{tick_percentile:.1f}｜斜率：{tick_slope:.2f}｜TRIN：{trin_value:.2f}\n"
            "大盤動能轉弱，注意個股風險與回檔"
        )
        send_to_discord(message)

# ✅ 接著模擬自動進出場
def analyze_signal_and_return(symbol, df, latest_price, latest_open, latest_high, latest_low, latest_volume,
                              latest_rsi, latest_vwap, volume_ratio, ema5_above_ema20,
                              kd_status, tmo_cross, atr, signal_note,
                              latest_tmo, tmo_slope, latest_adx,
                              plus_di, minus_di, candle_type):
    # ✅ 自動進出場邏輯
    auto_trade_and_monitor(
        symbol=symbol,
        latest_price=latest_price,
        signal_note=signal_note,
        direction="多" if "多" in (signal_note or "") else "空",
        tick_percentile=None,  # 如有 TICK 分析結果可以補上
        trin=None,             # 如有 TRIN 結果也補上
        latest_rsi=latest_rsi,
        latest_tmo=latest_tmo,
        tmo_slope=tmo_slope,
        vwap_diff=(latest_price - latest_vwap) / latest_vwap,
        volume_ratio=volume_ratio,
        latest_adx=latest_adx,
        plus_di=plus_di,
        minus_di=minus_di,
        kd_status=kd_status,
        candle_type=candle_type,
        session="regular",
        strategy_version="v1.0",
        confidence_score=1.0
    )

    return {
        "df": df,
        "latest_price": latest_price,
        "latest_open": latest_open,
        "latest_high": latest_high,
        "latest_low": latest_low,
        "latest_volume": latest_volume,
        "latest_rsi": latest_rsi,
        "latest_vwap": latest_vwap,
        "volume_ratio": volume_ratio,
        "ema5_above_ema20": ema5_above_ema20,
        "kd_status": kd_status,
        "tmo_cross": tmo_cross,
        "atr": atr.iloc[-1],
        "signal_note": signal_note
    }

def should_push_signal(signal_note, entry_price_dict, symbol):
    if "預警" in signal_note:
        return True
    if ("正式進場" in signal_note) and symbol not in entry_price_dict:
        return True
    return False

# === 技術工具函數 ===

# ✅ 模擬 TICK 系列
def get_tick_series():
    import pandas as pd  # 如果前面已經有匯入可以省略
    return pd.Series([random.randint(-1000, 1000) for _ in range(30)])

# ✅ TICK 百分位
def get_tick_percentile(tick_series):
    if tick_series is None or tick_series.empty:
        print("[WARNING] tick_series 是空的，無法計算百分位")
        return Noneg
    try:
        current_tick = tick_series.iloc[-1]
        rank = (tick_series < current_tick).sum()
        percentile = (rank / len(tick_series)) * 100
        return round(percentile, 2)
    except Exception as e:
        print(f"[ERROR] 計算 tick 百分位失敗：{e}")
        return None

# ✅ TICK 斜率
def get_tick_slope(tick_series, window=5):
    if len(tick_series) < window + 1:
        return 0
    return tick_series.iloc[-1] - tick_series.iloc[-window - 1]

# ✅ TRIN 模擬值
def get_trin_value():
    return round(random.uniform(0.5, 2.0), 2)

# ✅ 主掃描函數
def run_scanner(tick_series):
    # ✅ 初始化成功與失敗計數器
    success_count = 0
    fail_count = 0

    # ✅ 每次掃描前，先檢查持倉是否該出場
    for symbol in list(positions.keys()):
        latest_price = get_latest_price(symbol)
        check_exit_and_notify_dynamic(symbol, latest_price, datetime.now())

    # ✅ 抓大盤指標
    tick_percentile = get_tick_percentile(tick_series)
    tick_slope = get_tick_slope(tick_series)
    trin_value = get_trin_value()

    print("=" * 50)
    print(f"[INFO] TICK 百分位：{tick_percentile} | 斜率：{tick_slope} | TRIN：{trin_value}")
    print("=" * 50)

    # ✅ 推播市場潛伏訊號（如果有）
    check_market_latent_signals(tick_percentile, tick_slope, trin_value)

    # ✅ 股票清單
    stock_list = load_stock_list(STOCK_LIST_CSV)

    for symbol in stock_list:
        try:
            print(f"[DEBUG] 嘗試抓資料：{symbol}")
            df = fetch_stock_data(symbol)

            if df is None or df.empty or 'close' not in df.columns or len(df) < 15:
                print(f"[警告] {symbol} 無效或資料不足，跳過")
                fail_count += 1
                continue

            print(f"[INFO] {symbol} K線筆數：{len(df)}")
            print(f"[INFO] {symbol} K線取得成功，開始進行技術指標分析")
            
            # 技術指標
            latest_price = df['close'].iloc[-1]
            rsi = RSIIndicator(close=df['close']).rsi()
            latest_rsi = rsi.iloc[-1]

            # VWAP
            vwap = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
            latest_vwap = vwap.iloc[-1]

             # 成交量倍數
            volume = df['volume']
            volume_avg = volume.rolling(window=20).mean()
            volume_ratio = volume.iloc[-1] / volume_avg.iloc[-1]

            # K線形態（陽線 or 陰線）
            latest_open = df['open'].iloc[-1]
            candle_type = "陽線" if latest_price > latest_open else "陰線"

            # 計算 OBV 指標
            obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()

            # TMO 計算（簡化：以 5期的差分平均當作動能）
            tmo = df['close'].diff().rolling(window=5).mean()
            latest_tmo = tmo.iloc[-1]
            prev_tmo = tmo.iloc[-2] if len(tmo) >= 2 else 0
            tmo_cross = latest_tmo > 0 and prev_tmo <= 0

            # 潛伏訊號（預警推播）
            signal_note = detect_latent_signal(df, rsi, tmo, obv, latest_price, latest_vwap)
            if signal_note:
                message = (
                    f"{signal_note} {symbol}\n"
                    f"收盤：{latest_price:.2f}｜RSI: {latest_rsi:.1f}｜TMO: {latest_tmo:.2f}｜"
                    f"VWAP: {latest_vwap:.2f}｜量：{volume_ratio:.2f}x"
                )
                send_to_discord(message)

            # 正式進場訊號條件
            signal_note = None
            direction = None

            # 🐸 多頭進場條件
            if latest_rsi < 30 and latest_price > latest_vwap and tmo_cross and volume_ratio > 1.5 and candle_type == "陽線":
                signal_note = "🐸 正式進場 - 多頭"
                direction = "long"

            # 🐶 空頭進場條件
            elif latest_rsi > 70 and latest_price < latest_vwap and latest_tmo < 0 and volume_ratio > 1.5 and candle_type == "陰線":
                signal_note = "🐶 正式進場 - 空頭"
                direction = "short"

            # ✅ 補這段正式推播
            if signal_note and direction:
                send_to_discord(
                    f"{signal_note} {symbol} @ {latest_price:.2f}｜方向：{direction.upper()}｜"
                    f"RSI：{latest_rsi:.1f}｜TMO：{latest_tmo:.2f}｜VWAP：{latest_vwap:.2f}｜成交量：{volume_ratio:.2f}x｜K線：{candle_type}"
                )

            success_count += 1  # ✅ 放在最後，表示這支股票處理成功

        except Exception as e:
            print(f"[ERROR] {symbol} 發生錯誤：{e}")
            fail_count += 1

    # === Step 4: 模擬進場 ===
    check_exit_and_notify(symbol, latest_price)

    # 如果沒有任何訊號，照樣顯示資訊
    if not signal_note:
        print(
            f"📌 {symbol}｜收盤：${latest_price:.2f}｜RSI：{latest_rsi:.1f}｜"
            f"TMO：{latest_tmo:.2f}｜VWAP：${latest_vwap:.2f}｜Volume 倍數：{volume_ratio:.2f}x｜K棒：{candle_type}"
        )
    
    if signal_note and symbol not in entry_price_dict and len(positions_held) < max_positions:
        allocated = total_capital * position_size_pct
        if capital_left >= allocated:
            entry_price_dict[symbol] = latest_price
            positions_held[symbol] = allocated
            entry_direction_dict[symbol] = direction
            capital_left -= allocated
            entry_time_dict[symbol] = datetime.now()  # ✅ 記錄進場時間
            print(f"[ENTRY] {symbol} 進場 ({direction}) @ {latest_price:.2f}，資金 ${allocated:.2f}，剩餘 ${capital_left:.2f}")
            send_to_discord(f"{signal_note} {symbol} @ {latest_price:.2f} | RSI: {latest_rsi:.1f} | TMO: {latest_tmo:.2f} | 倍量: {volume_ratio:.2f} | K: {candle_type}")

    # === Step 5: 出場條件 ===
    
    
        
# 執行掃描並接收統計結果
tick_series = get_tick_series()
success_count, fail_count = run_scanner(tick_series)

# 印出統計結果
print(f"\n[統計] 本輪成功 {success_count} 檔，失敗 {fail_count} 檔，有效率：{round(success_count / (success_count + fail_count + 1e-6) * 100, 2)}%")

# ✅ 主程式入口
if __name__ == "__main__":
    while True:
        tick_series = get_tick_series()

        if tick_series is not None and not tick_series.empty:
            tick_percentile = get_tick_percentile(tick_series)
            print(f"[INFO] 當前 TICK 百分位：{tick_percentile:.2f}")
        else:
            tick_percentile = None
            print("[WARNING] tick_series 是空的，跳過 tick 百分位計算")

        tick_series = get_tick_series()                       # 🟢 第一步：先抓 TICK 序列
        tick_percentile = get_tick_percentile(tick_series)    # 🟢 第二步：算百分位
        tick_slope = get_tick_slope(tick_series)              # 🟢 第三步：算斜率
        current_tick = tick_series.iloc[-1]                   # 🟢 第四步：抓當前值
        trin_value = get_trin_value()                         # 🟢 第五步：TRIN 指標

        if tick_percentile is not None and tick_slope is not None and trin_value is not None:
            if tick_percentile > 50 and tick_slope > 0 and trin_value < 1.0:
                message = (
                    f"📊 **[大盤潛伏多頭]**\n"
                    f"TICK 百分位：{tick_percentile:.1f}｜斜率：+{tick_slope:.0f}｜TRIN：{trin_value:.2f}\n"
                    "大盤動能轉強，觀察個股多方機會"
                )
                send_to_discord(message)

            if tick_percentile < 5 and tick_slope < 0 and trin_value > 1.0:
                message = (
                    f"📉 **[大盤潛伏空頭]**\n"
                    f"TICK 百分位：{tick_percentile:.1f}｜斜率：{tick_slope:.0f}｜TRIN：{trin_value:.2f}\n"
                    "大盤動能轉弱，觀察個股空方壓力"
                )
                send_to_discord(message)

            if current_tick > 1000:
                message = (
                    f"🚀 **[TICK 極端多頭]**\n"
                    f"TICK 當前值：{current_tick:.0f}｜斜率：+{tick_slope:.0f}｜百分位：{tick_percentile:.1f}\n"
                    "市場情緒極端偏多，短線可能急拉"
                )
                send_to_discord(message)

            if current_tick < -1000:
                message = (
                    f"⚠️ **[TICK 極端空頭]**\n"
                    f"TICK 當前值：{current_tick:.0f}｜斜率：{tick_slope:.0f}｜百分位：{tick_percentile:.1f}\n"
                    "市場情緒極端偏空，短線恐慌賣壓湧現"
                )
                send_to_discord(message)

            # ✅ 寫入 TICK 歷史紀錄到 Google Sheets
            write_tick_to_sheet(current_tick, tick_percentile, tick_slope, trin_value)

    try:   # ✅ 執行掃描器
        success_count, fail_count = run_scanner(tick_series)
        efficiency = round(success_count / (success_count + fail_count + 1e-6) * 100, 2)
        print(f"\n[統計] ✅ 成功 {success_count} 檔，❌ 失敗 {fail_count} 檔，有效率：{efficiency}%")

        # ✅ 可加每日統計與推播（選配）
        # generate_and_push_summary(df_log)

    except Exception as e:
        print(f"[ERROR] 掃描輪出錯：{e}")
        time.sleep(30)    
        
    print("[INFO] 等待 60 秒再執行下一輪...")
    time.sleep(60)

    #✅ 統計 df_log 交易資料（這區建議你主程式原本就有）
    total_trades = len(df_log)
    win_count = len(df_log[df_log['pnl'] > 0])
    lose_count = len(df_log[df_log['pnl'] <= 0])
    total_pnl = df_log['pnl'].sum() * 100
    max_profit = df_log['pnl'].max() * 100
    max_loss = df_log['pnl'].min() * 100

    avg_seconds = df_log['holding_time'].mean()
    hours = int(avg_seconds // 3600)
    minutes = int((avg_seconds % 3600) // 60)
    avg_holding_time_str = f"{hours} 小時 {minutes} 分"

    # ✅ 建立 summary_row
    summary_row = {
        "日期": datetime.now().strftime("%Y-%m-%d"),
        "策略版本": "v4.2",
        "總交易次數": total_trades,
        "勝場": win_count,
        "敗場": lose_count,
        "勝率": f"{(win_count / total_trades * 100):.1f}%",
        "總報酬率": f"{total_pnl:.2f}%",
        "最大獲利": f"{max_profit:.2f}%",
        "最大虧損": f"{max_loss:.2f}%",
        "平均持倉時間": avg_holding_time_str
    }
    # ✅ 每日總結統計 + 推播（就在這裡補上）
    write_summary_to_sheets(summary_row)
    send_summary_to_discord(summary_row)
