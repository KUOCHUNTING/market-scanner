import pytz
import pandas as pd
from datetime import datetime, timedelta, time as dtime
from polygon import RESTClient
from datetime import datetime

def fetch_stock_data(symbol, api_key):
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
