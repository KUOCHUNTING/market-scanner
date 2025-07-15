import pandas as pd
import traceback
import random

from modules.utils.file_loader import load_stock_list
from modules.fetch_stock_data import fetch_stock_data
from modules.get_fundamentals import get_fundamentals
from modules.filter_fundamentals import filter_fundamentals
from modules.indicators.calculate_indicators import calculate_indicators
from modules.utils.validate_indicators import is_invalid
from modules.config import POLYGON_API_KEY, capital_left

# 🧠 統一策略邏輯
from modules.strategy import (
    detect_trading_signal,
    get_rrov_score,
    get_trend_score,
    get_mean_score,
    compute_confidence_score,
    detect_squeeze_breakout
)

# 💼 建倉模組
from modules.entry.handle_squeeze_entry import handle_squeeze_entry
from modules.entry.handle_signal_entry import handle_signal_entry

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

            latest_price = df["close"].iloc[-1]
            if pd.isna(latest_price) or latest_price <= 0:
                print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
                continue

            # ✅ 評分與策略得分
            rrov_score = get_rrov_score(indicators, latest_price)
            trend_score = get_trend_score(indicators)
            mean_score = get_mean_score(indicators, latest_price)

            score = compute_confidence_score(
                rsi=indicators["rsi"].iloc[-1],
                roc=indicators["roc"].iloc[-1],
                obv=indicators["obv"].iloc[-1],
                vwap_deviation=indicators["vwap"].iloc[-1] - latest_price,
                zscore=indicators["zscore"].iloc[-1],
                bb_deviation=(latest_price - indicators["bb_lower"].iloc[-1]) /
                             (indicators["bb_upper"].iloc[-1] - indicators["bb_lower"].iloc[-1] + 1e-6),
                ema5=indicators["ema_5"].iloc[-1],
                ema20=indicators["ema_20"].iloc[-1],
            )

            # ✅ 擠壓策略建倉處理
            squeeze_result = detect_squeeze_breakout(symbol)
            handle_squeeze_entry(symbol, squeeze_result)

            # ✅ 技術策略建倉處理
            signal_type, strategy_name, signal_note, direction, extra = detect_trading_signal(
                symbol, df, indicators, latest_price
            )
            if signal_type is None:
                print(f"[略過] {symbol} ➜ 無明確訊號")
                continue

            handle_signal_entry(
                symbol=symbol,
                latest_price=latest_price,
                direction=direction,
                score=score,
                strategy_name=strategy_name,
                signal_type=signal_type,
                signal_note=signal_note,
                indicators=indicators,
                trend_score=trend_score,
                rrov_score=rrov_score,
                mean_score=mean_score,
                capital_left=capital_left
            )

        except Exception as e:
            print(f"[錯誤] {symbol} 掃描錯誤：{e}")
            traceback.print_exc()
