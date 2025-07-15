import pytz
from datetime import datetime, time

def is_us_market_open():
    est = pytz.timezone("US/Eastern")
    now_est = datetime.now(est)
    market_open = est.localize(datetime.combine(now_est.date(), time(9, 30)))
    market_close = est.localize(datetime.combine(now_est.date(), time(16, 0)))
    return market_open <= now_est <= market_close
