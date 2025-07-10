import pandas as pd

def detect_trading_signal(symbol, df, indicators, debug=False, force_test=False):
    if 'volume' not in df.columns:
        print(f"[跳過] {symbol} 缺少 volume 欄位")
        return None, None, None, None

    if len(df) < 60:
        if debug:
            print(f"[跳過] {symbol} 資料不足（僅 {len(df)} 筆）")
        return None, None, None, None
    
    # === 6. 抓技術指標資料
    if 'close' not in df.columns or df['close'].isnull().all():
        print(f"[跳過] {symbol} ➜ close 欄位無效")
        return

    latest_price = df['close'].iloc[-1]
    if pd.isna(latest_price) or latest_price <= 0:
        print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
        return
    prev_close = df['close'].iloc[-2]
    price_change = abs(latest_price - prev_close) / prev_close

    rsi = indicators['rsi'].iloc[-1]
    rsi_prev = indicators['rsi'].iloc[-2]
    roc = indicators['roc'].iloc[-1]
    roc_prev = indicators['roc'].iloc[-2]
    obv = indicators['obv'].iloc[-1]
    obv_prev = indicators['obv'].iloc[-2]
    vwap = indicators['vwap'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]

    # ✅ 修正欄位命名
    lower_band = indicators['bb_lower'].iloc[-1]
    upper_band = indicators['bb_upper'].iloc[-1]

    # ✅ 防呆處理：避免除以零
    vwap_deviation = (latest_price - vwap) / vwap if vwap != 0 else None
    mean = df['close'].rolling(window=20).mean().iloc[-1]
    std = df['close'].rolling(window=20).std().iloc[-1]
    zscore = (latest_price - mean) / std if std and not pd.isna(std) else 0

    signal_type = None
    signal_note = None
    direction = None
    strategy_name = None

    # === 模擬測試用
    if force_test and symbol in ["TSLA", "NVDA"]:
        return "BUY", "🧪 測試訊號：模擬建倉", "多", "測試策略"

    # === 🟢 RROV 多單主策略
    if (
        rsi < 35 and rsi > rsi_prev and
        roc < 0 and roc > roc_prev and
        obv > obv_prev and
        abs(latest_price - vwap) / vwap < 0.05 and
        price_change < 0.01
    ):
        return "BUY", "🐸 多單建倉（RROV）：RSI回升 + ROC翻揚 + OBV上升 + VWAP貼近", "多", "RROV 主策略"

    # === 🟢 順勢多單策略
    if (
        rsi > 50 and rsi > rsi_prev and
        roc > 0 and roc > roc_prev and
        obv > obv_prev and
        latest_price > vwap and
        ema5 > ema20 and
        price_change < 0.015
    ):
        return "BUY", "🐸 多單建倉（順勢多單）：RSI>50轉強、VWAP上方、EMA多頭排列", "多", "順勢多單"

    # === 🟢 均值回歸多單策略
    if (
        latest_price < lower_band and
        rsi < 35 and rsi > rsi_prev and
        zscore < -2 and
        ema5 > ema20
    ):
        return "BUY", "🐸 多單建倉（均值回歸）：跌破布林 + RSI回升 + Z-score超跌", "多", "均值回歸"

    # === 🔴 RROV 空單主策略
    if (
        rsi > 65 and rsi < rsi_prev and
        roc > 0 and roc < roc_prev and
        obv < obv_prev and
        abs(latest_price - vwap) / vwap < 0.05 and
        price_change < 0.01
    ):
        return "SELL", "🐶 空單建倉（RROV）：RSI轉弱 + ROC下滑 + OBV下降 + VWAP貼近", "空", "RROV 主策略"

    # === 🔴 順勢空單策略
    if (
        rsi < 50 and rsi < rsi_prev and
        roc < 0 and roc < roc_prev and
        obv < obv_prev and
        latest_price < vwap and
        ema5 < ema20 and
        price_change < 0.015
    ):
        return "SELL", "🐶 空單建倉（順勢空單）：RSI<50轉弱、VWAP下方、EMA死叉", "空", "順勢空單"

    # === 🔴 均值回歸空單策略
    if (
        latest_price > upper_band and
        rsi > 65 and rsi < rsi_prev and
        zscore > 2 and
        ema5 < ema20
    ):
        return "SELL", "🐶 空單建倉（均值回歸）：突破布林 + RSI轉弱 + Z-score過熱", "空", "均值回歸"

    # === ⛔ 條件未滿足診斷
    if debug:
        reasons = []
        if rsi < 50:
            if rsi >= 35 or rsi <= rsi_prev: reasons.append("RSI未回升")
            if roc >= 0 or roc <= roc_prev: reasons.append("ROC未翻揚")
            if obv <= obv_prev: reasons.append("OBV未上升")
            if abs(latest_price - vwap) / vwap >= 0.05: reasons.append("價格未貼近VWAP")
            if price_change >= 0.01: reasons.append("價格已脫離起漲點")
        else:
            if rsi <= 65 or rsi >= rsi_prev: reasons.append("RSI未轉弱")
            if roc <= 0 or roc >= roc_prev: reasons.append("ROC未下滑")
            if obv >= obv_prev: reasons.append("OBV未下降")
            if abs(latest_price - vwap) / vwap >= 0.05: reasons.append("價格未貼近VWAP")
            if price_change >= 0.01: reasons.append("價格已脫離起跌點")
        if reasons:
            note = f"⛔ 無法進場：{'、'.join(reasons)}"
            return None, note, "無", "無策略"

    # === ⚠️ 爆量預警
    curr_volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].rolling(20).mean().iloc[-1]
    volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1.0

    if volume_ratio >= 5 and (rsi < 40 or latest_price < lower_band * 1.02):
        return "ALERT_VOLUME_SPIKE_LONG", f"⚠️ [預警 - 低檔爆量] ➜ 量比={volume_ratio:.1f}x，RSI={rsi:.1f}", "多", "爆量預警"
    elif volume_ratio >= 5 and (rsi > 70 or latest_price > upper_band * 0.98):
        return "ALERT_VOLUME_SPIKE_SHORT", f"⚠️ [預警 - 高檔爆量] ➜ 量比={volume_ratio:.1f}x，RSI={rsi:.1f}", "空", "爆量預警"

    # === 未達條件，輸出診斷訊息
    if debug:
        print(f"[未達條件] {symbol} ➜ 無進場訊號，RSI={rsi:.1f}、Z-score={zscore:.2f}、VWAP乖離={vwap_deviation:.2% if vwap_deviation else 'N/A'}")
    return None, None, None, None
