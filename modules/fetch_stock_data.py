import pytz
import pandas as pd
from datetime import datetime, timedelta, time as dtime
from polygon import RESTClient

def fetch_stock_data(symbol, api_key, restrict_to_today=False):
    est = pytz.timezone("US/Eastern")
    now_est = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(est)

    market_open = est.localize(datetime.combine(now_est.date(), dtime(9, 30)))
    market_close = est.localize(datetime.combine(now_est.date(), dtime(16, 0)))

    # === 判斷抓資料區段 ===
    if now_est > market_close:
        print(f"[時間判斷] 盤後狀態 ➜ 抓當日開盤至收盤")
        start_time = market_open
        end_time = market_close

    elif now_est < market_open:
        print(f"[時間判斷] 盤前狀態 ➜ 改抓上一交易日")
        prev_day = now_est.date() - timedelta(days=1)
        while prev_day.weekday() >= 5:
            prev_day -= timedelta(days=1)
        start_time = est.localize(datetime.combine(prev_day, dtime(9, 30)))
        end_time = est.localize(datetime.combine(prev_day, dtime(16, 0)))

    else:
        print(f"[時間判斷] 盤中狀態 ➜ 抓近 250 分鐘資料")
        end_time = now_est
        start_time = now_est - timedelta(minutes=5 * 50)

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

        if not bars or len(bars) == 0:
            print(f"[❌錯誤] {symbol} ➜ 無 bars 資料（API 回傳空）")
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

        # ✅ 限制模式：只抓今天資料就不補抓
        if restrict_to_today:
            if len(df_all) < 60:
                print(f"[⚠️ 限制模式] {symbol} ➜ restrict_to_today=True，資料僅 {len(df_all)} 根，略過")
                return None
            else:
                print(f"[✅ 限制模式] {symbol} ➜ 已取得今日資料 {len(df_all)} 根")
        else:
            # ✅ 自動補抓直到滿足 60 根
            retry_days = 0
            prev_day = start_time.date()
            while len(df_all) < 60 and retry_days < 10:
                retry_days += 1
                prev_day -= timedelta(days=1)
                while prev_day.weekday() >= 5:
                    prev_day -= timedelta(days=1)

                retry_start = est.localize(datetime.combine(prev_day, dtime(9, 30)))
                retry_end = est.localize(datetime.combine(prev_day, dtime(16, 0)))
                from_ts = int(retry_start.timestamp() * 1000)
                to_ts = int(retry_end.timestamp() * 1000)

                print(f"[補抓] {symbol} 第 {retry_days} 天 ➜ {retry_start} → {retry_end}")

                bars_retry = client.get_aggs(
                    ticker=symbol,
                    multiplier=15,
                    timespan="minute",
                    from_=from_ts,
                    to=to_ts,
                    limit=100,
                    adjusted=True
                )

                if not bars_retry or len(bars_retry) == 0:
                    print(f"[補抓] 第 {retry_days} 天無資料")
                    continue

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

        # ✅ 最終防呆
        if df_all is None or len(df_all) < 60:
            print(f"[❌終止] {symbol} ➜ 資料不足（僅 {len(df_all)} 根），跳過")
            return None

        df_all["timestamp"] = pd.to_datetime(df_all["timestamp"], unit="ms")
        df_all.set_index("timestamp", inplace=True)
        df_all.sort_index(inplace=True)

        required_columns = ["open", "high", "low", "close", "volume"]
        for col in required_columns:
            if col not in df_all.columns:
                print(f"[錯誤] {symbol} ➜ 缺少欄位：{col}")
                print(df_all.head(3))
                return None

        return df_all

    except Exception as e:
        print(f"[❌例外] 抓取 {symbol} 發生錯誤：{e}")
        return None
