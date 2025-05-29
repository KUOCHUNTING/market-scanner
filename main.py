import os
from ta.trend import EMAIndicator
from ta.momentum import StochasticOscillator
from ta.volatility import AverageTrueRange
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from polygon import RESTClient
from datetime import datetime, timedelta
from pytz import timezone

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
        
        # ✅ 插入這段來正確取得 bars 清單
        bars = None
        if hasattr(aggs, 'results'):
            bars = aggs.results
        elif isinstance(aggs, list):
            bars = aggs
        else:
            print(f"[ERROR] 無法處理 aggs 結構：{symbol}")
            return None

        # ✅ bars 必須是非空 list
        if not bars or not isinstance(bars, list):
            print(f"[WARNING] 無效 bars（非 list）：{symbol}")
            return None
        
        required_fields = ["timestamp", "open", "high", "low", "close", "volume"]

        cleaned_bars = []
        for bar in bars:
            # ✅ 如果是 Agg 類別，就轉成 dict
            if hasattr(bar, '__dict__'):
                bar = vars(bar)
            elif not isinstance(bar, dict):
                print(f"[ERROR] 非法 bar 結構：{bar}")
                continue

            # ✅ 自動抓時間欄位
            time_key = "timestamp" if "timestamp" in bar else ("t" if "t" in bar else None)
            if time_key is None or bar[time_key] is None:
                print(f"[WARNING] 無有效時間欄位（{symbol}）：{bar}")
                continue
            else:
                bar["timestamp"] = bar[time_key]  # 統一欄位名稱為 timestamp，後面 DataFrame 可用

            # ✅ 確保有 timestamp 等欄位
            required_fields = ["timestamp", "open", "high", "low", "close", "volume"]
            if not all(field in bar and bar[field] is not None for field in required_fields):
                print(f"[WARNING] 缺少必要欄位: {bar}")
                continue

            cleaned_bars.append(bar)

        if len(cleaned_bars) == 0:
            print(f"[WARNING] 無有效 K 棒資料：{symbol}")
            return None
        
        # ✅ 建立 DataFrame 並轉換欄位
        df = pd.DataFrame(cleaned_bars)
        df['timestamp'] = [bar.get("timestamp") or bar.get("t") for bar in cleaned_bars]
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')  # ✅ 這裡就用 'timestamp' 了
        
        # ✅ 插入這段判斷：K棒資料太少就跳過
        if len(df) < 15:
            print(f"[WARNING] {symbol} K線不足（僅 {len(df)} 筆），跳過")
            return None
        

        # 技術指標
        rsi = RSIIndicator(close=df['close']).rsi()
        macd_hist = MACD(close=df['close']).macd_diff()
        vwap = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
        ema5 = EMAIndicator(close=df['close'], window=5).ema_indicator()
        ema20 = EMAIndicator(close=df['close'], window=20).ema_indicator()
        kd = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'])
        atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close']).average_true_range()

        # 最新值
        latest_rsi = rsi.iloc[-1]
        latest_macd = macd_hist.iloc[-1]
        latest_vwap = vwap.iloc[-1] if not pd.isna(vwap.iloc[-1]) else None
        latest_price = df['close'].iloc[-1]
        print(f"[INFO] {symbol} 最新收盤價：{latest_price:.2f}")
        latest_open = df['open'].iloc[-1]
        latest_high = df['high'].iloc[-1]
        latest_low = df['low'].iloc[-1]
        latest_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].mean()
        volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0
        ema5_above_ema20 = ema5.iloc[-1] > ema20.iloc[-1]
        ema_cross = "✅" if ema5.iloc[-1] > ema20.iloc[-1] else "❌"
        k_value = kd.stoch().iloc[-1]
        d_value = kd.stoch_signal().iloc[-1]
        kd_status = "金叉" if k_value > d_value else "死叉" if k_value < d_value else "中性"

        df['momentum'] = df['close'].diff()
        tmo_raw = df['momentum'].rolling(window=14).mean()
        tmo_cross = "黃金交叉" if tmo_raw.iloc[-1] > 0 and tmo_raw.iloc[-2] < 0 else \
                    "死亡交叉" if tmo_raw.iloc[-1] < 0 and tmo_raw.iloc[-2] > 0 else "中性"

        # VWAP 格式化
        if latest_vwap is None or pd.isna(latest_vwap):
            vwap_str = "無"
        else:
            vwap_str = f"{latest_vwap:.2f}"

        # 格式化印出
        print(f"[INFO] {symbol} | 價格: {latest_price:.2f} | RSI: {latest_rsi:.1f} | MACD: {latest_macd:+.2f} | "
              f"VWAP: {vwap_str} | 量能: {volume_ratio:.1f}x | EMA5>EMA20: {ema_cross} | KD: {kd_status}")
    
        if latest_vwap is None:
            print(f"[WARNING] VWAP 為 NaN，跳過：{symbol}")
            return None
            
            # 訊號判斷
        signal_note = None
        if latest_macd < 0 and latest_price < latest_vwap and volume_ratio > 1.5:
             signal_note = "🐶 正式進場 - 空頭"
        elif latest_rsi > 70 and rsi.iloc[-1] < rsi.iloc[-2]:
            signal_note = "⚠️ 預警 - 空頭轉折"
        elif latest_macd > 0 and latest_price > latest_vwap and volume_ratio > 1.5:
            signal_note = "🐸 正式進場 - 多頭"
        elif latest_rsi < 30 and rsi.iloc[-1] > rsi.iloc[-2]:
            signal_note = "⚠️ 預警 - 多頭轉折"

            # 印出訊號
        if signal_note:
            print("-" * 60)
            print(f"[DATA] {symbol} 最新K棒：")
            print(f"開：{latest_open:.2f} | 高：{latest_high:.2f} | 低：{latest_low:.2f} | 收：{latest_price:.2f} | 量：{latest_volume:,}")
            print(f"[INDICATOR] RSI: {latest_rsi:.1f} | MACD: {latest_macd:.2f} | VWAP: {latest_vwap:.2f} | 倍量: {volume_ratio:.2f}x")
            print(f"[ALERT] {signal_note}：{symbol}")
            print("-" * 60)

                # ✅ 主訊號推播到 Discord
            push_to_discord(
                symbol,
                latest_price,
                latest_rsi,
                latest_macd,
                latest_vwap,
                volume_ratio,
                ema_cross,
                kd_status,
                signal_note
            )

            # 再印延伸訊號
            # === 六大訊號分類 
            extended_signal = None
            # 🚀 強多 - 動能爆發
        if latest_rsi < 35 and rsi.iloc[-1] > rsi.iloc[-2] and latest_macd > 0 and ema_5.iloc[-1] > ema_20.iloc[-1]:
            extended_signal = "🚀 強多 - 動能爆發"

            # 🔥 強空 - 崩跌起點
        elif latest_rsi > 70 and rsi.iloc[-1] < rsi.iloc[-2] and latest_macd < 0 and latest_price < latest_vwap and volume_ratio > 2:
            extended_signal = "🔥 強空 - 崩跌起點"

            # 🐢 短多 - 技術回補
        elif latest_rsi > 30 and rsi.iloc[-1] > rsi.iloc[-2] and latest_price > latest_vwap and volume_ratio > 1.5:
            extended_signal = "🐢 短多 - 技術回補"

            # 🔄 短空 - 止漲訊號
        elif latest_rsi > 65 and rsi.iloc[-1] < rsi.iloc[-2] and latest_price < latest_vwap and latest_macd < 0 and volume_ratio > 1.5:
            extended_signal = "🔄 短空 - 止漲訊號"

            # 🧪 觀察 - 盤整突破
        elif 45 <= latest_rsi <= 55 and latest_macd > 0:
            extended_signal = "🧪 觀察 - 盤整突破"

            # ⚙️ 盤整中性（可選列印或略過）
        elif 45 < latest_rsi < 65 and abs(latest_macd) < 0.1 and abs(latest_price - latest_vwap) < 0.3:
            extended_signal = "⚙️ 盤整中性"

            # === 印出（有訊號才印） ===
        if extended_signal:
            print("-" * 60)
            print(f"[DATA] {symbol} 最新K棒：")
            print(f"開：{latest_open:.2f} | 高：{latest_high:.2f} | 低：{latest_low:.2f} | 收：{latest_price:.2f} | 量：{latest_volume:,}")
            print(f"[INDICATOR] RSI: {latest_rsi:.1f} | MACD: {latest_macd:.2f} | VWAP: {latest_vwap:.2f} | 倍量: {volume_ratio:.2f}x")
            print(f"[ALERT] {extended_signal}：{symbol}")
            print("-" * 60)
                
                # ✅ 延伸訊號也推播
            push_to_discord(
                symbol,
                latest_price,
                latest_rsi,
                latest_macd,
                latest_vwap,
                volume_ratio,
                ema_cross,
                kd_status,
                extended_signal
            )

            return {
                "df": df,
                "latest_rsi": latest_rsi,
                "latest_macd": latest_macd,
                "latest_vwap": latest_vwap,
                "volume_ratio": volume_ratio,
                "ema5_above_ema20": ema5_above_ema20,
                "kd_status": kd_status,
                "tmo_cross": tmo_cross,
                "atr": atr.iloc[-1],
                "latest_price": latest_price,
                "latest_open": latest_open,
                "latest_high": latest_high,
                "latest_low": latest_low,
                "latest_volume": latest_volume,
                "signal_note": signal_note,
                "extended_signal": extended_signal

                
            }
    except Exception as e:
        print(f"[ERROR] 抓取資料失敗 {symbol}：{e}")
        return None
         
# === 主程式 ===
def run_scanner():
    stock_list = load_stock_list(STOCK_LIST_CSV)
    success_count = 0
    fail_count = 0

    for symbol in stock_list:
        data = fetch_stock_data(symbol)
        if data:
            success_count += 1
            # 可加入推播 / 儲存 / 分類
        else:
            fail_count += 1

    print(f"\n[統計] 本輪成功 {success_count} 檔，失敗 {fail_count} 檔，有效率：{round(success_count / (success_count + fail_count + 1e-6) * 100, 2)}%")

# === 程式入口點 ===
if __name__ == "__main__":
    run_scanner()
