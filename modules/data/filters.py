from modules.filter_fundamentals import filter_fundamentals
from modules.utils.validate_indicators import is_invalid

def filter_liquidity(avg_volume, price, min_dollar_volume=5_000_000):
    """
    根據成交額過濾：排除流動性太低的股票
    avg_volume：近 5 日平均成交量
    price：股價
    min_dollar_volume：最低成交額（預設 500 萬）
    """
    try:
        dollar_volume = avg_volume * price
        return dollar_volume >= min_dollar_volume
    except Exception as e:
        print(f"[❌ 流動性過濾錯誤] {e}")
        return False
