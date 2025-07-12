import pandas as pd
import traceback
import random
from .fetch_stock_data import fetch_stock_data
from .get_fundamentals import get_fundamentals
from .filter_fundamentals import filter_fundamentals
from .calculate_indicators import calculate_indicators
from .detect_trading_signal import detect_trading_signal
from .compute_confidence_score import compute_confidence_score
from .load_stock_list import load_stock_list
from .config import POLYGON_API_KEY, capital_left, WEBHOOK_URL
from modules.notify.discord_push import send_discord_message
from modules.enter_position import enter_position
from modules.strategy.utils import get_strategy_display
from modules.strategy.strategy_score import get_rrov_score, get_trend_score, get_mean_score
from modules.notify.build_discord_message import build_entry_message
from modules.strategy.detect_squeeze_breakout import detect_squeeze_breakout

stock_list = load_stock_list()

# ✅ 整齊版摘要顯示
def print_debug_summary(symbol, indicators, latest_price, score, rrov_score, trend_score, mean_score):
    rsi = indicators['rsi'].iloc[-1]
    ema5 = indicators['ema_5'].iloc[-1]
    ema20 = indicators['ema_20'].iloc[-1]
    obv = indicators['obv'].iloc[-1]
    zscore = indicators['zscore'].iloc[-1]
    obv_trend = "上升" if obv - indicators['obv'].iloc[-2] > 0 else "下降"
    vwap = indicators['vwap'].iloc[-1]
    vwap_diff = latest_price - vwap
    vwap_pct = (vwap_diff / vwap) * 100
    ema_relation = "EMA5 > EMA20" if ema5 > ema20 else "EMA5 < EMA20"

    print("───────────── 技術判斷摘要 ─────────────")
    print(f"📌 股票代號：{symbol}")
    print(f"🧠 技術信心：{score:.2f}")
    print(f"🎯 命中率 ➜ 順勢：{trend_score:.2f}｜RROV：{rrov_score:.2f}｜均值：{mean_score:.2f}")
    print(f"📈 收盤價：${latest_price:.2f}｜RSI：{rsi:.1f}｜Z-score：{zscore:.2f}")
    print(f"📉 {ema_relation}｜VWAP乖離：{vwap_pct:.2f}%｜OBV變化：{obv_trend}")
    print("─────────────────────────────────────")

# ✅ 掃描主邏輯
def scan_market(symbol_list):
    global capital_left
    random.shuffle(symbol_list)
    MIN_REQUIRED_CAPITAL = 3000
    if capital_left < MIN_REQUIRED_CAPITAL:
        print(f"[資金耗盡] 剩餘資金 ${capital_left:.2f} 已低於 ${MIN_REQUIRED_CAPITAL}，暫停掃描...")
        return

    for symbol in symbol_list:
        try:
            print(f"\n📡 掃描中：{symbol}")
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

            # ✅ 三策略命中率
            rrov_score = get_rrov_score(indicators, latest_price)
            trend_score = get_trend_score(indicators)
            mean_score = get_mean_score(indicators, latest_price)

            # ✅ 技術信心分數
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

            # ✅ 顯示終端摘要
            print_debug_summary(symbol, indicators, latest_price, score, rrov_score, trend_score, mean_score)

            # ✅ 額外偵測擠壓 + 突破策略
            squeeze_result = detect_squeeze_breakout(symbol)
            if squeeze_result:
                print(f"📣 [{symbol}] 擠壓突破策略觸發！")
                print(f"分數：{squeeze_result['score']}")
                print(f"命中條件：{', '.join(squeeze_result['conditions_met'])}")

                # ✅ 組裝推播訊息
                from modules.notify.build_discord_message import build_breakout_message
                msg = build_breakout_message(squeeze_result)
                send_discord_message(WEBHOOK_URL, msg)

               # ✅ 擠壓突破策略也建倉
                shares, capital_used = enter_position(
                    symbol=symbol,
                    price=squeeze_result["close"],
                    direction="做多",
                    score=squeeze_result["score"],
                    strategy_name="擠壓突破",
                    rsi=squeeze_result.get("rsi"),
                    ema5=squeeze_result.get("ema_5"),
                    ema20=squeeze_result.get("ema_20"),
                    obv=None,  # 若你想抓 OBV 也可加上
                    signal_note="Squeeze OFF + 價格突破 + 技術條件命中",
                )

                if shares:
                    print(f"✅ 擠壓策略建倉成功：{shares} 股，用資金 ${capital_used:.2f}")

            # ✅ 判斷是否有交易訊號
            signal_type, strategy_name, signal_note, direction = detect_trading_signal(
                symbol, df, indicators, latest_price
            )

            if signal_type is None:
                print(f"[略過] {symbol} ➜ 無明確訊號")
                continue

            # ✅ 建倉執行（模擬）
            result = enter_position(symbol, latest_price, direction, score, strategy_name)
            if result is None:
                print(f"[略過] {symbol} ➜ 建倉失敗")
                continue

            shares, capital_used = result

            # ✅ 推播訊息組裝與發送
            message = build_entry_message(
                symbol=symbol,
                strategy_type="📌 技術選股",
                signal_type=signal_type,
                direction=direction,
                score=score,
                win_rate=rrov_score,
                trend_text=direction,
                trend_emoji="📈" if direction == "做多" else "📉",
                up_count=result[2] if len(result) > 2 else 0,
                down_count=result[3] if len(result) > 3 else 0,
                ema_trend="多頭" if indicators['ema_5'].iloc[-1] > indicators['ema_20'].iloc[-1] else "空頭",
                signal_note=signal_note,
                strategy_name=strategy_name,
                shares=shares,
                capital_used=int(capital_used),  # ✅ 移除小數點
                capital_left=int(capital_left)
            )
            send_discord_message(WEBHOOK_URL, message)

        except Exception as e:
            print(f"[錯誤] {symbol} 掃描錯誤：{e}")
            traceback.print_exc()
