from datetime import datetime

def check_volume_alert(symbol, df, indicators):
    try:
        if 'close' not in df.columns or df['close'].isnull().all():
            print(f"[跳過] {symbol} ➜ close 欄位無效")
            return

        latest_price = df['close'].iloc[-1]
        if pd.isna(latest_price) or latest_price <= 0:
            print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
            return
        
        curr_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1.0

        rsi = indicators['rsi'].iloc[-1]
        roc = indicators['roc'].iloc[-1]
        vwap = indicators['vwap'].iloc[-1]
        zscore = indicators['zscore'].iloc[-1]
        obv = indicators['obv'].iloc[-1]
        upper_band = indicators['bb_upper'].iloc[-1]
        lower_band = indicators['bb_lower'].iloc[-1]
        ema_cross = indicators.get('ema_status', 'N/A')
        candle_type = indicators.get('candle_type', 'N/A')

        signal_type = None
        signal_note = ""
        direction = None
        strategy_name = None

        if volume_ratio >= 5:
            if rsi < 40 or latest_price < lower_band * 1.02:
                signal_type = "ALERT_VOLUME_SPIKE_LONG"
                signal_note = f"⚠️ **[預警 - 低檔爆量]** ➜ 量比={volume_ratio:.1f}x，RSI={rsi:.1f}"
                direction = "多"
                strategy_name = "爆量預警"

            elif rsi > 70 or latest_price > upper_band * 0.98:
                signal_type = "ALERT_VOLUME_SPIKE_SHORT"
                signal_note = f"⚠️ **[預警 - 高檔爆量]** ➜ 量比={volume_ratio:.1f}x，RSI={rsi:.1f}"
                direction = "空"
                strategy_name = "爆量預警"

        if signal_type:
            strategy_display = get_strategy_display(strategy_name)
            obv_change = obv - indicators['obv'].iloc[-2] if len(indicators['obv']) > 1 else 0
            vwap_deviation = abs(latest_price - vwap) / vwap * 100 if vwap else 0
            bb_deviation = (
                abs(latest_price - lower_band) / lower_band * 100 if direction == "多"
                else abs(latest_price - upper_band) / upper_band * 100
            )

            # ✅ 推播到 Discord
            push_to_discord(
                symbol=symbol,
                price=latest_price,
                rsi=rsi,
                roc=roc,
                vwap=vwap,
                volume_ratio=volume_ratio,
                ema_cross=ema_cross,
                candle_type=candle_type,
                signal_type=signal_type,
                signal_note=signal_note,
                confidence_score=0,
                direction=direction,
                strategy_name=strategy_name,
                zscore=zscore,
                obv=obv,
                obv_change=obv_change,
                vwap_deviation=vwap_deviation,
                bb_deviation=bb_deviation
            )

            # ✅ 寫入 Sheets ➜ 預警紀錄
            write_to_sheet([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 時間
                symbol,                                        # 股票代碼
                direction,                                     # 多空
                latest_price,                                  # 價格
                signal_type,                                   # 訊號類型
                signal_note,                                   # 描述
                round(rsi, 2), round(zscore, 2), round(vwap, 2), round(volume_ratio, 2),
                strategy_name, "預警"
            ], sheet="預警紀錄")
    except Exception as e:
        print(f"[錯誤] 爆量預警錯誤：{symbol} ➜ {e}")
