# === 技術指標 ===
from ta.volume import OnBalanceVolumeIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, ADXIndicator, MACD
from datetime import datetime  # 若還沒寫在最上面就加
from ta.volume import OnBalanceVolumeIndicator

# === 自訂函數 ===
from utils import detect_candle_pattern, calculate_tmo
import pandas as pd
import random
import requests
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

# === 系統模組 ===
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from pytz import timezone

def write_to_sheet(symbol, direction, pnl, entry_price, exit_price, volume_ratio, rsi, tmo, candle_type, remark):
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
            f"{pnl * 100:.2f}%",
            entry_price,
            exit_price,
            f"{volume_ratio:.2f}x",
            f"{rsi:.1f}",
            f"{tmo:.2f}",
            candle_type,
            remark
        ]

        sheet.append_row(row)
        print(f"[✅ 已寫入 Sheets] {symbol} - {remark}")

    except Exception as e:
        print(f"[ERROR] 寫入 Google Sheets 失敗：{e}")

def detect_latent_signal(df, rsi, tmo, obv, latest_price, latest_vwap):
       """
       回傳潛伏訊號類別（'潛伏多頭'、'潛伏空頭' 或 None）
       條件：價格與指標背離產生共振（RSI、TMO、OBV、VWAP）
       """
       signal_note = None

       # 🟢 潛伏多頭條件
       if (
           df['close'].iloc[-1] < df['close'].iloc[-3] and                    # 價格下跌中
           rsi.iloc[-1] > rsi.iloc[-2] and rsi.iloc[-2] < 30 and              # RSI < 30 且回升
           tmo.iloc[-1] > tmo.iloc[-2] and tmo.iloc[-2] < 0 and               # TMO 在低檔翻多
           obv.iloc[-1] > obv.iloc[-3] and                                    # OBV 上升（資金進場）
           latest_price > latest_vwap                                         # 價格站回 VWAP 上方
       ):
           signal_note = "🌱 潛伏多頭（多重共振）"

       # 🔴 潛伏空頭條件
       elif (
           df['close'].iloc[-1] > df['close'].iloc[-3] and                    # 價格上漲中
           rsi.iloc[-1] < rsi.iloc[-2] and rsi.iloc[-2] > 70 and              # RSI > 70 且下彎
           tmo.iloc[-1] < tmo.iloc[-2] and tmo.iloc[-2] > 5 and               # TMO 高檔轉弱
           obv.iloc[-1] < obv.iloc[-3] and                                    # OBV 下滑（資金撤出）
           latest_price < latest_vwap                                         # 價格跌破 VWAP
       ):
           signal_note = "🌪 潛伏空頭（多重共振）"

       return signal_note

# === 資料來源 ===
from polygon import RESTClient

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
    symbol, direction, signal_type, tick_percentile, trin, latest_rsi, latest_macd,
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
            tick_percentile, trin, latest_rsi, latest_macd, latest_tmo, tmo_slope,
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
        print(f"[DEBUG] 處理中股票：{symbol}")
        client = RESTClient(api_key=API_KEY)
        est = timezone("US/Eastern")
        now = datetime.now(est)
        end = now - timedelta(minutes=15)
        start = end - timedelta(minutes=35)
        print(f"[INFO] 正在抓取延遲15分鐘資料：{symbol} - 時間範圍 {start} ~ {end}")

        aggs = client.get_aggs(
            ticker=symbol,
            multiplier=5,
            timespan="minute",
            from_=start.strftime("%Y-%m-%d"),
            to=end.strftime("%Y-%m-%d"),
            limit=100,
            adjusted=True
        )

        # ✅ 取得 bars 清單
        bars = aggs.results if hasattr(aggs, 'results') else (aggs if isinstance(aggs, list) else None)
        if not bars or not isinstance(bars, list):
            print(f"[WARNING] 無效 bars：{symbol}")
            return None

        cleaned_bars = []

        for bar in bars:
            if hasattr(bar, '__dict__'):
                bar = vars(bar)
            elif not isinstance(bar, dict):
                continue

            time_key = "timestamp" if "timestamp" in bar else ("t" if "t" in bar else None)
            if time_key is None or bar[time_key] is None:
                continue

            bar["timestamp"] = bar[time_key]

            required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
            if not all(field in bar and bar[field] is not None for field in required_fields):
                continue

            cleaned_bars.append(bar)

        if len(cleaned_bars) == 0:
            print(f"[WARNING] 無有效 K 棒資料：{symbol}")
            return None

        # ✅ 建立 DataFrame 並轉換欄位
        df = pd.DataFrame(cleaned_bars)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        if len(df) < 15:
            print(f"[WARNING] {symbol} K線不足（僅 {len(df)} 筆），跳過")
            return None

        return df

    except Exception as e:
        print(f"[ERROR] {symbol} 資料抓取失敗：{e}")
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
    breakout_signal = evaluate_breakout_signal(df)
    if breakout_signal:
        print(f"[BREAKOUT] {symbol}: {breakout_signal}")
        # push_to_discord(symbol, signal_note=breakout_signal)  # 如需推播

    # ⚠️ 多頭預警
    if latest_rsi < 30 and rsi.iloc[-2] < rsi.iloc[-1] and tmo_slope > 0 and latest_price >= latest_vwap * 0.98:
        signal_note = f"⚠️ 預警 - 多頭轉折\n📊 RSI：{latest_rsi:.1f} ↗️\n⚡ TMO：{latest_tmo:.2f} ↗️\n🕯️ K棒：{candle_type}"

    # ⚠️ 空頭預警
    elif latest_rsi > 70 and rsi.iloc[-2] > rsi.iloc[-1] and tmo_slope < 0 and latest_price <= latest_vwap * 1.02:
        signal_note = f"⚠️ 預警 - 空頭轉折\n📊 RSI：{latest_rsi:.1f} ↘️\n⚡ TMO：{latest_tmo:.2f} ↘️\n🕯️ K棒：{candle_type}"

    # 🐸 多頭正式進場
    elif (
        latest_rsi > 30 and rsi.iloc[-2] < rsi.iloc[-1] and
        tmo.iloc[-2] < 0 and latest_tmo > 0 and tmo_slope > 0 and
        latest_price > latest_vwap and volume_ratio > 1.5 and
        ema5_above_20 and candle_type in ['hammer', 'bullish_engulfing'] and
        latest_adx > 20 and latest_plus_di > latest_minus_di
        ):
        signal_note = f"🐸 正式進場 - 多頭\n📊 RSI：{latest_rsi:.1f} ↗️\n⚡ TMO：{latest_tmo:.2f} ↗️\n📈 VWAP：上穿\n🔍 成交量：{volume_ratio:.2f} 倍\n🕯️ K棒：{candle_type}\n📐 ADX：{latest_adx:.1f} | DI+: {latest_plus_di:.1f} > DI-: {latest_minus_di:.1f}"

    if symbol not in entry_price_dict and len(positions_held) < max_positions:
        allocated = total_capital * position_size_pct

        # 若剩餘資金不足，就不進場
        if capital_left < allocated:
            print(f"[SKIP] 資金不足，無法進場：{symbol}")
        else:
            # 記錄進場價格與資金
            entry_price_dict[symbol] = latest_price
            positions_held[symbol] = allocated
            capital_left -= allocated
            entry_direction_dict[symbol] = 'long'

            # 拿 direction 變數出來用
            direction = entry_direction_dict[symbol]
        
            print(f"[ENTRY] 進場：{symbol} @ {latest_price:.2f}，投入資金 ${allocated:.2f}，剩餘資金 ${capital_left:.2f}")
            # ✅ 可選：推播進場訊息
            send_to_discord(
                f"🟢 **[自動進場 - {'多頭' if direction == 'long' else '空頭'}開倉]** {symbol} @ {latest_price:.2f}\n"
                f"📊 RSI: {latest_rsi:.1f} | TMO: {latest_tmo:.2f} | 倍量: {volume_ratio:.2f}x | K棒: {candle_type}\n"
                f"📐 ADX: {latest_adx:.1f} | DI+: {latest_plus_di:.1f} / DI-: {latest_minus_di:.1f}\n"
                f"💰 已分配資金：${allocated:.2f} | 剩餘資金：${capital_left:.2f}\n"
                f"🕑 類型：✅進場完成"
            )
        
    # 🐶 空頭正式進場
    elif (
        latest_rsi < 70 and rsi.iloc[-2] > rsi.iloc[-1] and
        tmo.iloc[-2] > 0 and latest_tmo < 0 and tmo_slope < 0 and
        latest_price < latest_vwap and volume_ratio > 1.5 and
        ema5_below_20 and candle_type in ['gravestone_doji', 'bearish_engulfing'] and
        latest_adx > 20 and latest_minus_di > latest_plus_di
        ):
        signal_note = f"🐶 正式進場 - 空頭\n📊 RSI：{latest_rsi:.1f} ↘️\n⚡ TMO：{latest_tmo:.2f} ↘️\n📉 VWAP：跌破\n🔍 成交量：{volume_ratio:.2f} 倍\n🕯️ K棒：{candle_type}\n📐 ADX：{latest_adx:.1f} | DI-: {latest_minus_di:.1f} > DI+: {latest_plus_di:.1f}"

    if latest_macd < 0 and latest_price < latest_vwap and volume_ratio > 1.5:
        signal_note = "🐶 正式進場 - 空頭"

        # ✅ 空頭模擬進場（與多頭邏輯相同，只是方向不同）
        if symbol not in entry_price_dict and len(positions_held) < max_positions:
            allocated = total_capital * position_size_pct

            if capital_left < allocated:
                print(f"[SKIP] 資金不足，無法進場：{symbol}")
            else:
                entry_price_dict[symbol] = latest_price
                positions_held[symbol] = allocated
                capital_left -= allocated
                entry_direction_dict[symbol] = 'short'

                # 拿 direction 變數出來用
                direction = entry_direction_dict[symbol]

                print(f"[ENTRY] 空頭進場：{symbol} @ {latest_price:.2f}，投入資金 ${allocated:.2f}，剩餘資金 ${capital_left:.2f}")
            
                # ✅ 推播空頭進場訊息
                send_to_discord(
                    f"🟢 **[自動進場 - {'多頭' if direction == 'long' else '空頭'}開倉]** {symbol} @ {latest_price:.2f}\n"
                    f"📊 RSI: {latest_rsi:.1f} | TMO: {latest_tmo:.2f} | 倍量: {volume_ratio:.2f}x | K棒: {candle_type}\n"
                    f"📐 ADX: {latest_adx:.1f} | DI+: {latest_plus_di:.1f} / DI-: {latest_minus_di:.1f}\n"
                    f"💰 已分配資金：${allocated:.2f} | 剩餘資金：${capital_left:.2f}\n"
                    f"🕑 類型：✅進場完成"
                )

    # ✅ 如果有訊號但沒進場，也發送預警推播
    if should_push_signal(signal_note, entry_price_dict, symbol):
        send_to_discord(
            f"🟡 **[策略訊號 - 多頭準備]** {symbol} @ {latest_price:.2f}\n"
            f"📊 RSI: {latest_rsi:.1f} | TMO: {latest_tmo:.2f} | 倍量: {volume_ratio:.2f}x | K棒: {candle_type}\n"
            f"📐 ADX: {latest_adx:.1f} | DI+: {latest_plus_di:.1f} / DI-: {latest_minus_di:.1f}\n"
            f"🕑 類型：⚠️訊號通知（尚未進場）"
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
total_capital = 100000
position_size_pct = 0.05
max_positions = 5
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
            latest_macd=None,
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
        return None
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
    tick_percentile = get_tick_percentile(tick_series)
    tick_slope = get_tick_slope(tick_series)
    trin_value = get_trin_value()
    
    print("=" * 50)
    print(f"[INFO] TICK 百分位：{tick_percentile} | 斜率：{tick_slope} | TRIN：{trin_value}")
    print("=" * 50)

    # === Step 0.5: 推播大盤潛伏訊號（不影響個股邏輯）===
    check_market_latent_signals(tick_percentile, tick_slope, trin_value)


       # === Step 1: 開始個股掃描 ===
       stock_list = load_stock_list(STOCK_LIST_CSV)
       uccess_count = 0
       fail_count = 0

       for symbol in stock_list:
           df = fetch_stock_data(symbol)

           if df is None or df.empty or 'close' not in df.columns:
               print(f"[WARNING] {symbol} 無效 df，跳過")
               fail_count += 1
               continue

    # 最新價格
    latest_price = df['close'].iloc[-1]
        # === Step 2: 技術指標計算 ===
        from ta.momentum import RSIIndicator
        from ta.trend import EMAIndicator
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

        # === Step 3: 判斷進場條件 ===
        signal_note = None
        direction = None

        # === Step 3: 潛伏訊號偵測 + 推播 ===
        signal_note = detect_latent_signal(df, rsi, tmo, obv, latest_price, latest_vwap)

        if signal_note:
            message = (
                f"{signal_note} {symbol}\n"
                f"收盤：{latest_price:.2f}｜RSI: {latest_rsi:.1f}｜TMO: {latest_tmo:.2f}｜"
                f"VWAP: {latest_vwap:.2f}｜量：{volume_ratio:.2f}x"
            )
            send_to_discord(message)

        # 🐸 多頭訊號：符合多項條件
        if latest_rsi < 30 and latest_price > latest_vwap and tmo_cross and volume_ratio > 1.5 and candle_type == "陽線":
            signal_note = "🐸 正式進場 - 多頭"
            direction = 'long'

        # 🐶 空頭訊號（你可以另外定義條件）
        elif latest_rsi > 70 and latest_price < latest_vwap and latest_tmo < 0 and volume_ratio > 1.5 and candle_type == "陰線":
            signal_note = "🐶 正式進場 - 空頭"
            direction = 'short'

        # === Step 4: 模擬進場 ===
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
        if symbol in entry_price_dict and symbol in entry_direction_dict:
            entry_price = entry_price_dict[symbol]
            direction = entry_direction_dict[symbol]

            if direction == 'long':
                pnl = (latest_price - entry_price) / entry_price
            elif direction == 'short':
                pnl = (entry_price - latest_price) / entry_price
            else:
                pnl = 0

            if pnl >= 0.05:
                send_to_discord(f"🎯 **[停利出場]** {symbol} | 報酬：+{pnl*100:.2f}%")
                capital_left += positions_held[symbol]

                # ✅ 出場寫入紀錄
                write_to_sheet(
                    symbol=symbol,
                    direction=direction,
                    pnl=pnl,
                    entry_price=entry_price,
                    exit_price=latest_price,
                    volume_ratio=volume_ratio,
                    rsi=latest_rsi,
                    tmo=latest_tmo,
                    candle_type=candle_type,
                    remark="停利出場"
                )

                del entry_price_dict[symbol]
                del positions_held[symbol]
                del entry_direction_dict[symbol]
            elif pnl <= -0.02:
                send_to_discord(f"🛑 **[停損出場]** {symbol} | 報酬：{pnl*100:.2f}%")
                capital_left += positions_held[symbol]

                write_to_sheet(
                    symbol=symbol,
                    direction=direction,
                    pnl=pnl,
                    entry_price=entry_price,
                    exit_price=latest_price,
                    volume_ratio=volume_ratio,
                    rsi=latest_rsi,
                    tmo=latest_tmo,
                    candle_type=candle_type,
                    remark="停損出場"
                )

                del entry_price_dict[symbol]
                del positions_held[symbol]
                del entry_direction_dict[symbol]
            success_count += 1
            # 可加入推播 / 儲存 / 分類
        else:
            fail_count += 1

    print(f"\n[統計] 本輪成功 {success_count} 檔，失敗 {fail_count} 檔，有效率：{round(success_count / (success_count + fail_count + 1e-6) * 100, 2)}%")

# ✅ 主程式入口
if __name__ == "__main__":
    tick_series = get_tick_series()

    if tick_series is not None and not tick_series.empty:
        tick_percentile = get_tick_percentile(tick_series)
        print(f"[INFO] 當前 TICK 百分位：{tick_percentile:.2f}")
    else:
        tick_percentile = None
        print("[WARNING] tick_series 是空的，跳過 tick 百分位計算")

    run_scanner(tick_series)  # ✅ 呼叫在最後執行
