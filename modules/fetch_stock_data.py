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

        df_all = pd
