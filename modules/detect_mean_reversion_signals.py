def detect_mean_reversion_signals(df, symbol):
    if len(df) < 60:
        return None, None, None, None, None, None

    indicators = calculate_indicators(df)

    # ✅ 防呆檢查：必要欄位缺失就跳過
    required_keys = ['rsi', 'zscore', 'ema_5', 'ema_20', 'bb_lower', 'bb_upper', 'vwap', 'obv']
    for key in required_keys:
        if key not in indicators or indicators[key].isna().iloc[-1]:
            print(f"[跳過] {symbol} ➜ 指標 {key} 缺失或為 NaN")
            return None, None, None, None, None, None
        
    if 'close' not in df.columns or df['close'].isnull().all():
        print(f"[跳過] {symbol} ➜ df['close'] 欄位無效或全部為空，無法取得 latest_price")
        return None, None, None, None, None, None  # ⚠️ 確保 return 數量符合你函數格式

    latest_price = df['close'].iloc[-1]
    if pd.isna(latest_price) or latest_price <= 0:
        print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
        return None, None, None, None, None, None
    latest_rsi = indicators['rsi'].iloc[-1]
    prev_rsi = indicators['rsi'].iloc[-2]
    zscore = indicators['zscore'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]
    lower_band = indicators['bb_lower'].iloc[-1]
    upper_band = indicators['bb_upper'].iloc[-1]
    vwap = indicators['vwap'].iloc[-1]
    obv = indicators['obv'].iloc[-1]
    # ✅ 多單均值回歸條件
    if (
        latest_price < lower_band and
        latest_rsi > prev_rsi and latest_rsi < 35 and
        zscore < -2 and
        ema5 > ema20
    ):
        note = f"📈 多單均值回歸：跌破布林下緣 + RSI回升 + Z-score={zscore:.2f} + EMA5上穿EMA20"
        return "BUY", note, zscore, latest_rsi, vwap, obv

    # ✅ 空單均值回歸條件
    elif (
        latest_price > upper_band and
        latest_rsi < prev_rsi and latest_rsi > 65 and
        zscore > 2 and
        ema5 < ema20
    ):
        note = f"📉 空單均值回歸：突破布林上緣 + RSI轉弱 + Z-score={zscore:.2f} + EMA5下彎EMA20"
        return "SELL", note, zscore, latest_rsi, vwap, obv

    return None, None, None, None, None, None