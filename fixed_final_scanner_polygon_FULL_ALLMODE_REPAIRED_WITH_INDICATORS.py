
import requests
import pandas as pd

from ta.momentum import RSIIndicator
from ta.trend import MACD
import requests

DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK"

def analyze_indicators_and_alert(df, symbol):
    try:
        rsi = RSIIndicator(close=df["close"]).rsi()
        macd = MACD(close=df["close"])
        macd_hist = macd.macd_diff()
        latest_rsi = rsi.iloc[-1]
        latest_macd = macd_hist.iloc[-1]

        print(f"📊 {symbol} RSI: {latest_rsi:.2f}, MACD Hist: {latest_macd:.4f}")
        if latest_rsi < 100:
            print(f"🚨 RSI 條件觸發：{latest_rsi}")
            send_discord_alert(f"✅ 多單訊號: {symbol} RSI={latest_rsi:.2f}, MACD翻紅")
        elif latest_rsi > 80 and latest_macd < 0:
            send_discord_alert(f"❌ 空單訊號: {symbol} RSI={latest_rsi:.2f}, MACD翻綠")
    except Exception as e:
        print(f"❌ {symbol} 指標判斷錯誤:{e}")

def send_discord_alert(message):
    try:
        payload = {"content": message}
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 204:
            print("📢 Discord 推播成功")
        else:
            print(f"⚠️ Discord 推播失敗,狀態碼:{response.status_code}")
    except Exception as e:
        print(f"❌ 推播失敗:{e}")

import os
from datetime import datetime

def fetch_stock_bars(symbol, multiplier=5, timespan="minute", from_date="2024-05-01", to_date="2024-05-23", adjusted=True, extended=False):
    api_key = os.getenv("POLYGON_API_KEY")
    if not extended:
        print(f"🔐 使用 API KEY:{api_key}")
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        params = {
            "adjusted": str(adjusted).lower(),
            "sort": "asc",
            "apiKey": api_key
        }
        print(f"🌐 正常盤資料請求:{url}?adjusted={params['adjusted']}&sort={params['sort']}&apiKey=***")
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"❌ API 回傳錯誤:{response.status_code} - {response.text}")
            return None
        data = response.json().get("results", [])
        if not data:
            print("⚠️ 無資料")
            return None
        df = pd.DataFrame(data)
        df["t"] = pd.to_datetime(df["t"], unit="ms")
        df = df.rename(columns={"t": "datetime", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        df = df.sort_values("datetime")
        df.set_index("datetime", inplace=True)
        return df
    else:
        url = f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
        params = {"apiKey": api_key}
        print(f"🌐 盤前/盤後 snapshot 請求:{url}?apiKey=***")
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"❌ Snapshot API 錯誤:{response.status_code} - {response.text}")
            return None
        data = response.json().get("ticker", {})
        if not data:
            print("⚠️ Snapshot 無資料")
            return None

        rows = []
        now = datetime.now()
        for label, block in [("preMarket", data.get("preMarket")), ("afterHours", data.get("afterHours"))]:
            if block:
                rows.append({
                    "datetime": now.replace(microsecond=0),
                    "open": block.get("o"),
                    "high": block.get("h"),
                    "low": block.get("l"),
                    "close": block.get("c"),
                    "volume": block.get("v")
                })

        if not rows:
            print("⚠️ 無盤前盤後數據")
            return None

        df = pd.DataFrame(rows)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        return df



from datetime import datetime, time as dtime

def is_extended_hours():
    now = datetime.utcnow().time()  # 使用 UTC,Polygon API 為美東時間
    return (now < dtime(13, 30) or now > dtime(20, 0))  # 美東時間 9:30am-4:00pm -> UTC 13:30–20:00



import time
import os
import time
import sys


import requests
import pandas as pd

from ta.momentum import RSIIndicator
from ta.trend import MACD
import requests

DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK"

def analyze_indicators_and_alert(df, symbol):
    try:
        rsi = RSIIndicator(close=df["close"]).rsi()
        macd = MACD(close=df["close"])
        macd_hist = macd.macd_diff()
        latest_rsi = rsi.iloc[-1]
        latest_macd = macd_hist.iloc[-1]

        print(f"📊 {symbol} RSI: {latest_rsi:.2f}, MACD Hist: {latest_macd:.4f}")
        if latest_rsi < 100:
            print(f"🚨 RSI 條件觸發：{latest_rsi}")
            send_discord_alert(f"✅ 多單訊號: {symbol} RSI={latest_rsi:.2f}, MACD翻紅")
        elif latest_rsi > 80 and latest_macd < 0:
            send_discord_alert(f"❌ 空單訊號: {symbol} RSI={latest_rsi:.2f}, MACD翻綠")
    except Exception as e:
        print(f"❌ {symbol} 指標判斷錯誤:{e}")

def send_discord_alert(message):
    try:
        payload = {"content": message}
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 204:
            print("📢 Discord 推播成功")
        else:
            print(f"⚠️ Discord 推播失敗,狀態碼:{response.status_code}")
    except Exception as e:
        print(f"❌ 推播失敗:{e}")

import os

def fetch_stock_bars(symbol, timespan="5minute", from_="2023-01-01", to_="2023-01-02", limit=1000):
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        raise ValueError("POLYGON_API_KEY 未設定,請於環境變數中設置。")

    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/{timespan}/{from_}/{to_}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": limit,
        "apiKey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "results" not in data:
            print(f"⚠️ 無有效資料:{symbol}")
            return pd.DataFrame()

        df = pd.DataFrame(data["results"])
        df["t"] = pd.to_datetime(df["t"], unit="ms")
        df.rename(columns={"t": "datetime", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}, inplace=True)
        df.set_index("datetime", inplace=True)
        return df

    except Exception as e:
        print(f"❌ {symbol} 資料抓取失敗:{e}")
        return pd.DataFrame()


print("▶️ 啟動掃描器初始化...")

# 1. 檢查模組
try:
    import pandas as pd
    from ta.momentum import RSIIndicator
    from ta.trend import MACD
    import requests
    from ta.volatility import BollingerBands
    print("✅ 所有必要模組成功載入")
except Exception as e:
    print(f"❌ 模組載入失敗: {e}")
    sys.exit()

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"

def analyze_indicators_and_alert(df, symbol):
    try:
        rsi = RSIIndicator(close=df["close"]).rsi()
        macd = MACD(close=df["close"])
        macd_hist = macd.macd_diff()
        latest_rsi = rsi.iloc[-1]
        latest_macd = macd_hist.iloc[-1]

        print(f"📊 {symbol} RSI: {latest_rsi:.2f}, MACD Hist: {latest_macd:.4f}")
        if latest_rsi < 100:
            print(f"🚨 RSI 條件觸發：{latest_rsi}")
            send_discord_alert(f"✅ 多單訊號: {symbol} RSI={latest_rsi:.2f}, MACD翻紅")
        elif latest_rsi > 80 and latest_macd < 0:
            send_discord_alert(f"❌ 空單訊號: {symbol} RSI={latest_rsi:.2f}, MACD翻綠")
    except Exception as e:
        print(f"❌ {symbol} 指標判斷錯誤:{e}")

def send_discord_alert(message):
    try:
        payload = {"content": message}
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 204:
            print("📢 Discord 推播成功")
        else:
            print(f"⚠️ Discord 推播失敗,狀態碼:{response.status_code}")
    except Exception as e:
        print(f"❌ 推播失敗:{e}")

    import numpy as np
    import requests
    from ta.momentum import RSIIndicator
    from ta.trend import MACD
    from ta.volatility import BollingerBands
    print("✅ 所有必要模組成功載入")
try:
    import pandas as pd
    import numpy as np
except Exception as e:
    print(f"模組載入失敗: {e}")
    sys.exit()

csv_path = "filtered_us_stocks_common_only.csv"
if not os.path.exists(csv_path):
    print(f"❌ 找不到股票清單:{csv_path}")
    sys.exit()
else:
    print(f"✅ 股票清單檔案存在:{csv_path}")

# 3. 載入股票清單並檢查格式
try:
    df = pd.read_csv(csv_path)
    if "symbol" not in df.columns:
        print("❌ 股票清單缺少 'symbol' 欄位")
        sys.exit()
    symbol_list = df["symbol"].dropna().tolist()
    print(f"✅ 成功載入股票清單,共 {len(symbol_list)} 檔")
except Exception as e:
    print(f"❌ 股票清單讀取失敗:{e}")
    sys.exit()

# 4. 檢查是否有 main() 函數定義
try:
    with open(__file__, encoding="utf-8") as f:
        content = f.read()
    if "def main" not in content:
        print("❌ 沒有定義 main() 主程式")
        sys.exit()
    else:
        print("✅ 偵測到 main() 主程式定義")
except Exception as e:
    print(f"❌ 無法檢查 main():{e}")
    sys.exit()

print("✅ 啟動追蹤區段執行完畢,接下來將進入主程式...")
time.sleep(1)


def get_us_stock_symbols_from_polygon():
    try:
        print("🔄 正在從 Polygon 線上獲取股票清單...")
        url = f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&limit=1000&apiKey={POLYGON_API_KEY}"
        symbols = []
        page = 1
        while True:
            paged_url = url + f"&page={page}"
            res = requests.get(paged_url)
            data = res.json()
            if 'results' not in data:
                break
            for item in data['results']:
                symbol = item['ticker']
                # 排除 ETF 或 OTC
                if '.' not in symbol and not symbol.endswith('W'):
                    symbols.append(symbol)
            if not data.get('next_url'):
                break
            page += 1
        print(f"✅ 共獲得 {len(symbols)} 檔股票")
        return symbols
    except Exception as e:
        print(f"❌ 無法取得線上股票清單:{e}")
        return []



# === S3 整合模組(自動下載 Polygon 雲端檔案) ===
import boto3
from botocore.config import Config


# === S3 整合模組(自動下載 Polygon 雲端檔案) ===
import boto3
from botocore.config import Config

def download_from_polygon_s3(bucket_name, object_key, local_file_path,
                              access_key='YOUR_ACCESS_KEY',
                              secret_key='YOUR_SECRET_KEY',
                              endpoint_url='https://files.polygon.io'):
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
            config=Config(signature_version='s3v4')
        )
        s3.download_file(bucket_name, object_key, local_file_path)
        print(f"✅ 已下載 {object_key} 到本地 {local_file_path}")
        return True
    except Exception as e:
        print(f"❌ S3 下載錯誤:{e}")
        return False


DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1373309204810563604/CUhbQ6sFvtNqSsEXxw7TnnMocMyV_VwfDqr7p3iiz3lXFUkzLNZXbzdO9EEEp87pk6lE"
DISCORD_WEBHOOK = None  # 保底定義,防止未設定錯誤

# === 模組補充 ===
import pandas as pd

from ta.momentum import RSIIndicator
from ta.trend import MACD
import requests

DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK"

def analyze_indicators_and_alert(df, symbol):
    try:
        rsi = RSIIndicator(close=df["close"]).rsi()
        macd = MACD(close=df["close"])
        macd_hist = macd.macd_diff()
        latest_rsi = rsi.iloc[-1]
        latest_macd = macd_hist.iloc[-1]

        print(f"📊 {symbol} RSI: {latest_rsi:.2f}, MACD Hist: {latest_macd:.4f}")
        if latest_rsi < 100:
            print(f"🚨 RSI 條件觸發：{latest_rsi}")
            send_discord_alert(f"✅ 多單訊號: {symbol} RSI={latest_rsi:.2f}, MACD翻紅")
        elif latest_rsi > 80 and latest_macd < 0:
            send_discord_alert(f"❌ 空單訊號: {symbol} RSI={latest_rsi:.2f}, MACD翻綠")
    except Exception as e:
        print(f"❌ {symbol} 指標判斷錯誤:{e}")

def send_discord_alert(message):
    try:
        payload = {"content": message}
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 204:
            print("📢 Discord 推播成功")
        else:
            print(f"⚠️ Discord 推播失敗,狀態碼:{response.status_code}")
    except Exception as e:
        print(f"❌ 推播失敗:{e}")

import ta
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator

import os
import requests
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY") or "y6h2VA5s_prMdJ2VzTtfFV3bRBdsslEV"
from datetime import datetime, timedelta



def fetch_data_from_polygon(symbol, timeframe='5'):
    try:
        now = datetime.utcnow()
        start = now - timedelta(days=5)
        start_str = start.strftime('%Y-%m-%d')
        end_str = now.strftime('%Y-%m-%d')

        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{timeframe}/minute/{start_str}/{end_str}?adjusted=true&sort=asc&limit=10000&apiKey={POLYGON_API_KEY}"
        res = requests.get(url)

        try:
            data = res.json()
            if 'results' not in data:
                print(f"❌ {symbol} 無資料")
                return None
        except Exception as e:
            print(f"⚠️ JSON 解析錯誤:{e}")
            return None

        df = pd.DataFrame(data['results'])
        df['t'] = pd.to_datetime(df['t'], unit='ms')
        df.set_index('t', inplace=True)
        df.rename(columns={
            'o': 'Open',
            'h': 'High',
            'l': 'Low',
            'c': 'Close',
            'v': 'Volume'
        }, inplace=True)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]

    except Exception as e:
        print(f"⚠️ 抓取 Polygon 資料時出錯:{e}")
        return None
    except Exception as e:
        print(f"❌ {symbol} 抓取失敗:{e}")
        return None

import requests
import time
import json
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === TICK 三重共振判斷 ===

def get_market_session(now):
    if now.hour < 9 or (now.hour == 9 and now.minute < 30):
        return "盤前"
    elif now.hour >= 16:
        return "盤後"
    else:
        return "盤中"

def check_tick_triple_confluence():
    # 模擬回傳 true 為符合共振(實際邏輯請按需設計)
    return True

# === Google Sheets 寫入函數 ===

# === ML 訓練資料寫入函式 ===
def write_to_ml_training_log(symbol, indicators, signal_type, return_pct, win_flag, holding_time):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1D76gQOfYNm_x8Xw5dKOba4sBN6uVwe0Kio0m2H3I1zE").sheet1

        now = datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d %H:%M:%S")
        row = [
            now,
            symbol,
            indicators.get("rsi", ""),
            indicators.get("macd", ""),
            indicators.get("vwap_position", ""),
            indicators.get("volume_ratio", ""),
            indicators.get("tmo", ""),
            indicators.get("tick_confluence", ""),
            signal_type,
            return_pct,
            win_flag,
            holding_time
        ]
        sheet.append_row(row)
    except Exception as e:
        print("寫入 ML 訓練資料失敗:", e)

import joblib
import numpy as np
import os

# === 載入 ML 模型並預測勝率 ===
def predict_win_probability(indicators):
    try:
        model_path = "ml_model.pkl"
        if not os.path.exists(model_path):
            print("未找到 ML 模型,略過機器學習過濾")
            return 1.0  # 如果沒有模型,預設都通過

        model = joblib.load(model_path)
        feature_vector = np.array([
            indicators.get('rsi', 0),
            indicators.get('macd', 0),
            indicators.get('vwap_position', 0),
            indicators.get('volume_ratio', 1),
            indicators.get('tmo', 0),
            1 if indicators.get('tick_confluence') else 0
        ])
        proba = model.predict_proba(feature_vector)[0][1]
        return proba
    except Exception as e:
        print("ML 預測錯誤:", e)
        return 1.0  # 如果錯誤,預設都通過


def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/")
        tab = sheet.worksheet(signal_type)
        tab.append_row([now, stock_code, price, win_rate, return_pct, holding_time])
    except Exception as e:
        print(f"❌ Sheets 寫入錯誤:{e}")

# === Discord 推播函數 ===
def send_discord_alert(message):
    try:
        if DISCORD_WEBHOOK:
            requests.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        print(f"⚠️ Discord 發送失敗:{e}")

# === 出場記錄函數 ===
def record_exit(symbol, exit_type, exit_price):
    entry_data = positions.get(symbol)
    if not entry_data:
        return
    entry_price = entry_data["entry"]
    entry_time = entry_data["time"]
    return_pct = round((exit_price - entry_price) / entry_price * 100, 2)
    holding_time = (datetime.now() - entry_time).total_seconds() / 60
    holding_str = f"{round(holding_time, 1)} 分鐘"
    win_rate = "WIN" if return_pct > 0 else "LOSS"
    print(f"⏹️ 出場紀錄 {symbol} | {exit_type} | 報酬 {return_pct}% | 持倉時間 {holding_str}")
    write_to_gsheet_tab(symbol, "正式出場", exit_price, win_rate, return_pct, holding_str)
    send_discord_alert(f"⏹️ 出場 [{symbol}] | {exit_type.upper()} | 報酬:{return_pct}% | 持倉:{holding_str}")
    del positions[symbol]



# === 讀取股票清單 CSV ===

def send_discord_message(message):
    try:
        send_discord_alert(message)
    except Exception as e:
        print(f"⚠️ Discord 發送錯誤:{e}")


def calculate_daily_performance():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("紀錄")
        data = sheet.get_all_records()
        if not data:
            return
        wins = sum(1 for row in data if float(row["報酬率"]) > 0)
        total = len(data)
        avg_return = sum(float(row["報酬率"]) for row in data) / total
        avg_holding = sum(float(row["持倉時間"]) for row in data) / total
        summary = [datetime.now().strftime("%Y-%m-%d"), total, wins, round(wins/total*100, 2), round(avg_return, 2), round(avg_holding, 2)]
        try:
            stat_sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("每日統計")
        except:
            stat_sheet = client.open_by_key(GOOGLE_SHEET_ID).add_worksheet(title="每日統計", rows="100", cols="10")
            stat_sheet.append_row(["日期", "總筆數", "獲利筆數", "勝率(%)", "平均報酬(%)", "平均持倉時間"], value_input_option="USER_ENTERED")
        stat_sheet.append_row(summary, value_input_option="USER_ENTERED")
        print("✅ 已寫入每日統計")
    except Exception as e:
        print(f"❌ 統計寫入失敗:{e}")


def retrain_ml_model():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet("ML訓練資料集")
        data = sheet.get_all_records()
        if len(data) < 100:
            return
        df = pd.DataFrame(data)
        features = df.drop(columns=["報酬率", "獲利與否"])
        labels = df["獲利與否"]
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(features, labels)
        with open("ml_model.pkl", "wb") as f:
            pickle.dump(model, f)
        print("✅ ML 模型已重新訓練並儲存")
    except Exception as e:
        print(f"❌ ML 模型訓練錯誤:{e}")


    # === 自動優化 RSI 條件 ===
    best_rsi = None
    best_win_rate = 0
    for rsi_thresh in [25, 28, 30, 32, 35]:
        rsi_data = data[data['rsi'] < rsi_thresh]
        if len(rsi_data) < 10:
            continue
        win_rate = rsi_data['label'].sum() / len(rsi_data)
        if win_rate > best_win_rate:
            best_win_rate = win_rate
            best_rsi = rsi_thresh
    print(f'✅ 最佳 RSI 條件為 < {best_rsi},勝率:{best_win_rate:.2%}')
    with open('best_params.txt', 'w') as f:
        f.write(f'RSI條件: < {best_rsi}, 勝率: {best_win_rate:.2%}')

    # === 寫入 Google Sheets:每日最佳參數 ===
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('gpc_cred.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1D76gQOfYNm_x8Xw5dKOba4sBN6uVwe0Kio0m2H3I1zE/').worksheet('每日最佳參數')
        now = datetime.now().strftime('%Y-%m-%d')
        sheet.append_row([now, best_rsi, f'{best_win_rate:.2%}', len(data), f'ml_model_{now}.pkl'])
    except Exception as e:
        print(f'⚠️ Google Sheets 寫入失敗:{e}')
def load_symbols():
    print("📂 嘗試載入股票清單 CSV 檔...")
    df = None
    try:
        df = pd.read_csv('filtered_us_stocks_common_only.csv')
        if 'symbol' in df.columns:
            return df['symbol'].dropna().tolist()
        else:
            return df.iloc[:, 0].dropna().tolist()
    except Exception as e:
        print(f'⚠️ 載入股票清單錯誤:{e}')
        return []
    try:
        df = pd.read_csv('filtered_us_stocks_common_only.csv')
        if 'symbol' in df.columns:
            return df['symbol'].dropna().tolist()
        else:
            return df.iloc[:, 0].dropna().tolist()
    except Exception as e:
        print(f'⚠️ 載入股票清單錯誤:{e}')
        return []

# === 資金控管設定 ===
capital = 100000  # 本金 10 萬
position_size_pct = 0.05  # 每筆投入 5%
max_stocks_held = 5
positions = {}  # 持倉紀錄:{symbol: {'entry': 價格, 'time': 時間}}

# === 判斷是否出場(停利/停損) ===
def check_exit_conditions(symbol, current_price):
    if symbol not in positions:
        return None
    entry = positions[symbol]['entry']
    gain = (current_price - entry) / entry * 100
    if gain >= 5:
        return 'take_profit'
    elif gain <= -2:
        return 'stop_loss'
    return None
# === 引入模組 ===
import numpy as np
print("✅ 腳本啟動成功,開始執行市場掃描器")


from datetime import datetime
import pytz

# 判斷美東時間是否為盤前 / 盤中 / 盤後
def get_market_session():
    eastern = pytz.timezone("US/Eastern")
    now_et = datetime.now(eastern).time()
    if now_et >= datetime.strptime("04:00", "%H:%M").time() and now_et < datetime.strptime("09:30", "%H:%M").time():
        return "pre"
    elif now_et >= datetime.strptime("09:30", "%H:%M").time() and now_et < datetime.strptime("16:00", "%H:%M").time():
        return "regular"
    elif now_et >= datetime.strptime("16:00", "%H:%M").time() and now_et < datetime.strptime("20:00", "%H:%M").time():
        return "post"
    else:
        return "closed"

# 範例推播(可與正式邏輯整合)
session = get_market_session()
print(f"⏰ 現在時段:{session}")

if session == "pre":
    send_discord_message("⚠️ [盤前異動] 偵測啟動中...")
elif session == "post":
    send_discord_message("⚠️ [盤後異動] 偵測啟動中...")
else:
    print("➡️ 非盤前盤後時段,不推播盤前/盤後訊息")


def send_discord_message(content):
    try:
        if response.status_code == 204:
            print(f"✅ 推播成功:{content}")
        else:
            print(f"❌ 推播失敗,狀態碼: {response.status_code},回應: {response.text}")
    except Exception as e:
        print(f"❌ 發送 Discord 推播時錯誤:{e}")


# === TICK 三重共振模組 ===
def get_tick_data():
    try:
        if df is None or df.empty:
            return None
        return df['Close']
    except Exception as e:
        print(f"TICK 資料抓取錯誤: {e}")
        return None

def check_tick_triple_confluence(tick_series):
    try:
        if len(tick_series) < 10:
            return False
        latest = tick_series.iloc[-1]
        history = tick_series[:-1]
        perc_rank = np.sum(history < latest) / len(history)
        slope = tick_series.diff().rolling(5).mean().iloc[-1]
        avg_bias = tick_series.tail(10).mean()
        return (
            (perc_rank >= 0.95 or perc_rank <= 0.05) and
            abs(slope) > 50 and
            (avg_bias > 600 or avg_bias < -600)
        )
    except Exception as e:
        print(f"TICK 共振判斷錯誤: {e}")
        return False

# === 15分鐘共振 ===
def detect_15min_entry(symbol):
    try:
        if df is None or df.empty or len(df) < 10:
            return False
        close = df['Close']
        volume = df['Volume']
        rsi = RSIIndicator(close=close, window=14).rsi()
        macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
        macd_line = macd.macd()
        macd_signal = macd.macd_signal()
        ema = EMAIndicator(close=close.diff(), window=5).ema_indicator()
        conds = [
            rsi.iloc[-1] > 50,
            macd_line.iloc[-2] < macd_signal.iloc[-2] and macd_line.iloc[-1] > macd_signal.iloc[-1],
            close.iloc[-1] > vwma.iloc[-1],
            tmo.iloc[-1] > 0 and tmo.iloc[-2] <= 0,
            volume.iloc[-1] > volume.rolling(20).mean().iloc[-1] * 1.2
        ]
        return sum(conds) >= 3
    except Exception as e:
        print(f"[15分鐘多頭判斷錯誤] {symbol}: {e}")
        return False


# === 15分鐘空頭共振判斷 ===
def detect_15min_short_entry(symbol):
    try:
        if df is None or df.empty or len(df) < 10:
            return False
        close = df['Close']
        volume = df['Volume']
        rsi = RSIIndicator(close=close, window=14).rsi()
        macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
        macd_line = macd.macd()
        macd_signal = macd.macd_signal()
        ema = EMAIndicator(close=close.diff(), window=5).ema_indicator()
        conds = [
            rsi.iloc[-1] < 50,
            macd_line.iloc[-2] > macd_signal.iloc[-2] and macd_line.iloc[-1] < macd_signal.iloc[-1],
            close.iloc[-1] < vwma.iloc[-1],
            tmo.iloc[-1] < 0 and tmo.iloc[-2] >= 0,
            volume.iloc[-1] > volume.rolling(20).mean().iloc[-1] * 1.2
        ]
        return sum(conds) >= 3
    except Exception as e:
        print(f"[15分鐘空頭判斷錯誤] {symbol}: {e}")
        return False

# === 爆量啟動預警模組(多空共用)===
def detect_early_explosion(df, symbol):
    try:
        close = df['Close']
        volume = df['Volume']
        high = df['High']
        low = df['Low']
        rsi = RSIIndicator(close=close, window=14).rsi()
        ema = EMAIndicator(close=close.diff(), window=5).ema_indicator()
        vol_avg = volume.rolling(20).mean()

        # 上漲啟動條件
        breakout_up = close.iloc[-1] > high.shift(1).rolling(10).max().iloc[-1]
        strong_volume = volume.iloc[-1] > vol_avg.iloc[-1] * 2
        momentum_up = (rsi.iloc[-1] > 50 and tmo.iloc[-1] > 0 and close.iloc[-1] > vwma.iloc[-1])

        # 下跌啟動條件
        breakout_down = close.iloc[-1] < low.shift(1).rolling(10).min().iloc[-1]
        momentum_down = (rsi.iloc[-1] < 50 and tmo.iloc[-1] < 0 and close.iloc[-1] < vwma.iloc[-1])

        if breakout_up and strong_volume and momentum_up:
            send_to_discord(f"🔔 爆量上漲預警:${symbol} 啟動中(突破高點 + 放量)")
        elif breakout_down and strong_volume and momentum_down:
            send_to_discord(f"🔻 爆量下跌預警:${symbol} 下殺中(跌破低點 + 放量)")
    except Exception as e:
        print(f"[爆量啟動預警錯誤] {symbol}: {e}")


# === 共振觀察訊號(提前預警)===
def detect_watch_signal_with_15min_tick(symbol, df):
    try:
        close = df['Close']
        volume = df['Volume']
        rsi = RSIIndicator(close=close, window=14).rsi()
        macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
        macd_line = macd.macd()
        macd_signal = macd.macd_signal()
        ema = EMAIndicator(close=close.diff(), window=5).ema_indicator()
        vol_avg = volume.rolling(20).mean()

        conds = [
            rsi.iloc[-1] > 45,
            macd_line.iloc[-2] < macd_signal.iloc[-2] and macd_line.iloc[-1] > macd_signal.iloc[-1],
            close.iloc[-1] > vwma.iloc[-1],
            tmo.iloc[-1] > 0 and tmo.iloc[-2] <= 0,
            volume.iloc[-1] > vol_avg.iloc[-1] * 1.5
        ]

        if sum(conds) >= 3:
            if detect_15min_entry(symbol):
                tick_series = get_tick_data()
                if tick_series is not None and check_tick_triple_confluence(tick_series):
                    send_to_discord(f"🔍[共振觀察]${symbol}(5分 + 15分 + TICK)")
                    write_to_gsheet_tab(symbol, "🔍 共振觀察", close.iloc[-1], "-", "-", "-")
    except Exception as e:
        print(f"[共振觀察錯誤] {symbol}: {e}")

import pandas as pd

from ta.momentum import RSIIndicator
from ta.trend import MACD
import requests

DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK"

def analyze_indicators_and_alert(df, symbol):
    try:
        rsi = RSIIndicator(close=df["close"]).rsi()
        macd = MACD(close=df["close"])
        macd_hist = macd.macd_diff()
        latest_rsi = rsi.iloc[-1]
        latest_macd = macd_hist.iloc[-1]

        print(f"📊 {symbol} RSI: {latest_rsi:.2f}, MACD Hist: {latest_macd:.4f}")
        if latest_rsi < 100:
            print(f"🚨 RSI 條件觸發：{latest_rsi}")
            send_discord_alert(f"✅ 多單訊號: {symbol} RSI={latest_rsi:.2f}, MACD翻紅")
        elif latest_rsi > 80 and latest_macd < 0:
            send_discord_alert(f"❌ 空單訊號: {symbol} RSI={latest_rsi:.2f}, MACD翻綠")
    except Exception as e:
        print(f"❌ {symbol} 指標判斷錯誤:{e}")

def send_discord_alert(message):
    try:
        payload = {"content": message}
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 204:
            print("📢 Discord 推播成功")
        else:
            print(f"⚠️ Discord 推播失敗,狀態碼:{response.status_code}")
    except Exception as e:
        print(f"❌ 推播失敗:{e}")


import requests
from datetime import datetime, timedelta

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY") or "y6h2VA5s_prMdJ2VzTtfFV3bRBdsslEV"

def fetch_data_from_polygon(symbol, timeframe='5'):
    try:
        now = datetime.utcnow()
        start = now - timedelta(days=5)
        start_str = start.strftime('%Y-%m-%d')
        end_str = now.strftime('%Y-%m-%d')

        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{timeframe}/minute/{start_str}/{end_str}?adjusted=true&sort=asc&limit=10000&apiKey={POLYGON_API_KEY}"
        res = requests.get(url)

        try:
            data = res.json()
            if 'results' not in data:
                print(f"❌ {symbol} 無資料")
                return None
        except Exception as e:
            print(f"⚠️ JSON 解析錯誤:{e}")
            return None

        df = pd.DataFrame(data['results'])
        df['t'] = pd.to_datetime(df['t'], unit='ms')
        df.set_index('t', inplace=True)
        df.rename(columns={
            'o': 'Open',
            'h': 'High',
            'l': 'Low',
            'c': 'Close',
            'v': 'Volume'
        }, inplace=True)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]

    except Exception as e:
        print(f"⚠️ 抓取 Polygon 資料時出錯:{e}")
        return None
    except Exception as e:
        print(f"❌ {symbol} 抓取失敗:{e}")
        return None

import requests
import time
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials

positions = {}

def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("/etc/secrets/gcp_cred.json", scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key("1MkjggPDw1t_sTDLoMYH1E7CFOYrv0CkxTROpj-9NAHw")

        if "共振進場" in signal_type:
            tab = "共振進場"
        elif "共振預警" in signal_type:
            tab = "共振預警"
        elif "正式進場" in signal_type:
            tab = "正式進場"
        elif "預警" in signal_type:
            tab = "預警訊號"
        elif "出場" in signal_type:
            tab = "出場紀錄"
        else:
            tab = "其他"

        try:
            sheet = spreadsheet.worksheet(tab)
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=tab, rows="1000", cols="10")
            sheet.append_row(["時間", "股票代碼", "訊號類型", "價格", "勝率", "報酬率", "持倉時間"], value_input_option="USER_ENTERED")

        row = [now, stock_code, signal_type, price, win_rate, return_pct, holding_time]
        sheet.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        print(f"寫入 Google Sheets 失敗:{e}")

def send_to_discord(message):
    try:
        if DISCORD_WEBHOOK:
            requests.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        print(f"⚠️ Discord 發送失敗:{e}")
def is_market_open():
    eastern = pytz.timezone("US/Eastern")
    now_est = datetime.now(eastern)
    if now_est.weekday() >= 5:
        return False
    market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_est.replace(hour=16, minute=0, microsecond=0)
    return market_open <= now_est <= market_close


def get_all_us_symbols():
    url = "https://raw.githubusercontent.com/ldavis44/stock-symbol-list/master/all/all_tickers.txt"
    try:
        r = requests.get(url)
        all_symbols = [s.strip().replace(".", "-") for s in r.text.splitlines() if s.strip()]
        # 過濾掉 OTC / ETF 類型(簡單篩掉常見 ETF / OTC 標記)
        filtered = [s for s in all_symbols if not any(tag in s.upper() for tag in ['ETF', '-U', '.PK', '.OB', 'OTC'])]
        return filtered
    except:
        return []

    url = "https://raw.githubusercontent.com/ldavis44/stock-symbol-list/master/all/all_tickers.txt"
    try:
        r = requests.get(url)
        return [s.strip().replace(".", "-") for s in r.text.splitlines() if s.strip()]
    except:
        return []

def get_tick_data():
    try:
        df.dropna(inplace=True)
        latest = df["Close"].iloc[-1]
        slope = df["Close"].diff().tail(3).mean()
        percentile = (df["Close"] < latest).sum() / len(df["Close"]) * 100
        return latest, slope, percentile
    except:
        return 0, 0, 50

def calc_indicators(df):
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["STD"] = df["Close"].rolling(20).std()
    df["Upper"] = df["SMA20"] + 2 * df["STD"]
    df["Lower"] = df["SMA20"] - 2 * df["STD"]
    df["Basis"] = df["SMA20"]
    rsi = df["Close"].rolling(21).apply(lambda x: 100 - (100 / (1 + (x.pct_change().dropna() > 0).sum() / max((x.pct_change().dropna() < 0).sum(), 1))), raw=False)
    tmo = rsi.rolling(5).mean().rolling(3).mean()
    signal = tmo.rolling(3).mean()
    df["TMO"] = tmo
    df["TMO_signal"] = signal
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal_macd = macd.ewm(span=9, adjust=False).mean()
    df["MACD_line"] = macd
    df["MACD_signal"] = signal_macd
    df["MACD_hist"] = macd - signal_macd
    df["TP"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["Cum_TPV"] = (df["TP"] * df["Volume"]).cumsum()
    df["Cum_Vol"] = df["Volume"].cumsum()
    df["VWAP"] = df["Cum_TPV"] / df["Cum_Vol"]
    df["VolAvg"] = df["Volume"].rolling(16).mean()
    return df

def enhanced_exit(symbol, direction, latest):
    try:
        entry = positions[symbol]
        entry_price = entry["price"]
        entry_time = entry["entry_time"]
        exit_price = latest["Close"]
        exit_time = datetime.now()
        pnl = exit_price - entry_price if direction == "long" else entry_price - exit_price
        return_pct = (pnl / entry_price) * 100
        return_pct_str = f"{return_pct:.2f}%"
        result = "Win" if return_pct > 0 else "Loss"
        holding_minutes = (exit_time - entry_time).total_seconds() / 60
        holding_str = f"{int(holding_minutes)}分鐘"
        exit_type = f"出場-{'多單' if direction == 'long' else '空單'}"
        send_to_discord(f"[{exit_type}] {symbol}｜現價 {exit_price:.2f}｜報酬率 {return_pct_str}｜{result}")
        write_to_gsheet_tab(symbol, exit_type, exit_price, result, return_pct_str, holding_str)
        del positions[symbol]
    except Exception as e:
        print(f"{symbol} 出場錯誤:{e}")

def check_signal(symbol, tick_val, tick_slope, tick_perc):
    try:
        if df is None or df.empty or len(df) < 30:
            return
        df = calc_indicators(df)
        latest = df.iloc[-1]
        if latest["Close"] < 1 or latest["Close"] > 10:
            return

        bull_tick = tick_val > 300 and tick_slope > 30 and tick_perc > 90
        bear_tick = tick_val < -300 and tick_slope < -30 and tick_perc < 10
        long_general = latest["TMO"] > latest["TMO_signal"] and latest["MACD_line"] > 0 and latest["Close"] > latest["VWAP"]
        short_general = latest["TMO"] < latest["TMO_signal"] and latest["MACD_line"] < 0 and latest["Close"] < latest["VWAP"]
        long_strong = latest["Close"] > latest["Upper"] and latest["TMO"] > latest["TMO_signal"] and latest["MACD_hist"] > 0 and latest["Volume"] > latest["VolAvg"] * 1.2 and latest["Close"] > latest["VWAP"]
        short_strong = latest["Close"] < latest["Lower"] and latest["TMO"] < latest["TMO_signal"] and latest["MACD_hist"] < 0 and latest["Volume"] > latest["VolAvg"] * 1.2 and latest["Close"] < latest["VWAP"]

        if symbol in positions:
            entry = positions[symbol]
            if entry["type"] == "long" and (latest["Close"] >= entry["price"] + 5 or latest["Low"] <= entry["price"] - 2):
                enhanced_exit(symbol, "long", latest)
            elif entry["type"] == "short" and (latest["Close"] <= entry["price"] - 5 or latest["High"] >= entry["price"] + 2):
                enhanced_exit(symbol, "short", latest)

        if long_strong and bull_tick:
            send_to_discord(f"[🚨共振進場] {symbol} 多單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "共振進場-多單", latest["Close"], "N/A", "N/A", "0秒")
            positions[symbol] = {"price": latest["Close"], "type": "long", "entry_time": datetime.now()}
        elif short_strong and bear_tick:
            send_to_discord(f"[🚨共振進場] {symbol} 空單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "共振進場-空單", latest["Close"], "N/A", "N/A", "0秒")
            positions[symbol] = {"price": latest["Close"], "type": "short", "entry_time": datetime.now()}
        elif long_strong:
            send_to_discord(f"[✅正式進場] {symbol} 多單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "正式進場-多單", latest["Close"], "N/A", "N/A", "0秒")
            positions[symbol] = {"price": latest["Close"], "type": "long", "entry_time": datetime.now()}
        elif short_strong:
            send_to_discord(f"[✅正式進場] {symbol} 空單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "正式進場-空單", latest["Close"], "N/A", "N/A", "0秒")
            positions[symbol] = {"price": latest["Close"], "type": "short", "entry_time": datetime.now()}
        elif long_general and bull_tick:
            send_to_discord(f"[⚡️共振預警] {symbol} 多單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "共振預警-多單", latest["Close"], "N/A", "N/A", "尚未進場")
        elif short_general and bear_tick:
            send_to_discord(f"[⚡️共振預警] {symbol} 空單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "共振預警-空單", latest["Close"], "N/A", "N/A", "尚未進場")
        elif long_general:
            send_to_discord(f"[⚠️預警] {symbol} 多單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "預警-多單", latest["Close"], "N/A", "N/A", "尚未進場")
        elif short_general:
            send_to_discord(f"[⚠️預警] {symbol} 空單｜價格 {latest['Close']:.2f}")
            write_to_gsheet_tab(symbol, "預警-空單", latest["Close"], "N/A", "N/A", "尚未進場")
    except Exception as e:
        print(f"{symbol} 發生錯誤:{e}")


def run_daily_report():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1MkjggPDw1t_sTDLoMYH1E7CFOYrv0CkxTROpj-9NAHw")
        ws = sheet.worksheet("出場紀錄")
        records = ws.get_all_values()[1:]

        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        today_records = [r for r in records if r[0].startswith(today)]
        if not today_records:
            print("今天無出場資料")
            return
        wins = [r for r in today_records if "Win" in r[4]]
        losses = [r for r in today_records if "Loss" in r[4]]
        win_rate = round(len(wins) / len(today_records) * 100, 2)
        avg_return = round(sum([float(r[5].replace("%", "")) for r in today_records]) / len(today_records), 2)
        avg_hold = round(sum([int(r[6].replace("分鐘", "")) for r in today_records]) / len(today_records), 2)
        stat_sheet = sheet.worksheet("統計報表") if "統計報表" in [ws.title for ws in sheet.worksheets()] else sheet.add_worksheet(title="統計報表", rows="100", cols="10")
        stat_sheet.append_row([today, len(today_records), f"{win_rate}%", f"{avg_return}%", f"{avg_hold}分鐘"], value_input_option="USER_ENTERED")
        print("今日統計報表已寫入")
    except Exception as e:
        print("統計報表錯誤:", e)
# === 資金控管設定 ===
INITIAL_CAPITAL = 100000
POSITION_SIZE_PCT = 0.05
MAX_POSITION_PER_TRADE = 6000
MAX_ACTIVE_POSITIONS = 5
current_positions = {}  # 儲存目前持股狀態 {symbol: {"entry_price": .., "entry_time": .., "amount": ..}}

def can_enter_new_trade():
    return len(current_positions) < MAX_ACTIVE_POSITIONS

def calculate_position_amount(price):
    capital_to_use = min(INITIAL_CAPITAL * POSITION_SIZE_PCT, MAX_POSITION_PER_TRADE)
    shares = capital_to_use // price
    return shares, capital_to_use

def record_entry(symbol, price):
    shares, invested = calculate_position_amount(price)
    current_positions[symbol] = {
        "entry_price": price,
        "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "amount": invested,
        "shares": shares
    }
    print(f"✅ 進場:{symbol} @ ${price}, 金額 = ${invested}, 張數 = {shares}")

def record_exit(symbol, exit_price):
    if symbol in current_positions:
        entry = current_positions[symbol]
        profit = (exit_price - entry["entry_price"]) * entry["shares"]
        return_pct = profit / entry["amount"] * 100
        holding_time = f'{datetime.now() - datetime.strptime(entry["entry_time"], "%Y-%m-%d %H:%M:%S")}'
        print(f"📤 出場:{symbol} @ ${exit_price}, 報酬 = {return_pct:.2f}%, 持倉時間 = {holding_time}")
        del current_positions[symbol]
        return return_pct, holding_time
    return None, None




# === 停利 / 停損 設定 ===
TAKE_PROFIT_PCT = 5.0
STOP_LOSS_PCT = -2.0

def check_exit_conditions(symbol, current_price):
    if symbol in current_positions:
        entry = current_positions[symbol]
        entry_price = entry["entry_price"]
        change_pct = (current_price - entry_price) / entry_price * 100
        if change_pct >= TAKE_PROFIT_PCT or change_pct <= STOP_LOSS_PCT:
            return True, change_pct
    return False, 0.0








# === Discord 推播函式 ===
def send_discord_alert(message):
    try:
        if DISCORD_WEBHOOK:
            requests.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        print(f"⚠️ Discord 發送失敗:{e}")



# === Google Sheets 寫入函式 ===
def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/14SSmjk2Ae3rqx0VyiVoVWBXpq0NVNvsLs1RWckuX4Ko/").worksheet("正式進場")
        sheet.append_row([now, stock_code, signal_type, price, win_rate, return_pct, holding_time])
    except Exception as e:
        print("❌ Google Sheets 寫入失敗:", e)




def load_symbols():
    print("📂 嘗試載入股票清單 CSV 檔...")
    df = None
    try:
        df = pd.read_csv('filtered_us_stocks_common_only.csv')
        if 'symbol' in df.columns:
            return df['symbol'].dropna().tolist()
        else:
            return df.iloc[:, 0].dropna().tolist()
    except Exception as e:
        print(f'⚠️ 載入股票清單錯誤:{e}')
        return []
    """載入7000檔美股普通股清單(排除ETF與OTC)"""
    try:
        df = pd.read_csv("filtered_us_stocks_common_only.csv")
    except pd.errors.ParserError:
        print('⚠️ CSV 讀取錯誤,略過錯行')
    print(f"📊 股票清單載入成功,共 {len(df)} 檔")
    return df["symbol"].tolist()


def main():
    print("✅ 進入 main()")
    print("✅ 腳本啟動成功:V8_DEBUG 版本")
    print("🚀 啟動 main() 成功,準備進入股票清單擷取流程")
    print("✅ 執行的是 DEBUG 確認版本 SCANNER_FINAL_OK_V8")
    print("🔍 [DEBUG] 開始掃描符號列表...")

    symbols = get_us_stock_symbols_from_polygon()
    if not symbols:
        print("⚠️ 股票清單為空,請檢查 API Key 或網路")
        return
    print("🚀 開始進行掃描...")
    for idx, symbol in enumerate(symbols):
        print(f"   ▶️ [TRACE] 掃描第 {idx+1} 檔:{symbol}")
        for attempt in range(3):
            try:
                for attempt in range(3):
                    try:
                        df = fetch_stock_bars(symbol, interval='5', days=5)
                        if df is not None and len(df) > 0:
                            break
                    except Exception as e:
                        print(f'⚠️ 第 {attempt+1} 次抓 {symbol} 失敗:{e}')
                    time.sleep(1)
                if df is not None and len(df) > 0:
                    break
                else:
                    print(f'❌ {symbol} 無資料,已記錄')
                    with open('missing_data_log.txt', 'a') as f:
                        f.write(symbol + '\n')
                    break
            except Exception as e:
                print(f'⚠️ 第 {attempt+1} 次抓 {symbol} 失敗:{e}')
            time.sleep(1)
        if df is not None:
            try:
                tick_data = get_tick_data()
                tick_perc = 50.0  # 預設值,可替換為實際百分位計算
            except Exception as e:
                print(f'⚠️ 無法取得 TICK 資料:{e}')
                tick_data = None
            signal = check_signal(symbol, df, tick_data, tick_perc)
            if signal:
                send_discord(f"{symbol}:{signal}")



# === Polygon 29元 測試模式設定 ===
import time
import random
MAX_SYMBOLS = 5  # 每輪最多掃描幾檔
SCAN_INTERVAL = 60  # 每次掃描間隔(秒)
print("⚠️ [測試模式] 啟用 Polygon $29 測試方案,每輪僅掃描少量股票,避免限速錯誤")
if __name__ == "__main__":
    main()
    import time
    while True:
        main()
        time.sleep(30)



# === 主程式 ===

def main():
    print("✅ 進入 main()")
    print("✅ 腳本啟動成功:V8_DEBUG 版本")
    print("🚀 啟動 main() 成功,準備進入股票清單擷取流程")
    print("✅ 執行的是 DEBUG 確認版本 SCANNER_FINAL_OK_V8")
    print("🔍 [DEBUG] 開始掃描符號列表...")

    symbols = get_us_stock_symbols_from_polygon()
    if not symbols:
        print("⚠️ 股票清單為空,請檢查 API Key 或網路")
        return
    print("🚀 開始進行掃描...")
    for idx, symbol in enumerate(symbols):
        print(f"   ▶️ [TRACE] 掃描第 {idx+1} 檔:{symbol}")
        for attempt in range(3):
            try:
                for attempt in range(3):
                    try:
                        df = fetch_stock_bars(symbol, interval='5', days=5)
                        if df is not None and len(df) > 0:
                            break
                    except Exception as e:
                        print(f'⚠️ 第 {attempt+1} 次抓 {symbol} 失敗:{e}')
                    time.sleep(1)
                if df is not None and len(df) > 0:
                    break
            except Exception as e:
                print(f'⚠️ 第 {attempt+1} 次抓 {symbol} 失敗:{e}')
            time.sleep(1)
        if df is not None:
            signal = check_signal(symbol, df, tick_data, tick_perc)
            if signal:
                send_discord(f"{symbol}:{signal}")


if __name__ == "__main__":
    main()
    while True:
        main()
        time.sleep(30)  # 每 30 秒掃描一次



# === 模組 ===
import pandas as pd

from ta.momentum import RSIIndicator
from ta.trend import MACD
import requests

DISCORD_WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK"

def analyze_indicators_and_alert(df, symbol):
    try:
        rsi = RSIIndicator(close=df["close"]).rsi()
        macd = MACD(close=df["close"])
        macd_hist = macd.macd_diff()
        latest_rsi = rsi.iloc[-1]
        latest_macd = macd_hist.iloc[-1]

        print(f"📊 {symbol} RSI: {latest_rsi:.2f}, MACD Hist: {latest_macd:.4f}")
        if latest_rsi < 100:
            print(f"🚨 RSI 條件觸發：{latest_rsi}")
            send_discord_alert(f"✅ 多單訊號: {symbol} RSI={latest_rsi:.2f}, MACD翻紅")
        elif latest_rsi > 80 and latest_macd < 0:
            send_discord_alert(f"❌ 空單訊號: {symbol} RSI={latest_rsi:.2f}, MACD翻綠")
    except Exception as e:
        print(f"❌ {symbol} 指標判斷錯誤:{e}")

def send_discord_alert(message):
    try:
        payload = {"content": message}
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 204:
            print("📢 Discord 推播成功")
        else:
            print(f"⚠️ Discord 推播失敗,狀態碼:{response.status_code}")
    except Exception as e:
        print(f"❌ 推播失敗:{e}")


import requests
from datetime import datetime, timedelta

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY") or "y6h2VA5s_prMdJ2VzTtfFV3bRBdsslEV"

def fetch_data_from_polygon(symbol, timeframe='5'):
    try:
        now = datetime.utcnow()
        start = now - timedelta(days=5)
        start_str = start.strftime('%Y-%m-%d')
        end_str = now.strftime('%Y-%m-%d')

        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{timeframe}/minute/{start_str}/{end_str}?adjusted=true&sort=asc&limit=10000&apiKey={POLYGON_API_KEY}"
        res = requests.get(url)

        try:
            data = res.json()
            if 'results' not in data:
                print(f"❌ {symbol} 無資料")
                return None
        except Exception as e:
            print(f"⚠️ JSON 解析錯誤:{e}")
            return None

        df = pd.DataFrame(data['results'])
        df['t'] = pd.to_datetime(df['t'], unit='ms')
        df.set_index('t', inplace=True)
        df.rename(columns={
            'o': 'Open',
            'h': 'High',
            'l': 'Low',
            'c': 'Close',
            'v': 'Volume'
        }, inplace=True)
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]

    except Exception as e:
        print(f"⚠️ 抓取 Polygon 資料時出錯:{e}")
        return None
    except Exception as e:
        print(f"❌ {symbol} 抓取失敗:{e}")
        return None

import requests
import time
import numpy as np
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from concurrent.futures import ThreadPoolExecutor, as_completed

# === Discord 與 Sheets 設定 ===
positions = {}
capital = 100000
position_size_pct = 0.05
max_stocks_held = 5

# === 股票清單 ===
def load_symbols():
    df = None
    try:
        df = pd.read_csv('filtered_us_stocks_common_only.csv')
        if 'symbol' in df.columns:
            return df['symbol'].dropna().tolist()
        else:
            return df.iloc[:, 0].dropna().tolist()
    except Exception as e:
        print(f'⚠️ 載入股票清單錯誤:{e}')
        return []
    try:
        df = pd.read_csv('filtered_us_stocks_common_only.csv')
    except pd.errors.ParserError:
        print('⚠️ CSV 讀取錯誤,略過錯行')
    return df['symbol'].tolist()

# === 判斷盤別 ===
def get_market_session():
    eastern = pytz.timezone("US/Eastern")
    now_et = datetime.now(eastern).time()
    if now_et >= datetime.strptime("04:00", "%H:%M").time() and now_et < datetime.strptime("09:30", "%H:%M").time():
        return "pre"
    elif now_et >= datetime.strptime("09:30", "%H:%M").time() and now_et < datetime.strptime("16:00", "%H:%M").time():
        return "regular"
    elif now_et >= datetime.strptime("16:00", "%H:%M").time() and now_et < datetime.strptime("20:00", "%H:%M").time():
        return "post"
    return "closed"

# === 推播功能 ===
def send_discord_alert(message):
    try:
        if DISCORD_WEBHOOK:
            requests.post(DISCORD_WEBHOOK, json={"content": message})
    except Exception as e:
        print(f"⚠️ Discord 發送失敗:{e}")

# === Sheets 寫入功能 ===
def write_to_gsheet_tab(stock_code, signal_type, price, win_rate, return_pct, holding_time):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("gcp_cred.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/xxx")
        tab = sheet.worksheet(signal_type)
        tab.append_row([now, stock_code, price, win_rate, return_pct, holding_time])
    except:
        pass

# === 出場條件 ===
def check_exit_conditions(symbol, current_price):
    if symbol not in positions:
        return None
    entry = positions[symbol]['entry']
    gain = (current_price - entry) / entry * 100
    if gain >= 5:
        return 'take_profit'
    elif gain <= -2:
        return 'stop_loss'
    return None

# === 出場紀錄 ===
def record_exit(symbol, exit_type, current_price):
    entry = positions[symbol]['entry']
    entry_time = positions[symbol]['time']
    pct = round((current_price - entry) / entry * 100, 2)
    hold = round((datetime.now() - entry_time).total_seconds() / 60, 1)
    win = "WIN" if pct > 0 else "LOSS"
    write_to_gsheet_tab(symbol, "正式出場", current_price, win, pct, hold)
    send_discord_alert(f"⏹️ 出場 [{symbol}]｜{exit_type}｜報酬 {pct}%｜持倉 {hold} 分鐘")
    del positions[symbol]

    rsi = RSIIndicator(close=close, window=14).rsi()
    macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    macd_line = macd.macd()
    macd_signal = macd.macd_signal()
    ema = EMAIndicator(close=close.diff(), window=5).ema_indicator()
# === 正式進場邏輯(需自定) ===
def detect_15min_entry(symbol):
    return False  # 範例:你可以自行寫條件

# === TICK 共振(模擬) ===
def check_tick_triple_confluence():
    import random

def random_choice():
    return random.choice([True, False])

# === 多執行緒掃描單支股票 ===
def scan_symbol(symbol):
    # 價格過濾:僅分析價格介於 1 到 10 美元的個股
    try:
        if latest_price < 1 or latest_price > 10:
            return  # 排除不在價格範圍內的股票
    except:
        return  # 若抓不到價格則略過

    try:
        if df is None or df.empty or len(df) < 10:
            return
        current_price = df['Close'].iloc[-1]
        session = get_market_session()
        if symbol in positions:
            exit_type = check_exit_conditions(symbol, current_price)
            if exit_type:
                record_exit(symbol, exit_type, current_price)
            return
        if len(positions) >= max_stocks_held:
            return
        if detect_15min_entry(symbol):
            positions[symbol] = {"entry": current_price, "time": datetime.now()}
            if check_tick_triple_confluence():
                write_to_gsheet_tab(symbol, "共振進場", current_price, "-", "-", "-")
                send_discord_alert(f"🚨 共振進場 [{symbol}]｜價格:{current_price}")
            else:
                write_to_gsheet_tab(symbol, "正式進場", current_price, "-", "-", "-")
                send_discord_alert(f"✅ 正式進場 [{symbol}]｜價格:{current_price}")
        elif detect_warning_entry(symbol, df):
            write_to_gsheet_tab(symbol, "預警試單", current_price, "-", "-", "-")
            send_discord_alert(f"⚠️ 預警試單 [{symbol}]｜價格:{current_price}｜盤別:{session}")
    except Exception as e:
        print(f"⚠️ 錯誤 {symbol}: {e}")

# === 主程式(多執行緒) ===

def main():
    print("✅ 進入 main()")
    print("✅ 腳本啟動成功:V8_DEBUG 版本")
    print("🚀 啟動 main() 成功,準備進入股票清單擷取流程")
    print("✅ 執行的是 DEBUG 確認版本 SCANNER_FINAL_OK_V8")
    print("🔍 [DEBUG] 開始掃描符號列表...")

    symbols = get_us_stock_symbols_from_polygon()
    if not symbols:
        print("⚠️ 股票清單為空,請檢查 API Key 或網路")
        return
    print("🚀 開始進行掃描...")
    for idx, symbol in enumerate(symbols):
        print(f"   ▶️ [TRACE] 掃描第 {idx+1} 檔:{symbol}")
        for attempt in range(3):
            try:
                for attempt in range(3):
                    try:
                        df = fetch_stock_bars(symbol, interval='5', days=5)
                        if df is not None and len(df) > 0:
                            break
                    except Exception as e:
                        print(f'⚠️ 第 {attempt+1} 次抓 {symbol} 失敗:{e}')
                    time.sleep(1)
                if df is not None and len(df) > 0:
                    break
            except Exception as e:
                print(f'⚠️ 第 {attempt+1} 次抓 {symbol} 失敗:{e}')
            time.sleep(1)
        if df is not None:
            signal = check_signal(symbol, df, tick_data, tick_perc)
            if signal:
                send_discord(f"{symbol}:{signal}")


if __name__ == "__main__":
    main()
    scan_round = 1
    while True:
        start_time = time.time()
        main()
        elapsed = time.time() - start_time
        print(f'✅ 第 {scan_round} 輪掃描完成,用時 {elapsed:.2f} 秒')
        print(f'⏳ 等待下一輪掃描 {SCAN_INTERVAL} 秒...')
        time.sleep(SCAN_INTERVAL)



import traceback

# === Google Sheets 無資料紀錄模組 ===
import gspread
import datetime
from oauth2client.service_account import ServiceAccountCredentials

# === Google Sheets 多分頁紀錄模組 ===
import gspread
import datetime
from oauth2client.service_account import ServiceAccountCredentials

def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("google_sheets_credentials.json", scope)
    client = gspread.authorize(creds)
    return client.open("交易紀錄總表")

def write_to_gsheet_tab(symbol, tab, *args):
    try:
        sheet = get_sheet()
        worksheet = sheet.worksheet(tab)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [symbol] + list(args) + [now]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"✅ 已寫入 {tab}:{symbol}")
    except Exception as e:
        print(f"❌ [Sheets 寫入失敗 - {tab}] {symbol}:{e}")

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [symbol, "無資料", now]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"✅ 已記錄無資料股票:{symbol}")
    except Exception as e:
        print(f"❌ [Sheets 寫入失敗] {symbol}:{e}")


def main():
    print("✅ 進入 main()")
    print("✅ 腳本啟動成功:V8_DEBUG 版本")
    print("🚀 啟動 main() 成功,準備進入股票清單擷取流程")
    print("✅ 執行的是 DEBUG 確認版本 SCANNER_FINAL_OK_V8")
    print("🔍 [DEBUG] 開始掃描符號列表...")

    symbols = get_us_stock_symbols_from_polygon()
    if not symbols:
        print("⚠️ 股票清單為空,請檢查 API Key 或網路")
        return
    print("🚀 開始進行掃描...")
    for idx, symbol in enumerate(symbols):
        print(f"   ▶️ [TRACE] 掃描第 {idx+1} 檔:{symbol}")
        for attempt in range(3):
            try:
                for attempt in range(3):
                    try:
                        df = fetch_stock_bars(symbol, interval='5', days=5)
                        if df is not None and len(df) > 0:
                            break
                    except Exception as e:
                        print(f'⚠️ 第 {attempt+1} 次抓 {symbol} 失敗:{e}')
                    time.sleep(1)
                if df is not None and len(df) > 0:
                    break
            except Exception as e:
                print(f'⚠️ 第 {attempt+1} 次抓 {symbol} 失敗:{e}')
            time.sleep(1)
        if df is not None:
            signal = check_signal(symbol, df, tick_data, tick_perc)
            if signal:
                send_discord(f"{symbol}:{signal}")


if __name__ == "__main__":
    main()
    print(">>> 啟動主函數 main()", flush=True)
    main()
