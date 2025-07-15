# modules/utils/market_time.py
import pytz
from datetime import datetime, time as dtime

def get_us_market_times():
    est = pytz.timezone("US/Eastern")
    now_est = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(est)

    market_open = est.localize(datetime.combine(now_est.date(), dtime(9, 30)))
    market_close = est.localize(datetime.combine(now_est.date(), dtime(16, 0)))
    return now_est, market_open, market_close

def get_market_phase():
    """
    回傳當前市場時段：
    - "premarket"：盤前（< 09:30）
    - "open"：盤中（09:30 ~ 16:00）
    - "afterhours"：盤後（> 16:00）
    """
    now_est, market_open, market_close = get_us_market_times()

    if now_est < market_open:
        return "premarket"
    elif now_est <= market_close:
        return "open"
    else:
        return "afterhours"

def is_us_market_open():
    """
    是否為盤中時段（09:30 ~ 16:00）
    """
    return get_market_phase() == "open"
