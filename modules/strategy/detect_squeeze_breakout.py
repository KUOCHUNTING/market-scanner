from modules.fetch_stock_data import fetch_stock_data
from modules.config import POLYGON_API_KEY

def detect_squeeze_breakout(symbol):
    df = fetch_stock_data(symbol, api_key=POLYGON_API_KEY)
    if df.isnull().values.any() or len(df) < 25:
        return None

    # === 計算技術指標 ===
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

    # RSI
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
    df['OBV'].iloc[1:] = (df['Volume'].iloc[1:] * ((df['Close'].iloc[1:] > df['Close'].shift(1).iloc[1:]) * 2 - 1)).cumsum()

    # 平均量
    df['avg_volume'] = df['Volume'].rolling(window=20).mean()

    today = df.iloc[-1]
    yesterday = df.iloc[-2]

    if not yesterday['squeeze_on'] and today['squeeze_on']:
        return None

    if yesterday['squeeze_on'] and not today['squeeze_on']:
        # === 多方條件 ===
        long_conditions = {
            "價格突破BB上軌": today['Close'] > today['BB_upper'],
            "RSI > 60": today['RSI'] > 60,
            "EMA5 > EMA20": today['EMA_5'] > today['EMA_20'],
            "放量突破": today['Volume'] > today['avg_volume'] * 1.2,
            "OBV上升": today['OBV'] > df['OBV'].iloc[-5]
        }

        long_score = sum(long_conditions.values())

        if long_score >= 3:
            return {
                "strategy_name": "擠壓突破（多）",
                "direction": "做多",
                "score": long_score,
                "conditions_met": [k for k, v in long_conditions.items() if v],
                "close": round(today['Close'], 2),
                "rsi": round(today['RSI'], 1),
                "zscore": None,
                "ema_5": round(today['EMA_5'], 2),
                "ema_20": round(today['EMA_20'], 2)
            }

        # === 空方條件 ===
        short_conditions = {
            "價格跌破BB下軌": today['Close'] < today['BB_lower'],
            "RSI < 40": today['RSI'] < 40,
            "EMA5 < EMA20": today['EMA_5'] < today['EMA_20'],
            "放量下殺": today['Volume'] > today['avg_volume'] * 1.2,
            "OBV下降": today['OBV'] < df['OBV'].iloc[-5]
        }

        short_score = sum(short_conditions.values())

        if short_score >= 3:
            return {
                "strategy_name": "擠壓崩跌（空）",
                "direction": "做空",
                "score": short_score,
                "conditions_met": [k for k, v in short_conditions.items() if v],
                "close": round(today['Close'], 2),
                "rsi": round(today['RSI'], 1),
                "zscore": None,
                "ema_5": round(today['EMA_5'], 2),
                "ema_20": round(today['EMA_20'], 2)
            }

    return None
