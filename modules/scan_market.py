from .fetch_stock_data import fetch_stock_data  # 抓取 K 線
from .get_fundamentals import get_fundamentals
from .filter_fundamentals import filter_fundamentals
from .calculate_indicators import calculate_indicators
from .detect_trading_signal import detect_trading_signal
from .compute_confidence_score import compute_confidence_score
from .load_stock_list import load_stock_list
from .config import POLYGON_API_KEY, capital_left
from .compute_confidence_score import get_strategy_match_score
import pandas as pd
import traceback  # ✅ 你要 print traceback 時一定要加這行

stock_list = load_stock_list()

def scan_market(symbol_list):
    global capital_left
    MIN_REQUIRED_CAPITAL = 3000
    if capital_left < MIN_REQUIRED_CAPITAL:
        print(f"[資金耗盡] 剩餘資金 ${capital_left:.2f} 已低於 ${MIN_REQUIRED_CAPITAL}，暫停掃描...")
        return

    for symbol in symbol_list:
        try:
            print(f"📡 掃描中：{symbol}")

            # === ✅ 1. 抓 K 線資料
            df = fetch_stock_data(symbol, POLYGON_API_KEY)

            if df is None or df.empty:
                print(f"[跳過] {symbol} ➜ 無資料")
                continue

            # === ✅ 2. 抓基本面（含 fallback 平均成交量計算）
            fundamentals = get_fundamentals(symbol, POLYGON_API_KEY, df)

            # === ✅ 3. 基本面過濾（只過濾流動性與停牌）
            passed, reason = filter_fundamentals(symbol, fundamentals)
            if not passed:
                print(f"[跳過] {symbol} ➜ {reason}")
                continue

            # === ✅ 4. 技術指標分析
            indicators = calculate_indicators(df)

            # === ✅ 2. 技術信心分數
            score = compute_confidence_score(
                rsi=indicators['rsi'].iloc[-1],
                roc=indicators['roc'].iloc[-1],
                obv=indicators['obv'].iloc[-1],
                vwap_deviation=indicators['vwap'].iloc[-1] - df['close'].iloc[-1],
                zscore=indicators['zscore'].iloc[-1],
                bb_deviation=(
                    df['close'].iloc[-1] - indicators['bb_lower'].iloc[-1]
                ) / (indicators['bb_upper'].iloc[-1] - indicators['bb_lower'].iloc[-1] + 1e-6),
                ema5=indicators['ema_5'].iloc[-1],
                ema20=indicators['ema_20'].iloc[-1]
            )

            # === ✅ 3. 策略條件判斷與命中率
            is_breakout = df['close'].iloc[-1] > indicators['bb_upper'].iloc[-1]
            volume_surge = indicators['volume'].iloc[-1] > indicators['volume'].rolling(20).mean().iloc[-1] * 1.2
            price_above_ema5 = indicators['close'].iloc[-1] > indicators['ema_5'].iloc[-1]

            rrov_conditions = {
                "突破壓力": is_breakout,
                "量能放大": volume_surge,
                "短期強勢": price_above_ema5
            }
            match_score = get_strategy_match_score('RROV', rrov_conditions)

            print(f"🎯 {symbol} ➜ 技術信心：{score:.2f}｜RROV 命中率：{match_score:.2f}")

            if score >= 0.75 and match_score >= 0.66:
                from modules.notify.discord_push import send_discord_message
                from modules.config import WEBHOOK_URL
                message = f"🚀【RROV 起漲警示】{symbol}｜技術信心 {score:.2f}｜命中率 {match_score:.2f}"
                send_discord_message(WEBHOOK_URL, message)
            if indicators is None:
                print(f"[跳過] {symbol} ➜ 指標產生失敗")
                continue

            # === ✅ 5. 防呆檢查：所有必要欄位是否存在且有值
            required_keys = [
                'rsi', 'roc', 'obv', 'zscore', 'vwap',
                'ema_5', 'ema_20', 'bb_upper', 'bb_lower', 'bb_mid'
            ]
            skip = False
            for key in required_keys:
                if key not in indicators or indicators[key].isna().iloc[-1]:
                    print(f"[跳過] {symbol} ➜ 指標 {key} 缺失或為 NaN")
                    skip = True
                    break
            if skip:
                continue

           # === 6. 抓技術指標資料
            if 'close' not in df.columns or df['close'].isnull().all():
                print(f"[跳過] {symbol} ➜ close 欄位無效")
                continue

            latest_price = df['close'].iloc[-1]
            if pd.isna(latest_price) or latest_price <= 0:
                print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
                continue
            rsi = indicators['rsi'].iloc[-1]
            roc = indicators['roc'].iloc[-1]
            obv = indicators['obv'].iloc[-1]
            obv_diff = obv - indicators['obv'].iloc[-2]
            zscore = indicators['zscore'].iloc[-1]
            vwap = indicators['vwap'].iloc[-1]
            ema5 = indicators['ema_5'].iloc[-1]
            ema20 = indicators['ema_20'].iloc[-1]
            upper_band = indicators['bb_upper'].iloc[-1]
            lower_band = indicators['bb_lower'].iloc[-1]
            mid_band = indicators['bb_mid'].iloc[-1]

            # ✅ EMA 金叉條件
            cond_ema_cross = (
                indicators["ema_5"].iloc[-2] < indicators["ema_20"].iloc[-2] and
                ema5 > ema20
            )
            # ✅ 插入這段統計 EMA 上彎 / 下彎 次數
            try:
                trend_series = indicators['ema_trend'].tail(20)  # 最後 20 根趨勢
                up_count = (trend_series == "上彎").sum()
                down_count = (trend_series == "下彎").sum()

                if up_count > down_count:
                    trend_bias = "偏多"
                elif down_count > up_count:
                    trend_bias = "偏空"
                else:
                    trend_bias = "盤整"

                ema_summary = f"EMA 趨勢：上彎 {up_count} 次｜下彎 {down_count} 次（{trend_bias}）"
            except Exception as e:
                ema_summary = "EMA 趨勢：統計失敗"
                print(f"[錯誤] {symbol} EMA 統計失敗：{e}")

            print(f"[EMA] {symbol} ➜ {ema_summary}")

            # === 3. 防呆處理
            try:
                obv_diff = indicators['obv'].diff().iloc[-1]
            except:
                obv_diff = 0

            if vwap != 0:
                vwap_deviation = (latest_price - vwap) / vwap * 100
            else:
                vwap_deviation = None

            # 可選：volume_ratio 也可防呆
            try:
                volume_ratio = df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
            except:
                volume_ratio = 1

            # === ✅ 技術傾向判斷（用來參考，不決定是否建倉）===
            bias = "⚪ 中性"
            if rsi > 60 or roc > 0.5 or ema5 > ema20 or obv_diff > 0:
                bias = "🟢 技術偏多（僅供參考）"
            elif rsi < 40 or roc < -0.5 or ema5 < ema20 or obv_diff < 0:
                bias = "🔴 技術偏空（僅供參考）"

            # === ✅ 真正的策略篩選與訊號邏輯 ===
            signal_type, signal_note, direction, strategy_name = detect_trading_signal(symbol, df, indicators, debug=True)

            if not signal_type:
                print(f"[略過] {symbol} ➜ 無明確策略訊號，跳過")
                continue

            # ✅ 僅對「順勢策略」進行半山腰過濾
            if strategy_name == "順勢策略":
                if direction == "多":
                    if not (
                        rsi > 60 and ema5 > ema20 and
                        abs(latest_price - vwap) / vwap < 0.03 and
                        latest_price < indicators['bb_upper'].iloc[-1] * 0.98
                    ):
                        print(f"[略過] {symbol} ➜ 多單順勢策略條件不佳（可能半山腰）")
                        continue
                elif direction == "空":
                    if not (
                        rsi < 40 and ema5 < ema20 and
                        abs(latest_price - vwap) / vwap < 0.03 and
                        latest_price > indicators['bb_lower'].iloc[-1] * 1.02
                    ):
                        print(f"[略過] {symbol} ➜ 空單順勢策略條件不佳（可能半山腰）")
                        continue

            # ✅ 3. 推播建倉訊號
            signal_type, signal_note, direction, strategy_name = detect_trading_signal(symbol, df, indicators, debug=True)

            # 🔁 補上 EMA 統計摘要
            if signal_note:
                signal_note += f"\n📊 {ema_summary}"
            else:
                signal_note = f"📊 {ema_summary}"

            # ✅ 4. 信心分數與建倉資訊計算
            confidence_score = 0.0
            if signal_type:
                # 計算 VWAP 與 BB 偏離
                vwap_deviation = abs(latest_price - vwap) / vwap * 100 if vwap else 0
                lower_band = indicators['bb_lower'].iloc[-1] if 'bb_lower' in indicators and indicators['bb_lower'].iloc[-1] > 0 else None
                bb_deviation = ((latest_price - lower_band) / lower_band * 100) if lower_band else 0

                confidence_score = compute_confidence_score(
                    rsi=rsi,
                    roc=roc,
                    obv=obv,
                    zscore=zscore,
                    vwap_deviation=vwap_deviation,
                    bb_deviation=bb_deviation,
                    ema5=ema5,
                    ema20=ema20
                )

                # 計算投入資金與股數
                capital_per_trade = 5000
                position_size = int(capital_per_trade / latest_price)
            # ✅ 多單條件（RROV / 均值回歸）
            cond_rsi_long = rsi < 35 and rsi > indicators['rsi'].iloc[-2]
            cond_roc_long = roc < 0 and roc > indicators['roc'].iloc[-2]
            cond_obv_long = obv > indicators['obv'].iloc[-2]
            cond_vwap_near = abs(latest_price - vwap) / vwap < 0.05

            cond_price_low = latest_price < indicators['bb_lower'].iloc[-1]
            cond_rsi_rebound = rsi > indicators['rsi'].iloc[-2] and rsi < 35
            cond_zscore_low = zscore < -2
            ond_ema_cross = ema5 > ema20

            # ✅ 空單條件（RROV / 均值回歸）
            cond_rsi_short = rsi > 65 and rsi < indicators['rsi'].iloc[-2]
            cond_roc_short = roc > 0 and roc < indicators['roc'].iloc[-2]
            cond_obv_short = obv < indicators['obv'].iloc[-2]

            cond_price_high = latest_price > indicators['bb_upper'].iloc[-1]
            cond_rsi_drop = rsi < indicators['rsi'].iloc[-2] and rsi > 65
            cond_zscore_high = zscore > 2
            cond_ema_death = ema5 < ema20

            # ✅ 補上技術方向布林旗標（用於技術條件邏輯）
            is_bullish = rsi > 50 and ema5 > ema20
            is_bearish = rsi < 50 and ema5 < ema20

            # ✅ 順勢策略條件（多空共用）
            cond_ema_trend = ema5 > ema20 if is_bullish else ema5 < ema20
            cond_rsi_trend = rsi > 55 if is_bullish else rsi < 45
            cond_obv_trend = obv > indicators['obv'].iloc[-2] if is_bullish else obv < indicators['obv'].iloc[-2]
            cond_price_above_vwap = latest_price > vwap if is_bullish else latest_price < vwap

            # ✅ 條件分流填入（多空雙向）
            if is_bullish:
                rrov_conditions = {
                    "RSI低位翻揚": cond_rsi_long,
                    "ROC翻揚": cond_roc_long,
                    "OBV上升": cond_obv_long,
                    "VWAP貼近": cond_vwap_near,
                }
                mean_revert_conditions = {
                    "跌破布林下緣": cond_price_low,
                    "RSI回升": cond_rsi_rebound,
                    "Z-score超跌": cond_zscore_low,
                    "EMA金叉": cond_ema_cross,
                }

            elif is_bearish:
                rrov_conditions = {
                    "RSI轉弱": cond_rsi_short,
                    "ROC下滑": cond_roc_short,
                    "OBV下降": cond_obv_short,
                    "VWAP貼近": cond_vwap_near,
                }
                mean_revert_conditions = {
                    "突破布林上緣": cond_price_high,
                    "RSI下降": cond_rsi_drop,
                    "Z-score過熱": cond_zscore_high,
                    "EMA死叉": cond_ema_death,
                }

            # ✅ 順勢策略條件（多空都可以計算）
            if is_bullish or is_bearish:
                trend_follow_conditions = {
                    "EMA順勢": cond_ema_trend,
                    "RSI順勢": cond_rsi_trend,
                    "OBV趨勢": cond_obv_trend,
                    "價格在VWAP之上/下": cond_price_above_vwap,
                }

            # ✅ 命中率計算（加入順勢）
            rrov_score = get_strategy_match_score("RROV", rrov_conditions)
            mean_score = get_strategy_match_score("均值回歸", mean_revert_conditions)
            trend_score = get_strategy_match_score("順勢策略", trend_follow_conditions)

            # === ✅ 印出策略命中分數（方便追蹤與 debug）===
            print(f"[策略診斷] {symbol} ➜ 順勢={trend_score:.2f}｜RROV={rrov_score:.2f}｜均值回歸={mean_score:.2f}")

            # === ✅ 若完全沒命中就跳過（都為 0）
            if trend_score == 0 and rrov_score == 0 and mean_score == 0:
                strategy_name = "策略未命中"
                strategy_display = "📌 未知策略"
                print(f"[策略選擇] {symbol} ➜ ❌ 無策略命中，跳過建倉")
                continue

            # === ✅ 改用 >= 比較，防止誤判 ===
            if trend_score >= rrov_score and trend_score >= mean_score:
                strategy_name = "順勢策略"
                strategy_display = get_strategy_display(strategy_name)
                print(f"[策略選擇] {symbol} ➜ 使用順勢策略（命中 {trend_score*100:.0f}%）")

            elif rrov_score >= mean_score:
                strategy_name = "RROV"
                strategy_display = get_strategy_display(strategy_name)
                print(f"[策略選擇] {symbol} ➜ 使用 RROV（命中 {rrov_score*100:.0f}%）")

            else:
                strategy_name = "均值回歸"
                strategy_display = get_strategy_display(strategy_name)
                print(f"[策略選擇] {symbol} ➜ 使用均值回歸（命中 {mean_score*100:.0f}%）")

            # === ✅ 額外 Debug 印出 Emoji 對照確認 ===
            print(f"[DEBUG] {symbol} ➜ 策略名稱：{strategy_name}｜emoji：{strategy_display}")
            
            # ✅ 集中處理 emoji 顯示（統一）
            strategy_display = get_strategy_display(strategy_name)

            # === ✅ 若三策略皆為 0，略過不進場
            if max(trend_score, rrov_score, mean_score) == 0:
                print(f"[略過] {symbol} ➜ 無策略條件命中，不進場")
                continue

            # === ✅ 若為「均值回歸策略」但未進場，印出診斷
            signal_type1, signal_note1, *_ = detect_mean_reversion_signals(df, symbol)
            if signal_type1 is None and signal_note1 and "未進場" in signal_note1:
                clean_note = signal_note1.replace("⛔ ", "").replace("：", "：\n")
                bb_dev = (
                    (latest_price - indicators["lower_band"].iloc[-1]) / indicators["lower_band"].iloc[-1] * 100
                    if indicators["lower_band"].iloc[-1] > 0 else 0
                )
                ema_diff = ema5 - ema20
                content = (
                    f"⛔ **[均值回歸未進場 - 診斷]** {symbol}\n"
                    f"🔍 原因：{clean_note}\n"
                    f"📉 價格=${latest_price:.2f}｜RSI={rsi:.1f}｜Z-score={zscore:.2f}\n"
                    f"📊 布林乖離：{bb_dev:.2f}%｜EMA 差值：{ema_diff:.2f}"
                )
                push_to_discord(content=content)

            # === ✅ 補充 RROV 診斷推播（未進場）
            signal_type2, signal_note2, direction2, strategy_name2 = detect_trading_signal(symbol, df, indicators)
            if signal_type2 is None and signal_note2:
                clean_note = signal_note2.replace("⛔ ", "").replace("（均值回歸）", "").replace("均值回歸", "").strip()
                vwap_dev = abs(latest_price - vwap) / vwap * 100 if vwap else 0
                content = (
                    f"⛔ **[RROV未進場 - 診斷]** {symbol}\n"
                    f"🔍 原因：{clean_note}\n"
                    f"📉 價格=${latest_price:.2f}｜RSI={rsi:.1f}｜ROC={roc:.2f}｜VWAP={vwap:.2f}｜VWAP乖離={vwap_dev:.2f}%"
                )
                push_to_discord(content=content)

            # === ✅ 潛伏預警（如 ALERT_BUY / ALERT_SELL）
            if signal_type1 in ["ALERT_BUY", "ALERT_SELL"]:
                obv_change = indicators['obv'].diff().iloc[-1] or 0
                vwap_dev = (latest_price - vwap) / vwap * 100 if vwap else 0
                bb_dev = 0
                if latest_price > indicators['bb_upper'].iloc[-1]:
                    bb_dev = (latest_price - indicators['bb_upper'].iloc[-1]) / indicators['bb_upper'].iloc[-1] * 100
                elif latest_price < indicators['bb_lower'].iloc[-1]:
                    bb_dev = (latest_price - indicators['bb_lower'].iloc[-1]) / indicators['bb_lower'].iloc[-1] * 100

                direction = "多" if signal_type1 == "ALERT_BUY" else "空"
                explanation = (
                    "潛伏多頭：貼近布林下緣 + RSI 低位 + Z-score 偏低 + EMA扭轉"
                    if signal_type1 == "ALERT_BUY" else
                    "潛伏空頭：突破布林上緣 + RSI 偏高 + Z-score 偏高，EMA即將死叉"
                )
                final_note = f"{signal_note1 or '⚠️ 無訊號說明'}\n📘 {explanation}"
                push_to_discord(
                    symbol=symbol,
                    price=latest_price,
                    rsi=rsi,
                    roc=roc,
                    vwap=vwap,
                    volume_ratio=indicators.get('volume_ratio', 1.0),
                    ema_cross=indicators.get('ema_status', 'N/A'),
                    candle_type=indicators.get('candle_type', 'N/A'),
                    signal_type=signal_type1,
                    signal_note=final_note,
                    confidence_score=None,
                    direction=direction,
                    strategy_name=strategy_display,
                    zscore=zscore,
                    obv=obv,
                    obv_change=obv_change,
                    vwap_deviation=vwap_dev,
                    bb_deviation=bb_dev
                )
                continue

            # === ✅ 若訊號成立才建倉 + 扣資金 + 推播 ===
            if signal_type1 in ["BUY", "SELL"]:
                direction = "多" if signal_type1 == "BUY" else "空"

                obv_change = indicators['obv'].diff().iloc[-1]
                if pd.isna(obv_change):
                    obv_change = 0

                vwap_deviation = (latest_price - indicators['vwap'].iloc[-1]) / indicators['vwap'].iloc[-1] * 100
                bb_deviation = ((latest_price - indicators['bb_lower'].iloc[-1]) / indicators['bb_lower'].iloc[-1]) * 100
                ema_diff = indicators['ema_5'].iloc[-1] - indicators['ema_20'].iloc[-1]

                confidence_score = compute_confidence_score(
                rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    obv=indicators['obv'].iloc[-1],
                    vwap_deviation=abs(vwap_deviation),
                    zscore=indicators['zscore'].iloc[-1],
                    bb_deviation=bb_deviation,
                    ema5=indicators['ema_5'].iloc[-1],
                    ema20=indicators['ema_20'].iloc[-1]
                )

                capital_required = min(TOTAL_CAPITAL * POSITION_RATIO, MAX_CAPITAL_PER_POSITION, capital_left)
                shares = int(capital_required / latest_price)

                if capital_left < capital_required or shares == 0:
                    print(f"[跳過] {symbol} ➜ 資金不足，剩餘資金={capital_left:.2f}，需要={capital_required:.2f}")

                elif can_enter_new_position(symbol, capital_required):
                    # ✅ 先定義策略名稱與 emoji 名稱
                    strategy_display = get_strategy_display(strategy_name)

                    # ✅ 抓最新指標值
                    zscore = indicators['zscore'].iloc[-1]
                    rsi = indicators['rsi'].iloc[-1]
                    roc = indicators['roc'].iloc[-1]
                    obv = indicators['obv'].iloc[-1]
                    ema5 = indicators['ema_5'].iloc[-1]
                    ema20 = indicators['ema_20'].iloc[-1]
                    vwap = indicators['vwap'].iloc[-1]
                    obv_diff = obv_change

                    # ✅ 建倉股數與資金（假設你已計算 shares、capital_required）
                    capital_per_trade = capital_required
                    position_size = shares  # 或 shares = compute_position_size(price)

                    # ✅ 執行建倉（一次傳入所有推播參數）
                    enter_position(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        signal_note=signal_note1,
                        rsi=rsi,
                        zscore=zscore,
                        strategy_name=strategy_name,
                        ema5=ema5,
                        ema20=ema20,
                        roc=roc,
                        obv=obv,
                        vwap=vwap,
                        confidence_score=confidence_score,
                        strategy_display=strategy_display  # ✅ 新增傳入 emoji 版策略名
                    )

                    # ✅ 組合推播訊息
                    signal_note = f"🐸 多單建倉訊號｜{strategy_display}" if "多" in direction else f"🐻 空單建倉訊號｜{strategy_display}"
                    push_note = (
                        f"{signal_note}\n"
                        f"📉 價格=${latest_price:.2f}｜RSI={rsi:.1f}｜策略：{strategy_display}｜信心分數：{confidence_score:.2f}\n"
                        f"💰 進場資金：${capital_per_trade:,.0f}｜📦 股數：{position_size:,} 股\n"
                        f"💼 剩餘資金：${capital_left:,.0f}"
                    )

                    # ✅ 推播
                    push_entry_to_discord(
                        symbol=symbol,
                        direction=direction,
                        price=latest_price,
                        signal_note=signal_note,
                        zscore=zscore,
                        rsi=rsi,
                        roc=roc,
                        obv=obv,
                        obv_change=obv_diff,
                        ema5=ema5,
                        ema20=ema20,
                        vwap=vwap,
                        strategy=strategy_display,
                        confidence_score=confidence_score,
                        capital_left=capital_left,
                        df=df
                    )

                    # ✅ 資金更新
                    quantity = position_size
                    capital_used = capital_per_trade
                    capital_left -= capital_used

                    # ✅ 記錄
                    record_entry_position(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        shares=quantity,
                        strategy_name=strategy_name,
                        confidence_score=confidence_score,
                        capital_used=capital_used
                    )

                    write_entry_to_sheet(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        shares=quantity,
                        capital=capital_used,
                        strategy=strategy_name,
                        confidence=confidence_score,
                        capital_left=capital_left
                    )

                    positions[symbol] = {
                        "entry_price": entry_price,
                        "latest_price": latest_price,
                        "direction": direction,
                        "quantity": shares,
                        "capital_used": capital,
                        "sell_stage": 0,
                        "max_gain": 0.0,
                        "strategy": strategy_name,
                        "entry_time": datetime.now()
                    }

            # === ⛔ 沒進場，但有診斷理由，就推播診斷訊息
            elif signal_type1 is None and signal_note1 and "未進場" in signal_note1:
                try:
                    ema5 = indicators['ema_5'].iloc[-1]
                    ema20 = indicators['ema_20'].iloc[-1]
                    ema_diff = ema5 - ema20
                    ema_bias = "多頭" if ema_diff > 0 else "空頭" if ema_diff < 0 else "無趨勢"

                    bb_dev = ((latest_price - indicators['bb_lower'].iloc[-1]) / indicators['bb_lower'].iloc[-1]) * 100

                    # 簡化說明訊息
                    content = (
                        f"⛔ **[均值回歸未進場 - 診斷]** {symbol}\n"
                        f"🔍 原因：{signal_note1.replace('⛔ ', '')}\n"
                        f"📉 價格=${latest_price:.2f}｜RSI={indicators['rsi'].iloc[-1]:.1f}｜Z-score={indicators['zscore'].iloc[-1]:.2f}\n"
                        f"📊 布林乖離：{bb_dev:.2f}%｜EMA 差值：{ema_diff:.2f}（{ema_bias}）"
                    )
                except Exception as e:
                    content = f"⛔ **[均值回歸未進場 - 診斷]** {symbol}\n❌ 診斷資料缺失：{e}"

                push_to_discord(content)

                continue  # ✅ 跳過 RROV，避免重複建倉

            # === ✅ RROV 策略建倉
            if signal_type2 in ["BUY", "SELL"]:
                direction = "多" if signal_type2 == "BUY" else "空"

                obv_change = indicators['obv'].diff().iloc[-1]
                if pd.isna(obv_change):
                    obv_change = 0

                vwap_deviation = (latest_price - indicators['vwap'].iloc[-1]) / indicators['vwap'].iloc[-1] * 100
                bb_deviation = (latest_price - indicators['bb_lower'].iloc[-1]) / indicators['bb_lower'].iloc[-1] * 100
                ema_diff = indicators['ema_5'].iloc[-1] - indicators['ema_20'].iloc[-1]

                confidence_score = compute_confidence_score(
                    rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    obv=indicators['obv'].iloc[-1],
                    vwap_deviation=abs(vwap_deviation),
                    zscore=indicators['zscore'].iloc[-1],
                    bb_deviation=bb_deviation,
                    ema5=indicators['ema_5'].iloc[-1],
                    ema20=indicators['ema_20'].iloc[-1]
                )

                # === 資金與股數限制
                capital_required = min(TOTAL_CAPITAL * POSITION_RATIO, MAX_CAPITAL_PER_POSITION, capital_left)
                shares = int(capital_required / latest_price)

                if capital_left < capital_required or shares == 0:
                    print(f"[跳過] {symbol} ➜ 資金不足，剩餘資金={capital_left:.2f}，需要={capital_required:.2f}")
                    continue
                
                # ✅ 建倉前：防重複建倉
                if symbol in entered_positions:
                    print(f"[跳過] {symbol} ➜ 已建倉，避免重複進場")
                    continue

                if can_enter_new_position(symbol, capital_required):
                    # ✅ 先定義策略與顯示名稱
                    strategy_display = get_strategy_display(strategy_name)

                    # ✅ 指標與資金資訊
                    rsi = indicators['rsi'].iloc[-1]
                    zscore = indicators['zscore'].iloc[-1]
                    roc = indicators['roc'].iloc[-1]
                    obv = indicators['obv'].iloc[-1]
                    ema5 = indicators['ema_5'].iloc[-1]
                    ema20 = indicators['ema_20'].iloc[-1]
                    vwap = indicators['vwap'].iloc[-1]
                    obv_diff = obv_change
                    capital_per_trade = capital_required
                    position_size = shares

                    # ✅ 訊號說明（多 or 空）
                    signal_note = f"🐸 多單建倉訊號｜{strategy_display}" if "多" in direction else f"🐻 空單建倉訊號｜{strategy_display}"

                    # ✅ 建倉
                    enter_position(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        signal_note=signal_note,
                        rsi=rsi,
                        zscore=zscore,
                        roc=roc,
                        obv=obv,
                        ema5=ema5,
                        ema20=ema20,
                        vwap=vwap,
                        strategy_name=strategy_name,
                        confidence_score=confidence_score,
                        strategy_display=strategy_display
                    )

                    # ✅ 資金更新與紀錄
                    capital_left -= capital_required

                    # ✅ 推播建倉訊息
                    push_entry_to_discord(
                        symbol=symbol,
                        direction=direction,
                        price=latest_price,
                        signal_note=signal_note,
                        zscore=zscore,
                        rsi=rsi,
                        roc=roc,
                        obv=obv,
                        obv_change=obv_diff,
                        ema5=ema5,
                        ema20=ema20,
                        vwap=vwap,
                        strategy=strategy_display,
                        confidence_score=confidence_score,
                        capital_left=capital_left,
                        df=df
                    )

                    record_entry_position(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        shares=position_size,
                        strategy_name=strategy_name,
                        confidence_score=confidence_score,
                        capital_used=capital_required
                    )

                    write_entry_to_sheet(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        shares=position_size,
                        capital=capital_required,
                        strategy=strategy_name,
                        confidence=confidence_score,
                        capital_left=capital_left
                    )

                    positions[symbol] = {
                        "entry_price": latest_price,
                        "latest_price": latest_price,        # ✅ 用 latest_price
                        "direction": direction,
                        "quantity": position_size,          # ✅ 用 position_size
                        "capital_used": capital_required,   # ✅ 用 capital_required
                        "sell_stage": 0,
                        "max_gain": 0.0,
                        "strategy": strategy_name,
                        "entry_time": datetime.now()
                    }

                    # ✅ 技術推播 - 所有指標整合
                    send_entry_push(
                        symbol=symbol,
                        direction=direction,
                        strategy_name=strategy_name,
                        strategy_emoji=strategy_display,  # emoji 須預先定義：📈📉📊 等
                        confidence_score=confidence_score,
                        latest_price=latest_price,
                        capital_used = capital_required,
                        capital_left=capital_left,
                        shares=shares,
                        rsi=rsi,
                        ema5=ema5,
                        ema20=ema20,
                        zscore=zscore,
                        vwap=vwap,
                        bb_upper=upper_band,
                        bb_lower=lower_band,
                        volume_ratio=volume_ratio,
                        obv_change_text="上升" if obv_diff > 0 else "下滑" if obv_diff < 0 else "震盪",
                        trend_note=trend_bias,               # 例如：偏空 / 偏多 / 盤整
                        emoji_trend=bias[:2],               # 取前兩字：🟢 / 🔴 / ⚪
                        trend_score=trend_score,            # 來自策略診斷區
                        rrov_score=rrov_score,
                        mean_score=mean_score,
                        roc=roc
                    )

                    print(f"[✅ 建倉同步] {symbol} ➜ 建倉價格={latest_price}，數量={position_size}，策略={strategy_name}")
                    
            elif strategy_name == "順勢策略" and signal_type1 in ["BUY", "SELL"]:
                direction = "多" if signal_type1 == "BUY" else "空"

                # === ✅ 補強條件：防止買在半山腰 ===
                if direction == "多":
                    if not (
                        rsi > 60 and
                        ema5 > ema20 and
                        abs(latest_price - vwap) / vwap < 0.03 and
                        latest_price < indicators['bb_upper'].iloc[-1] * 0.98
                    ):
                        print(f"[略過] {symbol} ➜ 多單順勢策略條件不佳（可能半山腰）")
                        continue

                elif direction == "空":
                    if not (
                        rsi < 40 and
                        ema5 < ema20 and
                        abs(latest_price - vwap) / vwap < 0.03 and
                        latest_price > indicators['bb_lower'].iloc[-1] * 1.02
                    ):
                        print(f"[略過] {symbol} ➜ 空單順勢策略條件不佳（可能半山腰）")
                        continue

                obv_change = indicators['obv'].diff().iloc[-1]
                if pd.isna(obv_change):
                    obv_change = 0

                vwap_deviation = (latest_price - indicators['vwap'].iloc[-1]) / indicators['vwap'].iloc[-1] * 100
                bb_deviation = (latest_price - indicators['bb_lower'].iloc[-1]) / indicators['bb_lower'].iloc[-1] * 100
                ema_diff = indicators['ema_5'].iloc[-1] - indicators['ema_20'].iloc[-1]

                confidence_score = compute_confidence_score(
                    rsi=indicators['rsi'].iloc[-1],
                    roc=indicators['roc'].iloc[-1],
                    obv=indicators['obv'].iloc[-1],
                    vwap_deviation=abs(vwap_deviation),
                    zscore=indicators['zscore'].iloc[-1],
                    bb_deviation=bb_deviation,
                    ema5=indicators['ema_5'].iloc[-1],
                    ema20=indicators['ema_20'].iloc[-1]
                )

                capital_required = min(TOTAL_CAPITAL * POSITION_RATIO, MAX_CAPITAL_PER_POSITION, capital_left)
                shares = int(capital_required / latest_price)

                if capital_left < capital_required or shares == 0:
                    print(f"[跳過] {symbol} ➜ 資金不足，剩餘資金={capital_left:.2f}，需要={capital_required:.2f}")
                    return

                if symbol in entered_positions:
                    print(f"[跳過] {symbol} ➜ 已建倉，避免重複進場")
                    return

                if can_enter_new_position(symbol, capital_required):
                    strategy_display = get_strategy_display(strategy_name)

                    rsi = indicators['rsi'].iloc[-1]
                    zscore = indicators['zscore'].iloc[-1]
                    roc = indicators['roc'].iloc[-1]
                    obv = indicators['obv'].iloc[-1]
                    ema5 = indicators['ema_5'].iloc[-1]
                    ema20 = indicators['ema_20'].iloc[-1]
                    vwap = indicators['vwap'].iloc[-1]
                    obv_diff = obv_change
                    capital_per_trade = capital_required
                    position_size = shares

                    signal_note = f"📈 多單建倉訊號｜{strategy_display}" if "多" in direction else f"📉 空單建倉訊號｜{strategy_display}"

                    # ✅ 執行建倉
                    enter_position(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        signal_note=signal_note,
                        rsi=rsi,
                        zscore=zscore,
                        strategy_name=strategy_name,
                        ema5=ema5,
                        ema20=ema20,
                        roc=roc,
                        obv=obv,
                        vwap=vwap,
                        confidence_score=confidence_score,
                        strategy_display=strategy_display
                    )

                     # ✅ 更新資金
                    capital_left -= capital_required

                    # ✅ 推播訊息
                    push_entry_to_discord(
                        symbol=symbol,
                        direction=direction,
                        price=latest_price,
                        signal_note=signal_note,
                        zscore=zscore,
                        rsi=rsi,
                        roc=roc,
                        obv=obv,
                        obv_change=obv_diff,
                        ema5=ema5,
                        ema20=ema20,
                        vwap=vwap,
                        strategy=strategy_display,
                        confidence_score=confidence_score,
                        capital_left=capital_left,
                        df=df
                    )

                    record_entry_position(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        shares=position_size,
                        strategy_name=strategy_name,
                        confidence_score=confidence_score,
                        capital_used=capital_required
                    )

                    write_entry_to_sheet(
                        symbol=symbol,
                        price=latest_price,
                        direction=direction,
                        shares=position_size,
                        capital=capital_required,
                        strategy=strategy_name,
                        confidence=confidence_score,
                        capital_left=capital_left
                    )

                    positions[symbol] = {
                        "entry_price": entry_price,
                        "latest_price": latest_price,
                        "direction": direction,
                        "quantity": shares,
                        "capital_used": capital,
                        "sell_stage": 0,
                        "max_gain": 0.0,
                        "strategy": strategy_name,
                        "entry_time": datetime.now()
                    }
                # === 3. 出場邏輯
                if symbol in positions:
                    check_exit_and_notify(symbol, latest_price)
                    
        except Exception as e:
            print(f"[錯誤] {symbol} 描錯誤：{e}\n{traceback.format_exc()}")
            continue
# ✅ 單獨執行用（不影響其他模組呼叫）
if __name__ == "__main__":
    symbol_list = load_stock_list()
    scan_market(symbol_list)
