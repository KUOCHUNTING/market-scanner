# modules/utils/market_time.py
import pytz
from datetime import datetime, time as dtime

def is_us_market_open():
    """
    判斷是否為美股盤中（美東 09:30 ~ 16:00）
    """
    est = pytz.timezone("US/Eastern")
    now_est = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(est)

    market_open = est.localize(datetime.combine(now_est.date(), dtime(9, 30)))
    market_close = est.localize(datetime.combine(now_est.date(), dtime(16, 0)))

    return market_open <= now_est <= market_close
