from ta.momentum import RSIIndicator

def calculate_indicators(df):
    if len(df) < 60:
        print("[警告] 技術指標計算時資料不足，跳過")
        return None

    required_columns = ['close', 'volume']
    for col in required_columns:
        if col not in df.columns or df[col].isnull().all():
            print(f"⚠️ [警告] 缺少必要欄位：{col}，跳過該股票")
            return None
        if df[col].isnull().all():
            print(f"⚠️ [警告] 欄位 {col} 全部是空值 ➜ 跳過")
            return None

    # === 基礎欄位 ===
    close = df['close']
    volume = df['volume']

    # === RSI（14）===
    rsi = RSIIndicator(close=close, window=15).rsi()

    # === ROC（9）===
    roc = ROCIndicator(close=close, window=10).roc()

    # === OBV ===
    obv = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

    # === Z-score（20）===
    rolling_mean = close.rolling(21).mean()
    rolling_std = close.rolling(21).std()
    zscore = (close - rolling_mean) / rolling_std

    # === Bollinger Bands（20, 2x）===
    bb = BollingerBands(close=close, window=20, window_dev=2)
    lower_band = bb.bollinger_lband()
    upper_band = bb.bollinger_hband()
    mid_band = bb.bollinger_mavg()

    # === VWAP（成交量加權平均價）===
    df['cum_vol'] = volume.cumsum()
    df['cum_vwap'] = (close * volume).cumsum()
    vwap = df['cum_vwap'] / df['cum_vol']

    # === EMA（5日與 20日）===
    ema_5 = EMAIndicator(close=close, window=5).ema_indicator()
    ema_20 = EMAIndicator(close=close, window=20).ema_indicator()

    # === EMA 趨勢判斷（上彎、下彎、糾結）===
    ema_5_slope = ema_5.diff()
    ema_20_slope = ema_20.diff()
    ema_trend = []
    for i in range(len(ema_5_slope)):
        if ema_5_slope.iloc[i] > 0 and ema_20_slope.iloc[i] > 0:
            ema_trend.append("上彎")
        elif ema_5_slope.iloc[i] < 0 and ema_20_slope.iloc[i] < 0:
            ema_trend.append("下彎")
        else:
            ema_trend.append("糾結")

    # === 成交量資訊 ===
    curr_volume = volume.iloc[-1]
    avg_volume = volume.rolling(20).mean().iloc[-1]
    volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1.0

    # === EMA 上穿 / 下彎 狀態判斷 ===
    ema_status = (ema_5 > ema_20).replace({True: "上穿", False: "下彎"})

    # === K 棒型態判斷（簡化）===
    last_open = df['open'].iloc[-1]
    last_close = df['close'].iloc[-1]
    last_high = df['high'].iloc[-1]
    last_low = df['low'].iloc[-1]

    body_size = abs(last_close - last_open)
    upper_shadow = last_high - max(last_close, last_open)
    lower_shadow = min(last_close, last_open) - last_low

    if body_size < 0.1 * (last_high - last_low):
        candle_type = "十字線"
    elif last_close > last_open and lower_shadow > 2 * body_size:
        candle_type = "錘頭"
    elif last_close < last_open and upper_shadow > 2 * body_size:
        candle_type = "流星"
    elif last_close > last_open:
        candle_type = "陽線"
    else:
        candle_type = "陰線"

    # === 回傳所有指標 ===
    return {
        'rsi': rsi,
        'roc': roc,
        'obv': obv,
        'zscore': zscore,
        'bb_lower': lower_band,
        'bb_upper': upper_band,
        'bb_mid': mid_band,
        'vwap': vwap,
        'ema_5': ema_5,
        'ema_20': ema_20,
        'ema_trend': pd.Series(ema_trend, index=df.index),
        'curr_volume': curr_volume,
        'volume_ratio': volume_ratio,
        'avg_volume': avg_volume,
        'ema_status': ema_status,
        'candle_type': candle_type
    }
