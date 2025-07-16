# modules/strategy/resonance_detector.py

import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volume import OnBalanceVolumeIndicator

def fetch_rsi_obv(symbol: str, interval="15m", lookback="2d"):
    """抓取最近資料並計算 RSI 與 OBV"""
    try:
        data = yf.download(symbol, interval=interval, period=lookback, progress=False)
        data.dropna(inplace=True)
        if len(data) < 10:
            return None

        data["rsi"] = RSIIndicator(close=data["Close"]).rsi()
        data["obv"] = OnBalanceVolumeIndicator(close=data["Close"], volume=data["Volume"]).on_balance_volume()
        return data[["Close", "rsi", "obv"]]
    except Exception as e:
        print(f"❌ {symbol} 抓取失敗：{e}")
        return None

def is_rsi_obv_turning_positive(df: pd.DataFrame) -> bool:
    """判斷 RSI 與 OBV 是否剛剛轉為上升"""
    if df is None or len(df) < 5:
        return False

    recent = df.iloc[-3:]  # 最近 3 根
    rsi_trend = recent["rsi"].diff().iloc[-2:].tolist()
    obv_trend = recent["obv"].diff().iloc[-2:].tolist()

    rsi_up = all(x > 0 for x in rsi_trend)
    obv_up = all(x > 0 for x in obv_trend)

    return rsi_up and obv_up

def detect_sector_resonance(etf_symbol: str, constituent_symbols: list, min_ratio: float = 0.6):
    """
    檢查 ETF 是否轉強 + 成分股共振
    :param etf_symbol: 板塊 ETF 代碼（如 XLK）
    :param constituent_symbols: 該板塊的成分股清單
    :param min_ratio: 幾成成分股需共振（預設 60%）
    :return: 是否共振（True/False）、共振股票列表
    """
    etf_df = fetch_rsi_obv(etf_symbol)
    if not is_rsi_obv_turning_positive(etf_df):
        return False, []

    resonant_stocks = []
    for symbol in constituent_symbols:
        stock_df = fetch_rsi_obv(symbol)
        if is_rsi_obv_turning_positive(stock_df):
            resonant_stocks.append(symbol)

    ratio = len(resonant_stocks) / max(1, len(constituent_symbols))
    return ratio >= min_ratio, resonant_stocks
