from modules.notify.check_exit_and_notify import check_exit_and_notify
from modules.market_data import get_latest_price  # 你要自己實作

def execute_exit(symbol):
    try:
        latest_price = get_latest_price(symbol)
        check_exit_and_notify(symbol, latest_price)
    except Exception as e:
        print(f"[錯誤] execute_exit 失敗：{symbol} ➜ {e}")