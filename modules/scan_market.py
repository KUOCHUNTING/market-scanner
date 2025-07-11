import pandas as pd
import traceback
import random
from .fetch_stock_data import fetch_stock_data
from .get_fundamentals import get_fundamentals
from .filter_fundamentals import filter_fundamentals
from .calculate_indicators import calculate_indicators
from .detect_trading_signal import detect_trading_signal
from .compute_confidence_score import compute_confidence_score, get_strategy_match_score
from .load_stock_list import load_stock_list
from .config import POLYGON_API_KEY, capital_left, WEBHOOK_URL
from modules.notify.discord_push import send_discord_message
from modules.enter_position import enter_position
from modules.strategy.utils import get_strategy_display  # ✅ 補上策略顯示名稱

stock_list = load_stock_list()

def scan_market(symbol_list):
    global capital_left

    random.shuffle(symbol_list)
    MIN_REQUIRED_CAPITAL = 3000
    if capital_left < MIN_REQUIRED_CAPITAL:
        print(f"[資金耗盡] 剩餘資金 ${capital_left:.2f} 已低於 ${MIN_REQUIRED_CAPITAL}，暫停掃描...")
        return

    for symbol in symbol_list:
        try:
            print(f"📡 掃描中：{symbol}")
            df = fetch_stock_data(symbol, POLYGON_API_KEY)
            if df is None or df.empty:
                print(f"[跳過] {symbol} ➜ 無資料")
                continue

            fundamentals = get_fundamentals(symbol, POLYGON_API_KEY, df)
            passed, reason = filter_fundamentals(symbol, fundamentals)
            if not passed:
                print(f"[跳過] {symbol} ➜ {reason}")
                continue

            indicators = calculate_indicators(df)
            if indicators is None:
                print(f"[跳過] {symbol} ➜ 指標產生失敗")
                continue

            required_keys = ['rsi', 'roc', 'obv', 'zscore', 'vwap', 'ema_5', 'ema_20', 'bb_upper', 'bb_lower', 'bb_mid']
            if any(k not in indicators or indicators[k].isna().iloc[-1] for k in required_keys):
                print(f"[跳過] {symbol} ➜ 技術指標缺失")
                continue

            latest_price = df['close'].iloc[-1]
            if pd.isna(latest_price) or latest_price <= 0:
                print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
                continue

            score = compute_confidence_score(
                rsi=indicators['rsi'].iloc[-1],
                roc=indicators['roc'].iloc[-1],
                obv=indicators['obv'].iloc[-1],
                vwap_deviation=indicators['vwap'].iloc[-1] - latest_price,
                zscore=indicators['zscore'].iloc[-1],
                bb_deviation=(latest_price - indicators['bb_lower'].iloc[-1]) /
                             (indicators['bb_upper'].iloc[-1] - indicators['bb_lower'].iloc[-1] + 1e-6),
                ema5=indicators['ema_5'].iloc[-1],
                ema20=indicators['ema_20'].iloc[-1]
            )

            is_breakout = latest_price > indicators['bb_upper'].iloc[-1]
            volume_surge = indicators['curr_volume'] > indicators['avg_volume'] * 1.2
            price_above_ema5 = latest_price > indicators['ema_5'].iloc[-1]
            rrov_conditions = {
                "突破壓力": is_breakout,
                "量能放大": volume_surge,
                "短期強勢": price_above_ema5
            }
            match_score = get_strategy_match_score('RROV', rrov_conditions)
            print(f"🎯 {symbol} ➜ 技術信心：{score:.2f}｜RROV 命中率：{match_score:.2f}")

            try:
                trend_series = indicators['ema_trend'].tail(20)
                up_count = (trend_series == "上彎").sum()
                down_count = (trend_series == "下彎").sum()
                ema_trend = "多" if up_count > down_count else "空" if down_count > up_count else "盤整"
            except Exception as e:
                ema_trend = "未知"
                print(f"[錯誤] {symbol} EMA 統計失敗：{e}")

            rsi = indicators['rsi'].iloc[-1]
            roc = indicators['roc'].iloc[-1]
            ema5 = indicators['ema_5'].iloc[-1]
            ema20 = indicators['ema_20'].iloc[-1]
            obv = indicators['obv'].iloc[-1]
            obv_diff = indicators['obv'].diff().iloc[-1]
            bias = "🟢 技術偏多" if rsi > 60 or roc > 0.5 or ema5 > ema20 or obv_diff > 0 else \
                   "🔴 技術偏空" if rsi < 40 or roc < -0.5 or ema5 < ema20 or obv_diff < 0 else "⚪ 中性"

            signal_type, signal_note, direction, strategy_name = detect_trading_signal(symbol, df, indicators, debug=True)
            if not signal_type:
                print(f"[略過] {symbol} ➜ 無明確策略訊號")
                continue

            # ✅ 補上完整 enter_position 呼叫
            enter_position(
                symbol=symbol,
                price=latest_price,
                direction=direction,
                signal_note=signal_note,
                rsi=rsi,
                zscore=indicators["zscore"].iloc[-1],
                strategy_name=strategy_name,
                strategy_display=get_strategy_display(strategy_name),
                ema5=ema5,
                ema20=ema20,
                upper_band=indicators["bb_upper"].iloc[-1],
                lower_band=indicators["bb_lower"].iloc[-1],
                mid_band=indicators["bb_mid"].iloc[-1],
                roc=roc,
                obv=obv,
                vwap=indicators["vwap"].iloc[-1],
                confidence_score=score
            )

            # 半山腰過濾（順勢策略專屬）
            if strategy_name == "順勢策略":
                vwap = indicators['vwap'].iloc[-1]
                if direction == "多":
                    if not (rsi > 60 and ema5 > ema20 and abs(latest_price - vwap)/vwap < 0.03 and latest_price < indicators['bb_upper'].iloc[-1]*0.98):
                        print(f"[略過] {symbol} ➜ 多單順勢策略條件不佳")
                        continue
                elif direction == "空":
                    if not (rsi < 40 and ema5 < ema20 and abs(latest_price - vwap)/vwap < 0.03 and latest_price > indicators['bb_lower'].iloc[-1]*1.02):
                        print(f"[略過] {symbol} ➜ 空單順勢策略條件不佳")
                        continue

            # 推播變數補齊
            strategy_type = "技術策略"
            trend_emoji = "🟢" if ema_trend == "多" else "🔴" if ema_trend == "空" else "⚪"
            trend_text = ema_trend
            win_rate = match_score * 100

            # ✅ 推播完整訊息
            message = f"🚀【{strategy_type} 訊號】{symbol}\n"
            message += f"📊 類型：{signal_type}（方向：{direction}）\n"
            message += f"🧠 信心分數：{score:.2f}｜RROV 命中率：{win_rate:.2f}%\n"
            message += f"📈 技術傾向：{trend_emoji} 技術偏{trend_text}\n"
            message += f"📉 EMA 趨勢：上漲 {up_count} 次｜下跌 {down_count} 次（偏{ema_trend}）\n"
            message += f"📋 訊號說明：{signal_note}"
            message += f"\n🧠 策略：{strategy_name}"
            send_discord_message(WEBHOOK_URL, message)

        except Exception as e:
            print(f"[錯誤] {symbol} 描錯誤：{e}")
            traceback.print_exc()
