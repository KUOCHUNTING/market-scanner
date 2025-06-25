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
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import base64
import json

def get_credentials_from_base64(env_var_key):
    base64_key = os.getenv(env_var_key)
    if not base64_key:
        raise ValueError("Google Sheets 金鑰尚未設定")
    json_data = base64.b64decode(base64_key).decode('utf-8')
    return ServiceAccountCredentials.from_json_keyfile_dict(json.loads(json_data), [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ])

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
POLYGON_API_KEY = "3Oa52hFieaUvTyToZudJanq39Rw9zApi"
STOCK_LIST_CSV = "filtered_us_stocks_common_only.csv"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1387445157221240934/7r4YYzzJYOEIJxCN-OIQ_rIhnOL3EU7Tl7KdNEfsdkxEqMUSya5k6iLn4kZDYH8piOv1")

# === 🧠 交易資金設定 ===
TOTAL_CAPITAL = 1_000_000             # 初始總資金（單位：美元）
POSITION_RATIO = 0.05                 # 每次進場佔總資金 5%
MAX_PER_POSITION = 6_000              # 單檔最大投入資金
MAX_ACTIVE_POSITIONS = 10             # 最多同時持有 10 檔
capital_left = TOTAL_CAPITAL          # 當前剩餘資金
positions = {}                  # 持倉記錄：symbol -> {'entry_price', 'shares', 'entry_time'}

# ===== 工具函數：計算策略達成率 =====================
def get_strategy_match_score(strategy_name, conditions_dict):
    satisfied = sum(1 for v in conditions_dict.values() if v)
    total = len(conditions_dict)
    return satisfied / total

def push_to_discord(
    symbol,
    price,
    rsi,
    roc,
    vwap,
    volume_ratio,
    ema_cross="N/A",
    kd_status="N/A",
    candle_type="N/A",
    signal_type=None,
    signal_note=None,
    confidence_score=None,
    direction=None,
    strategy_name="RROV策略",
    zscore=None,
    obv=None,
    obv_change=None,
    vwap_deviation=None,
    bb_deviation=None
):
    import requests
    from datetime import datetime

    # ✅ Discord Webhook URL（請依需求替換）
    webhook_url = "https://discord.com/api/webhooks/1387445157221240934/7r4YYzzJYOEIJxCN-OIQ_rIhnOL3EU7Tl7KdNEfsdkxEqMUSya5k6iLn4kZDYH8piOv1"

    # ✅ Emoji 標記（方向）
    emoji = "🐸" if direction == "多" else "🐶"

    # ✅ 格式保險（避免 NoneType）
    price_text = f"${price:.2f}" if price is not None else "N/A"
    rsi_text = f"{rsi:.1f}" if rsi is not None else "N/A"
    roc_text = f"{roc:.2f}" if roc is not None else "N/A"
    vwap_text = f"{vwap:.2f}" if vwap is not None else "N/A"
    zscore_text = f"{zscore:.2f}" if zscore is not None else "N/A"
    obv_text = f"{int(obv):,}" if obv is not None else "N/A"
    obvchg_text = f"{obv_change:.1f}" if obv_change is not None else "N/A"
    vwdev_text = f"{vwap_deviation:.1f}%" if vwap_deviation is not None else "N/A"
    bbdev_text = f"{bb_deviation:.1f}%" if bb_deviation is not None else "N/A"
    conf_text = f"{confidence_score:.2f}" if confidence_score is not None else "N/A"

    # ✅ 推播內容組合
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"{emoji} **[{strategy_name}]** {symbol}｜{signal_note}\n"
    content += f"🕒 {time_str}｜方向：{direction}\n"
    content += f"💵 價格：{price_text}｜RSI：{rsi_text}｜ROC：{roc_text}｜Z-score：{zscore_text}\n"
    content += f"📊 VWAP：{vwap_text}｜VWAP乖離：{vwdev_text}｜布林乖離：{bbdev_text}\n"
    content += f"📈 OBV：{obv_text}（變化：{obvchg_text}）｜成交量倍數：{volume_ratio:.1f}\n"
    content += f"🔀 EMA交叉：{ema_cross}｜KD：{kd_status}｜K棒：{candle_type}\n"
    content += f"🤖 信心分數：{conf_text}"

    # ✅ 發送到 Discord
    try:
        data = {"content": content}
        response = requests.post(webhook_url, json=data)
        if response.status_code == 204:
            print(f"[✅推播成功] {symbol} ➜ {signal_type}")
        else:
            print(f"[⚠️推播失敗] 狀態碼：{response.status_code}，回應：{response.text}")
    except Exception as e:
        print(f"[錯誤] Discord 推播失敗：{e}")

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

        # ✅ 加入這段：去除 volume 為 None 或為 0 的資料
        df_all = df_all.dropna(subset=["close", "volume"])
        df_all = df_all[df_all["volume"] > 0]

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

                # ✅ 補抓資料也要清洗掉缺失或 0 值
                df_retry = df_retry.dropna(subset=["close", "volume"])
                df_retry = df_retry[df_retry["volume"] > 0]

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
    

import traceback

def scan_market(symbol_list):
    for symbol in symbol_list:
        try:
            print(f"📡 掃描中：{symbol}")

            # === 1. 抓資料
            df = fetch_stock_data(symbol, POLYGON_API_KEY)
            if df is None or len(df) < 27:
                print(f"[跳過] {symbol} 資料不足")
                continue

            print(f"[DEBUG] {symbol} 欄位：{df.columns.tolist()}")

            # === 2. 技術指標
            indicators = calculate_indicators(df)
            latest_price = df['close'].iloc[-1]

            rsi = indicators['rsi'].iloc[-1]
            roc = indicators['roc'].iloc[-1]
            obv = indicators['obv'].iloc[-1]
            zscore = indicators['zscore'].iloc[-1]
            vwap = indicators['vwap'].iloc[-1]
            ema5 = indicators['ema_5'].iloc[-1]
            ema20 = indicators['ema_20'].iloc[-1]

            # === 3. 防呆處理
            try:
                obv_diff = indicators['obv'].diff().iloc[-1]
            except:
                obv_diff = 0

            if vwap != 0:
                vwap_deviation = (latest_price - vwap) / vwap * 100
            else:
                vwap_deviation = None

            # 可選：volume_ratio 也可防呆
            try:
                volume_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
            except:
                volume_ratio = 1

            # === 4. 顯示資訊
            direction = "🟢 偏多" if rsi < 60 and zscore < 1 else "🔴 偏空"
            print(f"[資訊] {direction}|{symbol} ➜ 價格=${latest_price:.2f}|RSI={rsi:.1f}|ROC={roc:.2f}|OBV={int(obv):,}|VWAP={vwap:.2f}|Z-score={zscore:.2f}|EMA5={ema5:.2f}|EMA20={ema20:.2f}")

            # === 5. 策略判斷與推播
            signal_type, signal_note = detect_trading_signal(symbol, df, indicators, debug=True)
            if signal_type:
                push_to_discord(
                    symbol=symbol,
                    price=latest_price,
                    rsi=rsi,
                    roc=roc,
                    vwap=vwap,
                    volume_ratio=volume_ratio,
                    ema_cross=indicators.get('ema_status', 'N/A'),
                    kd_status=indicators.get('kd_status', 'N/A'),
                    candle_type=indicators.get('candle_type', 'N/A'),
                    signal_type=signal_type,
                    signal_note=signal_note,
                    confidence_score=compute_confidence_score(rsi=rsi, roc=roc, obv=obv, zscore=zscore),
                    direction="多" if signal_type == "BUY" else "空",
                    strategy_name="RROV策略",
                    zscore=zscore,
                    obv=obv,
                    obv_change=obv_diff,
                    vwap_deviation=vwap_deviation,
                    bb_deviation=((latest_price - indicators['lower_band'].iloc[-1]) / indicators['lower_band'].iloc[-1] * 100)
                        if indicators['lower_band'].iloc[-1] > 0 else None
                )

        except Exception as e:
            print(f"[錯誤] {symbol} 描錯誤：{e}\n{traceback.format_exc()}")
            continue

            # === 判斷趨勢傾向
            bias = "⚪ 中性"
            if (rsi > 60 or roc > 0.5 or ema5 > ema20 or obv_diff > 0):
                bias = "🟢 偏多"
            elif (rsi < 40 or roc < -0.5 or ema5 < ema20 or obv_diff < 0):
                bias = "🔴 偏空"

            # === 輸出技術資訊，趨勢放最前
            print(f"[資訊] {bias}｜{symbol} ➜ 價格=${latest_price:.2f}｜RSI={rsi:.1f}｜ROC={roc:.2f}｜OBV={int(obv):,}｜VWAP={vwap:.2f}｜Z-score={zscore:.2f}｜EMA5={ema5:.2f}｜EMA20={ema20:.2f}")

            # === 🧠 根據命中條件決定使用哪個策略（含多空分流） =====================

            # ✅ 判斷方向：多 or 空
            is_bullish = rsi < 50 and ema5 > ema20
            is_bearish = rsi > 50 and ema5 < ema20

            # ✅ 多單條件
            cond_rsi_long = rsi < 35 and rsi > indicators['rsi'].iloc[-2]
            cond_roc_long = roc < 0 and roc > indicators['roc'].iloc[-2]
            cond_obv_long = obv > indicators['obv'].iloc[-2]
            cond_vwap_near = abs(latest_price - vwap) / vwap < 0.05

            cond_price_low = latest_price < indicators['lower_band'].iloc[-1]
            cond_rsi_rebound = rsi > indicators['rsi'].iloc[-2] and rsi < 35
            cond_zscore_low = zscore < -2
            cond_ema_cross = ema5 > ema20

            # ✅ 空單條件
            cond_rsi_short = rsi > 65 and rsi < indicators['rsi'].iloc[-2]
            cond_roc_short = roc > 0 and roc < indicators['roc'].iloc[-2]
            cond_obv_short = obv < indicators['obv'].iloc[-2]

            cond_price_high = latest_price > indicators['upper_band'].iloc[-1]
            cond_rsi_drop = rsi < indicators['rsi'].iloc[-2] and rsi > 65
            cond_zscore_high = zscore > 2
            cond_ema_death = ema5 < ema20

            # ✅ 條件分流：依照方向套用不同策略
            if is_bullish:
                rrov_conditions = {
                    "RSI低位翻揚": cond_rsi_long,
                    "ROC翻揚": cond_roc_long,
                    "OBV上升": cond_obv_long,
                    "VWAP貼近": cond_vwap_near,
                }
                mean_revert_conditions = {
                    "跌破布林下緣": cond_price_low,
                    "RSI回升": cond_rsi_rebound,
                    "Z-score超跌": cond_zscore_low,
                    "EMA金叉": cond_ema_cross,
                }
            elif is_bearish:
                rrov_conditions = {
                    "RSI轉弱": cond_rsi_short,
                    "ROC下滑": cond_roc_short,
                    "OBV下降": cond_obv_short,
                    "VWAP貼近": cond_vwap_near,
                }
                mean_revert_conditions = {
                    "突破布林上緣": cond_price_high,
                    "RSI下降": cond_rsi_drop,
                    "Z-score過熱": cond_zscore_high,
                    "EMA死叉": cond_ema_death,
                }
            else:
                rrov_conditions = {}
                mean_revert_conditions = {}

            # ✅ 計算命中率
            rrov_score = get_strategy_match_score("RROV", rrov_conditions)
            mean_score = get_strategy_match_score("均值回歸", mean_revert_conditions)

            # ✅ 選擇策略
            selected_strategy = None
            if rrov_score > mean_score:
                selected_strategy = "RROV"
                print(f"[策略選擇] {symbol} ➜ 使用 RROV（命中 {rrov_score*100:.0f}%）")
            elif mean_score > rrov_score:
                selected_strategy = "均值回歸"
                print(f"[策略選擇] {symbol} ➜ 使用均值回歸（命中 {mean_score*100:.0f}%）")
            else:
                selected_strategy = "均值回歸"
                print(f"[策略選擇] {symbol} ➜ 無明顯優勢策略，預設使用均值回歸")

            # === 策略一：均值回歸策略
            signal_type1, signal_note1 = detect_mean_reversion_signals(df, symbol)

            # === ⚠️ 均值回歸策略未進場 ➜ 發送診斷推播
            if signal_type1 is None and signal_note1 and "未進場" in signal_note1:
                clean_note = signal_note1.replace("⛔ ", "").replace("：", "：\n")

                bb_deviation = (
                    (latest_price - indicators["lower_band"].iloc[-1]) / indicators["lower_band"].iloc[-1] * 100
                    if indicators["lower_band"].iloc[-1] > 0 else 0
                )
                ema_diff = indicators["ema_5"].iloc[-1] - indicators["ema_20"].iloc[-1]

                content = (
                    f"⛔ **[均值回歸未進場 - 診斷]** {symbol}\n"
                    f"🔍 原因：{clean_note}\n"
                    f"📉 價格=${latest_price:.2f}｜RSI={rsi:.1f}｜Z-score={zscore:.2f}\n"
                    f"📊 布林乖離={bb_deviation:.2f}%｜EMA差值={ema_diff:.2f}"
                )

                push_to_discord(content=content)

            # === 策略二：RROV 策略（後面再判斷）
            signal_type2, signal_note2 = detect_trading_signal(symbol, df, indicators)

            # === ⚠️ 無建倉時也要推播診斷訊息
            if signal_type2 is None and signal_note2:
                latest_price = df['close'].iloc[-1]
                vwap = indicators['vwap'].iloc[-1]
                vwap_deviation = (abs(latest_price - vwap) / vwap) * 100

                # 🔁 去除「均值回歸」關鍵字
                clean_note = signal_note2.replace("⛔ ", "").replace("（均值回歸）", "").replace("均值回歸", "").strip()

                content = (
                    f"⛔ **[RROV未進場 - 診斷]** {symbol}\n"
                    f"🔍 原因：{clean_note}\n"
                    f"📉 價格=${latest_price:.2f}｜"
                    f"RSI={indicators['rsi'].iloc[-1]:.1f}｜"
                    f"ROC={indicators['roc'].iloc[-1]:.2f}｜"
                    f"VWAP={vwap:.2f}｜VWAP乖離={vwap_deviation:.2f}%"
                )
                push_to_discord(content=content)

            # === ⚠️ 若為均值回歸潛伏預警，只推播不建倉
            if signal_type1 in ["ALERT_BUY", "ALERT_SELL"]:
                obv_change = indicators['obv'].diff().iloc[-1]
                if pd.isna(obv_change):
                    obv_change = 0

                vwap_deviation = (latest_price - indicators['vwap'].iloc[-1]) / indicators['vwap'].iloc[-1] * 100

                bb_deviation = 0
                if latest_price > indicators['upper_band'].iloc[-1]:
                    bb_deviation = (latest_price - indicators['upper_band'].iloc[-1]) / indicators['upper_band'].iloc[-1] * 100
                elif latest_price < indicators['lower_band'].iloc[-1]:
                    bb_deviation = (latest_price - indicators['lower_band'].iloc[-1]) / indicators['lower_band'].iloc[-1] * 100

                push_to_discord(
                    symbol=symbol,
                    price=latest_price,
                    rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    vwap=indicators['vwap'].iloc[-1],
                    volume_ratio=indicators['volume_ratio'].iloc[-1],
                    ema_cross=indicators['ema_status'],
                    kd_status=indicators['kd_status'],
                    candle_type=indicators['candle_type'],
                    signal_type=signal_type1,
                    signal_note=signal_note1,
                    confidence_score=None,
                    direction="多" if signal_type1 == "ALERT_BUY" else "空",
                    strategy_name="均值回歸策略",
                    zscore=indicators['zscore'].iloc[-1],
                    obv=indicators['obv'].iloc[-1],
                    obv_change=obv_change,
                    vwap_deviation=vwap_deviation,
                    bb_deviation=bb_deviation
                )
                continue

            # === ✅ 均值回歸正式建倉
            if signal_type1 in ["BUY", "SELL"]:
                direction = "多" if signal_type1 == "BUY" else "空"

                obv_change = indicators['obv'].diff().iloc[-1]
                if pd.isna(obv_change):
                    obv_change = 0

                vwap_deviation = (latest_price - indicators['vwap'].iloc[-1]) / indicators['vwap'].iloc[-1] * 100
                bb_deviation = ((latest_price - indicators['lower_band'].iloc[-1]) / indicators['lower_band'].iloc[-1]) * 100
                ema_diff = indicators['ema_5'].iloc[-1] - indicators['ema_20'].iloc[-1]

                confidence_score = compute_confidence_score(
                    rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    obv=obv_change,
                    vwap_deviation=vwap_deviation,
                    zscore=indicators['zscore'].iloc[-1],
                    bb_deviation=bb_deviation,
                    ema_diff=ema_diff
                )

                # ✅ 推播正式建倉訊號
                push_to_discord(
                    symbol=symbol,
                    price=latest_price,
                    rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    vwap=indicators['vwap'].iloc[-1],
                    volume_ratio=indicators['volume_ratio'].iloc[-1],
                    ema_cross=indicators['ema_status'],
                    kd_status=indicators['kd_status'],
                    candle_type=indicators['candle_type'],
                    signal_type=signal_type1,
                    signal_note=signal_note1,
                    confidence_score=confidence_score,
                    direction=direction,
                    strategy_name="均值回歸策略",
                    zscore=indicators['zscore'].iloc[-1],
                    obv=indicators['obv'].iloc[-1],
                    obv_change=obv_change,
                    vwap_deviation=vwap_deviation,
                    bb_deviation=bb_deviation
                )

                # ✅ 建倉資金與張數
                capital_required = min(TOTAL_CAPITAL * POSITION_RATIO, MAX_PER_POSITION)
                shares = int(capital_required / latest_price)

                # ✅ 建倉
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

                # === 若完全沒進場，但有診斷訊息，就推播
                if signal_type1 is None and signal_note1 and "未進場" in signal_note1:
                    content = (
                        f"⛔ **[均值回歸未進場 - 診斷]** {symbol}\n"
                        f"🔍 原因：{signal_note1.replace('⛔ ', '')}\n"
                        f"📉 價格=${latest_price:.2f}｜RSI={rsi:.1f}｜Z-score={zscore:.2f}｜EMA5={ema5:.2f}｜EMA20={ema20:.2f}"
                    )
                    push_to_discord(content)

                continue  # ✅ 跳過 RROV，避免重複建倉

            # === ✅ RROV 策略建倉
            if signal_type2 in ["BUY", "SELL"]:
                direction = "多" if signal_type2 == "BUY" else "空"

                obv_change = indicators['obv'].diff().iloc[-1]
                if pd.isna(obv_change):
                    obv_change = 0

                vwap_deviation = (latest_price - indicators['vwap'].iloc[-1]) / indicators['vwap'].iloc[-1] * 100
                ema_diff = indicators['ema_5'].iloc[-1] - indicators['ema_20'].iloc[-1]

                confidence_score = compute_confidence_score(
                    rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    obv=obv_change,
                    vwap_deviation=vwap_deviation,
                    ema_diff=ema_diff
                )

                # ✅ 推播建倉訊號
                push_to_discord(
                    symbol=symbol,
                    price=latest_price,
                    rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    vwap=indicators['vwap'].iloc[-1],
                    volume_ratio=indicators['volume_ratio'].iloc[-1],
                    ema_cross=indicators['ema_status'],
                    kd_status=indicators['kd_status'],
                    candle_type=indicators['candle_type'],
                    signal_type=signal_type2,
                    signal_note=signal_note2,
                    confidence_score=confidence_score,
                    direction=direction,
                    strategy_name="RROV策略",
                    zscore=indicators['zscore'].iloc[-1],
                    obv=indicators['obv'].iloc[-1],
                    obv_change=obv_change,
                    vwap_deviation=vwap_deviation
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
                elif signal_type2 is None and signal_note2 and "未進場" in signal_note2:
                    content = (
                        f"⛔ **[RROV未進場 - 診斷]** {symbol}\n"
                        f"🔍 原因：{signal_note2.replace('⛔ ', '')}\n"
                        f"📉 價格=${latest_price:.2f}｜RSI={rsi:.1f}｜ROC={roc:.2f}｜VWAP={vwap:.2f}"
                    )
                    push_to_discord(content)

            # === 3. 出場邏輯
            if symbol in positions:
                check_exit_and_notify(symbol, latest_price)

        except Exception as e:
            print(f"[錯誤] {symbol} 掃描錯誤：{e}")
        
def detect_mean_reversion_signals(df, symbol):
    if len(df) < 27:
        return None, None

    ind = calculate_indicators(df)
    if ind is None:
        return None, None

    latest_price = df['close'].iloc[-1]
    latest_rsi = ind['rsi'].iloc[-1]
    prev_rsi = ind['rsi'].iloc[-2]
    zscore = ind['zscore'].iloc[-1]
    ema5 = ind['ema_5'].iloc[-1]
    ema20 = ind['ema_20'].iloc[-1]
    lower_band = ind['lower_band'].iloc[-1]
    upper_band = ind['upper_band'].iloc[-1]

    # ✅ 條件逐一計算（多單）
    cond_price_low = latest_price < lower_band
    cond_rsi_rebound = latest_rsi > prev_rsi and latest_rsi < 35
    cond_zscore_low = zscore < -2
    cond_ema_bull = ema5 > ema20

    if cond_price_low and cond_rsi_rebound and cond_zscore_low and cond_ema_bull:
        note = "📈 多單均值回歸：跌破布林下緣 + RSI 回升 + Z-score 偏低 + EMA多方\n🔎 大盤盤整中，啟動均值回歸判斷"
        return "BUY", note

    # ✅ 空單條件
    cond_price_high = latest_price > upper_band
    cond_rsi_weak = latest_rsi < prev_rsi and latest_rsi > 65
    cond_zscore_high = zscore > 2
    cond_ema_bear = ema5 < ema20

    if cond_price_high and cond_rsi_weak and cond_zscore_high and cond_ema_bear:
        note = "📉 空單均值回歸：突破布林上緣 + RSI 轉弱 + Z-score 偏高 + EMA空方\n🔎 大盤盤整中，啟動均值回歸判斷"
        return "SELL", note

    # ⚠️ 潛伏多單預警條件
    if (
        latest_price < lower_band * 1.01 and
        latest_rsi < 40 and
        zscore < -1.5 and
        ema5 > ema20 * 0.98
    ):
        note = "⚠️ 潛伏多頭：貼近布林下緣 + RSI 低位 + Z-score 偏低 + EMA即將金叉"
        return "ALERT_BUY", note

    # ⚠️ 潛伏空單預警條件
    if (
        latest_price > upper_band * 0.99 and
        latest_rsi > 60 and
        zscore > 1.5 and
        ema5 < ema20 * 1.02
    ):
        note = "⚠️ 潛伏空頭：接近布林上緣 + RSI 高位 + Z-score 偏高 + EMA即將死叉"
        return "ALERT_SELL", note

    # ❗ 無訊號時：列出未達標條件（只針對多單正式進場做提示）
    failed = []
    if not cond_price_low:
        failed.append("價格未跌破布林下緣")
    if not cond_rsi_rebound:
        failed.append("RSI未回升或高於35")
    if not cond_zscore_low:
        failed.append("Z-score未小於 -2")
    if not cond_ema_bull:
        failed.append("EMA5未上穿EMA20")

    msg = f"⛔ 均值回歸未進場：{'、'.join(failed)}"
    print(f"[未達條件] {symbol}（均值回歸）➜ {msg}")
    return None, msg

# === 2. 技術指標計算函數 ===

def calculate_indicators(df):
    if len(df) < 27:
        print("[警告] 技術指標計算時資料不足，跳過")
        return None

    required_columns = ['close', 'volume']
    for col in required_columns:
        if col not in df.columns or df[col].isnull().all():
            print(f"⚠️ [警告] 缺少必要欄位：{col}，跳過該股票")
            return None
        if df[col].isnull().all():
            print(f"⚠️ [警告] 欄位 {col} 全部是空值 ➜ 跳過")
            return None
        
        
    # ✅ 必須補上這兩行
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

    # === 成交量資訊 ===
    curr_volume = volume.iloc[-1]
    avg_volume = volume.rolling(20).mean().iloc[-1]
    volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1.0

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
        'ema_20': ema_20,
        'curr_volume': curr_volume,
        'volume_ratio': volume_ratio,
        'avg_volume': avg_volume
    }

def compute_confidence_score(rsi, roc, obv, vwap_deviation, zscore, bb_deviation):
    score = 0

    # ✅ RSI
    if rsi < 30:
        score += 0.3
    elif rsi < 40:
        score += 0.2
    elif rsi < 50:
        score += 0.1

    # ✅ ROC
    if roc > 1:
        score += 0.3
    elif roc > 0:
        score += 0.2

    # ✅ OBV
    if obv > 0:
        score += 0.2

    # ✅ EMA 趨勢
    if ema5 > ema20:
        score += 0.2

    # ✅ VWAP 貼近
    if abs(vwap) < 1.0:
        score += 0.1

    # ✅ Z-score 越偏離越加分
    if abs(zscore) > 2:
        score += 0.3
    elif abs(zscore) > 1.5:
        score += 0.2
    elif abs(zscore) > 1:
        score += 0.1

    # ✅ 布林乖離加分（>0 表示上穿、<0 表示跌破下緣）
    if bb_deviation < -2:
        score += 0.3
    elif bb_deviation < -1:
        score += 0.2
    elif bb_deviation > 2:
        score += 0.3
    elif bb_deviation > 1:
        score += 0.2

    return min(score, 1.0)

# === 3. 訊號判斷邏輯（多空建倉，無預警） ===

def detect_trading_signal(symbol, df, indicators, debug=False, force_test=False):

    if 'volume' not in df.columns:
        print(f"[跳過] {symbol} 缺少 volume 欄位")
        return None, None

    if len(df) < 27:
        if debug:
            print(f"[跳過] {symbol} 資料不足（僅 {len(df)} 筆）")
        return None, None

    # === 基本指標讀取 ===
    latest_price = df['close'].iloc[-1]
    rsi = indicators['rsi'].iloc[-1]
    roc = indicators['roc'].iloc[-1]
    obv = indicators['obv'].iloc[-1]
    vwap = indicators['vwap'].iloc[-1]

    # ✅ VWAP 乖離（避免除以零）
    if vwap != 0:
        vwap_deviation = (latest_price - vwap) / vwap
    else:
        vwap_deviation = None  # 或設定為 0

    # ✅ Z-score 計算（避免 std = 0 或 NaN）
    mean = df['close'].rolling(window=20).mean().iloc[-1]
    std = df['close'].rolling(window=20).std().iloc[-1]
    if std != 0 and not pd.isna(std):
        zscore = (latest_price - mean) / std
    else:
        zscore = 0

    signal_type = None
    signal_note = None

    # ✅ 半山腰區間排除
    if 45 <= rsi <= 65:
        if debug:
            print(f"[跳過] {symbol} RSI在半山腰區間（{rsi:.1f}），不進場")
        return None, None

    # ✅ 強制測試訊號
    if force_test and symbol in ["TSLA", "NVDA"]:
        return "BUY", "🧪 測試訊號：模擬建倉"

    # === 🟢 多單建倉條件
    cond_rsi_long = rsi < 35 and rsi > indicators['rsi'].iloc[-2]
    cond_roc_long = roc < 0 and roc > indicators['roc'].iloc[-2]
    cond_obv_long = obv > indicators['obv'].iloc[-2]
    cond_vwap_near = abs(latest_price - vwap) / vwap < 0.05

    if cond_rsi_long and cond_roc_long and cond_obv_long and cond_vwap_near:
        return "BUY", "🐸 多單建倉：RSI回升 + ROC翻揚 + OBV上升 + 貼近VWAP"

    # === 🔴 空單建倉條件
    cond_rsi_short = rsi > 65 and rsi < indicators['rsi'].iloc[-2]
    cond_roc_short = roc > 0 and roc < indicators['roc'].iloc[-2]
    cond_obv_short = obv < indicators['obv'].iloc[-2]

    if cond_rsi_short and cond_roc_short and cond_obv_short and cond_vwap_near:
        return "SELL", "🐶 空單建倉：RSI轉弱 + ROC下滑 + OBV下降 + 貼近VWAP"

    # === 📉 條件未滿足：列出未達項目
    failed_conditions = []

    # 判斷是哪個方向的未達條件
    if rsi < 50:  # 多單偏多
        if not cond_rsi_long:
            failed_conditions.append("RSI未低位翻揚")
        if not cond_roc_long:
            failed_conditions.append("ROC未由負翻正")
        if not cond_obv_long:
            failed_conditions.append("OBV未上升")
        if not cond_vwap_near:
            failed_conditions.append("價格遠離VWAP")
        if debug:
            print(f"[未達條件] {symbol}（RROV 多單）➜ {'、'.join(failed_conditions)}")
    else:  # 偏空邏輯
        if not cond_rsi_short:
            failed_conditions.append("RSI未轉弱")
        if not cond_roc_short:
            failed_conditions.append("ROC未由正轉弱")
        if not cond_obv_short:
            failed_conditions.append("OBV未下降")
        if not cond_vwap_near:
            failed_conditions.append("價格遠離VWAP")
        if debug:
            print(f"[未達條件] {symbol}（RROV 空單）➜ {'、'.join(failed_conditions)}")

    # === 📊 技術分析資訊輸出（含爆量）
    obv_change = obv - indicators['obv'].iloc[-2]
    vwap_deviation = (abs(latest_price - vwap) / vwap) * 100
    lower_band = indicators['lower_band'].iloc[-1]
    upper_band = indicators['upper_band'].iloc[-1]
    bb_diff = (latest_price - lower_band) / lower_band * 100
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]
    ema_diff = ema5 - ema20

    curr_volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].rolling(20).mean().iloc[-1]
    volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1.0

    # === ⚠️ 異常爆量預警
    if volume_ratio >= 5 and (rsi < 40 or latest_price < lower_band * 1.02):
        return "ALERT_VOLUME_SPIKE_LONG", f"⚠️ **[預警 - 低檔爆量]** {symbol} ➜ 成交量為均量 {volume_ratio:.1f} 倍，RSI={rsi:.1f}"
    elif volume_ratio >= 5 and (rsi > 70 or latest_price > upper_band * 0.98):
        return "ALERT_VOLUME_SPIKE_SHORT", f"⚠️ **[預警 - 高檔爆量]** {symbol} ➜ 成交量為均量 {volume_ratio:.1f} 倍，RSI={rsi:.1f}"

    # === 🪵 除錯資訊
    if debug:
        print(f"[調試] {symbol} ➜ RSI={rsi:.1f}, ROC={roc:.2f}, OBV變化={obv_change:.2f}, VWAP乖離={vwap_deviation:.2f}%")
        print(f"[補充] Z-score={zscore:.2f}, BB下緣乖離={bb_diff:.2f}%, EMA差={ema_diff:.2f}")
        print(f"[成交量] 現量={curr_volume:,} 股，均量={avg_volume:,.0f} 股 ➜ 倍率={volume_ratio:.2f}x")

    return None, f"⛔ RROV未進場：{'、'.join(failed_conditions)}" if failed_conditions else None
       

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
        requests.post(WEBHOOK_URL, json={"content": content})
    except Exception as e:
        print(f"[EXCEPTION] Discord 推播錯誤：{e}")

def enter_position(symbol, price, direction, signal_note, rsi=None, zscore=None,
                   ema5=None, ema20=None, upper_band=None, lower_band=None, mid_band=None,
                   roc=None, obv=None, vwap=None, confidence_score=None):
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
    if upper_band is not None and lower_band is not None and mid_band is not None:
        msg += f"📉 布林通道：上軌={upper_band:.2f}｜中軌={mid_band:.2f}｜下軌={lower_band:.2f}\n"

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
            roc=roc or 0,
            obv=obv or 0,
            vwap=vwap or 0,
            confidence_score=confidence_score or 0.5,
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
        requests.post(WEBHOOK_URL, json={"content": msg})
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

    requests.post(WEBHOOK_URL, json={"content": content})

    # ✅ 若剩餘股數為 0 → 移除持倉
    if pos["quantity"] <= 0:
        del positions[symbol]

def push_to_discord(symbol, price, rsi, roc, vwap, volume_ratio,
                    ema_cross, kd_status, candle_type,
                    signal_type, signal_note, confidence_score,
                    direction, strategy_name, zscore, obv,
                    obv_change=None, vwap_deviation=None, bb_deviation=None):  # ✅ 可選參數整合
    try:
        # Emoji 標記
        emoji = "🐸" if direction == "多" else "🐶"

        # 格式處理（保險防止 None）
        rsi_text = f"{rsi:.1f}" if rsi is not None else "N/A"
        roc_text = f"{roc:.2f}" if roc is not None else "N/A"
        vwap_text = f"{vwap:.2f}" if vwap is not None else "N/A"
        zscore_text = f"{zscore:.2f}" if zscore is not None else "N/A"
        obv_text = f"{int(obv):,}" if obv is not None else "N/A"
        volume_text = f"{volume_ratio:.2f}x" if volume_ratio is not None else "N/A"
        confidence_text = f"{confidence_score:.2f}" if confidence_score is not None else "N/A"

        # 組裝訊息
        msg = (
            f"{emoji} **[{strategy_name}]** {symbol}\n"
            f"💵 價格：${price:.2f} | RSI：{rsi_text} | ROC：{roc_text} | Z-score：{zscore_text}\n"
            f"📊 VWAP：{vwap_text} | 成交量：{volume_text} | OBV：{obv_text}\n"
        )

        # ✅ 額外數值段落（視狀況補充）
        if vwap_deviation is not None:
            msg += f"📉 VWAP 乖離：{vwap_deviation:+.2f}%\n"

        if bb_deviation is not None:
            msg += f"📈 布林乖離：{bb_deviation:+.2f}%\n"

        if obv_change is not None:
            msg += f"🔄 OBV 變化量：{obv_change:+,.0f}\n"

        msg += (
            f"📈 EMA：{ema_cross} | KD：{kd_status} | K棒：{candle_type}\n"
            f"🧠 信心分數：{confidence_text}\n"
            f"🔔 **訊號類型**：{signal_note}"
        )

        # 發送到 Discord
        payload = {"content": msg}
        response = requests.post(WEBHOOK_URL, json=payload)

        if response.status_code != 204:
            print(f"[⚠️警告] Discord 推播失敗 ➜ {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[❌錯誤] 推播失敗：{e}")

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
