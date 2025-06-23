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

entered_positions = {}  # ✅ 用來記錄哪些股票已建倉，避免重複
API_KEY = os.getenv("POLYGON_API_KEY") or "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"
STOCK_LIST_CSV = "filtered_us_stocks_common_only.csv"
WEBHOOK_URL = "https://discord.com/api/webhooks/1385222120321187850/_qzr0Jq0JP7WtXRFHQcs-l0-kzYg0k6GjrT4J2V8mf9zWqaMFw9SZMbtJsIt7LGOptI6"

# === 🧠 交易資金設定 ===
TOTAL_CAPITAL = 1_000_000             # 初始總資金（單位：美元）
POSITION_RATIO = 0.05                 # 每次進場佔總資金 5%
MAX_PER_POSITION = 6_000              # 單檔最大投入資金
MAX_ACTIVE_POSITIONS = 10             # 最多同時持有 10 檔
capital_left = TOTAL_CAPITAL          # 當前剩餘資金
positions = {}                  # 持倉記錄：symbol -> {'entry_price', 'shares', 'entry_time'}

def can_enter_new_position(symbol, capital_required):
    # 已經持有該股票
    if symbol in positions:
        return False
    # 同時持股超限
    if len(positions) >= MAX_ACTIVE_POSITIONS:
        print(f"[資金控管] 持股達上限（{MAX_ACTIVE_POSITIONS} 檔），跳過 {symbol}")
        return False
    # 單檔超過最大投入
    if capital_required > MAX_PER_POSITION:
        print(f"[資金控管] 單檔超出上限 $6000：{symbol}")
        return False
    # 資金不足
    if capital_required > capital_left:
        print(f"[資金控管] 資金不足，無法進場 {symbol}")
        return False
    return True

# === 🛡️ 出場風控參數（含三段鎖利）===
TRAIL_TRIGGER = 0.03            # +3% 啟動移動停利
TRAIL_MARGIN = 0.015            # 回落 1.5% 停利出場
DEFAULT_STOP_LOSS = 0.02        # -2% 強制停損
DEFAULT_TAKE_PROFIT = 0.05      # +5% 預設停利

def write_trade_to_sheet(strategy_type, symbol, direction, entry_price, shares,
                         invested_capital, rsi, zscore, roc, obv, vwap,
                         confidence_score, signal_note, sheet_webhook_url):
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_today = datetime.now().strftime("%Y-%m-%d")

    payload = {
        "action": "append",
        "strategy": strategy_type,
        "symbol": symbol,
        "direction": direction,
        "price": entry_price,
        "shares": shares,
        "capital": invested_capital,
        "rsi": round(rsi, 2),
        "zscore": round(zscore, 2),
        "roc": round(roc, 2),
        "obv": int(obv),
        "vwap": round(vwap, 2),
        "confidence_score": round(confidence_score, 2),
        "signal_note": signal_note,
        "datetime": now,
        "date": date_today,
        # 新增這三項（如果是出場紀錄才會帶入）
        "return_rate": locals().get("return_rate", ""),
        "holding_minutes": locals().get("holding_minutes", ""),
        "pnl": locals().get("profit_loss_amount", "")   
            }

    try:
        response = requests.post(sheet_webhook_url, json=payload)
        if response.status_code == 200:
            print(f"[✅] 已寫入 Google Sheets：{symbol} - {strategy_type}")
        else:
            print(f"[⚠️] 寫入失敗 {symbol}：{response.status_code}, {response.text}")
    except Exception as e:
        print(f"[❌] Sheets 寫入錯誤 {symbol}：{e}")

def update_exit_data_to_sheet(symbol, entry_time, return_rate, pnl, holding_minutes):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = get_credentials_from_base64("GCP_KEY_BASE64")
    client = gspread.authorize(creds)

    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit")
    ws = sheet.worksheet("交易記錄")

    all_records = ws.get_all_records()
    target_row = None

    for idx, row in enumerate(all_records, start=2):  # 從第2列開始（第1列是欄位）
        if row['symbol'] == symbol and row['return_rate'] == "":
            target_row = idx
            break

    if target_row:
        ws.update_cell(target_row, 15, round(return_rate, 2))      # O欄：報酬率
        ws.update_cell(target_row, 16, holding_minutes)            # P欄：持倉時間
        ws.update_cell(target_row, 17, round(pnl, 2))              # Q欄：損益金額
        print(f"[✅] 出場資訊已更新：{symbol}")
    else:
        print(f"[⚠️] 找不到對應的建倉紀錄：{symbol}")

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

    # 設定當天交易時段（09:30～16:00）
    market_open = est.localize(datetime.combine(now_est.date(), dtime(9, 30)))
    market_close = est.localize(datetime.combine(now_est.date(), dtime(16, 0)))
    now = datetime.now(est)

    # 預設抓今天最新資料區間（往前 250 分鐘 = 約 30 根）
    end_time = now
    start_time = now - timedelta(minutes=5 * 50)

    if now_est > market_close:
        start_time = market_open
        end_time = market_close

    elif now_est < market_open:
        print(f"[補資料] 當前時間為盤前，改抓上一個交易日")
        prev_day = now_est.date() - timedelta(days=1)
        while prev_day.weekday() >= 5:
            prev_day -= timedelta(days=1)
        start_time = est.localize(datetime.combine(prev_day, dtime(9, 30)))
        end_time = est.localize(datetime.combine(prev_day, dtime(16, 0)))

    from_ts = int(start_time.timestamp() * 1000)
    to_ts = int(end_time.timestamp() * 1000)

    print(f"[DEBUG] 抓取 {symbol} 15 分K：{start_time} → {end_time}")

    try:
        client = RESTClient(api_key=api_key)

        # 初始抓取
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

        df_all = pd.DataFrame([{
            "timestamp": bar.timestamp,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        } for bar in bars])

        print(f"[DEBUG] {symbol} 初始抓到 {len(df_all)} 根")

        # 自動補抓，直到湊滿 30 根（往前最多抓 5 個交易日）
        retry_days = 0
        prev_day = start_time.date()
        while len(df_all) < 30 and retry_days < 5:
            retry_days += 1
            prev_day -= timedelta(days=1)
            while prev_day.weekday() >= 5:
                prev_day -= timedelta(days=1)

            start_time = est.localize(datetime.combine(prev_day, dtime(9, 30)))
            end_time = est.localize(datetime.combine(prev_day, dtime(16, 0)))
            from_ts = int(start_time.timestamp() * 1000)
            to_ts = int(end_time.timestamp() * 1000)

            print(f"[補抓] {symbol} 第 {retry_days} 天 ➜ {start_time} → {end_time}")

            bars_retry = client.get_aggs(
                ticker=symbol,
                multiplier=5,
                timespan="minute",
                from_=from_ts,
                to=to_ts,
                limit=100,
                adjusted=True
            )

            if bars_retry:
                df_retry = pd.DataFrame([{
                    "timestamp": bar.timestamp,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume
                } for bar in bars_retry])

                if not df_retry.empty:
                    df_all = pd.concat([df_retry, df_all], ignore_index=True)
                    print(f"[補抓] 累積筆數：{len(df_all)}")
            else:
                print(f"[補抓] 第 {retry_days} 天無資料，繼續")

        if len(df_all) < 30:
            print(f"[❌終止] {symbol} 最終仍不足 30 根（僅 {len(df_all)}），跳過")
            return None

        print(f"[✅完成] {symbol} 資料總筆數：{len(df_all)}")

        # 整理格式
        df_all["timestamp"] = pd.to_datetime(df_all["timestamp"], unit="ms")
        df_all.set_index("timestamp", inplace=True)
        df_all.sort_index(inplace=True)

        return df_all

    except Exception as e:
        print(f"[❌錯誤] 抓取 {symbol} 失敗：{e}")
        return None
        
def detect_mean_reversion_signals(df, symbol):
    if len(df) < 30:
        return None, None

    ind = calculate_indicators(df)
    latest_price = df['close'].iloc[-1]
    latest_rsi = ind['rsi'].iloc[-1]
    prev_rsi = ind['rsi'].iloc[-2]
    zscore = ind['zscore'].iloc[-1]
    ema5 = ind['ema_5'].iloc[-1]
    ema20 = ind['ema_20'].iloc[-1]
    lower_band = ind['lower_band'].iloc[-1]
    upper_band = ind['upper_band'].iloc[-1]

    # ✅ 多單均值回歸條件
    if (
        latest_price < lower_band and
        latest_rsi > prev_rsi and latest_rsi < 35 and
        zscore < -2 and
        ema5 > ema20
    ):
        note = "📈 多單均值回歸：跌破布林下緣 + RSI 回升 + Z-score 偏低 + EMA多方\n🔎 大盤盤整中，啟動均值回歸判斷"
        return "BUY", note

    # ✅ 空單均值回歸條件
    elif (
        latest_price > upper_band and
        latest_rsi < prev_rsi and latest_rsi > 65 and
        zscore > 2 and
        ema5 < ema20
    ):
        note = "📉 空單均值回歸：突破布林上緣 + RSI 轉弱 + Z-score 偏高 + EMA空方\n🔎 大盤盤整中，啟動均值回歸判斷"
        return "SELL", note
    
    # ⚠️ 潛伏多單預警條件
    elif (
        latest_price < lower_band * 1.01 and
        latest_rsi < 40 and
        zscore < -1.5 and
        ema5 > ema20 * 0.98
    ):
        note = "⚠️ 潛伏多頭：貼近布林下緣 + RSI 低位 + Z-score 偏低 + EMA即將金叉"
        return "ALERT_BUY", note

    # ⚠️ 潛伏空單預警條件
    elif (
        latest_price > upper_band * 0.99 and
        latest_rsi > 60 and
        zscore > 1.5 and
        ema5 < ema20 * 1.02
    ):
        note = "⚠️ 潛伏空頭：接近布林上緣 + RSI 高位 + Z-score 偏高 + EMA即將死叉"
        return "ALERT_SELL", note

    # ❗無訊號則明確回傳 None, None

    return None, None

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

def compute_confidence_score(rsi, roc, obv, vwap, ema5, ema20):
    score = 0

    # RSI 越接近低位反彈越加分
    if rsi < 30:
        score += 0.3
    elif rsi < 40:
        score += 0.2
    elif rsi < 50:
        score += 0.1

    # ROC 上升加分
    if roc > 1:
        score += 0.3
    elif roc > 0:
        score += 0.2

    # OBV 增加加分
    if obv > 0:
        score += 0.2

    # EMA 趨勢加分
    if ema5 > ema20:
        score += 0.2

    # VWAP 趨勢確認
    if abs(vwap) < 1.0:  # 貼近 VWAP
        score += 0.1

    return min(score, 1.0)  # 上限 1.0

# === 3. 訊號判斷邏輯（多空建倉，無預警） ===

def detect_trading_signal(symbol, df, indicators):  # ✅ 有 symbol 參數
    latest_price = df['close'].iloc[-1]
    rsi = indicators['rsi'].iloc[-1]
    roc = indicators['roc'].iloc[-1]
    obv = indicators['obv'].iloc[-1]
    vwap = indicators['vwap'].iloc[-1]
    zscore = indicators['zscore'].iloc[-1]

    signal_type = None
    signal_note = None

    # 排除 RSI 半山腰
    in_neutral_zone = 45 <= rsi <= 65
    if in_neutral_zone:
        return None, None

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

    # === 📉 都沒觸發建倉條件，這裡補上調試輸出
    if signal_type is None:
        obv_change = obv - indicators['obv'].iloc[-2]
        vwap_deviation = (abs(latest_price - vwap) / vwap) * 100
        zscore = indicators['zscore'].iloc[-1]
        lower_band = indicators['lower_band'].iloc[-1]
        bb_diff = (latest_price - lower_band) / lower_band * 100
        ema5 = indicators['ema_5'].iloc[-1]
        ema20 = indicators['ema_20'].iloc[-1]
        ema_diff = ema5 - ema20

        print(f"[調試] {symbol} 未觸發建倉條件 ➜ 價格={latest_price:.2f}, RSI={rsi:.1f}, ROC={roc:.2f}, OBV變化={obv_change:.2f}, VWAP乖離={vwap_deviation:.2f}%")
        print(f"[補充] Z-score={zscore:.2f}, 跌破布林下緣={bb_diff:.2f}%, EMA差={ema_diff:.2f}")
        print(f"[判斷] {symbol} 訊號：{signal_type}, 說明：{signal_note}")
        return signal_type, signal_note
# === 5. 推播模組（Discord） ===

def push_entry_to_discord(symbol, direction, price, signal_note, zscore=None, rsi=None, strategy=None):
    emoji = "🐸" if direction == "多" else "🐶"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    capital_used = TOTAL_CAPITAL * POSITION_SIZE
    quantity = int(capital_used // price)

    content = f"{emoji} **[建倉訊號 - {direction}單]** {symbol}\n" \
              f"💵 價格：${price:.2f}｜方向：{direction}\n" \
              f"📈 資金投入：${capital_used:.2f}｜股數：約 {quantity} 股\n"

    # ✅ 均值回歸策略才顯示 Z-score
    if strategy == "均值回歸策略" and zscore is not None:
        label = "超跌" if zscore < -2 else "超漲" if zscore > 2 else "偏離中"
        content += f"📊 Z-score：{zscore:.2f}（{label}）\n"

    if rsi is not None:
        content += f"📉 RSI：{rsi:.1f}\n"

    # ✅ 顯示策略名稱（不論是哪種策略都會顯示）
    if strategy:
        content += f"🎯 策略名稱：{strategy}\n"

    content += f"📌 條件說明：{signal_note}\n" \
               f"🕒 時間：{time_str}"

    try:
        requests.post(webhook_url, json={"content": content})
    except Exception as e:
        print(f"[EXCEPTION] Discord 推播錯誤：{e}")

def enter_position(symbol, price, direction, signal_note, rsi=None, zscore=None):
    global capital_left

    # ✅ 避免重複建倉
    if symbol in entered_positions:
        print(f"[跳過] {symbol} 已建倉，略過重複進場")
        return

    capital_used = TOTAL_CAPITAL * POSITION_SIZE
    quantity = int(capital_used // price)
    
    if quantity <= 0:
        print(f"[跳過] {symbol} 價格過高，無法建倉")
        return

    now = datetime.now()

    # ✅ 建倉記錄
    positions[symbol] = {
        "direction": direction,
        "entry_price": price,
        "shares": quantity,
        "entry_time": now,
        "capital_used": capital_used,
        "sell_stage": 0,
        "max_gain": 0.0,
        "strategy": "均值回歸"
    }
    entered_positions[symbol] = {
        "price": price,
        "direction": direction,
        "entry_time": now
    }

    capital_left -= capital_used

    print(f"[ENTRY] 建倉 {symbol} {direction}單，價格={price:.2f}，股數={quantity}，投入資金=${capital_used:.2f}")

    # ✅ 推播訊息
    emoji = "🐸" if direction == "多" else "🐶"
    msg = (
        f"{emoji} **[建倉 - {direction}單]** {symbol}\n"
        f"📌 策略：🎯 均值回歸策略\n"
        f"💵 價格：${price:.2f}｜方向：{direction}\n"
        f"📈 投入：${capital_used:,.2f}｜約 {quantity} 股\n"
    )
    if zscore is not None:
        msg += f"📊 Z-score：{zscore:.2f}（{'超跌' if zscore < -2 else '超漲' if zscore > 2 else '偏離中'}）\n"
    if isinstance(rsi, pd.Series):
        rsi = rsi.iloc[-1]
    if rsi is not None and pd.notna(rsi):
        msg += f"📉 RSI：{rsi:.1f}\n"
    if ema5 is not None and ema20 is not None:
        cross_label = "黃金交叉" if ema5 > ema20 else "死亡交叉"
        msg += f"📐 EMA：5日={ema5:.2f}｜20日={ema20:.2f}（{cross_label}）\n"
    if bb_upper is not None and bb_lower is not None and bb_middle is not None:
        msg += f"📉 布林通道：上軌={bb_upper:.2f}｜中軌={bb_middle:.2f}｜下軌={bb_lower:.2f}\n"

    msg += f"🧠 條件：{signal_note}\n" \
           f"🕒 時間：{now.strftime('%Y-%m-%d %H:%M:%S')}"
    
    print(f"[推播訊息]\n{msg}")
    try:
        requests.post(WEBHOOK_URL, json={"content": msg})
    except Exception as e:
        print(f"[EXCEPTION] Discord 推播錯誤：{e}")

    # ✅ 判斷策略類型：均值回歸 or RROV
    strategy_type = "均值回歸" if "布林" in signal_note or "Z-score" in signal_note else "RROV"

    # ✅ 寫入 Google Sheets（這段一定要在 def 裡面縮排）
    try:
        write_trade_to_sheet(
            strategy_type=strategy_type,
            symbol=symbol,
            direction=direction,
            entry_price=price,
            shares=quantity,
            invested_capital=capital_used,
            rsi=rsi if not isinstance(rsi, pd.Series) else rsi.iloc[-1],
            zscore=zscore if zscore is not None else 0,
            roc=roc if 'roc' in locals() else 0,
            obv=obv if 'obv' in locals() else 0,
            vwap=vwap if 'vwap' in locals() else 0,
            confidence_score=confidence_score if 'confidence_score' in locals() else 0.5,
            signal_note=signal_note,
            sheet_webhook_url="https://script.google.com/macros/s/AKfycbw1XkrMXXS0dPKu1Elok9LUJIgYMkpBh4NtbfIVYIyK0b_TiycsxF7TJoWNql0b-wAj/exec"
        )
    except Exception as e:
        print(f"[EXCEPTION] Sheets 寫入錯誤：{e}")

def push_exit_to_discord(symbol, direction, entry_price, exit_price, return_rate, shares, reason):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    strategy = positions[symbol].get("strategy", "未標記策略")  # 取出策略名稱

    emoji = "🐸" if direction == "多" else "🐶"

    msg = f"""{emoji} **[出場 - {direction}單]** {symbol}
📌 策略：{'🎯 均值回歸策略' if strategy == '均值回歸' else '📊 RROV 策略'}
💵 出場價格：${exit_price:.2f}｜進場價格：${entry_price:.2f}
📊 報酬率：{return_rate:.2%}｜股數：{shares}
🔄 出場原因：{reason}
🕒 時間：{now}"""

    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
    except Exception as e:
        print(f"[EXCEPTION] 出場推播錯誤：{e}")

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
    profit_dollar = abs(exit_qty * (latest_price - entry_price)) if direction == "多" else abs(exit_qty * (entry_price - latest_price))
    # ✅ 回收資金
    capital_left += latest_price * exit_qty
    pos["quantity"] -= exit_qty
    pos["sell_stage"] = sell_stage

    # ✅ 👇 這裡加 Console 印出紀錄
    print(f"[EXIT] {symbol} 出場 {direction}單，數量={exit_qty}，價格={latest_price:.2f}，報酬率={return_rate*100:.2f}%")


    # ✅ 推播出場訊息
    emoji = "✅" if return_rate >= 0 else "⚠️"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ✅ 🔽 插在這裡！
    strategy_key = pos.get("strategy", "一般策略")
    if strategy_key == "均值回歸":
        strategy_name = "🎯 均值回歸策略"
    elif strategy_key == "RROV":
        strategy_name = "📊 RROV 策略"
    else:
        strategy_name = "📌 未知策略"

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

            # === 1. 抓資料
            df = fetch_stock_data(symbol, POLYGON_API_KEY)
            if df is None or len(df) < 30:
                print(f"[跳過] {symbol} 資料不足")
                continue

            # === 2. 技術指標計算
            indicators = calculate_indicators(df)
            latest_price = df['close'].iloc[-1]

            # === ✅ 均值回歸策略建倉判斷（放這裡）======================
            signal_type1, signal_note1 = detect_mean_reversion_signals(df, symbol)

            # === ⚠️ 若為潛伏預警，只推播不建倉
            if signal_type1 in ["ALERT_BUY", "ALERT_SELL"]:
                push_to_discord(
                    symbol=symbol,
                    price=latest_price,
                    rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    obv_change=indicators['obv'].diff().iloc[-1],
                    vwap_deviation=(latest_price - indicators['vwap'].iloc[-1]) / indicators['vwap'].iloc[-1] * 100,
                    ema_diff=indicators['ema_5'].iloc[-1] - indicators['ema_20'].iloc[-1],
                    zscore=indicators['zscore'].iloc[-1],
                    signal_type=signal_type1,
                    signal_note=signal_note1
                )
                continue  # ✅ 只推播，跳過建倉處理

            if signal_type1:
                direction = "多" if signal_type1 == "BUY" else "空"
                confidence_score = compute_confidence_score(
                    rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    obv=indicators['obv'].diff().iloc[-1],
                    vwap=indicators['vwap'].iloc[-1],
                    ema5=indicators['ema_5'].iloc[-1],
                    ema20=indicators['ema_20'].iloc[-1],
                    zscore=indicators['zscore'].iloc[-1]
                )


                capital_required = min(TOTAL_CAPITAL * POSITION_RATIO, MAX_PER_POSITION)
                shares = int(capital_required / latest_price)

                if can_enter_new_position(symbol, capital_required):
                    enter_position(
                        symbol=symbol,
                        price=latest_price,
                        shares=shares,
                        direction=direction,
                        signal_note=signal_note1,
                        rsi=indicators['rsi'].iloc[-1],
                        zscore=indicators['zscore'].iloc[-1],
                        strategy="均值回歸策略",
                        confidence=confidence_score
                    )
                continue  # ✅ 若已建倉就跳過 RROV 判斷

            # === ✅ RROV策略建倉（保留）
            signal_type2, signal_note2 = detect_trading_signal(symbol, df, indicators)
            if signal_type2:
                direction = "多" if signal_type2 == "BUY" else "空"
                confidence_score = compute_confidence_score(
                    rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    obv=indicators['obv'].diff().iloc[-1],
                    vwap=indicators['vwap'].iloc[-1],
                    ema5=indicators['ema_5'].iloc[-1],
                    ema20=indicators['ema_20'].iloc[-1]
                )

                capital_required = min(TOTAL_CAPITAL * POSITION_RATIO, MAX_PER_POSITION)
                shares = int(capital_required / latest_price)

                if can_enter_new_position(symbol, capital_required):
                    enter_position(
                        symbol=symbol,
                        price=latest_price,
                        shares=shares,
                        direction=direction,
                        signal_note=signal_note2,
                        rsi=indicators['rsi'].iloc[-1],
                        zscore=indicators['zscore'].iloc[-1],
                        strategy="RROV策略",
                        confidence=confidence_score
                    )

            # === 3. 出場邏輯
            if symbol in positions:
                check_exit_and_notify(symbol, latest_price)

        except Exception as e:
            print(f"[錯誤] {symbol} 掃描錯誤：{e}")


def push_to_discord(symbol, price, rsi, vwap, volume_ratio, ema_cross, kd_status, candle_type, signal_note):
    try:
        vwap_text = f"{vwap:.2f}" if vwap is not None and not pd.isna(vwap) else "無"
        message = (
            f"📣 **[訊號]** {symbol}\n"
            f"💰 價格：${price:.2f} | RSI：{rsi:.1f}\n"
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
            rsi=rsi,
            strategy="均值回歸策略"  # ✅ 加這行！
        )
        return True
    return False
    
def main_loop():
    while True:
        symbol_list = load_stock_list()  # 確保這是回傳股票代碼清單的函數
        scan_market(symbol_list)
        time.sleep(60)

# === ✅ 程式啟動測試推播 ===
try:
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    test_msg = f"✅ **[程式啟動通知]**\n📢 已成功啟動交易掃描系統\n🕒 時間：{now}"
    print(f"[啟動] {test_msg}")
    requests.post(WEBHOOK_URL, json={"content": test_msg})
except Exception as e:
    print(f"[EXCEPTION] Discord 測試推播錯誤：{e}")

# ✅ 主程式區（放最外層）
if __name__ == "__main__":
    main_loop()
