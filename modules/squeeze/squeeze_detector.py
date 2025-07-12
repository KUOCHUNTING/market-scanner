# modules/squeeze/squeeze_detector.py

import yfinance as yf
import pandas as pd

def fetch_squeeze_data(symbol):
    df = yf.download(symbol, period="3mo", interval="1d")
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['STD'] = df['Close'].rolling(window=20).std()
    df['BB_upper'] = df['MA20'] + 2 * df['STD']
    df['BB_lower'] = df['MA20'] - 2 * df['STD']

    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=20).mean()

    df['KC_upper'] = df['MA20'] + 1.5 * df['ATR']
    df['KC_lower'] = df['MA20'] - 1.5 * df['ATR']
    df['squeeze_on'] = (df['BB_upper'] < df['KC_upper']) & (df['BB_lower'] > df['KC_lower'])

    return df