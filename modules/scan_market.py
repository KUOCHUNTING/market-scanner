# === 📦 套件與模組匯入 ===
import pandas as pd
import traceback
import random

# === 📊 自訂模組 ===
from .fetch_stock_data import fetch_stock_data
from .get_fundamentals import get_fundamentals
from .filter_fundamentals import filter_fundamentals
from .calculate_indicators import calculate_indicators
from .detect_trading_signal import detect_trading_signal
from .compute_confidence_score import compute_confidence_score
from .load_stock_list import load_stock_list
from .config import POLYGON_API_KEY, capital_left, WEBHOOK_URL

# === 📤 推播與建倉模組 ===
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import build_entry_message
from modules.enter_position import enter_position

# === 🧠 策略工具與評分模組 ===
from modules.strategy.utils import get_strategy_display
from modules.strategy.strategy_score import (get_rrov_scores,get_trend_scores,get_mean_scores)

# === 🧾 載入股票清單 ===
stock_list = load_stock_list()

# ✅ 整齊版摘要顯示
def print_debug_summary(symbol, indicators, latest_price, score, rrov_score, trend_score, 
                        strategy_name=None, direction=None, strategy_hit=None,
                        trend_long=None, trend_short=None, 
                        rrov_long=None, rrov_short=None, 
                        mean_long=None, mean_short=None):

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

    if trend_long is not None and trend_short is not None:
        print(f"🎯 命中率 ➜")
        print(f"　🔹 順勢：多 {trend_long:.2f}｜空 {trend_short:.2f}")
        print(f"　🔹 RROV：多 {rrov_long:.2f}｜空 {rrov_short:.2f}")
        print(f"　🔹 均值：多 {mean_long:.2f}｜空 {mean_short:.2f}")

    print(f"📈 收盤價：${latest_price:.2f}｜RSI：{rsi:.1f}｜Z-score：{zscore:.2f}")
    print(f"📉 {ema_relation}｜VWAP乖離：{vwap_pct:.2f}%｜OBV變化：{obv_trend}")

    if strategy_name:
        print(f"📊 策略：{strategy_name}｜方向：{direction}｜命中：{strategy_hit}")

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
            rrov_long, rrov_short = get_rrov_scores(indicators, latest_price)
            trend_long, trend_short = get_trend_scores(indicators)
            mean_long, mean_short = get_mean_scores(indicators, latest_price)

            # 顯示技術摘要
            print(f"📌 股票代號：{symbol}")
            print(f"🎯 多頭命中 ➜ 順勢：{trend_long:.2f}｜RROV：{rrov_long:.2f}｜均值：{mean_long:.2f}")
            print(f"🎯 空頭命中 ➜ 順勢：{trend_short:.2f}｜RROV：{rrov_short:.2f}｜均值：{mean_short:.2f}")

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
            print_debug_summary(
                symbol,
                indicators,
                latest_price,
                score,
                rrov_long,
                rrov_short,
                trend_long,
                trend_short,
                mean_long,
                mean_short
            )

            # ✅ 判斷是否有交易訊號
            signal_type, strategy_name, signal_note, direction = detect_trading_signal(
                df, indicators, latest_price, rrov_score, trend_score, mean_score
            )

            if signal_type is None:
                print(f"[略過] {symbol} ➜ 無明確訊號")
                continue

            # ✅ 嘗試建倉（模擬進場）
            print(f"[進場嘗試] {symbol} ➜ 策略：{strategy_name}｜方向：{direction}｜價格：{latest_price:.2f}")
            result = enter_position(symbol, latest_price, direction, score, strategy_name)
            
            if result is None:
                print(f"[略過] {symbol} ➜ 建倉失敗")
                continue

            shares, capital_used = result
            print(f"[✅ 建倉成功] {symbol} ➜ 股數：{shares}｜花費資金：${capital_used:.2f}｜剩餘資金：${capital_left:.2f}")
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
