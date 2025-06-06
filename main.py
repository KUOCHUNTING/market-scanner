# === 技術指標 ===
# 技術指標（你有用 RSI、OBV、MFI）
from ta.volume import OnBalanceVolumeIndicator, MFIIndicator
from ta.volatility import AverageTrueRange  # 若有用 ATR 就保留
from ta.momentum import RSIIndicator  # 使用 RSI
# （若你用 KD 才需要 StochasticOscillator，否則可刪）

# 基本函數
import requests
import pandas as pd
from pytz import timezone
from datetime import datetime, timedelta, timezone as dt_timezone
from datetime import timezone as dt_timezone
import random


# === 補上缺失匯入 ===
from ta.trend import EMAIndicator
from ta.momentum import StochasticOscillator

# === 補上缺失函式 ===
def get_latest_price(symbol):
    # ✅ 模擬價格資料（實際應串接 API）
    print(f"[模擬] get_latest_price 呼叫:{symbol}")
    return 5.00  # 模擬價格

def get_latest_tick():
    # ✅ 模擬 TICK 值（實際應串接 API）
    print("[模擬] get_latest_tick 呼叫")
    return 500  # 模擬 TICK 指數

def detect_candle_type(df):
    # ✅ 基本 K 棒判斷邏輯
    close = df['close'].iloc[-1]
    open_ = df['open'].iloc[-1]
    if close > open_:
        return "陽線"
    elif close < open_:
        return "陰線"
    else:
        return "十字線"


# === 輔助資訊函數 ===
def get_market_cap(symbol):
    # ✅ 模擬值:預設回傳 3 億市值
    return 300_000_000

# Google Sheets 套件
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# .env 環境變數
from dotenv import load_dotenv
import os
# Alpaca API
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv
load_dotenv()

# ✅ 正確用法（字串方式）
TIMEFRAME_1MIN = TimeFrame(1, "Min")
TIMEFRAME_5MIN = TimeFrame(5, "Min")
TIMEFRAME_1DAY = TimeFrame(1, "Day")
# Alpaca（抓個股＋下單）
load_dotenv()  # ✅ 讀取 .env 檔
API_KEY = "AK1OZ6UJMMDD0MQ1ZJ76"
SECRET_KEY = "2ieUy3dxoSoD4PmzzKRy6fmunMb7H9VGdN1a2Kr3"
client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
# Polygon（抓 TICK）
POLYGON_API_KEY = "YmbcjRd1RA6l3pTlN0NvKRzd7OY4eV8k"
from polygon import RESTClient

def generate_daily_summary():
    try:
        # Google Sheets 連線
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Trading Log").worksheet("交易紀錄")  # ✅ 這裡是你紀錄進出場的分頁名稱

        # 讀取資料並轉為 DataFrame
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        # 篩選今天的資料
        today_str = datetime.now(timezone("US/Eastern")).strftime("%Y-%m-%d")
        df_today = df[df["entry_time"].str.startswith(today_str)]

        if df_today.empty:
            return f"📊 **[今日績效速報]**\\n🗓️ 日期:{today_str}\\n⚠️ 今日尚無任何交易紀錄。"

        total_trades = len(df_today)
        wins = len(df_today[df_today["return_rate"] > 0])
        losses = len(df_today[df_today["return_rate"] <= 0])
        win_rate = (wins / total_trades) * 100
        total_return = df_today["return_rate"].sum() * 100
        capital_used = df_today["capital_used"].sum()
        capital_left = df_today["capital_left"].iloc[-1]

        report = (
            f"📊 **[今日績效速報]**\\n"
            f"🗓️ 日期:{today_str}\\n"
            f"💼 總進場筆數:{total_trades}\\n"
            f"✅ 勝場:{wins}｜❌ 敗場:{losses}\\n"
            f"📈 勝率:{win_rate:.1f}%\\n"
            f"💰 總報酬率:{total_return:.2f}%\\n"
            f"💸 今日投入資金:${capital_used:,.0f}\\n"
            f"💼 剩餘資金:${capital_left:,.0f}"
        )
        return report
    except Exception as e:
        return f"[ERROR] 產生績效摘要失敗:{e}"
    
def init_sheets():
    print("[DEBUG] 開始執行 init_sheets()")  # ← 放最上面
    try:
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME)

        # 定義所有分頁與對應欄位
        pages = {
            "交易紀錄": ["日期", "股票代號", "進場時間", "出場時間", "持倉時間", "方向", "進場價格", "出場價格", "報酬率", "資金投入", "剩餘資金", "訊號類型", "是否TICK共振", "TICK 百分位", "TRIN 值", "TMO 值", "TMO 斜率", "RSI 值", "MACD 狀態", "VWAP 乖離", "成交量倍數", "OBV 方向", "策略版本", "信心分數"],
            "每日績效統計": ["日期", "勝場數", "負場數", "勝率", "總交易次數", "總投入資金", "總損益金額", "總報酬率", "最大獲利", "最大虧損", "平均持倉時間", "策略版本", "機器學習最佳策略"],
            "每日盤前情緒紀錄": ["日期", "TICK 百分位", "TICK 均值", "TICK 斜率", "TRIN 值", "VIX 值", "VIX 變化率", "當日預判方向"],
            "TICK共振紀錄": ["時間", "TICK 值", "TICK 百分位", "TICK 斜率", "TRIN 值", "共振股票代號"],
            "每日最佳參數": ["日期", "RSI 低點門檻", "TMO 金叉值門檻", "VWAP 乖離門檻", "ROC 濾網", "成交量倍數閾值", "VWAP 漲幅停利閾值", "選用策略名稱", "模型準確率"],
            "潛伏訊號紀錄": ["時間", "股票代號", "價格", "RSI", "TMO", "VWAP 乖離", "成交量倍數", "OBV", "當時盤勢情緒", "是否推播", "預警類型"]
        }

        for sheet_name, headers in pages.items():
            try:
                worksheet = sheet.worksheet(sheet_name)
                if not worksheet.row_values(1):
                    worksheet.insert_row(headers, index=1)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols=str(len(headers)))
                worksheet.insert_row(headers, index=1)
        print("[INFO] Google Sheets 初始化完成")
    except Exception as e:
        print(f"[ERROR] 初始化 Sheets 時失敗:{e}")   

now_utc = datetime.now(dt_timezone.utc)
now_est = datetime.now(timezone("US/Eastern"))
# === 資料來源 ===
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1372956363235393536/2bELr_6LwGlk2K7G4B3d3J0MBD5iv04IwC33pQaWxAHcRbgn6sBVtkvI_65FfmC4Um5f"  # 記得換成自己的

capital_left = 1000000  # 初始資金
report_sent = False     # 今日績效報告是否已推播
positions = {}          # 全部持倉記錄
entered_positions = {}  # 全域變數記錄進場股票
# ✅ 建立觀察名單的容器（追蹤潛伏預警股票）
observed_candidates = {}

def send_to_discord(message):  # ✅ 安全不會衝突
    try:
        payload = {"content": message}
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"[推播失敗] Discord 發送錯誤:{e}")
# === 技術工具函數 ===
    except Exception as e:
        print(f"[ERROR] {e}")
def get_tick_series(minutes=30):
    try:
        est = timezone("US/Eastern")
        now = datetime.now(est)
        start_time = now - timedelta(minutes=minutes)

        client = RESTClient(api_key=POLYGON_API_KEY)
        aggs = client.get_aggs(
            ticker="TICK",
            multiplier=1,
            timespan="minute",
            from_=start_time.strftime("%Y-%m-%dT%H:%M:%S"),
            to=now.strftime("%Y-%m-%dT%H:%M:%S"),
            limit=minutes,
            adjusted=True
        )

        if hasattr(aggs, 'results'):
            bars = aggs.results
        elif isinstance(aggs, list):
            bars = aggs
        else:
            print(f"[ERROR] TICK bars 結構無效")
            return None

        cleaned = []
        for bar in bars:
            b = vars(bar) if hasattr(bar, '__dict__') else bar
            if all(k in b for k in ["t", "o", "h", "l", "c", "v"]):
                cleaned.append({
                    "timestamp": pd.to_datetime(b["t"], unit='ms'),
                    "open": b["o"],
                    "high": b["h"],
                    "low": b["l"],
                    "close": b["c"],
                    "volume": b["v"]
                })

        df = pd.DataFrame(cleaned)
        return df if not df.empty else None

    except Exception as e:
        print(f"[ERROR] get_tick_series 錯誤:{e}")
        return None

# 動態風控參數
TRAIL_TRIGGER = 0.03  # +3% 啟動追蹤停利
TRAIL_MARGIN = 0.015  # 回落超過 1.5% 即出場
DEFAULT_STOP_LOSS = 0.02
DEFAULT_TAKE_PROFIT = 0.05

# ✅ 出場判斷邏輯（可放在最前面）
def check_exit_and_notify_dynamic(symbol, latest_price, now):
    should_exit = False  # ✅ 初始化避免未賦值錯誤
    global capital_left
    if symbol not in positions:
        return

    entry_data = positions[symbol]
    entry_price = entry_data['entry_price']
    direction = entry_data['direction']
    capital_used = entry_data['capital_used']
    entry_time = entry_data['entry_time']
    
    holding_time = int((now - entry_time).total_seconds())
    return_rate = (latest_price - entry_price) / entry_price if direction == "多" else (entry_price - latest_price) / entry_price

    # ✅ 插入:TRIN + TICK 共振風控強制平倉邏輯
    tick_value = get_latest_tick()
    trin_value = get_trin_value()

    if direction == "多" and trin_value >= 1.5 and tick_value < -1000:
        should_exit = True
        reason = f"⚠️ 市場風控出場:TRIN={trin_value:.2f}，TICK={tick_value}（極端空頭）"

    elif direction == "空" and trin_value <= 0.8 and tick_value > 1000:
        should_exit = True
        reason = f"⚠️ 市場風控出場:TRIN={trin_value:.2f}，TICK={tick_value}（極端多頭）"

    if should_exit:
        profit_percent = return_rate * 100
        exit_price = latest_price

        message = f"⚠️ **[風控 - 強制平倉]** ⚠️ {symbol} {direction}單\n" \
                  f"📊 TRIN:{trin_value:.2f}｜TICK:{tick_value}\n" \
                  f"📉 出場價格:${exit_price:.2f}｜進場:${entry_price:.2f}\n" \
                  f"💰 報酬率:{profit_percent:.2f}%｜持倉時間:{holding_time}秒\n" \
                  f"📌 理由:{reason}"

        push_to_discord(symbol, latest_price, rsi_value, macd_status, vwap_deviation, volume_ratio, ema5, candle_type, direction, signal_note)

        # ✅ 回收資金
        capital_left += capital_used
        del positions[symbol]
        return

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
    elif return_rate >= 0.05 and entry_data.get('sell_stage', 0) < 98:
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
        entry_data['holding_ratio'] = max(0, entry_data['holding_ratio'] - exit_ratio)

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

        # ✅ emoji 方向依照多空決定
        if direction == "空":
            emoji_up = "📉"
            emoji_down = "📈"
        else:
            emoji_up = "📈"
            emoji_down = "📉"

        send_to_discord(
            f"{signal_emoji} **[{stage_note}]** {symbol} @ ${exit_price:.2f}\n"
            f"{emoji_up} 報酬:{return_rate*100:.2f}%｜{emoji_down} 回落:{drawdown*100:.2f}%\n"
            f"💰 出場:{exit_ratio*100:.0f}%｜剩餘:{entry_data['holding_ratio']*100:.0f}%"
        )

        # ✅ 寫入 Sheets（改為完整參數呼叫新版 write_to_sheet）

        write_to_sheet(
            symbol=symbol,
            direction=direction,
            pnl=return_rate,
            entry_price=entry_price,
            exit_price=latest_price,
            volume_ratio=entry_data.get('volume_ratio', 1.0),
            obv=entry_data.get('obv', 0),
            rsi=entry_data.get('rsi', 50),
            tmo=entry_data.get('tmo', 0),
            candle_type="陽線" if latest_price > entry_price else "陰線",
            remark="✅ 出場",
            holding_time=holding_time,
            vwap=entry_data.get('vwap', 0),
            ema_cross=entry_data.get('ema_cross', ""),
            kd_status=entry_data.get('kd_status', ""),
            tick_percentile=entry_data.get('tick_percentile', 50),
            tick_slope=entry_data.get('tick_slope', 0),
            trin_value=entry_data.get('trin_value', 1.0),
            strategy_version="v1.0",
            confidence_score=entry_data.get('confidence_score', 0.8),
            signal_type="出場"
        )

        # ✅ 出場 Console 紀錄
        print(f"[出場紀錄] {symbol} | 報酬 {return_rate:.2%} | 出場比例 {exit_ratio:.0%}")

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

# === 系統模組 ===
    write_to_sheet(symbol, direction, entry_price, latest_price, return_rate, holding_time, signal_type,
               tick_percentile, trin_value, tmo_value, tmo_slope, rsi_value, macd_status, 
               vwap_deviation, volume_ratio, obv, rsi, tmo, candle_type, remark, 
               vwap, ema_cross, kd_status, tick_slope, strategy_version, confidence_score)
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open("Trading Log").worksheet("交易紀錄")
    except Exception as e:
        print(f"[ERROR] {e}")

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

    except Exception as e:
        print(f"[ERROR] Sheets 寫入失敗:{e}")


# ✅ 股票代號有效性判斷（過濾 ETF / OTC）
def is_valid_symbol(symbol: str) -> bool:
    symbol = symbol.upper()

    # 排除場外 OTC 股票（通常代號結尾為 F / Q）
    if symbol.endswith("F") or symbol.endswith("Q"):
        print(f"[FILTER] ❌ {symbol} 為 OTC 股票，排除")
        return False

    # 排除 ETF（代號中包含 ETF 關鍵字）
    if "ETF" in symbol:
        print(f"[FILTER] ❌ {symbol} 為 ETF，排除")
        return False

    return True  # ✅ 通過過濾

        # ✅ 股票篩選條件（專為小資策略）
def filter_stock_conditions(symbol, price, market_cap, avg_volume_10d, atr_3d):
    if price < 1 or price > 5:
        print(f"[FILTER] ❌ {symbol} 價格不符:{price}")
        return False

    if market_cap is not None and market_cap < 100_000_000:
        print(f"[FILTER] ❌ {symbol} 市值過低:{market_cap}")
        return False

    if avg_volume_10d is not None and avg_volume_10d < 500_000:
        print(f"[FILTER] ❌ {symbol} 平均量過低:{avg_volume_10d}")
        return False

    if atr_3d is not None and (atr_3d / price) < 0.02:
        print(f"[FILTER] ❌ {symbol} 波動不足:ATR={atr_3d:.2f}, Price={price:.2f}")
        return False

    return True  # ✅ 通過全部過濾

def add_to_observed_candidates(symbol, price, reason):
    now = datetime.now()
    observed_candidates[symbol] = {
        "start_time": now,
        "last_push_time": now,
        "entry_price": price,
        "reason": reason,
        "notified_expiring": False
    }
    print(f"[OBSERVE] 📌 已加入觀察名單:{symbol}（原因:{reason}）")

def check_abnormal_volume(symbol, df):
    """
    偵測是否發生異常爆量:最新成交量 > 過去 20 根平均量的 5 倍
    若條件成立，推播通知並將該 symbol 加入 observed_candidates
    """
    try:
        # 1. 計算過去 20 根 K 棒的平均成交量
        avg_volume_20 = df['volume'].iloc[-21:-1].mean()
        latest_volume = df['volume'].iloc[-1]
        latest_price = df['close'].iloc[-1]

        # 技術指標:OBV 與 VWAP
        obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()
        obv_rising = obv.iloc[-1] > obv.iloc[-3]

        vwap_series = (df['volume'] * df['close']).cumsum() / df['volume'].cumsum()
        vwap_deviation = abs(df['close'].iloc[-1] - vwap_series.iloc[-1]) / vwap_series.iloc[-1]
        vwap_slope_up = vwap_series.iloc[-1] > vwap_series.iloc[-3]

        # 補充技術指標
        ema5 = df['close'].ewm(span=5).mean().iloc[-1]
        rsi_value = RSIIndicator(close=df['close']).rsi().iloc[-1]
        macd_status = "DIF>DEA" if MACD(close=df['close']).macd_diff().iloc[-1] > 0 else "DIF<DEA"
        volume_ratio = latest_volume / avg_volume_20
        candle_type = "陽線" if df['close'].iloc[-1] > df['open'].iloc[-1] else "陰線"
        direction = "多"  # 假設方向為多（如需自動判斷可另外設條件）
        signal_note = "異常爆量潛伏"
        
        # 動態生成附註說明
        extra_notes = []
        if obv_rising:
            extra_notes.append("OBV 快速上揚")
        if vwap_slope_up:
            extra_notes.append("VWAP 呈現上升趨勢")
        indicator_text = "｜".join(extra_notes) if extra_notes else "無明顯技術指標變化"

        # ✅ 判斷是否異常爆量
        if latest_volume > 5 * avg_volume_20:
            message = (
                f"⚠️ **[💣💣異常爆量警告💣💣]** {symbol}\n"
                f"📈 價格:${latest_price:.2f}｜成交量:{latest_volume:,} 股\n"
                f"🧪 過去20根平均量:{avg_volume_20:,.0f} 股｜倍數:{volume_ratio:.1f}x\n"
                f"📊 技術指標:{indicator_text}\n"
                f"📌 已加入觀察名單，隨時注意回檔推播！\n"
                f"🕒 時間:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            push_to_discord(symbol, latest_price, rsi_value, macd_status, vwap_deviation,
                            volume_ratio, ema5, candle_type, direction, signal_note)

            # 3. 如果還沒在觀察名單，就加入（並記錄加入時間與理由）
            if symbol not in observed_candidates:
                observed_candidates[symbol] = {
                    "entry_time": datetime.now(),
                    "reason": "異常爆量觀察"
                }
                print(f"[OBSERVE] 🔔 已加入觀察名單:{symbol}（原因:異常爆量）")

    except Exception as e:
        print(f"[ERROR] 檢查 {symbol} 異常爆量時出錯:{e}")

# 範例:在主程式的迴圈中，每次抓完 df 之後呼叫這個函數
try:
    df_list = pd.read_csv("filtered_us_stocks_common_only.csv")
    stock_list = df_list['symbol'].tolist()
except Exception as e:
    print(f"[ERROR] 無法載入股票清單:{e}")
    stock_list = []

    check_abnormal_volume(symbol, df)   

def detect_latent_signal(df, rsi, tmo, obv, latest_price, latest_vwap):
    print(f"[DEBUG] 呼叫 detect_latent_signal 用參數:price={latest_price:.2f}, vwap={latest_vwap:.2f}")
    print(f"[DEBUG] 傳入參數:rsi={rsi:.2f}, tmo={tmo:.2f}, obv={obv.iloc[-1]:.2f}, price={latest_price:.2f}, vwap={latest_vwap:.2f}")

    auto_entry = False
    direction = None
    signal_note = None  # ✅ 預設為 None

    price = latest_price
    symbol = df['symbol'].iloc[-1]
    ema5 = df['close'].ewm(span=5, adjust=False).mean().iloc[-1]
    candle_type = "陽線" if df['close'].iloc[-1] > df['open'].iloc[-1] else "陰線"
    obv_direction = "上升" if obv.iloc[-1] > obv.iloc[-3] else "下滑"
    now = datetime.now()

    # ✅ 第一次通知（預警 - 多空轉折）
    if price < ema5 and rsi.iloc[-1] > rsi.iloc[-2] and tmo.iloc[-1] > tmo.iloc[-2]:
        add_to_observed_candidates(symbol, price, "RSI 回升 + TMO 金叉")
        signal_note = (
            f"⚠️ **[{symbol}] 潛伏 - 多頭轉折**\n"
            f"📈 價格雖跌，但動能轉強\n"
            f"📊 RSI:{rsi.iloc[-1]:.1f} ↗️｜TMO:{tmo.iloc[-1]:.2f} ↗️｜VWAP:下方｜🕯️ {candle_type}"
            f"📌 加入觀察名單，等待正式啟動"
        )
        push_to_discord(symbol, latest_price, rsi_value, macd_status, vwap_deviation, volume_ratio, ema5, candle_type, direction, signal_note)
        direction = "long"

    elif price > ema5 and rsi.iloc[-1] < rsi.iloc[-2] and tmo.iloc[-1] < tmo.iloc[-2]:
        add_to_observed_candidates(symbol, price, "RSI 過熱 + TMO 死叉")
        signal_note = (
            f"⚠️ **[{symbol}] 潛伏 - 空頭轉折**\n"
            f"📉 價格雖漲，但技術轉弱\n"
            f"📊 RSI:{rsi.iloc[-1]:.1f} ↘️｜TMO:{tmo.iloc[-1]:.2f} ↘️｜VWAP:上方｜🕯️ {candle_type}"
            f"📌 加入觀察名單，等待正式啟動"
        )
        push_to_discord(symbol, latest_price, rsi_value, macd_status, vwap_deviation, volume_ratio, ema5, candle_type, direction, signal_note)
        direction = "short"

    # ✅ 第二次通知（正式建倉 - 多頭）
    if (
        df['close'].iloc[-1] < df['close'].iloc[-3] and
        rsi.iloc[-1] > rsi.iloc[-2] and rsi.iloc[-2] < 30 and
        tmo.iloc[-1] > tmo.iloc[-2] and tmo.iloc[-2] < 0 and
        obv.iloc[-1] > obv.iloc[-2] > obv.iloc[-3] and
        price > df['close'].iloc[-2] and
        abs(price - latest_vwap) / latest_vwap < 0.01 and
        df['close'].iloc[-1] > df['open'].iloc[-1]  # K棒為陽線 
    ):
        if symbol in observed_candidates:
            first = observed_candidates[symbol]
            price_diff = abs(price - first["price"]) / first["price"]
            time_diff = (now - first["time"]).total_seconds() / 60

            if price_diff <= 0.02 and time_diff <= 30:
                del observed_candidates[symbol]

                # ✅ 補上方向與 VWAP 狀態
                vwap_status = "上穿" if price > latest_vwap else "下方"
                direction = "long"

                signal_note = (
                    f"🐮 **潛伏多頭（正式建倉）** 🐮 {symbol}\n"
                    f"📈 價格:${price:.2f}｜K棒:陽線｜動能轉強\n"
                    f"📊 RSI:{rsi.iloc[-1]:.1f} ⬆️｜TMO:{tmo.iloc[-1]:.2f} ⬆️｜OBV:連續上升\n"
                    f"📏 VWAP 偏離:{abs(price - latest_vwap) / latest_vwap:.2%}（貼近主力成本）\n"
                    f"📌 技術面低檔翻揚，進場時機成立\n"
                    f"🕒 時間:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )

                if not is_safe_entry(latest_rsi, latest_price, latest_vwap, direction="long", symbol=symbol):
                    return

                # ✅ 加入 30 分鐘共振判斷（不覆蓋原本的 signal_note）
                df_30m = fetch_30min_data(symbol)
                has_confluence_30m = check_30min_confluence(df_30m)
                if has_confluence_30m:
                    signal_note += "\n📌 技術共振:✅ 30M 共振"
                else:
                    signal_note += "\n📌 技術共振:⚠️ 無 30M 共振"
                    print(f"[INFO] 潛伏多頭無共振，僅推播觀察:{symbol}")
        push_to_discord(symbol, latest_price, rsi_value, macd_status, vwap_deviation, volume_ratio, ema5, candle_type, direction, signal_note)
                   
        return  # ❗ 中止潛伏多頭建倉

    if symbol not in entered_positions:
        entered_positions[symbol] = {
            "price": price,
            "direction": direction,
            "entry_time": now
        }

        positions[symbol] = {
            'entry_price': price,
            'capital_used': 10000,  # ✅ 如尚未控資金，可固定
            'entry_time': now,
            'direction': direction,
            'max_gain': 0,
            'holding_ratio': 1.0,
            'sell_stage': 0
        }

        # ✅ 🔔 在成功建倉後，加入這段推播
        message = (
            f"🐮**[潛伏 - 多頭進場]** 🐮{symbol}\n"
            f"📈 價格:${latest_price:.2f}｜已滿足全部建倉條件\n"
            f"📊 RSI:{rsi:.1f} {arrow_rsi}｜TMO:{tmo:.2f} {arrow_tmo}｜OBV:{obv_status}｜VWAP:{vwap_status_text}｜🕯️ {candle_type}\n"
            f"📈 技術共振:{confluence_note}\n"
            f"💰 資金投入:${capital_used:.0f}｜股數:{shares}｜剩餘資金:${capital_left:.0f}\n"
            f"🕒 時間:{now.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_to_discord(message)

    # ✅ 第二次通知（正式建倉 - 空頭）
    if (
        df['close'].iloc[-1] > df['close'].iloc[-3] and                   # 價格仍在高檔
        rsi.iloc[-2] > 70 and rsi.iloc[-1] < rsi.iloc[-2] and             # RSI 高檔轉弱
        tmo.iloc[-2] > 0 and tmo.iloc[-1] < tmo.iloc[-2] and              # TMO 向下轉折
        obv.iloc[-1] < obv.iloc[-2] < obv.iloc[-3] and                    # OBV 三連跌，加強資金流出判斷
        df['close'].iloc[-1] < df['close'].iloc[-2] and                   # 價格下跌
        abs(df['close'].iloc[-1] - latest_vwap) / latest_vwap < 0.01 and  # 價格貼近 VWAP
        df['close'].iloc[-1] < df['open'].iloc[-1]
    ):
        if symbol in observed_candidates:
            first = observed_candidates[symbol]
            price_diff = abs(price - first["price"]) / first["price"]
            time_diff = (now - first["time"]).total_seconds() / 60

            if price_diff <= 0.02 and time_diff <= 30:
                del observed_candidates[symbol]

                # ✅ 補上方向與 VWAP 狀態
                vwap_status = "跌破" if price < latest_vwap else "上方"
                direction = "short"

                signal_note = (
                    f"🐻 **潛伏空頭（正式建倉）** 🐻{symbol}\n"
                    f"📉 價格:${latest_price:.2f}｜K棒:{candle_type}\n"
                    f"📊 RSI:{rsi:.1f} {rsi_trend}｜TMO:{tmo:.2f} {tmo_trend}｜OBV:{obv_direction}\n"
                    f"📏 VWAP 偏離:{vwap_deviation:.2%}（貼近主力成本）\n"
                    f"📌 技術面確認空頭啟動，建倉時機已到\n"
                    f"🕒 時間:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )

                if not is_safe_entry(latest_rsi, latest_price, latest_vwap, direction="short", symbol=symbol):
                    return

                # ✅ 加入共振
                df_30m = fetch_30min_data(symbol)
                has_confluence_30m = check_30min_confluence(df_30m, direction="short")

                if has_confluence_30m:
                    signal_note += "\n📈 技術共振:✅ 30M 共振"
                else:
                    signal_note += "\n📈 技術共振:⚠️ 無 30M 共振"
                    print(f"[INFO] 潛伏空頭無共振，僅推播觀察:{symbol}")
        push_to_discord(symbol, latest_price, rsi_value, macd_status, vwap_deviation, volume_ratio, ema5, candle_type, direction, signal_note)
                    
        return  # ❗ 停止潛伏空頭建倉

    if symbol not in entered_positions:
        entered_positions[symbol] = {
            "price": price,
            "direction": direction,
            "entry_time": now
        }

        positions[symbol] = {
            'entry_price': price,
            'capital_used': 10000,  # ✅ 尚未資金控管情境
            'entry_time': now,
            'direction': direction,
            'max_gain': 0,
            'holding_ratio': 1.0,
            'sell_stage': 0
        }

        message = (
            f"🐻**[潛伏 - 空頭進場]** 🐻{symbol}\n"
            f"📉 價格:${latest_price:.2f}｜已滿足全部建倉條件\n"
            f"📊 RSI:{rsi:.1f} {arrow_rsi}｜TMO:{tmo:.2f} {arrow_tmo}｜OBV:{obv_status}｜VWAP:{vwap_status_text}｜🕯️ {candle_type}\n"
            f"📈 技術共振:{confluence_note}\n"
            f"💰 資金投入:${capital_used:.0f}｜股數:{shares}｜剩餘資金:${capital_left:.0f}\n"
            f"🕒 時間:{now.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_to_discord(message)


    return signal_note, auto_entry, direction



# 設定美東時間
now_utc = datetime.now(dt_timezone.utc)  # ✅ 使用標準庫 timezone.utc
now_est = datetime.now(timezone("US/Eastern"))  # ✅ 使用 pytz 處理美東時間
market_open = now_est.replace(hour=9, minute=30, second=0, microsecond=0)
market_close = now_est.replace(hour=16, minute=0, second=0, microsecond=0)

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
            f"💰 價格:${price:.2f} | RSI:{rsi:.1f} | TMO:{tmo:.2f}\n"
            f"📊 VWAP:{vwap_text} | 倍量:{volume_ratio:.2f}x\n"
            f"📈 EMA:{ema_cross} | KD:{kd_status} | K棒:{candle_type}\n"
            f"🔔 **訊號類型**:{signal_note}"
        )
        payload = {"content": message}
        response = requests.post(WEBHOOK_URL, json=payload)
        if response.status_code != 204:
            print(f"[WARNING] Discord 推播失敗:{response.status_code} - {response.text}")
    except Exception as e:
        print(f"[ERROR] 發送 Discord 推播失敗:{e}")
    except Exception as e:
        print(f"[ERROR] {e}")

# ✅ 2. Google Sheets 寫入函式（可放在 push_to_discord 下方）

def load_stock_list(filepath):
    try:
        df = pd.read_csv(filepath)
        return df['symbol'].tolist()
    except Exception as e:
        print(f"[ERROR] 無法讀取股票清單:{e}")
        return []
stock_list = load_stock_list("filtered_us_stocks_common_only.csv")

from datetime import datetime, timedelta, timezone

def fetch_stock_data(symbol):
    try:
        # ✅ 設定 UTC 時區時間範圍
        now_utc = datetime.now(dt_timezone.utc)
        start_time = now_utc - timedelta(minutes=500)

        # ✅ 設定請求物件（新版 SDK 用 enum 寫法）
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Minute,  # ✅ 使用正確格式
            start=start_time,
            end=now_utc
        )

        # ✅ 抓資料並轉換為 dataframe
        bars = client.get_stock_bars(request).df

        # ✅ 檢查資料是否有效
        if bars.empty or 'close' not in bars.columns:
            print(f"[警告] {symbol} 無效或資料不足，跳過")
            return None

        # ✅ 整理 dataframe 格式
        bars.reset_index(inplace=True)
        bars['symbol'] = symbol
        return bars

    except Exception as e:
        print(f"[ERROR] 無法抓取 {symbol}:{e}")
        return None
        
def analyze_stock_data(symbol, bars, tick_value, trin_value):
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
        print(f"[DATA] {symbol} 最新收盤價:{latest_price:.2f}")

        # === 價格與量能基本資料 ===
        latest_open = df['open'].iloc[-1]
        latest_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0
        candle_type = detect_candle_pattern(df)  # K棒型態（自訂函數）

        # === RSI ===
        rsi = RSIIndicator(close=df['close'], window=14).rsi()
        latest_rsi = rsi.iloc[-1]

        # === VWAP ===
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        latest_vwap = vwap.iloc[-1] if not pd.isna(vwap.iloc[-1]) else 0

        # === TMO（你自訂的函數）===
        tmo = calculate_tmo(df)
        latest_tmo = tmo.iloc[-1]
        tmo_slope = tmo.diff().iloc[-1]

        # === OBV ===
        obv = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()
        obv_direction = "上升" if obv.iloc[-1] > obv.iloc[-2] else "下降"

        # === EMA 均線 ===
        ema5 = EMAIndicator(close=df['close'], window=5).ema_indicator()
        ema20 = EMAIndicator(close=df['close'], window=20).ema_indicator()
        ema_cross = "✅" if ema5.iloc[-1] > ema20.iloc[-1] else "❌"

        # === KD 指標 ===
        kd = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=14)
        k_value = kd.stoch().iloc[-1]
        d_value = kd.stoch_signal().iloc[-1]
        kd_status = "金叉" if k_value > d_value else "死叉" if k_value < d_value else "中性"

        # === 顯示 Debug Log ===
        print(f"[INFO] {symbol} 最新收盤:{latest_price:.2f}")
        print(f"📊 RSI:{latest_rsi:.1f}｜TMO:{latest_tmo:.2f}（斜率:{tmo_slope:.2f}）｜VWAP:{latest_vwap:.2f}")
        print(f"📈 量能:{volume_ratio:.2f} 倍｜EMA5>EMA20:{ema_cross}｜OBV:{obv_direction}｜KD:{kd_status}｜K棒:{candle_type}")

           # === 顯示 Debug Log ===
        print(f"[INFO] {symbol} 最新收盤:{latest_price:.2f}")
        print(f"📊 RSI:{latest_rsi:.1f}｜TMO:{latest_tmo:.2f}（斜率:{tmo_slope:.2f}）｜VWAP:{latest_vwap:.2f}")
        print(f"📈 量能:{volume_ratio:.2f} 倍｜EMA5>EMA20:{ema_cross}｜OBV:{obv_direction}｜KD:{kd_status}｜K棒:{candle_type}")

        # 根據技術指標產生方向判斷
        direction = None  # 預設
        if rsi < 30 and tmo > 0:
            direction = "多"
        elif rsi > 70 and tmo < 0:
            direction = "空"

        # 顯示方向 debug
        if direction:
            print(f"[訊號方向] {symbol} => {direction}單 訊號")

        # ✅ 插入:TRIN + TICK 共振風控條件
        if direction == "多" and trin_value >= 1.5 and tick_value < -1000:
            msg = f"⛔ **[風控 - 禁止多單進場]** ⛔ {symbol}\n" \
                  f"📊 TRIN:{trin_value:.2f}（偏空）｜TICK:{tick_value}（極端空頭）\n" \
                  f"🔒 市場共振風險過高，多單策略封鎖進場"
        push_to_discord(symbol, latest_price, rsi_value, macd_status, vwap_deviation, volume_ratio, ema5, candle_type, direction, signal_note)
            
        return None

        if direction == "空" and trin_value <= 0.8 and tick_value > 1000:
            msg = f"⛔ **[風控 - 禁止空單進場]** ⛔ {symbol}\n" \
                  f"📊 TRIN:{trin_value:.2f}（偏多）｜TICK:{tick_value}（極端多頭）\n" \
                  f"🔒 市場強勢共振，空單策略封鎖進場"
        push_to_discord(symbol, latest_price, rsi_value, macd_status, vwap_deviation, volume_ratio, ema5, candle_type, direction, signal_note)
            return None

        # 如果需要回傳值，也可以在這裡整理成 dict
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
        print(f"[ERROR] analyze_stock_data 發生錯誤:{e}")
        return None

def evaluate_breakout_signal(symbol, df):
    if df is None or len(df) < 30:
        return None

    close = df['close']
    volume = df['volume']

    # 技術指標預設值（假設你前面有計算出這些）
    latest_price = close.iloc[-1]
    latest_vwap = ...  # ← 要補上 VWAP 計算
    latest_rsi = ...   # ← RSI 值
    latest_tmo = ...   # ← TMO 值
    tmo_slope = ...    # ← TMO 斜率
    volume_ratio = ... # ← 成交量倍數
    candle_type = ...  # ← K棒型態
    ema5_above_20 = ...# ← EMA5 > EMA20 布林條件

    # 判斷是否為突破預警
    if bb_contracted and price_sideways and obv_slope.iloc[-1] > 0:
        breakout_signal = (
            f"🚀 **[突破預警]** {symbol}\n"
            f"📉 價格橫盤 + 布林收斂\n"
            f"💰 OBV 斜率上升，可能準備啟動"
        )
        print(f"[BREAKOUT] {symbol}: {breakout_signal}")
        push_to_discord(symbol, latest_price, rsi_value, macd_status, vwap_deviation, volume_ratio, ema5, candle_type, direction, signal_note)
        return breakout_signal

    # ✅ 條件不符就退出
    if latest_price > latest_vwap * 1.08 or latest_price < latest_vwap * 0.92:
        print(f"[WARNING] {symbol} 價格偏離 VWAP 過大，跳過")
        return None

    # ✅ 多空條件開始判斷
    signal_note = None

    # 多頭轉折預警
    if (
        latest_rsi < 35 and rsi.iloc[-2] < rsi.iloc[-1] and             # RSI 低檔回升
        tmo_slope > 0 and                                               # TMO 斜率轉強
        df['vwap'].iloc[-1] > df['vwap'].iloc[-2] > df['vwap'].iloc[-3] and  # VWAP 呈現連續上升（趨勢轉強）
        latest_price < latest_vwap and                                 # 尚未突破 VWAP（避免過度追高）
        obv.iloc[-1] > obv.iloc[-3]                                     # OBV 顯示資金流入
    ):
        signal_note = (
            f"⚠️ **[預警 - 多頭轉折]** {symbol}\n"
            f"📈 RSI:{latest_rsi:.1f} ↗️｜TMO 斜率:{tmo_slope:.2f}（轉強）\n"
            f"📊 VWAP:連3根上升，尚未突破（偏多趨勢）｜OBV:資金流入\n"
            f"📍 價格位於 VWAP 下方，觀察是否突破站上\n"
            f"🕒 時間:{now.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    # 空頭轉折預警
    elif (
        latest_rsi > 65 and                        # RSI 高檔
        rsi.iloc[-2] > rsi.iloc[-1] and            # RSI 轉弱
        tmo_slope < 0 and                          # TMO 動能轉弱
        vwap.iloc[-1] < vwap.iloc[-2] < vwap.iloc[-3] and   # VWAP 呈現向下三根連續
        obv.iloc[-1] < obv.iloc[-3]                # OBV 資金流出
    ):
        signal_note = (
            f"⚠️ **[預警 - 空頭轉折]** {symbol}\n"
            f"📉 RSI:{latest_rsi:.1f} ↘️｜TMO 斜率:{tmo_slope:.2f}｜OBV:資金流出\n"
            f"📉 VWAP:連3根下彎｜疑似轉弱進入空方觀察\n"
            f"🕒 時間:{now.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    # 正式多頭進場
    elif (
        latest_rsi < 40 and rsi.iloc[-2] < rsi.iloc[-1] and               # 1️⃣ RSI 低檔轉強
        tmo.iloc[-2] < 0 and latest_tmo < 0 and latest_tmo > tmo.iloc[-2] and  # 2️⃣ TMO 負值內部轉強（尚未翻正）
        abs(latest_price - latest_vwap) / latest_vwap < 0.03 and latest_price < latest_vwap and tmo_slope > 0 and  # 3️⃣ VWAP 下方但貼近＋斜率轉強
        volume_ratio > 1.5 and                                             # 4️⃣ 異常放量
        obv.iloc[-1] > obv.iloc[-3] and                                    # 5️⃣ OBV 資金流入
        candle_type in ['hammer', 'bullish_engulfing']                    # 6️⃣ 多頭反轉K棒
    ):
        signal_note = (
            f"🐮**[觀察 - 多頭進場]** 🐮{symbol}\n"
            f"📈 價格:${latest_price:.2f}｜距離 VWAP 僅 {vwap_deviation:.2%}\n"
            f"📊 RSI:{latest_rsi:.1f} ↗️｜TMO:{latest_tmo:.2f} ↗️｜OBV:上升\n"
            f"💥 VWAP 尚未站上但貼近｜📈 Volume:{volume_ratio:.2f}x｜🕯️ K棒:{candle_type}\n"
            f"🟢 多項轉強訊號共振，多頭建倉時機形成"
        )

        if not is_safe_entry(latest_rsi, latest_price, latest_vwap, direction="long", symbol=symbol):
            return

        # ✅ 檢查 30 分鐘共振（進場前確認）
        df_30m = fetch_30min_data(symbol)
        has_confluence_30m = check_30min_confluence(df_30m, direction="long")
        

        if not has_confluence_30m:
            signal_note += "｜⚠️ 無 30M 共振"
            print(f"[INFO] {symbol} 無 30M 共振，跳過正式進場")
            return  # 直接跳過進場
        else:
            signal_note += "｜✅ 30M 共振"

    if signal_note:
        push_to_discord(symbol, latest_price, rsi_value, macd_status, vwap_deviation, volume_ratio, ema5, candle_type, direction, signal_note)
        print(f"[SIGNAL] {symbol}: {signal_note}")
        return signal_note

    final_entry_signal_detected = True
    direction = "多"
    capital_used = capital_left * 0.05
    entry_price = latest_price

    positions[symbol] = {
        'entry_price': entry_price,
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
    print(f"[建倉紀錄] {symbol} 建倉於 {entry_price:.2f}｜投入資金 ${capital_used:.2f}")

    if final_entry_signal_detected and symbol not in entry_price_dict and len(positions_held) < max_positions:
        allocated = total_capital * position_size_pct

        # 若資金不足，跳過
        if capital_left < allocated:
            print(f"[SKIP] 資金不足，無法進場:{symbol}")
        else:
            # 計算股數與真實投入金額
            shares = int(allocated / latest_price)
            actual_cost = shares * latest_price

            if shares == 0:
                print(f"[SKIP] 價格過高，無法整股購買:{symbol}")
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
                    f"🟢 **[開倉 - 多頭進場]** {symbol} @ ${latest_price:.2f}｜{shares} 股\n"
                    f"📊 RSI: {latest_rsi:.1f} | TMO: {latest_tmo:.2f} | 倍量: {volume_ratio:.2f}x | K棒: {candle_type}\n"
                    f"📈 VWAP偏離:{vwap_deviation:.2%}｜OBV:{obv_status}｜TMO斜率:{tmo_slope:.2f}\n"
                    f"🔍 共振判斷:{'✅ 有 30分鐘共振' if is_confluence else '⚠️ 無 30分鐘共振'}\n"
                    f"💰 總投入:${actual_cost:.2f}｜剩餘資金:${capital_left:.2f}\n"
                    f"🕑 時間:{entry_time_dict[symbol]}"
                )
        
    # 🐶 空頭正式進場
    elif (
        latest_rsi > 60 and rsi.iloc[-2] > rsi.iloc[-1] and              # 1️⃣ RSI 高檔轉弱
        tmo.iloc[-2] > 0 and latest_tmo > 0 and latest_tmo < tmo.iloc[-2] and  # 2️⃣ TMO 正值內部轉弱（尚未翻負）
        abs(latest_price - latest_vwap) / latest_vwap < 0.03 and latest_price > latest_vwap and tmo_slope < 0 and  # 3️⃣ VWAP 上方但已貼近＋斜率轉弱
        volume_ratio > 1.5 and                                            # 4️⃣ 異常放量
        obv.iloc[-1] < obv.iloc[-3] and                                   # 5️⃣ OBV 資金流出
        candle_type in ['shooting_star', 'bearish_engulfing']            # 6️⃣ 空頭反轉K棒
    ):
        signal_note = (
            f"🐻**[觀察 - 空頭進場]** 🐻{symbol}\n"
            f"📉 價格:${latest_price:.2f}｜距離 VWAP 僅 {vwap_deviation:.2%}\n"
            f"📊 RSI:{latest_rsi:.1f} ↘️｜TMO:{latest_tmo:.2f} ↘️｜OBV:下滑\n"
            f"💥 VWAP 尚未跌破但貼近｜📈 Volume:{volume_ratio:.2f}x｜🕯️ K棒:{candle_type}\n"
            f"🛑 多項轉弱訊號共振，空頭建倉時機形成"
        )

        if not is_safe_entry(latest_rsi, latest_price, latest_vwap, direction="short", symbol=symbol):
            return

        # ✅ 檢查 30 分鐘共振（空頭版本）
        df_30m = fetch_30min_data(symbol)
        has_confluence_30m = check_30min_confluence(df_30m, direction="short")

        if not has_confluence_30m:
            signal_note += "\n📈 技術共振:⚠️ 無 30M 共振"
            print(f"[INFO] {symbol} 無 30M 共振，跳過正式空頭進場")
        push_to_discord(symbol, latest_price, rsi_value, macd_status, vwap_deviation, volume_ratio, ema5, candle_type, direction, signal_note)
            return  # ✅ 中止正式進場流程
        else:
            signal_note += "\n📈 技術共振:✅ 30M 共振"

        final_entry_signal_detected = True
        direction = "空"

    # ✅ 空頭建倉（需觸發 flag）
    if final_entry_signal_detected and symbol not in entry_price_dict and len(positions_held) < max_positions:
        allocated = total_capital * position_size_pct

        if capital_left < allocated:
            print(f"[SKIP] 資金不足，無法進場:{symbol}")
        else:
            shares = int(allocated / latest_price)
            actual_cost = shares * latest_price

            if shares == 0:
                print(f"[SKIP] 價格過高，無法整股放空:{symbol}")
            else:
                if symbol not in entered_positions:
                    entered_positions[symbol] = {
                        "price": latest_price,
                        "direction": "short",
                        "entry_time": datetime.now()
                    }

                entry_price_dict[symbol] = latest_price
                positions_held[symbol] = actual_cost
                capital_left -= actual_cost
                entry_direction_dict[symbol] = 'short'
                entry_shares_dict[symbol] = shares
                entry_time_dict[symbol] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                positions[symbol] = {
                    'entry_price': latest_price,
                    'capital_used': actual_cost,
                    'entry_time': datetime.now(),
                    'direction': "short",
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
                
                # 推播通知
                send_to_discord(
                    f"🔻 **[開倉 - 空頭進場]** {symbol} @ ${latest_price:.2f}｜{shares} 股\n"
                    f"📉 RSI: {latest_rsi:.1f} | TMO: {latest_tmo:.2f} | 倍量: {volume_ratio:.2f}x | K棒: {candle_type}\n"
                    f"📉 VWAP偏離:{vwap_deviation:.2%}｜OBV:{obv_status}｜TMO斜率:{tmo_slope:.2f}\n"
                    f"🔍 共振判斷:{'✅ 有 30分鐘共振' if is_confluence else '⚠️ 無 30分鐘共振'}\n"
                    f"💰 總投入:${actual_cost:.2f}｜剩餘資金:${capital_left:.2f}\n"
                    f"🕑 時間:{entry_time_dict[symbol]}"
                )
    
        # 印出訊號（新版格式）
    if signal_note:
        print("-" * 60)
        print(f"[DATA] {symbol} 最新K棒:")
        print(f"開:{latest_open:.2f} | 高:{latest_high:.2f} | 低:{latest_low:.2f} | 收:{latest_price:.2f} | 量:{latest_volume:,}")
        print(f"[INDICATOR] RSI: {latest_rsi:.1f} | TMO: {latest_tmo:.2f} | VWAP: {latest_vwap:.2f} | 倍量: {volume_ratio:.2f}x")
        print(f"[TREND] EMA交叉: {ema_cross} | OBV: {obv.iloc[-1]:.2f}（{obv_direction}）")
        print(f"[KD] K: {k_value:.1f} | D: {d_value:.1f} | 狀態: {kd_status} | K棒: {candle_type}")
        print(f"[ALERT] {signal_note}:{symbol}")
        print("-" * 60)

        # ✅ 主訊號推播到 Discord）
        push_to_discord(symbol, latest_price, rsi_value, macd_status, vwap_deviation, volume_ratio, ema5, candle_type, direction, signal_note)
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
            plus_di=latest_plus_di,
            minus_di=latest_minus_di,
            signal_note=signal_note
        )


entry_price_dict = {}
positions = {}  # 持倉記錄:{symbol: {...}}
total_capital = 1000000
position_size_pct = 0.05
max_positions = 15
capital_left = total_capital

def auto_trade_and_monitor(symbol, latest_price, signal_note, direction,
                           tick_percentile, trin, latest_rsi, latest_tmo, tmo_slope,
                           vwap_diff, volume_ratio, obv_value, obv_direction,
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
        send_to_discord(f"🐸 **[自動進場]** {symbol} @ {latest_price:.2f} 方向:{direction}")
    
        print(f"[自動進場] {symbol} @ {latest_price} 方向:{direction}")
        return

   # ✅ 出場邏輯
for symbol in list(positions.keys()):
    entry_data = positions[symbol]
    entry_price = entry_data['entry_price']
    direction = entry_data['direction']
    entry_time = entry_data['timestamp']
    holding_time_sec = int((now - entry_time).total_seconds())
    return_rate = (latest_price - entry_price) / entry_price if direction == "多" else (entry_price - latest_price) / entry_price

    if return_rate >= take_profit_rate or return_rate <= -stop_loss_rate:
        exit_price = latest_price
        capital_left += entry_data['capital_used']
        del positions[symbol]

        print(f"[出場] {symbol} @ {exit_price:.2f}，報酬率:{return_rate*100:.2f}%，持倉:{holding_time_sec} 秒")

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
            obv_value=obv_value,
            obv_direction=obv_direction,
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
            f"TICK 百分位:{tick_percentile:.1f}｜斜率:+{tick_slope:.2f}｜TRIN:{trin_value:.2f}\n"
            "大盤動能轉強，觀察個股多方機會"
        )
        send_to_discord(message)

    elif tick_percentile < 50 and tick_slope < 0 and trin_value > 1.0:
        message = (
            "📉 **[大盤潛伏空頭]**\n"
            f"TICK 百分位:{tick_percentile:.1f}｜斜率:{tick_slope:.2f}｜TRIN:{trin_value:.2f}\n"
            "大盤動能轉弱，注意個股風險與回檔"
        )
        send_to_discord(message)

# ✅ 接著模擬自動進出場
def analyze_signal_and_return(symbol, df, latest_price, latest_open, latest_high, latest_low, latest_volume,
                              latest_rsi, latest_vwap, volume_ratio, ema5_above_ema20,
                              kd_status, tmo_cross, atr, signal_note,
                              latest_tmo, tmo_slope, obv_value, obv_direction, candle_type):
    # ✅ 自動進出場邏輯
    auto_trade_and_monitor(
        symbol=symbol,
        latest_price=latest_price,
        signal_note=signal_note,
        direction=direction,
        tick_percentile=tick_percentile,
        trin=trin,
        latest_rsi=latest_rsi,
        latest_tmo=latest_tmo,
        tmo_slope=tmo_slope,
        vwap_diff=vwap_diff,
        volume_ratio=volume_ratio,
        obv_value=obv.iloc[-1],
        obv_direction=obv_direction,
        kd_status=kd_status,
        candle_type=candle_type,
        session=session,
        strategy_version=strategy_version,
        confidence_score=confidence_score
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


def check_30min_confluence(df_30m, direction="long"):
    try:
        rsi = RSIIndicator(df_30m['close'], window=14).rsi().iloc[-1]
        tmo_diff = df_30m['close'].diff(2).iloc[-1]
        vwap = (df_30m['high'] + df_30m['low'] + df_30m['close']) / 3
        latest_vwap = vwap.iloc[-1]
        obv = OnBalanceVolumeIndicator(close=df_30m['close'], volume=df_30m['volume']).on_balance_volume()
        obv_direction = "上升" if obv.iloc[-1] > obv.iloc[-2] else "下降"

        signal_strength = 0

        # ✅ 多頭方向評估
        if direction == "long":
            # ✅ RSI 處於低檔區（視為超賣轉多）
            if rsi < 40:
                signal_strength += 1

            # ✅ TMO 接近0且正在上升（黃金交叉初期）
            if -2 < tmo < 2 and tmo_diff > 0:
                signal_strength += 1

            # ✅ VWAP 偏離接近 0 且價格逐步向上靠攏（上升但尚未偏離過高）
            if -0.01 < vwap_deviation < 0.01 and price > df_30m['close'].iloc[-2]:
                signal_strength += 1

            # ✅ OBV 呈現上升趨勢（資金進場）
            if obv_direction == "上升":
                signal_strength += 1
        # ✅ 空頭方向評估
        elif direction == "short":
            # ✅ RSI 處於高檔（視為超買轉弱）
            if rsi > 60:
                signal_strength += 1

            # ✅ TMO 接近 0 且正在下降（死叉初期）
            if -2 < tmo < 2 and tmo_diff < 0:
                signal_strength += 1

            # ✅ VWAP 偏離接近 0 且價格逐步下壓
            if -0.01 < vwap_deviation < 0.01 and price < df_30m['close'].iloc[-2]:
                signal_strength += 1

            # ✅ OBV 呈現下降（資金流出）
            if obv_direction == "下降":
                signal_strength += 1

        return signal_strength >= 3
    except Exception as e:
        print(f"[ERROR] 無法檢查 30 分鐘共振:{e}")
        return False
    
    # ✅ 統一濾網判斷:RSI 半山腰 ＋ VWAP 過度偏離
    def is_safe_entry(rsi_value, price, vwap, direction="long", symbol=""):
        # --- 半山腰判斷 ---
        if direction == "long":
            if 45 <= rsi_value <= 65:
                print(f"[SKIP] {symbol} 多頭 RSI 在 45～65，疑似半山腰")
                return False
        elif direction == "short":
            if 35 <= rsi_value <= 55:
                print(f"[SKIP] {symbol} 空頭 RSI 在 35～55，疑似空頭半山腰")
                return False

        # --- VWAP 偏離過大判斷 ---
        if price > vwap * 1.08 or price < vwap * 0.92:
            print(f"[SKIP] {symbol} 價格偏離 VWAP 過大（偏離超過 ±8%）")
            return False

        # --- 條件皆通過 ---
        return True


        
