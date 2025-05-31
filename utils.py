# utils.py

def detect_candle_pattern(df):
    # 這裡是判斷 K 棒形態的簡易範例
    if df['close'].iloc[-1] > df['open'].iloc[-1]:
        return "陽線"
    else:
        return "陰線"

def calculate_tmo(df):
    # TMO 簡化範例：回傳一個趨勢值（實際你應該自己定義好策略）
    return df['close'].diff().rolling(window=5).mean().iloc[-1]