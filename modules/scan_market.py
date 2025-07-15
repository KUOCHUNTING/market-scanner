import pandas as pd
import traceback
import random
import math
from ta.momentum import RSIIndicator, ROCIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands
from ta.volume import OnBalanceVolumeIndicator
from modules.utils.file_loader import load_stock_list, load_api_keys
from modules.fetch_stock_data import fetch_stock_data
from modules.get_fundamentals import get_fundamentals
from modules.filter_fundamentals import filter_fundamentals
from modules.logic.detect_trading_signal import detect_trading_signal
from modules.compute_confidence_score import compute_confidence_score
from modules.load_stock_list import load_stock_list
from modules.config import POLYGON_API_KEY, capital_left, WEBHOOK_URL
from modules.notify.discord_push import send_discord_message
from modules.enter_position import enter_position
from modules.strategy.strategy_score import get_rrov_score, get_trend_score, get_mean_score
from modules.strategy.detect_squeeze_breakout import detect_squeeze_breakout
from modules.utils.validate_indicators import is_invalid
from modules.strategy.detect_squeeze_breakout import detect_squeeze_breakout
from modules.indicators.calculate_indicators import calculate_indicators
from modules.utils.format import get_last_value
from modules.notify.build_discord_message import build_entry_message
from modules.notify.build_discord_message import build_entry_message, build_mean_reversion_message, build_rrov_message, build_trend_message, build_breakout_message

# ✅ 股票清單
stock_list = load_stock_list()

# ✅ 主掃描函數
def scan_market(symbol_list):
    global capital_left
    random.shuffle(symbol_list)
    MIN_REQUIRED_CAPITAL = 3000

    if capital_left < MIN_REQUIRED_CAPITAL:
        print(f"[資金耗盡] 剩餘資金 ${capital_left:.2f}，暫停掃描")
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

            indicators = calculate_indicators(df, symbol)
            if indicators is None or is_invalid(indicators):
                print(f"[跳過] {symbol} ➜ 指標無效")
                continue

            latest_price = df['close'].iloc[-1]
            if pd.isna(latest_price) or latest_price <= 0:
                print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
                continue

            rrov_score = get_rrov_score(indicators, latest_price)
            trend_score = get_trend_score(indicators)
            mean_score = get_mean_score(indicators, latest_price)

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

            # 擠壓策略
            squeeze_result = detect_squeeze_breakout(symbol)
            if squeeze_result:
                print(f"📣 [{symbol}] 擠壓突破策略觸發！")
                msg = build_breakout_message(squeeze_result)
                send_discord_message(WEBHOOK_URL, msg)

                shares, capital_used, _ = enter_position(
                    symbol=symbol,
                    price=squeeze_result["close"],
                    direction=squeeze_result["direction"],
                    score=squeeze_result["score"],
                    strategy_name=squeeze_result["strategy_name"],
                    rsi=squeeze_result.get("rsi"),
                    ema5=squeeze_result.get("ema_5"),
                    ema20=squeeze_result.get("ema_20"),
                    signal_note="Squeeze OFF + 技術條件命中"
                )
                if shares:
                    print(f"✅ 擠壓策略建倉成功：{shares} 股，用資金 ${capital_used:.2f}")

            # 技術策略
            signal_type, strategy_name, signal_note, direction, extra = detect_trading_signal(symbol, df, indicators, latest_price)
            if signal_type is None:
                print(f"[略過] {symbol} ➜ 無明確訊號")
                continue

            result = enter_position(symbol, latest_price, direction, score, strategy_name)
            if result is None:
                continue

            shares, capital_used = result[:2]
            message = build_entry_message(
                symbol=symbol,
                price=latest_price,
                strategy_type="📌 技術選股",
                signal_type=signal_type,
                strategy_name=strategy_name,
                signal_note=signal_note,
                direction=direction,
                score=score,
                confidence_score=score,
                rsi = get_last_value(indicators.get("rsi")),
                zscore = get_last_value(indicators.get("zscore")),
                ema5 = get_last_value(indicators.get("ema_5")),
                ema20 = get_last_value(indicators.get("ema_20")),
                bb_upper = get_last_value(indicators.get("bb_upper")),
                bb_lower = get_last_value(indicators.get("bb_lower")),
                obv = get_last_value(indicators.get("obv")),
                trend_score=trend_score,
                rrov_score=rrov_score,
                mean_score=mean_score,
                shares=shares,
                capital_used=capital_used,
                capital_left=capital_left
            )
            send_discord_message(WEBHOOK_URL, message)

        except Exception as e:
            print(f"[錯誤] {symbol} 掃描錯誤：{e}")
            traceback.print_exc()
