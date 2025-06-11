from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta

# ✅ 請改成你的 API 金鑰（或從 .env 抓也可以）
API_KEY = "AKGTUMW0KZ1Z1UIGHCDA"
SECRET_KEY = "vSF9KalrwUm5UWcKSkEDpp67SfaSI799do60Fl0z"

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

request_params = StockBarsRequest(
    symbol_or_symbols="AAPL",
    timeframe=TimeFrame.Minute,
    start=datetime.utcnow() - timedelta(days=1),
    end=datetime.utcnow()
)

bars = client.get_stock_bars(request_params).df
print(bars.tail())
