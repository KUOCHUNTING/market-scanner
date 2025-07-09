# === 📦 系統與網路套件 ===
import os
import random
import requests
import traceback
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
import os, json, base64
from google.oauth2.service_account import Credentials
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# 建立美東時間
eastern = pytz.timezone("US/Eastern")
now_est = datetime.now(eastern)
print("建倉時間（美東）:", now_est.strftime("%Y-%m-%d %H:%M:%S"))

def calculate_exit_metrics(entry_price, exit_price, shares, entry_time, exit_time, direction="多"):
    """
    自動計算出場三大指標（已用總金額計算報酬率）：
    1. 報酬率 (%)（多單 / 空單）
    2. 損益金額 (USD)
    3. 持倉時間（格式：幾分幾秒）

    傳入：
        entry_price: float
        exit_price: float
        shares: int
        entry_time: datetime
        exit_time: datetime
        direction: str（"多" 或 "空"）

    回傳：
        return_rate (float), pnl (float), holding_duration_str (str)
    """
    try:
        # ✅ 防呆檢查
        if entry_price is None or entry_price <= 0.05 or shares <= 0:
            print(f"[跳過] 出場計算異常 ➜ entry_price={entry_price}, shares={shares}")
            return None, None, None

        # ✅ 計算進場與出場總金額
        entry_total = entry_price * shares
        exit_total = exit_price * shares

        # ✅ 根據方向計算損益與報酬率
        if direction == "多":
            pnl = exit_total - entry_total
        else:
            pnl = entry_total - exit_total  # 空單獲利：越跌越賺

        return_rate = (pnl / entry_total) * 100

        # ✅ 報酬率與損益防呆過濾
        if return_rate > 500 or return_rate < -90:
            print(f"[跳過] 報酬率異常（{return_rate:.2f}%）")
            return None, None, None

        if abs(pnl) > entry_total * 3:
            print(f"[跳過] 損益異常（${pnl:.2f}）➜ 超過進場金額三倍")
            return None, None, None

        # ✅ 持倉時間格式轉換（幾分幾秒）
        holding_delta = exit_time - entry_time
        total_seconds = int(holding_delta.total_seconds())
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        holding_duration_str = f"{minutes}分{seconds}秒"

        return round(return_rate, 2), round(pnl, 2), holding_duration_str

    except Exception as e:
        print(f"[❌ 錯誤] 無法計算出場指標：{e}")
        return None, None, None
    
# === Google Sheets 客戶端初始化（新版）
def get_gspread_client(base64_key):

    keyfile_dict = json.loads(base64.b64decode(base64_key))
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(keyfile_dict, scopes=scopes)
    return gspread.Client(auth=creds)

def connect_to_gsheet():
    b64_json = os.getenv("GCP_KEY_BASE64")
    info = json.loads(base64.b64decode(b64_json))
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    return client

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
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1389605152838647909/c2S7EkfYiFBUMF4WWNyk3XrgcsmGA1-8mqXZ19a5vXn-Ti0yY366L3h77SF7M47GOzej")
FMP_API_KEY = "RkRQwAwDCPHSTg1QE4MjIwsqWd0iHtd7"
# === 🧠 交易資金設定 ===
TOTAL_CAPITAL = 1_000_000             # 初始總資金（單位：美元）
POSITION_RATIO = 0.05                 # 每次進場佔總資金 5%
MAX_CAPITAL_PER_POSITION = 50000
MAX_SHARES_PER_POSITION = 6000  # 每檔最多持有 6000 股
MAX_ACTIVE_POSITIONS = 10             # 最多同時持有 10 檔
capital_left = TOTAL_CAPITAL
capital_left = int(capital_left)         # 當前剩餘資金
positions = {}                  # 持倉記錄：symbol -> {'entry_price', 'shares', 'entry_time'}

def write_entry_to_sheet(symbol, price, direction, shares, capital, strategy, confidence, capital_left):
    try:
        from datetime import datetime
        import base64, json, os, gspread
        from google.oauth2.service_account import Credentials

        keyfile_dict = json.loads(base64.b64decode(os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")))
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(keyfile_dict, scopes=scopes)
        client = gspread.Client(auth=creds)

        sheet = client.open("Trading Log").worksheet("建倉紀錄")
        now = datetime.now()

        row = [
            now.strftime("%Y-%m-%d %H:%M:%S"),  # 建倉時間
            now.strftime("%Y-%m-%d"),           # 建倉日期
            symbol,
            direction,
            shares,
            capital,
            price,
            strategy,
            confidence,
            capital_left  # ✅ 新增這一欄
        ]

        sheet.insert_row(row, index=2, value_input_option="USER_ENTERED")
        print(f"[✅ 建倉寫入成功] {symbol}")
    except Exception as e:
        print(f"[❌ 建倉寫入錯誤] {symbol} ➜ {type(e).__name__}：{e}")

def write_alert_to_sheet(symbol, price, direction, signal_type, signal_note, rsi, zscore, vwap, volume_ratio):
    try:
        from datetime import datetime
        import base64, json, os, gspread
        from google.oauth2.service_account import Credentials

        # === 1. 解碼憑證
        keyfile_dict = json.loads(base64.b64decode(os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")))
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(keyfile_dict, scopes=scopes)
        client = gspread.Client(auth=creds)

        # === 2. 打開預警紀錄分頁
        sheet = client.open("Trading Log").worksheet("預警紀錄")
        now = datetime.now()

        # === 3. 整理欄位（符合你定義的12欄格式）
        row = [
            now.strftime("%Y-%m-%d %H:%M:%S"),  # 時間
            symbol,                             # 股票代碼
            direction,                          # 多 / 空
            price,                              # 價格
            signal_type,                        # 訊號類型（ALERT_VOLUME_SPIKE_...）
            signal_note,                        # 訊號說明
            round(rsi, 2),                      # RSI
            round(zscore, 2),                   # Z-score
            round(vwap, 2),                     # VWAP
            round(volume_ratio, 2),             # 量比
            "爆量預警",                          # 策略名稱
            "預警"                                # 類別
        ]

        # === 4. 寫入最上方（第二列）
        sheet.insert_row(row, index=2, value_input_option="USER_ENTERED")
        print(f"[✅ 預警寫入成功] {symbol} ➜ {signal_type}")
    except Exception as e:
        print(f"[❌ 預警寫入錯誤] {symbol} ➜ {type(e).__name__}：{e}")

def record_entry_position(symbol, price, direction, shares, strategy_name,
                          confidence_score=None, capital_used=None):
    """
    建倉紀錄函數，用於儲存已進場部位資訊。
    """
    entry = {
        "symbol": symbol,
        "price": price,
        "direction": direction,
        "shares": shares,
        "strategy": strategy_name,
        "confidence": confidence_score,
        "capital_used": capital_used,
        "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    positions[symbol] = entry
    print(f"[✅紀錄] 已建倉：{symbol} @ ${price:.2f}｜方向：{direction}｜股數：{shares}｜策略：{strategy_name}")

def compute_position_size(latest_price):
    global capital_left

    # ✅ 資金不足直接跳過
    if capital_left < 100:
        print(f"[跳過] 可用資金不足（${capital_left:.2f}），略過建倉")
        return 0, 0

    # 1️⃣ 預設投入金額為總資金的 POSITION_RATIO（如 5%）
    proposed_capital = TOTAL_CAPITAL * POSITION_RATIO

    # 2️⃣ 不能超過剩餘資金
    proposed_capital = min(proposed_capital, capital_left)

    # 3️⃣ 根據股價換算可買股數（整數）
    shares = int(proposed_capital // latest_price)

    # 4️⃣ 股數不得超過 MAX_SHARES_PER_POSITION
    shares = min(shares, MAX_SHARES_PER_POSITION)

    # 5️⃣ 實際投入金額為 shares * price
    capital_used = shares * latest_price

    return shares, capital_used

# ===== 工具函數：計算策略達成率 =====================
def get_strategy_match_score(strategy_name, conditions_dict):
    total = len(conditions_dict)
    satisfied = sum(1 for cond in conditions_dict.values() if cond)

    if total == 0:
        print(f"[警告] 策略 {strategy_name} 無條件可供計算 ➜ 預設命中率為 0")
        return 0

    return satisfied / total

def can_enter_new_position(symbol, capital_required):
    # 已經持有該股票
    if symbol in positions:
        return False

    # 同時持股超限
    if len(positions) >= MAX_ACTIVE_POSITIONS:
        print(f"[資金控管] 持股達上限 [{MAX_ACTIVE_POSITIONS}] 檔")
        return False

    # 單檔超出最大投入限制
    if capital_required > MAX_CAPITAL_PER_POSITION:
        print(f"[資金控管] 單檔超出上限 ${MAX_CAPITAL_PER_POSITION:,}：{symbol}")
        return False

    # 資金不足
    if capital_required > capital_left:
        print(f"[資金控管] 資金不足，無法進場 {symbol}")
        return False

    return True

def get_fundamentals(symbol, polygon_api_key, df=None):
    try:
        url = f"https://api.polygon.io/v3/reference/tickers/{symbol}?apiKey={polygon_api_key}"
        res = requests.get(url)
        data = res.json().get("results", {})

        avg_volume_api = float(data.get("average_volume", 0))
        avg_volume_fallback = 0

        if avg_volume_api == 0 and df is not None and "volume" in df.columns:
            avg_volume_fallback = df["volume"].tail(60).mean()  # ✅ 用近 60 根 K 計算，約等於 3 日均量

        avg_volume = avg_volume_api if avg_volume_api > 0 else avg_volume_fallback

        return {
            "market_cap": float(data.get("market_cap", 0)),
            "avg_volume": avg_volume,
            "price": float(data.get("last_close", {}).get("price", 0)),
            "is_otc": data.get("market", "").lower() == "otc",
            "is_delisted": not data.get("active", True),
            "is_recent_earning": False
        }

    except Exception as e:
        print(f"[❌ 基本面抓取失敗] {symbol} ➜ {e}")
        return {
            "market_cap": 0,
            "avg_volume": 0,
            "price": 0,
            "is_otc": True,
            "is_delisted": True,
            "is_recent_earning": True
        }

def filter_fundamentals(symbol, fundamentals):
    avg_volume = fundamentals.get("avg_volume", 0)
    price = fundamentals.get("price", 5)
    is_delisted = fundamentals.get("is_delisted", False)
    is_recent_earning = fundamentals.get("is_recent_earning", False)

    # ✅ 只過濾流動性太差的股票
    if avg_volume < 300_000:
        return False, "❌ 流動性過低（<30萬）不適合隔日沖"

    # ✅ 避免停牌或財報波動
    if is_delisted:
        return False, "❌ 已下市或停牌"
    if is_recent_earning:
        return False, "⚠️ 財報發布期，波動過大"

    return True, "✅ 通過（流動性良好）"
# === 🛡️ 出場風控參數（含三段鎖利）===
TRAIL_TRIGGER = 0.03            # +3% 啟動移動停利
TRAIL_MARGIN = 0.015            # 回落 1.5% 停利出場
DEFAULT_STOP_LOSS = 0.02        # -2% 強制停損
DEFAULT_TAKE_PROFIT = 0.05      # +5% 預設停利

def write_trade_to_sheet(strategy_type, symbol, direction, entry_price, shares,
                         invested_capital, rsi, zscore, roc, obv, vwap,
                         confidence_score, signal_note, sheet_webhook_url,
                         return_rate=None, holding_minutes=None, pnl=None):

    from datetime import datetime
    import requests

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
        "date": date_today
    }

    if return_rate is not None:
        payload["return_rate"] = round(return_rate, 2)
        payload["holding_minutes"] = holding_minutes
        payload["pnl"] = round(pnl, 2)

    try:
        response = requests.post(sheet_webhook_url, json=payload)
        if response.ok:
            print(f"[✅ 寫入成功] {symbol} ➜ {strategy_type}")
        else:
            print(f"[⚠️ 寫入失敗] {symbol} ➜ 狀態碼：{response.status_code} ➜ {response.text}")
    except Exception as e:
        print(f"[❌ 錯誤] 無法寫入 Google Sheets ➜ {symbol} ➜ {e}")

def write_exit_to_sheet(
    symbol, entry_time, exit_time, return_rate, pnl, holding_minutes,
    exit_price=None,  # ✅ 新增參數
    rsi=None, zscore=None, roc=None, obv=None, vwap=None,
    ema5=None, ema20=None, strategy_name="未知策略"
):
    try:
        from datetime import datetime
        import base64, json, os, gspread
        from google.oauth2.service_account import Credentials

        keyfile_dict = json.loads(base64.b64decode(os.getenv("GOOGLE_SERVICE_ACCOUNT_BASE64")))
        scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(keyfile_dict, scopes=scopes)
        client = gspread.authorize(creds)

        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/edit")
        ws = sheet.worksheet("出場紀錄")  # 第二分頁

        # 組合資料列
        row = [
            entry_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(entry_time, datetime) else entry_time,
            exit_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(exit_time, datetime) else exit_time,
            symbol,
            f"{round(return_rate, 2)}%" if return_rate is not None else "N/A",
            f"${round(pnl, 2)}" if pnl is not None else "N/A",
            f"${round(exit_price, 2)}" if exit_price is not None else "N/A",  # ✅ 出場價格
            f"{holding_minutes}" if holding_minutes is not None else "N/A",
            round(rsi, 2) if rsi is not None else "",
            round(zscore, 2) if zscore is not None else "",
            round(roc, 2) if roc is not None else "",
            int(obv) if obv is not None else "",
            round(vwap, 2) if vwap is not None else "",
            round(ema5, 2) if ema5 is not None else "",
            round(ema20, 2) if ema20 is not None else "",
            strategy_name
        ]

        ws.append_row(row, value_input_option="USER_ENTERED")
        print(f"[✅ 出場紀錄寫入成功] {symbol}")

    except Exception as e:
        print(f"[❌ 出場紀錄寫入錯誤] {symbol} ➜ {type(e).__name__}：{e}")

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
    import pytz
    import pandas as pd
    from datetime import datetime, timedelta, time as dtime
    from polygon import RESTClient

    est = pytz.timezone("US/Eastern")
    now_est = datetime.now(est)

    market_open = est.localize(datetime.combine(now_est.date(), dtime(9, 30)))
    market_close = est.localize(datetime.combine(now_est.date(), dtime(16, 0)))

    now = datetime.now(est)
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

        bars = client.get_aggs(
            ticker=symbol,
            multiplier=15,
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

        df_all = df_all.dropna(subset=["close", "volume"])
        df_all = df_all[df_all["volume"] > 0]

        print(f"[DEBUG] {symbol} 初始抓到 {len(df_all)} 根")

        # 自動補抓直到湊滿 30 根
        retry_days = 0
        prev_day = start_time.date()
        while len(df_all) < 60 and retry_days < 10:
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
                multiplier=15,
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

                df_retry = df_retry.dropna(subset=["close", "volume"])
                df_retry = df_retry[df_retry["volume"] > 0]

                if not df_retry.empty:
                    df_all = pd.concat([df_retry, df_all], ignore_index=True)
                    print(f"[補抓] 累積筆數：{len(df_all)}")
            else:
                print(f"[補抓] 第 {retry_days} 天無資料")

        if len(df_all) < 60:
            print(f"[❌終止] {symbol} 最終仍不足 60 根（僅 {len(df_all)}），跳過")
            return None

        df_all["timestamp"] = pd.to_datetime(df_all["timestamp"], unit="ms")
        df_all.set_index("timestamp", inplace=True)
        df_all.sort_index(inplace=True)

        # ✅ 最後防呆檢查欄位
        required_columns = ["open", "high", "low", "close", "volume"]
        for col in required_columns:
            if col not in df_all.columns:
                print(f"[錯誤] {symbol} ➜ 缺少欄位：{col}")
                print(df_all.head(3))
                return None

        return df_all

    except Exception as e:
        print(f"[❌錯誤] 抓取 {symbol} 發生例外：{e}")
        return None
    
    
def detect_mean_reversion_signals(df, symbol):
    if len(df) < 60:
        return None, None, None, None, None, None

    indicators = calculate_indicators(df)

    # ✅ 防呆檢查：必要欄位缺失就跳過
    required_keys = ['rsi', 'zscore', 'ema_5', 'ema_20', 'bb_lower', 'bb_upper', 'vwap', 'obv']
    for key in required_keys:
        if key not in indicators or indicators[key].isna().iloc[-1]:
            print(f"[跳過] {symbol} ➜ 指標 {key} 缺失或為 NaN")
            return None, None, None, None, None, None
        
    if 'close' not in df.columns or df['close'].isnull().all():
        print(f"[跳過] {symbol} ➜ df['close'] 欄位無效或全部為空，無法取得 latest_price")
        return None, None, None, None, None, None  # ⚠️ 確保 return 數量符合你函數格式

    latest_price = df['close'].iloc[-1]
    if pd.isna(latest_price) or latest_price <= 0:
        print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
        return None, None, None, None, None, None
    latest_rsi = indicators['rsi'].iloc[-1]
    prev_rsi = indicators['rsi'].iloc[-2]
    zscore = indicators['zscore'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]
    lower_band = indicators['bb_lower'].iloc[-1]
    upper_band = indicators['bb_upper'].iloc[-1]
    vwap = indicators['vwap'].iloc[-1]
    obv = indicators['obv'].iloc[-1]
    # ✅ 多單均值回歸條件
    if (
        latest_price < lower_band and
        latest_rsi > prev_rsi and latest_rsi < 35 and
        zscore < -2 and
        ema5 > ema20
    ):
        note = f"📈 多單均值回歸：跌破布林下緣 + RSI回升 + Z-score={zscore:.2f} + EMA5上穿EMA20"
        return "BUY", note, zscore, latest_rsi, vwap, obv

    # ✅ 空單均值回歸條件
    elif (
        latest_price > upper_band and
        latest_rsi < prev_rsi and latest_rsi > 65 and
        zscore > 2 and
        ema5 < ema20
    ):
        note = f"📉 空單均值回歸：突破布林上緣 + RSI轉弱 + Z-score={zscore:.2f} + EMA5下彎EMA20"
        return "SELL", note, zscore, latest_rsi, vwap, obv

    return None, None, None, None, None, None
    
# ✅ Step 1: 決定策略名稱（這是你根據條件選出來的）
strategy_name = "均值回歸"  # 或 "RROV" / "順勢策略"

# ✅ Step 2: 定義策略名稱正規化函數
def normalize_strategy_name(name):
    if "RROV" in name:
        return "RROV"
    elif "均值" in name or "mean" in name:
        return "均值回歸"
    elif "順勢" in name:
        return "順勢策略"
    return name

# ✅ Step 3: emoji 對照表
strategy_label_map = {
    "RROV": "📊 RROV 策略",
    "均值回歸": "🎯 均值回歸策略",
    "順勢策略": "📈 順勢策略",
}

signal_note = "📌 預設訊號"

# ✅ Step 4: 封裝成函數供後面用
def get_strategy_display(name):
    return strategy_label_map.get(normalize_strategy_name(name), "📌 未知策略")


def scan_market(symbol_list):
    global capital_left
    MIN_REQUIRED_CAPITAL = 3000
    if capital_left < MIN_REQUIRED_CAPITAL:
        print(f"[資金耗盡] 剩餘資金 ${capital_left:.2f} 已低於 ${MIN_REQUIRED_CAPITAL}，暫停掃描...")
        return

    for symbol in symbol_list:
        try:
            print(f"📡 掃描中：{symbol}")

            # === ✅ 1. 抓 K 線資料
            df = fetch_stock_data(symbol, POLYGON_API_KEY)

            if df is None or df.empty:
                print(f"[跳過] {symbol} ➜ 無資料")
                continue

            # === ✅ 2. 抓基本面（含 fallback 平均成交量計算）
            fundamentals = get_fundamentals(symbol, POLYGON_API_KEY, df)

            # === ✅ 3. 基本面過濾（只過濾流動性與停牌）
            passed, reason = filter_fundamentals(symbol, fundamentals)
            if not passed:
                print(f"[跳過] {symbol} ➜ {reason}")
                continue

            # === ✅ 4. 技術指標分析
            indicators = calculate_indicators(df)
            if indicators is None:
                print(f"[跳過] {symbol} ➜ 指標產生失敗")
                continue

            # === ✅ 5. 防呆檢查：所有必要欄位是否存在且有值
            required_keys = [
                'rsi', 'roc', 'obv', 'zscore', 'vwap',
                'ema_5', 'ema_20', 'bb_upper', 'bb_lower', 'bb_mid'
            ]
            skip = False
            for key in required_keys:
                if key not in indicators or indicators[key].isna().iloc[-1]:
                    print(f"[跳過] {symbol} ➜ 指標 {key} 缺失或為 NaN")
                    skip = True
                    break
            if skip:
                continue

           # === 6. 抓技術指標資料
            if 'close' not in df.columns or df['close'].isnull().all():
                print(f"[跳過] {symbol} ➜ close 欄位無效")
                continue

            latest_price = df['close'].iloc[-1]
            if pd.isna(latest_price) or latest_price <= 0:
                print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
                continue
            rsi = indicators['rsi'].iloc[-1]
            roc = indicators['roc'].iloc[-1]
            obv = indicators['obv'].iloc[-1]
            obv_diff = obv - indicators['obv'].iloc[-2]
            zscore = indicators['zscore'].iloc[-1]
            vwap = indicators['vwap'].iloc[-1]
            ema5 = indicators['ema_5'].iloc[-1]
            ema20 = indicators['ema_20'].iloc[-1]
            upper_band = indicators['bb_upper'].iloc[-1]
            lower_band = indicators['bb_lower'].iloc[-1]
            mid_band = indicators['bb_mid'].iloc[-1]

            # ✅ EMA 金叉條件
            cond_ema_cross = (
                indicators["ema_5"].iloc[-2] < indicators["ema_20"].iloc[-2] and
                ema5 > ema20
            )
            # ✅ 插入這段統計 EMA 上彎 / 下彎 次數
            try:
                trend_series = indicators['ema_trend'].tail(20)  # 最後 20 根趨勢
                up_count = (trend_series == "上彎").sum()
                down_count = (trend_series == "下彎").sum()

                if up_count > down_count:
                    trend_bias = "偏多"
                elif down_count > up_count:
                    trend_bias = "偏空"
                else:
                    trend_bias = "盤整"

                ema_summary = f"EMA 趨勢：上彎 {up_count} 次｜下彎 {down_count} 次（{trend_bias}）"
            except Exception as e:
                ema_summary = "EMA 趨勢：統計失敗"
                print(f"[錯誤] {symbol} EMA 統計失敗：{e}")

            print(f"[EMA] {symbol} ➜ {ema_summary}")

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

            # === ✅ 技術傾向判斷（用來參考，不決定是否建倉）===
            bias = "⚪ 中性"
            if rsi > 60 or roc > 0.5 or ema5 > ema20 or obv_diff > 0:
                bias = "🟢 技術偏多（僅供參考）"
            elif rsi < 40 or roc < -0.5 or ema5 < ema20 or obv_diff < 0:
                bias = "🔴 技術偏空（僅供參考）"

            print(f"[技術傾向] {bias}｜{symbol} ➜ RSI={rsi:.1f}｜EMA5={ema5:.2f}｜EMA20={ema20:.2f}")

            # === ✅ 真正的策略篩選與訊號邏輯 ===
            signal_type, signal_note, direction, strategy_name = detect_trading_signal(symbol, df, indicators, debug=True)

            if not signal_type:
                print(f"[略過] {symbol} ➜ 無明確策略訊號，跳過")
                continue

            # ✅ 僅對「順勢策略」進行半山腰過濾
            if strategy_name == "順勢策略":
                if direction == "多":
                    if not (
                        rsi > 60 and ema5 > ema20 and
                        abs(latest_price - vwap) / vwap < 0.03 and
                        latest_price < indicators['bb_upper'].iloc[-1] * 0.98
                    ):
                        print(f"[略過] {symbol} ➜ 多單順勢策略條件不佳（可能半山腰）")
                        continue
                elif direction == "空":
                    if not (
                        rsi < 40 and ema5 < ema20 and
                        abs(latest_price - vwap) / vwap < 0.03 and
                        latest_price > indicators['bb_lower'].iloc[-1] * 1.02
                    ):
                        print(f"[略過] {symbol} ➜ 空單順勢策略條件不佳（可能半山腰）")
                        continue

            # ✅ 3. 推播建倉訊號
            signal_type, signal_note, direction, strategy_name = detect_trading_signal(symbol, df, indicators, debug=True)

            # 🔁 補上 EMA 統計摘要
            if signal_note:
                signal_note += f"\n📊 {ema_summary}"
            else:
                signal_note = f"📊 {ema_summary}"

            # ✅ 4. 信心分數與建倉資訊計算
            confidence_score = 0.0
            if signal_type:
                # 計算 VWAP 與 BB 偏離
                vwap_deviation = abs(latest_price - vwap) / vwap * 100 if vwap else 0
                lower_band = indicators['bb_lower'].iloc[-1] if 'bb_lower' in indicators and indicators['bb_lower'].iloc[-1] > 0 else None
                bb_deviation = ((latest_price - lower_band) / lower_band * 100) if lower_band else 0

                confidence_score = compute_confidence_score(
                    rsi=rsi,
                    roc=roc,
                    obv=obv,
                    zscore=zscore,
                    vwap_deviation=vwap_deviation,
                    bb_deviation=bb_deviation,
                    ema5=ema5,
                    ema20=ema20
                )

                # 計算投入資金與股數
                capital_per_trade = 5000
                position_size = int(capital_per_trade / latest_price)
            # ✅ 多單條件（RROV / 均值回歸）
            cond_rsi_long = rsi < 35 and rsi > indicators['rsi'].iloc[-2]
            cond_roc_long = roc < 0 and roc > indicators['roc'].iloc[-2]
            cond_obv_long = obv > indicators['obv'].iloc[-2]
            cond_vwap_near = abs(latest_price - vwap) / vwap < 0.05

            cond_price_low = latest_price < indicators['bb_lower'].iloc[-1]
            cond_rsi_rebound = rsi > indicators['rsi'].iloc[-2] and rsi < 35
            cond_zscore_low = zscore < -2
            ond_ema_cross = ema5 > ema20

            # ✅ 空單條件（RROV / 均值回歸）
            cond_rsi_short = rsi > 65 and rsi < indicators['rsi'].iloc[-2]
            cond_roc_short = roc > 0 and roc < indicators['roc'].iloc[-2]
            cond_obv_short = obv < indicators['obv'].iloc[-2]

            cond_price_high = latest_price > indicators['bb_upper'].iloc[-1]
            cond_rsi_drop = rsi < indicators['rsi'].iloc[-2] and rsi > 65
            cond_zscore_high = zscore > 2
            cond_ema_death = ema5 < ema20

            # ✅ 補上技術方向布林旗標（用於技術條件邏輯）
            is_bullish = rsi > 50 and ema5 > ema20
            is_bearish = rsi < 50 and ema5 < ema20

            # ✅ 順勢策略條件（多空共用）
            cond_ema_trend = ema5 > ema20 if is_bullish else ema5 < ema20
            cond_rsi_trend = rsi > 55 if is_bullish else rsi < 45
            cond_obv_trend = obv > indicators['obv'].iloc[-2] if is_bullish else obv < indicators['obv'].iloc[-2]
            cond_price_above_vwap = latest_price > vwap if is_bullish else latest_price < vwap

            # ✅ 條件分流填入（多空雙向）
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

            # ✅ 順勢策略條件（多空都可以計算）
            if is_bullish or is_bearish:
                trend_follow_conditions = {
                    "EMA順勢": cond_ema_trend,
                    "RSI順勢": cond_rsi_trend,
                    "OBV趨勢": cond_obv_trend,
                    "價格在VWAP之上/下": cond_price_above_vwap,
                }

            # ✅ 命中率計算（加入順勢）
            rrov_score = get_strategy_match_score("RROV", rrov_conditions)
            mean_score = get_strategy_match_score("均值回歸", mean_revert_conditions)
            trend_score = get_strategy_match_score("順勢策略", trend_follow_conditions)

            # === ✅ 印出策略命中分數（方便追蹤與 debug）===
            print(f"[策略診斷] {symbol} ➜ 順勢={trend_score:.2f}｜RROV={rrov_score:.2f}｜均值回歸={mean_score:.2f}")

            # === ✅ 若完全沒命中就跳過（都為 0）
            if trend_score == 0 and rrov_score == 0 and mean_score == 0:
                strategy_name = "策略未命中"
                strategy_display = "📌 未知策略"
                print(f"[策略選擇] {symbol} ➜ ❌ 無策略命中，跳過建倉")
                continue

            # === ✅ 改用 >= 比較，防止誤判 ===
            if trend_score >= rrov_score and trend_score >= mean_score:
                strategy_name = "順勢策略"
                strategy_display = get_strategy_display(strategy_name)
                print(f"[策略選擇] {symbol} ➜ 使用順勢策略（命中 {trend_score*100:.0f}%）")

            elif rrov_score >= mean_score:
                strategy_name = "RROV"
                strategy_display = get_strategy_display(strategy_name)
                print(f"[策略選擇] {symbol} ➜ 使用 RROV（命中 {rrov_score*100:.0f}%）")

            else:
                strategy_name = "均值回歸"
                strategy_display = get_strategy_display(strategy_name)
                print(f"[策略選擇] {symbol} ➜ 使用均值回歸（命中 {mean_score*100:.0f}%）")

            # === ✅ 額外 Debug 印出 Emoji 對照確認 ===
            print(f"[DEBUG] {symbol} ➜ 策略名稱：{strategy_name}｜emoji：{strategy_display}")
            
            # ✅ 集中處理 emoji 顯示（統一）
            strategy_display = get_strategy_display(strategy_name)

            # === ✅ 若三策略皆為 0，略過不進場
            if max(trend_score, rrov_score, mean_score) == 0:
                print(f"[略過] {symbol} ➜ 無策略條件命中，不進場")
                continue

            # === ✅ 若為「均值回歸策略」但未進場，印出診斷
            signal_type1, signal_note1, *_ = detect_mean_reversion_signals(df, symbol)
            if signal_type1 is None and signal_note1 and "未進場" in signal_note1:
                clean_note = signal_note1.replace("⛔ ", "").replace("：", "：\n")
                bb_dev = (
                    (latest_price - indicators["lower_band"].iloc[-1]) / indicators["lower_band"].iloc[-1] * 100
                    if indicators["lower_band"].iloc[-1] > 0 else 0
                )
                ema_diff = ema5 - ema20
                content = (
                    f"⛔ **[均值回歸未進場 - 診斷]** {symbol}\n"
                    f"🔍 原因：{clean_note}\n"
                    f"📉 價格=${latest_price:.2f}｜RSI={rsi:.1f}｜Z-score={zscore:.2f}\n"
                    f"📊 布林乖離：{bb_dev:.2f}%｜EMA 差值：{ema_diff:.2f}"
                )
                push_to_discord(content=content)

            # === ✅ 補充 RROV 診斷推播（未進場）
            signal_type2, signal_note2, direction2, strategy_name2 = detect_trading_signal(symbol, df, indicators)
            if signal_type2 is None and signal_note2:
                clean_note = signal_note2.replace("⛔ ", "").replace("（均值回歸）", "").replace("均值回歸", "").strip()
                vwap_dev = abs(latest_price - vwap) / vwap * 100 if vwap else 0
                content = (
                    f"⛔ **[RROV未進場 - 診斷]** {symbol}\n"
                    f"🔍 原因：{clean_note}\n"
                    f"📉 價格=${latest_price:.2f}｜RSI={rsi:.1f}｜ROC={roc:.2f}｜VWAP={vwap:.2f}｜VWAP乖離={vwap_dev:.2f}%"
                )
                push_to_discord(content=content)

            # === ✅ 潛伏預警（如 ALERT_BUY / ALERT_SELL）
            if signal_type1 in ["ALERT_BUY", "ALERT_SELL"]:
                obv_change = indicators['obv'].diff().iloc[-1] or 0
                vwap_dev = (latest_price - vwap) / vwap * 100 if vwap else 0
                bb_dev = 0
                if latest_price > indicators['bb_upper'].iloc[-1]:
                    bb_dev = (latest_price - indicators['bb_upper'].iloc[-1]) / indicators['bb_upper'].iloc[-1] * 100
                elif latest_price < indicators['bb_lower'].iloc[-1]:
                    bb_dev = (latest_price - indicators['bb_lower'].iloc[-1]) / indicators['bb_lower'].iloc[-1] * 100

                direction = "多" if signal_type1 == "ALERT_BUY" else "空"
                explanation = (
                    "潛伏多頭：貼近布林下緣 + RSI 低位 + Z-score 偏低 + EMA扭轉"
                    if signal_type1 == "ALERT_BUY" else
                    "潛伏空頭：突破布林上緣 + RSI 偏高 + Z-score 偏高，EMA即將死叉"
                )
                final_note = f"{signal_note1 or '⚠️ 無訊號說明'}\n📘 {explanation}"
                push_to_discord(
                    symbol=symbol,
                    price=latest_price,
                    rsi=rsi,
                    roc=roc,
                    vwap=vwap,
                    volume_ratio=indicators.get('volume_ratio', 1.0),
                    ema_cross=indicators.get('ema_status', 'N/A'),
                    candle_type=indicators.get('candle_type', 'N/A'),
                    signal_type=signal_type1,
                    signal_note=final_note,
                    confidence_score=None,
                    direction=direction,
                    strategy_name=strategy_display,
                    zscore=zscore,
                    obv=obv,
                    obv_change=obv_change,
                    vwap_deviation=vwap_dev,
                    bb_deviation=bb_dev
                )
                continue

            # === ✅ 若訊號成立才建倉 + 扣資金 + 推播 ===
            if signal_type1 in ["BUY", "SELL"]:
                direction = "多" if signal_type1 == "BUY" else "空"

                obv_change = indicators['obv'].diff().iloc[-1]
                if pd.isna(obv_change):
                    obv_change = 0

                vwap_deviation = (latest_price - indicators['vwap'].iloc[-1]) / indicators['vwap'].iloc[-1] * 100
                bb_deviation = ((latest_price - indicators['bb_lower'].iloc[-1]) / indicators['bb_lower'].iloc[-1]) * 100
                ema_diff = indicators['ema_5'].iloc[-1] - indicators['ema_20'].iloc[-1]

                confidence_score = compute_confidence_score(
                rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    obv=indicators['obv'].iloc[-1],
                    vwap_deviation=abs(vwap_deviation),
                    zscore=indicators['zscore'].iloc[-1],
                    bb_deviation=bb_deviation,
                    ema5=indicators['ema_5'].iloc[-1],
                    ema20=indicators['ema_20'].iloc[-1]
                )

                capital_required = min(TOTAL_CAPITAL * POSITION_RATIO, MAX_CAPITAL_PER_POSITION, capital_left)
                shares = int(capital_required / latest_price)

                if capital_left < capital_required or shares == 0:
                    print(f"[跳過] {symbol} ➜ 資金不足，剩餘資金={capital_left:.2f}，需要={capital_required:.2f}")

                elif can_enter_new_position(symbol, capital_required):
                    # ✅ 先定義策略名稱與 emoji 名稱
                    strategy_display = get_strategy_display(strategy_name)

                    # ✅ 抓最新指標值
                    zscore = indicators['zscore'].iloc[-1]
                    rsi = indicators['rsi'].iloc[-1]
                    roc = indicators['roc'].iloc[-1]
                    obv = indicators['obv'].iloc[-1]
                    ema5 = indicators['ema_5'].iloc[-1]
                    ema20 = indicators['ema_20'].iloc[-1]
                    vwap = indicators['vwap'].iloc[-1]
                    obv_diff = obv_change

                    # ✅ 建倉股數與資金（假設你已計算 shares、capital_required）
                    capital_per_trade = capital_required
                    position_size = shares  # 或 shares = compute_position_size(price)

                    # ✅ 執行建倉（一次傳入所有推播參數）
                    enter_position(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        signal_note=signal_note1,
                        rsi=rsi,
                        zscore=zscore,
                        strategy_name=strategy_name,
                        ema5=ema5,
                        ema20=ema20,
                        roc=roc,
                        obv=obv,
                        vwap=vwap,
                        confidence_score=confidence_score,
                        strategy_display=strategy_display  # ✅ 新增傳入 emoji 版策略名
                    )

                    # ✅ 組合推播訊息
                    signal_note = f"🐸 多單建倉訊號｜{strategy_display}" if "多" in direction else f"🐻 空單建倉訊號｜{strategy_display}"
                    push_note = (
                        f"{signal_note}\n"
                        f"📉 價格=${latest_price:.2f}｜RSI={rsi:.1f}｜策略：{strategy_display}｜信心分數：{confidence_score:.2f}\n"
                        f"💰 進場資金：${capital_per_trade:,.0f}｜📦 股數：{position_size:,} 股\n"
                        f"💼 剩餘資金：${capital_left:,.0f}"
                    )

                    # ✅ 推播
                    push_entry_to_discord(
                        symbol=symbol,
                        direction=direction,
                        price=latest_price,
                        signal_note=signal_note,
                        zscore=zscore,
                        rsi=rsi,
                        roc=roc,
                        obv=obv,
                        obv_change=obv_diff,
                        ema5=ema5,
                        ema20=ema20,
                        vwap=vwap,
                        strategy=strategy_display,
                        confidence_score=confidence_score,
                        capital_left=capital_left,
                        df=df
                    )

                    # ✅ 資金更新
                    quantity = position_size
                    capital_used = capital_per_trade
                    capital_left -= capital_used

                    # ✅ 記錄
                    record_entry_position(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        shares=quantity,
                        strategy_name=strategy_name,
                        confidence_score=confidence_score,
                        capital_used=capital_used
                    )

                    write_entry_to_sheet(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        shares=quantity,
                        capital=capital_used,
                        strategy=strategy_name,
                        confidence=confidence_score,
                        capital_left=capital_left
                    )

            # === ⛔ 沒進場，但有診斷理由，就推播診斷訊息
            elif signal_type1 is None and signal_note1 and "未進場" in signal_note1:
                try:
                    ema5 = indicators['ema_5'].iloc[-1]
                    ema20 = indicators['ema_20'].iloc[-1]
                    ema_diff = ema5 - ema20
                    ema_bias = "多頭" if ema_diff > 0 else "空頭" if ema_diff < 0 else "無趨勢"

                    bb_dev = ((latest_price - indicators['bb_lower'].iloc[-1]) / indicators['bb_lower'].iloc[-1]) * 100

                    # 簡化說明訊息
                    content = (
                        f"⛔ **[均值回歸未進場 - 診斷]** {symbol}\n"
                        f"🔍 原因：{signal_note1.replace('⛔ ', '')}\n"
                        f"📉 價格=${latest_price:.2f}｜RSI={indicators['rsi'].iloc[-1]:.1f}｜Z-score={indicators['zscore'].iloc[-1]:.2f}\n"
                        f"📊 布林乖離：{bb_dev:.2f}%｜EMA 差值：{ema_diff:.2f}（{ema_bias}）"
                    )
                except Exception as e:
                    content = f"⛔ **[均值回歸未進場 - 診斷]** {symbol}\n❌ 診斷資料缺失：{e}"

                push_to_discord(content)

                continue  # ✅ 跳過 RROV，避免重複建倉

            # === ✅ RROV 策略建倉
            if signal_type2 in ["BUY", "SELL"]:
                direction = "多" if signal_type2 == "BUY" else "空"

                obv_change = indicators['obv'].diff().iloc[-1]
                if pd.isna(obv_change):
                    obv_change = 0

                vwap_deviation = (latest_price - indicators['vwap'].iloc[-1]) / indicators['vwap'].iloc[-1] * 100
                bb_deviation = (latest_price - indicators['bb_lower'].iloc[-1]) / indicators['bb_lower'].iloc[-1] * 100
                ema_diff = indicators['ema_5'].iloc[-1] - indicators['ema_20'].iloc[-1]

                confidence_score = compute_confidence_score(
                    rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    obv=indicators['obv'].iloc[-1],
                    vwap_deviation=abs(vwap_deviation),
                    zscore=indicators['zscore'].iloc[-1],
                    bb_deviation=bb_deviation,
                    ema5=indicators['ema_5'].iloc[-1],
                    ema20=indicators['ema_20'].iloc[-1]
                )

                # === 資金與股數限制
                capital_required = min(TOTAL_CAPITAL * POSITION_RATIO, MAX_CAPITAL_PER_POSITION, capital_left)
                shares = int(capital_required / latest_price)

                if capital_left < capital_required or shares == 0:
                    print(f"[跳過] {symbol} ➜ 資金不足，剩餘資金={capital_left:.2f}，需要={capital_required:.2f}")
                    continue
                
                # ✅ 建倉前：防重複建倉
                if symbol in entered_positions:
                    print(f"[跳過] {symbol} ➜ 已建倉，避免重複進場")
                    continue

                if can_enter_new_position(symbol, capital_required):
                    # ✅ 先定義策略與顯示名稱
                    strategy_display = get_strategy_display(strategy_name)

                    # ✅ 指標與資金資訊
                    rsi = indicators['rsi'].iloc[-1]
                    zscore = indicators['zscore'].iloc[-1]
                    roc = indicators['roc'].iloc[-1]
                    obv = indicators['obv'].iloc[-1]
                    ema5 = indicators['ema_5'].iloc[-1]
                    ema20 = indicators['ema_20'].iloc[-1]
                    vwap = indicators['vwap'].iloc[-1]
                    obv_diff = obv_change
                    capital_per_trade = capital_required
                    position_size = shares

                    # ✅ 訊號說明（多 or 空）
                    signal_note = f"🐸 多單建倉訊號｜{strategy_display}" if "多" in direction else f"🐻 空單建倉訊號｜{strategy_display}"

                    # ✅ 建倉
                    enter_position(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        signal_note=signal_note,
                        rsi=rsi,
                        zscore=zscore,
                        roc=roc,
                        obv=obv,
                        ema5=ema5,
                        ema20=ema20,
                        vwap=vwap,
                        strategy_name=strategy_name,
                        confidence_score=confidence_score,
                        strategy_display=strategy_display
                    )

                    # ✅ 推播建倉訊息
                    push_entry_to_discord(
                        symbol=symbol,
                        direction=direction,
                        price=latest_price,
                        signal_note=signal_note,
                        zscore=zscore,
                        rsi=rsi,
                        roc=roc,
                        obv=obv,
                        obv_change=obv_diff,
                        ema5=ema5,
                        ema20=ema20,
                        vwap=vwap,
                        strategy=strategy_display,
                        confidence_score=confidence_score,
                        capital_left=capital_left,
                        df=df
                    )

                    # ✅ 資金更新與紀錄
                    capital_left -= capital_required

                    record_entry_position(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        shares=position_size,
                        strategy_name=strategy_name,
                        confidence_score=confidence_score,
                        capital_used=capital_required
                    )

                    write_entry_to_sheet(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        shares=position_size,
                        capital=capital_required,
                        strategy=strategy_name,
                        confidence=confidence_score,
                        capital_left=capital_left
                    )

            elif strategy_name == "順勢策略" and signal_type1 in ["BUY", "SELL"]:
                direction = "多" if signal_type1 == "BUY" else "空"

                # === ✅ 補強條件：防止買在半山腰 ===
                if direction == "多":
                    if not (
                        rsi > 60 and
                        ema5 > ema20 and
                        abs(latest_price - vwap) / vwap < 0.03 and
                        latest_price < indicators['bb_upper'].iloc[-1] * 0.98
                    ):
                        print(f"[略過] {symbol} ➜ 多單順勢策略條件不佳（可能半山腰）")
                        continue

                elif direction == "空":
                    if not (
                        rsi < 40 and
                        ema5 < ema20 and
                        abs(latest_price - vwap) / vwap < 0.03 and
                        latest_price > indicators['bb_lower'].iloc[-1] * 1.02
                    ):
                        print(f"[略過] {symbol} ➜ 空單順勢策略條件不佳（可能半山腰）")
                        continue

                obv_change = indicators['obv'].diff().iloc[-1]
                if pd.isna(obv_change):
                    obv_change = 0

                vwap_deviation = (latest_price - indicators['vwap'].iloc[-1]) / indicators['vwap'].iloc[-1] * 100
                bb_deviation = (latest_price - indicators['bb_lower'].iloc[-1]) / indicators['bb_lower'].iloc[-1] * 100
                ema_diff = indicators['ema_5'].iloc[-1] - indicators['ema_20'].iloc[-1]

                confidence_score = compute_confidence_score(
                    rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    obv=indicators['obv'].iloc[-1],
                    vwap_deviation=abs(vwap_deviation),
                    zscore=indicators['zscore'].iloc[-1],
                    bb_deviation=bb_deviation,
                    ema5=indicators['ema_5'].iloc[-1],
                    ema20=indicators['ema_20'].iloc[-1]
                )

                capital_required = min(TOTAL_CAPITAL * POSITION_RATIO, MAX_CAPITAL_PER_POSITION, capital_left)
                shares = int(capital_required / latest_price)

                if capital_left < capital_required or shares == 0:
                    print(f"[跳過] {symbol} ➜ 資金不足，剩餘資金={capital_left:.2f}，需要={capital_required:.2f}")
                    return

                if symbol in entered_positions:
                    print(f"[跳過] {symbol} ➜ 已建倉，避免重複進場")
                    return

                if can_enter_new_position(symbol, capital_required):
                    strategy_display = get_strategy_display(strategy_name)

                    rsi = indicators['rsi'].iloc[-1]
                    zscore = indicators['zscore'].iloc[-1]
                    roc = indicators['roc'].iloc[-1]
                    obv = indicators['obv'].iloc[-1]
                    ema5 = indicators['ema_5'].iloc[-1]
                    ema20 = indicators['ema_20'].iloc[-1]
                    vwap = indicators['vwap'].iloc[-1]
                    obv_diff = obv_change
                    capital_per_trade = capital_required
                    position_size = shares

                    signal_note = f"📈 多單建倉訊號｜{strategy_display}" if "多" in direction else f"📉 空單建倉訊號｜{strategy_display}"

                    # ✅ 執行建倉
                    enter_position(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        signal_note=signal_note,
                        rsi=rsi,
                        zscore=zscore,
                        strategy_name=strategy_name,
                        ema5=ema5,
                        ema20=ema20,
                        roc=roc,
                        obv=obv,
                        vwap=vwap,
                        confidence_score=confidence_score,
                        strategy_display=strategy_display
                    )

                    # ✅ 推播訊息
                    push_entry_to_discord(
                        symbol=symbol,
                        direction=direction,
                        price=latest_price,
                        signal_note=signal_note,
                        zscore=zscore,
                        rsi=rsi,
                        roc=roc,
                        obv=obv,
                        obv_change=obv_diff,
                        ema5=ema5,
                        ema20=ema20,
                        vwap=vwap,
                        strategy=strategy_display,
                        confidence_score=confidence_score,
                        capital_left=capital_left,
                        df=df
                    )

                    # ✅ 更新資金
                    capital_left -= capital_required

                    record_entry_position(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        shares=position_size,
                        strategy_name=strategy_name,
                        confidence_score=confidence_score,
                        capital_used=capital_required
                    )

                    write_entry_to_sheet(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        shares=position_size,
                        capital=capital_required,
                        strategy=strategy_name,
                        confidence=confidence_score,
                        capital_left=capital_left
                    )
                # === 3. 出場邏輯
                if symbol in positions:
                    check_exit_and_notify(symbol, latest_price)
                    
        except Exception as e:
            print(f"[錯誤] {symbol} 描錯誤：{e}\n{traceback.format_exc()}")
            continue
def check_volume_alert(symbol, df, indicators):
    try:
        if 'close' not in df.columns or df['close'].isnull().all():
            print(f"[跳過] {symbol} ➜ close 欄位無效")
            return

        latest_price = df['close'].iloc[-1]
        if pd.isna(latest_price) or latest_price <= 0:
            print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
            return
        
        curr_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1.0

        rsi = indicators['rsi'].iloc[-1]
        roc = indicators['roc'].iloc[-1]
        vwap = indicators['vwap'].iloc[-1]
        zscore = indicators['zscore'].iloc[-1]
        obv = indicators['obv'].iloc[-1]
        upper_band = indicators['bb_upper'].iloc[-1]
        lower_band = indicators['bb_lower'].iloc[-1]
        ema_cross = indicators.get('ema_status', 'N/A')
        candle_type = indicators.get('candle_type', 'N/A')

        signal_type = None
        signal_note = ""
        direction = None
        strategy_name = None

        if volume_ratio >= 5:
            if rsi < 40 or latest_price < lower_band * 1.02:
                signal_type = "ALERT_VOLUME_SPIKE_LONG"
                signal_note = f"⚠️ **[預警 - 低檔爆量]** ➜ 量比={volume_ratio:.1f}x，RSI={rsi:.1f}"
                direction = "多"
                strategy_name = "爆量預警"

            elif rsi > 70 or latest_price > upper_band * 0.98:
                signal_type = "ALERT_VOLUME_SPIKE_SHORT"
                signal_note = f"⚠️ **[預警 - 高檔爆量]** ➜ 量比={volume_ratio:.1f}x，RSI={rsi:.1f}"
                direction = "空"
                strategy_name = "爆量預警"

        if signal_type:
            strategy_display = get_strategy_display(strategy_name)
            obv_change = obv - indicators['obv'].iloc[-2] if len(indicators['obv']) > 1 else 0
            vwap_deviation = abs(latest_price - vwap) / vwap * 100 if vwap else 0
            bb_deviation = (
                abs(latest_price - lower_band) / lower_band * 100 if direction == "多"
                else abs(latest_price - upper_band) / upper_band * 100
            )

            # ✅ 推播到 Discord
            push_to_discord(
                symbol=symbol,
                price=latest_price,
                rsi=rsi,
                roc=roc,
                vwap=vwap,
                volume_ratio=volume_ratio,
                ema_cross=ema_cross,
                candle_type=candle_type,
                signal_type=signal_type,
                signal_note=signal_note,
                confidence_score=0,
                direction=direction,
                strategy_name=strategy_name,
                zscore=zscore,
                obv=obv,
                obv_change=obv_change,
                vwap_deviation=vwap_deviation,
                bb_deviation=bb_deviation
            )

            # ✅ 寫入 Sheets ➜ 預警紀錄
            write_to_sheet([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 時間
                symbol,                                        # 股票代碼
                direction,                                     # 多空
                latest_price,                                  # 價格
                signal_type,                                   # 訊號類型
                signal_note,                                   # 描述
                round(rsi, 2), round(zscore, 2), round(vwap, 2), round(volume_ratio, 2),
                strategy_name, "預警"
            ], sheet="預警紀錄")
    except Exception as e:
        print(f"[錯誤] 爆量預警錯誤：{symbol} ➜ {e}")

from ta.momentum import RSIIndicator, ROCIndicator
from ta.volume import OnBalanceVolumeIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands

def calculate_indicators(df):
    if len(df) < 60:
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

    # === 基礎欄位 ===
    close = df['close']
    volume = df['volume']

    # === RSI（14）===
    rsi = RSIIndicator(close=close, window=15).rsi()

    # === ROC（9）===
    roc = ROCIndicator(close=close, window=10).roc()

    # === OBV ===
    obv = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

    # === Z-score（20）===
    rolling_mean = close.rolling(21).mean()
    rolling_std = close.rolling(21).std()
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

    # === EMA 趨勢判斷（上彎、下彎、糾結）===
    ema_5_slope = ema_5.diff()
    ema_20_slope = ema_20.diff()
    ema_trend = []
    for i in range(len(ema_5_slope)):
        if ema_5_slope.iloc[i] > 0 and ema_20_slope.iloc[i] > 0:
            ema_trend.append("上彎")
        elif ema_5_slope.iloc[i] < 0 and ema_20_slope.iloc[i] < 0:
            ema_trend.append("下彎")
        else:
            ema_trend.append("糾結")

    # === 成交量資訊 ===
    curr_volume = volume.iloc[-1]
    avg_volume = volume.rolling(20).mean().iloc[-1]
    volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1.0

    # === EMA 上穿 / 下彎 狀態判斷 ===
    ema_status = (ema_5 > ema_20).replace({True: "上穿", False: "下彎"})

    # === K 棒型態判斷（簡化）===
    last_open = df['open'].iloc[-1]
    last_close = df['close'].iloc[-1]
    last_high = df['high'].iloc[-1]
    last_low = df['low'].iloc[-1]

    body_size = abs(last_close - last_open)
    upper_shadow = last_high - max(last_close, last_open)
    lower_shadow = min(last_close, last_open) - last_low

    if body_size < 0.1 * (last_high - last_low):
        candle_type = "十字線"
    elif last_close > last_open and lower_shadow > 2 * body_size:
        candle_type = "錘頭"
    elif last_close < last_open and upper_shadow > 2 * body_size:
        candle_type = "流星"
    elif last_close > last_open:
        candle_type = "陽線"
    else:
        candle_type = "陰線"

    # === 回傳所有指標 ===
    return {
        'rsi': rsi,
        'roc': roc,
        'obv': obv,
        'zscore': zscore,
        'bb_lower': lower_band,
        'bb_upper': upper_band,
        'bb_mid': mid_band,
        'vwap': vwap,
        'ema_5': ema_5,
        'ema_20': ema_20,
        'ema_trend': pd.Series(ema_trend, index=df.index),
        'curr_volume': curr_volume,
        'volume_ratio': volume_ratio,
        'avg_volume': avg_volume,
        'ema_status': ema_status,
        'candle_type': candle_type
    }

def compute_confidence_score(rsi, roc, obv, vwap_deviation, zscore, bb_deviation, ema5, ema20):
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
    if abs(vwap_deviation) < 1.0:
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

def detect_trading_signal(symbol, df, indicators, debug=False, force_test=False):
    if 'volume' not in df.columns:
        print(f"[跳過] {symbol} 缺少 volume 欄位")
        return None, None, None, None

    if len(df) < 60:
        if debug:
            print(f"[跳過] {symbol} 資料不足（僅 {len(df)} 筆）")
        return None, None, None, None
    
    # === 6. 抓技術指標資料
    if 'close' not in df.columns or df['close'].isnull().all():
        print(f"[跳過] {symbol} ➜ close 欄位無效")
        return

    latest_price = df['close'].iloc[-1]
    if pd.isna(latest_price) or latest_price <= 0:
        print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
        return
    prev_close = df['close'].iloc[-2]
    price_change = abs(latest_price - prev_close) / prev_close

    rsi = indicators['rsi'].iloc[-1]
    rsi_prev = indicators['rsi'].iloc[-2]
    roc = indicators['roc'].iloc[-1]
    roc_prev = indicators['roc'].iloc[-2]
    obv = indicators['obv'].iloc[-1]
    obv_prev = indicators['obv'].iloc[-2]
    vwap = indicators['vwap'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]

    # ✅ 修正欄位命名
    lower_band = indicators['bb_lower'].iloc[-1]
    upper_band = indicators['bb_upper'].iloc[-1]

    # ✅ 防呆處理：避免除以零
    vwap_deviation = (latest_price - vwap) / vwap if vwap != 0 else None
    mean = df['close'].rolling(window=20).mean().iloc[-1]
    std = df['close'].rolling(window=20).std().iloc[-1]
    zscore = (latest_price - mean) / std if std and not pd.isna(std) else 0

    signal_type = None
    signal_note = None
    direction = None
    strategy_name = None

    # === 模擬測試用
    if force_test and symbol in ["TSLA", "NVDA"]:
        return "BUY", "🧪 測試訊號：模擬建倉", "多", "測試策略"

    # === 🟢 RROV 多單主策略
    if (
        rsi < 35 and rsi > rsi_prev and
        roc < 0 and roc > roc_prev and
        obv > obv_prev and
        abs(latest_price - vwap) / vwap < 0.05 and
        price_change < 0.01
    ):
        return "BUY", "🐸 多單建倉（RROV）：RSI回升 + ROC翻揚 + OBV上升 + VWAP貼近", "多", "RROV 主策略"

    # === 🟢 順勢多單策略
    if (
        rsi > 50 and rsi > rsi_prev and
        roc > 0 and roc > roc_prev and
        obv > obv_prev and
        latest_price > vwap and
        ema5 > ema20 and
        price_change < 0.015
    ):
        return "BUY", "🐸 多單建倉（順勢多單）：RSI>50轉強、VWAP上方、EMA多頭排列", "多", "順勢多單"

    # === 🟢 均值回歸多單策略
    if (
        latest_price < lower_band and
        rsi < 35 and rsi > rsi_prev and
        zscore < -2 and
        ema5 > ema20
    ):
        return "BUY", "🐸 多單建倉（均值回歸）：跌破布林 + RSI回升 + Z-score超跌", "多", "均值回歸"

    # === 🔴 RROV 空單主策略
    if (
        rsi > 65 and rsi < rsi_prev and
        roc > 0 and roc < roc_prev and
        obv < obv_prev and
        abs(latest_price - vwap) / vwap < 0.05 and
        price_change < 0.01
    ):
        return "SELL", "🐶 空單建倉（RROV）：RSI轉弱 + ROC下滑 + OBV下降 + VWAP貼近", "空", "RROV 主策略"

    # === 🔴 順勢空單策略
    if (
        rsi < 50 and rsi < rsi_prev and
        roc < 0 and roc < roc_prev and
        obv < obv_prev and
        latest_price < vwap and
        ema5 < ema20 and
        price_change < 0.015
    ):
        return "SELL", "🐶 空單建倉（順勢空單）：RSI<50轉弱、VWAP下方、EMA死叉", "空", "順勢空單"

    # === 🔴 均值回歸空單策略
    if (
        latest_price > upper_band and
        rsi > 65 and rsi < rsi_prev and
        zscore > 2 and
        ema5 < ema20
    ):
        return "SELL", "🐶 空單建倉（均值回歸）：突破布林 + RSI轉弱 + Z-score過熱", "空", "均值回歸"

    # === ⛔ 條件未滿足診斷
    if debug:
        reasons = []
        if rsi < 50:
            if rsi >= 35 or rsi <= rsi_prev: reasons.append("RSI未回升")
            if roc >= 0 or roc <= roc_prev: reasons.append("ROC未翻揚")
            if obv <= obv_prev: reasons.append("OBV未上升")
            if abs(latest_price - vwap) / vwap >= 0.05: reasons.append("價格未貼近VWAP")
            if price_change >= 0.01: reasons.append("價格已脫離起漲點")
        else:
            if rsi <= 65 or rsi >= rsi_prev: reasons.append("RSI未轉弱")
            if roc <= 0 or roc >= roc_prev: reasons.append("ROC未下滑")
            if obv >= obv_prev: reasons.append("OBV未下降")
            if abs(latest_price - vwap) / vwap >= 0.05: reasons.append("價格未貼近VWAP")
            if price_change >= 0.01: reasons.append("價格已脫離起跌點")
        if reasons:
            note = f"⛔ 無法進場：{'、'.join(reasons)}"
            return None, note, "無", "無策略"

    # === ⚠️ 爆量預警
    curr_volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].rolling(20).mean().iloc[-1]
    volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1.0

    if volume_ratio >= 5 and (rsi < 40 or latest_price < lower_band * 1.02):
        return "ALERT_VOLUME_SPIKE_LONG", f"⚠️ [預警 - 低檔爆量] ➜ 量比={volume_ratio:.1f}x，RSI={rsi:.1f}", "多", "爆量預警"
    elif volume_ratio >= 5 and (rsi > 70 or latest_price > upper_band * 0.98):
        return "ALERT_VOLUME_SPIKE_SHORT", f"⚠️ [預警 - 高檔爆量] ➜ 量比={volume_ratio:.1f}x，RSI={rsi:.1f}", "空", "爆量預警"

    # === 未達條件，輸出診斷訊息
    if debug:
        print(f"[未達條件] {symbol} ➜ 無進場訊號，RSI={rsi:.1f}、Z-score={zscore:.2f}、VWAP乖離={vwap_deviation:.2% if vwap_deviation else 'N/A'}")
    return None, None, None, None

def summarize_ema_direction(ema_series):
    results = []
    prev_direction = None
    start_time = None

    for i in range(len(ema_series)):
        direction = ema_series.iloc[i]
        time = ema_series.index[i]

        if direction != prev_direction:
            if prev_direction is not None:
                results.append((start_time, prev_time, prev_direction))
            start_time = time
        prev_direction = direction
        prev_time = time

    # 補上最後一段
    if prev_direction is not None:
        results.append((start_time, prev_time, prev_direction))

    # 格式化輸出
    summary = []
    for start, end, direction in results:
        count = len(ema_series[(ema_series.index >= start) & (ema_series.index <= end)])
        summary.append(f"{start.strftime('%m/%d %H:%M')} ～ {end.strftime('%H:%M')}：{direction}（{count}根）")

    return summary
       

# === 5. 推播模組（Discord） ===

def push_entry_to_discord(symbol, direction, price, signal_note, zscore=None, rsi=None, roc=None,
                          obv=None, obv_change=None, ema5=None, ema20=None,
                          vwap=None, strategy=None, confidence_score=None,
                          capital_left=None, df=None):  # ✅ 加入剩餘資金

    import requests
    from datetime import datetime

    emoji = "🐸" if direction == "多" else "🐶"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    capital_used = TOTAL_CAPITAL * POSITION_RATIO
    quantity = int(capital_used // price)

    # === EMA 趨勢統計（只在均值回歸策略中執行）
    ema_trend_text = "N/A"
    if strategy == "均值回歸策略" and df is not None:
        try:
            ema_trend_text = analyze_ema_trend(df)
        except Exception as e:
            ema_trend_text = "統計失敗"
            print(f"[⚠️ EMA 趨勢統計失敗] {symbol}：{e}")

    # === 基礎資訊區 ===
    content = f"{emoji} **[建倉訊號 - {direction}單]** {symbol}\n"
    content += f"💵 價格：${price:.2f}｜方向：{direction}\n"
    content += f"📈 資金投入：${capital_used:,.0f}｜股數：約 {quantity} 股\n"
    if capital_left is not None:
        content += f"💼 剩餘資金：${capital_left:,.0f}\n"

    # === 策略標籤轉換 ===
    strategy_label = {
        "均值回歸策略": "🎯 均值回歸策略",
        "RROV 策略": "📊 RROV 策略",
        "順勢策略": "📈 順勢交易策略"
    }.get(strategy, "📌 未知策略")

    # === 策略細節區 ===
    if strategy == "均值回歸策略":
        if zscore is not None:
            label = "超跌" if zscore < -2 else "超漲" if zscore > 2 else "偏離中"
            content += f"📊 Z-score：{zscore:.2f}（{label}）\n"
        if ema5 is not None and ema20 is not None:
            diff = ema5 - ema20
            content += f"📈 EMA 差值：{diff:.2f}（5日 - 20日）\n"
        if rsi is not None:
            content += f"📉 RSI：{rsi:.1f}\n"

    elif strategy == "RROV 策略":
        rsi_text = f"📉 RSI：{rsi:.1f}" if rsi is not None else ""
        roc_text = f"ROC：{roc:.2f}" if roc is not None else ""
        line = "｜".join([x for x in [rsi_text, roc_text] if x])
        if line:
            content += f"{line}\n"
        if vwap is not None and vwap > 0:
            vwap_deviation = abs(price - vwap) / vwap * 100
            content += f"📊 VWAP 乖離：{vwap_deviation:.2f}%\n"
        if obv_change is not None:
            content += f"📈 OBV 變化：{obv_change:.2f}\n"

    elif strategy == "順勢策略":
        if ema5 is not None and ema20 is not None:
            trend_diff = ema5 - ema20
            content += f"📈 EMA 順勢：{trend_diff:.2f}（5日 - 20日）\n"
        if rsi is not None:
            content += f"📉 RSI：{rsi:.1f}\n"
        if obv_change is not None:
            content += f"📈 OBV 趨勢變化：{obv_change:.2f}\n"
        if vwap is not None:
            position = "高於" if price > vwap else "低於"
            content += f"📊 價格{position} VWAP：{price:.2f} vs {vwap:.2f}\n"

    # === 其他通用附加項目 ===
    if confidence_score is not None:
        content += f"🔍 信心分數：{confidence_score:.2f}\n"

    content += f"📌 策略：{strategy_label}\n"
    content += f"📝 條件說明：{signal_note}\n"
    content += f"🕒 時間：{time_str}"

    # === 發送 Discord 推播 ===
    try:
        requests.post(WEBHOOK_URL, json={"content": content})
        print(f"[✅推播成功] {symbol} 建倉通知已送出")
    except Exception as e:
        print(f"[❌推播失敗] {symbol}：{e}")

def enter_position(symbol, price, direction, signal_note,
                   rsi=None, zscore=None, strategy_name="未標記策略",
                   ema5=None, ema20=None, upper_band=None, lower_band=None, mid_band=None,
                   roc=None, obv=None, vwap=None, confidence_score=None,
                   strategy_display=None):
    global capital_left

    # ✅ 價格合法性檢查（最重要修正點）
    if price is None or price <= 0:
        print(f"[錯誤] {symbol} 建倉失敗 ➜ 價格無效：{price}")
        return

    # ✅ 避免重複建倉
    if symbol in entered_positions:
        print(f"[跳過] {symbol} 已建倉，略過重複進場")
        return

    # ✅ 計算股數與資金
    shares, capital_used = compute_position_size(price)

    # ✅ 防呆判斷：價格 / 股數 / 資金不能為 0
    if shares <= 0 or capital_used <= 0:
        print(f"[跳過] {symbol} 建倉失敗 ➜ 價格={price}｜股數={shares}｜資金=${capital_used:.2f}")
        return

    # ✅ 扣除資金
    capital_left -= capital_used
    print(f"[資金確認] 已扣資金：${capital_used:.2f}，剩餘資金：${capital_left:,.2f}")

    now = datetime.now()

    # ✅ 記錄正式部位資訊（給出場模組使用）
    positions[symbol] = {
        "direction": direction,
        "entry_price": price,
        "quantity": shares,
        "entry_time": now,
        "capital_used": capital_used,
        "sell_stage": 0,
        "max_gain": 0.0,
        "strategy": strategy_name,
        "strategy_display": strategy_display,
        "rsi": rsi,
        "zscore": zscore,
        "ema5": ema5,
        "ema20": ema20,
        "roc": roc,
        "obv": obv,
        "vwap": vwap,
        "confidence_score": confidence_score,
    }

    # ✅ 建倉簡易紀錄
    entered_positions[symbol] = {
        "price": price,
        "direction": direction,
        "capital_used": capital_used,
        "shares": shares,
        "strategy": strategy_name,
        "confidence_score": confidence_score,
    }

    # ✅ 建倉成功輸出
    print(f"[✅紀錄] 已建倉：{symbol} @ ${price:.2f}｜方向：{direction}｜股數：{shares}｜策略：{strategy_display or strategy_name}")

def push_exit_to_discord(symbol, direction, entry_price, exit_price, return_rate, shares, reason):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    strategy = positions[symbol].get("strategy", "未標記策略")

    if strategy == '均值回歸':
        strategy_label = "🎯 均值回歸策略"
    elif strategy == '順勢策略':
        strategy_label = "🔥 順勢策略"
    else:
        strategy_label = "📊 RROV 策略"

    emoji = "🐸" if direction == "多" else "🐶"

    msg = f"""{emoji} **[出場 - {direction}單]** {symbol}
📌 策略：{strategy_label}
💵 出場價格：${exit_price:.2f}｜進場價格：${entry_price:.2f}
📊 報酬率：{return_rate:.2%}｜股數：{shares}
🔄 出場原因：{reason}
🕒 時間：{now}"""

    try:
        requests.post(WEBHOOK_URL, json={"content": msg})
    except Exception as e:
        print(f"[EXCEPTION] 出場推播錯誤：{e}")


import requests

POLYGON_API_KEY = "3Oa52hFieaUvTyToZudJanq39Rw9zApi"  # ⚠️ 替換為你的實際 API 金鑰

def fetch_latest_price(symbol):
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={POLYGON_API_KEY}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if "results" in data and data["results"]:
            return data["results"][0]["c"]  # "c" 是收盤價 close
        else:
            raise ValueError(f"Polygon 回傳格式異常：{data}")
    except Exception as e:
        print(f"[錯誤] 抓取 {symbol} 最新價格失敗：{e}")
        return None

def fetch_latest_prices_batch(symbols):
    prices = {}
    for symbol in symbols:
        try:
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?adjusted=true&apiKey={POLYGON_API_KEY}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if "results" in data and data["results"]:
                prices[symbol] = data["results"][0]["c"]
            else:
                print(f"[警告] {symbol} ➜ 無回傳價格")
        except Exception as e:
            print(f"[錯誤] {symbol} 價格查詢失敗：{e}")
    return prices

# === 4. 出場邏輯模組（三段鎖利 + 停損） ===

def check_exit_and_notify(symbol, latest_price):
    global capital_left

    if symbol not in positions:
        return

    # ✅ 先修補缺欄位，避免出錯
    repair_position(symbol)
    pos = positions[symbol]

    # ✅ 預檢必要欄位（避免 KeyError）
    required_keys = ["entry_price", "direction", "quantity", "capital_used", "sell_stage", "max_gain"]
    for key in required_keys:
        if key not in pos:
            print(f"[錯誤] {symbol} ➜ 缺少必要欄位：{key} ➜ {pos}")
            return

    # ✅ 確保欄位都有後，再取值
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
    elif strategy_key == "順勢策略":
        strategy_name = "🔥 順勢策略"
    elif strategy_key == "RROV":
        strategy_name = "📊 RROV 策略"
    else:
        strategy_name = f"📌 {strategy_key}"

    content = (
        f"{emoji} **[出場通知 - {strategy_name}｜{direction}單]** {symbol}\n"
        f"📈 出場價格：${latest_price:.2f} ｜ 數量：{exit_qty} 股\n"
        f"📊 報酬率：{return_rate * 100:.2f}% ｜ 獲利金額：${profit_dollar:.2f}\n"
        f"🔄 原因：{reason}\n"
        f"🕒 時間：{time_str}"
    )

    requests.post(WEBHOOK_URL, json={"content": content})

    # ✅ 寫入完整出場紀錄（包含報酬率、損益、持倉時間、技術指標）
    exit_position(symbol, latest_price, pos)

    # ✅ 若剩餘股數為 0 → 移除持倉
    if pos["quantity"] <= 0:
        del positions[symbol]

def repair_position(symbol):
    if symbol not in positions:
        return
    pos = positions[symbol]

    # 防呆補欄位
    if "entry_price" not in pos:
        print(f"[修補] {symbol} ➜ 缺少 entry_price，自動補 0.01（⚠️ 測試用）")
        pos["entry_price"] = 0.01

    if "sell_stage" not in pos:
        pos["sell_stage"] = 0

    if "max_gain" not in pos:
        pos["max_gain"] = 0.0

    if "capital_used" not in pos:
        pos["capital_used"] = 0.0

    if "quantity" not in pos:
        pos["quantity"] = 0

    if "direction" not in pos:
        pos["direction"] = "多"  # 預設為多單

def exit_position(symbol, current_price, position_data):
    from datetime import datetime
    exit_time = datetime.now()

    # 提取部位資訊
    entry_price = position_data['entry_price']
    shares = position_data['shares']
    entry_time = position_data['entry_time']

    # 🔧 如果 entry_time 是字串，轉為 datetime
    if isinstance(entry_time, str):
        try:
            entry_time = datetime.fromisoformat(entry_time)
        except:
            print(f"[錯誤] entry_time 無法轉換：{entry_time}")
            return

    # ✅ 防呆判斷：若為補值或股數為 0，直接跳過
    if entry_price is None or entry_price <= 0.05 or shares <= 0:
        print(f"[跳過] {symbol} ➜ 出場無效（entry_price={entry_price}, shares={shares}）")
        return

    # ✅ 計算出場績效指標
    return_rate, pnl, holding_minutes = calculate_exit_metrics(
        entry_price=entry_price,
        exit_price=current_price,
        shares=shares,
        entry_time=entry_time,
        exit_time=exit_time
    )
    # ✅ 這行就是你要放的位置 ✅
    if return_rate < -90 or return_rate > 500:
        print(f"[跳過] {symbol} ➜ 報酬率異常（{return_rate:.2f}%），可能是假價格")
        return

    # 如果報酬率計算失敗（None）
    if return_rate is None:
        print(f"[跳過] {symbol} ➜ 出場計算失敗，略過寫入")
        return

    # ✅ 寫入出場紀錄
    write_exit_to_sheet(
        symbol=symbol,
        entry_time=entry_time,
        exit_time=exit_time,
        return_rate=return_rate,
        pnl=pnl,
        holding_minutes=holding_minutes,
        exit_price=exit_price,  # ✅ 新增：實際出場價格
        rsi=position_data.get("rsi"),
        zscore=position_data.get("zscore"),
        roc=position_data.get("roc"),
        obv=position_data.get("obv"),
        vwap=position_data.get("vwap"),
        ema5=position_data.get("ema5"),
        ema20=position_data.get("ema20"),
        strategy_name=position_data.get("strategy_display", "未知策略")
    )

    print(f"[📤 出場完成] {symbol} ➜ 損益：${pnl:.2f}｜報酬率：{return_rate:.2f}%｜持倉：{holding_minutes} 分鐘")

# ✅ 出場總掃描函數（會呼叫上面）
def check_all_positions():
    if not positions:
        print("[持倉檢查] 目前無持倉，略過出場檢查")
        return

    print(f"[持倉檢查] 共 {len(positions)} 檔持倉 ➜ 開始檢查出場條件")
    for symbol in list(positions.keys()):
        try:
            latest_price = fetch_latest_price(symbol)
            check_exit_and_notify(symbol, latest_price)
        except Exception as e:
            print(f"[錯誤] 檢查 {symbol} 出場條件時出錯：{e}")

import time
import requests

def push_to_discord(
    symbol=None, price=None, rsi=None, roc=None, vwap=None, volume_ratio=None,
    ema_cross=None, candle_type=None,
    signal_type=None, signal_note=None, confidence_score=None,
    direction=None, strategy_name=None, zscore=None, obv=None,
    obv_change=None, vwap_deviation=None, bb_deviation=None,
    content=None  # ✅ 支援純文字推播
):
    try:
        # ✅ 如果是純文字訊息（如診斷、簡報等）
        if content and str(content).strip() != "":
            response = requests.post(WEBHOOK_URL, json={"content": content})
            
            if response.status_code == 429:
                retry_after = response.json().get("retry_after", 1.5)
                print(f"[限速] 診斷推播限速 ➜ 等待 {retry_after:.2f} 秒後重發")
                time.sleep(retry_after)
                requests.post(WEBHOOK_URL, json={"content": content})
            elif response.status_code != 204:
                print(f"[⚠️診斷推播失敗] ➜ {response.status_code} - {response.text}")
            else:
                print("[✅推播] 純文字訊息已發送")
            return  # ✅ 傳送完就不執行下面格式化訊息

        # ✅ 若非 content 模式，則為格式化訊息推播
        if not signal_note or str(signal_note).strip() == "":
            print("[⚠️] 推播內容為空，略過發送")
            return

        # === 組合格式化內容 ===
        emoji = "🐸" if direction == "多" else "🐶" if direction == "空" else "❔"

        rsi_text = f"{rsi:.1f}" if rsi is not None else "N/A"
        roc_text = f"{roc:.2f}" if roc is not None else "N/A"
        vwap_text = f"{vwap:.2f}" if vwap is not None else "N/A"
        zscore_text = f"{zscore:.2f}" if zscore is not None else "N/A"
        obv_text = f"{int(obv):,}" if obv is not None else "N/A"
        volume_text = f"{volume_ratio:.2f}x" if volume_ratio is not None else "N/A"
        confidence_text = f"{confidence_score:.2f}" if confidence_score is not None else "N/A"

        msg = (
            f"{emoji} **[{strategy_name}]** {symbol}\n"
            f"💵 價格：${price:.2f} | RSI：{rsi_text} | ROC：{roc_text} | Z-score：{zscore_text}\n"
            f"📊 VWAP：{vwap_text} | 成交量：{volume_text} | OBV：{obv_text}\n"
        )

        if vwap_deviation is not None:
            msg += f"📉 VWAP 乖離：{vwap_deviation:+.2f}%\n"
        if bb_deviation is not None:
            msg += f"📈 布林乖離：{bb_deviation:+.2f}%\n"
        if obv_change is not None:
            msg += f"🔄 OBV 變化量：{obv_change:+,.0f}\n"

        msg += (
            f"📈 EMA：{ema_cross}\n"
            f"🧠 信心分數：{confidence_text}\n"
            f"🔔 **訊號類型**：{signal_note}"
        )

        response = requests.post(WEBHOOK_URL, json={"content": msg})

        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 1.5)
            print(f"[限速] 格式化推播限速 ➜ 等待 {retry_after:.2f} 秒後重發")
            time.sleep(retry_after)
            requests.post(WEBHOOK_URL, json={"content": msg})
        elif response.status_code != 204:
            print(f"[⚠️警告] Discord 推播失敗 ➜ {response.status_code} - {response.text}")
        else:
            print("[✅推播] 格式化訊息已發送")

    except Exception as e:
        print(f"[❌錯誤] 推播失敗：{e}")
    
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

import random
import threading
import time

# ✅ 定時檢查持倉（每 60 秒觸發一次）
def schedule_exit_check():
    if positions:
        print(f"[排程] 執行出場掃描...")
        check_all_positions()
    else:
        print("[排程] 無持倉，跳過出場檢查")
    threading.Timer(10, schedule_exit_check).start()  # 10 秒後再次執行自己

# ✅ 主程式區（掃描建倉 + 出場排程）
if __name__ == "__main__":
    # ✅ 啟動定時出場檢查排程
    schedule_exit_check()

    # ✅ 持續執行市場掃描（每 3 分鐘隨機掃一次）
    while True:
        symbol_list = load_stock_list()
        random.shuffle(symbol_list)
        print(f"[掃描啟動] 共 {len(symbol_list)} 檔")
        
        scan_market(symbol_list)  # ⬅️ 執行建倉邏輯

        time.sleep(180)  # ✅ 每 180 秒（3 分鐘）掃一次