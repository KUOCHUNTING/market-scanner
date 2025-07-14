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
from modules.detect_trading_signal import detect_trading_signal
from modules.compute_confidence_score import compute_confidence_score
from modules.load_stock_list import load_stock_list
from modules.config import POLYGON_API_KEY, capital_left, WEBHOOK_URL
from modules.notify.discord_push import send_discord_message
from modules.enter_position import enter_position
from modules.strategy.strategy_score import get_rrov_score, get_trend_score, get_mean_score
from modules.notify.build_discord_message import build_entry_message, build_breakout_message
from modules.strategy.detect_squeeze_breakout import detect_squeeze_breakout
from modules.utils.validate_indicators import is_invalid
from modules.strategy.detect_squeeze_breakout import detect_squeeze_breakout
# ✅ 股票清單
stock_list = load_stock_list()

# ✅ 計算技術指標
def calculate_indicators(df, symbol=None):
    if df is None or len(df) < 60:
        print("[⚠️ 警告] 技術指標計算時資料不足（小於 60 筆），跳過")
        return None

    required_columns = ['close', 'volume', 'open', 'high', 'low']
    for col in required_columns:
        if col not in df.columns:
            print(f"⚠️ [警告] 缺少必要欄位：{col}，跳過")
            return None
        if df[col].isnull().all():
            print(f"⚠️ [警告] 欄位 {col} 全為空 ➜ 跳過")
            return None

    try:
        close = df['close']
        volume = df['volume']

        rsi = RSIIndicator(close=close, window=15).rsi()
        if symbol:
            print(f"[DEBUG] {symbol} ➜ RSI 最後 10 根：\n{rsi.tail(10)}")
        roc = ROCIndicator(close=close, window=10).roc()
        obv = OnBalanceVolumeIndicator(close=close, volume=volume).on_balance_volume()

        zscore = (close - close.rolling(21).mean()) / close.rolling(21).std()

        bb = BollingerBands(close=close, window=20, window_dev=2)
        lower_band = bb.bollinger_lband()
        upper_band = bb.bollinger_hband()
        mid_band = bb.bollinger_mavg()

        df['cum_vol'] = volume.cumsum()
        df['cum_vwap'] = (close * volume).cumsum()
        vwap = df['cum_vwap'] / df['cum_vol']

        ema_5 = EMAIndicator(close=close, window=5).ema_indicator()
        ema_20 = EMAIndicator(close=close, window=20).ema_indicator()

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

        curr_volume = volume.iloc[-1]
        avg_volume = volume.rolling(20).mean().iloc[-1]
        volume_ratio = curr_volume / avg_volume if avg_volume > 0 else 1.0
        ema_status = (ema_5 > ema_20).replace({True: "上穿", False: "下彎"})

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

        # 防呆檢查
        key_checks = {
            "RSI": rsi,
            "Z-score": zscore,
            "EMA5": ema_5,
            "EMA20": ema_20,
            "BB上軌": upper_band,
            "OBV": obv
        }

        for name, series in key_checks.items():
            if series is None or series.dropna().empty or pd.isna(series.iloc[-1]):
                print(f"[❌ 錯誤] 指標 {name} ➜ 尾端無效值")
                log_invalid_indicator(f"{name} 無效")
                return None

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

    except Exception as e:
        print(f"[❌ 例外] 技術指標計算失敗：{e}")
        log_invalid_indicator(f"Exception: {e}")
        return None

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
                    signal_note="Squeeze OFF + 技術條件命中",
                    close_price=squeeze_result["close"]
                )
                if shares:
                    print(f"✅ 擠壓策略建倉成功：{shares} 股，用資金 ${capital_used:.2f}")

            # 技術策略
            signal_type, strategy_name, signal_note, direction = detect_trading_signal(symbol, df, indicators, latest_price)
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
                direction=direction,
                score=score,
                rrov_score=rrov_score,
                trend_text=direction,
                trend_emoji="📈" if direction == "做多" else "📉",
                up_count=result[2] if len(result) > 2 else 0,
                down_count=result[3] if len(result) > 3 else 0,
                ema_trend="多頭" if indicators['ema_5'].iloc[-1] > indicators['ema_20'].iloc[-1] else "空頭",
                signal_note=signal_note,
                strategy_name=strategy_name,
                shares=shares,
                capital_used=int(capital_used),
                capital_left=int(capital_left)
            )
            send_discord_message(WEBHOOK_URL, message)

        except Exception as e:
            print(f"[錯誤] {symbol} 掃描錯誤：{e}")
            traceback.print_exc()
