# modules/strategy/detect_squeeze_breakout.py

import yfinance as yf
import pandas as pd

def detect_squeeze_breakout(symbol):
    df = yf.download(symbol, period="3mo", interval="1d")
    if df.isnull().values.any() or len(df) < 25:
        return None  # 資料不足

    # === 計算指標 ===
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

    # RSI 計算
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # EMA
    df['EMA_5'] = df['Close'].ewm(span=5, adjust=False).mean()
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()

    # OBV
    df['OBV'] = 0
    df['OBV'][1:] = (df['Volume'][1:] * ((df['Close'][1:] > df['Close'].shift(1))[1:] * 2 - 1)).cumsum()

    # 平均成交量
    df['avg_volume'] = df['Volume'].rolling(window=20).mean()

    # === 檢查是否剛解除 Squeeze 且出現突破 ===
    today = df.iloc[-1]
    yesterday = df.iloc[-2]

    if not yesterday['squeeze_on'] and today['squeeze_on']:
        return None  # 今天才進入 squeeze，不進場

    if yesterday['squeeze_on'] and not today['squeeze_on']:
        # ➤ 剛剛解除擠壓：檢查是否符合突破條件
        cond_price_break = today['Close'] > today['BB_upper']
        cond_rsi = today['RSI'] > 60
        cond_ema = today['EMA_5'] > today['EMA_20']
        cond_volume = today['Volume'] > today['avg_volume'] * 1.5
        cond_obv = today['OBV'] > df['OBV'].iloc[-5]

        # 條件符合數量
        conditions = {
            "價格突破BB上軌": cond_price_break,
            "RSI > 60": cond_rsi,
            "EMA5 > EMA20": cond_ema,
            "放量突破": cond_volume,
            "OBV上升": cond_obv,
        }
        score = sum(conditions.values())

        if score >= 3:  # 至少命中 3 個條件才進場
            return {
                "symbol": symbol,
                "date": df.index[-1].strftime("%Y-%m-%d"),
                "close": round(today['Close'], 2),
                "score": score,
                "conditions_met": [k for k, v in conditions.items() if v],
                "rsi": round(today['RSI'], 1),
                "ema_5": round(today['EMA_5'], 2),
                "ema_20": round(today['EMA_20'], 2),
                "volume": int(today['Volume']),
                "avg_volume": int(today['avg_volume']),
            }
    return None
