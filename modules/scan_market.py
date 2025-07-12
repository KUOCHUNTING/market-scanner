def scan_market(symbol_list):
    from modules.fetch_stock_data import fetch_stock_data
    from modules.get_fundamentals import get_fundamentals
    from modules.filter_fundamentals import filter_fundamentals
    from modules.calculate_indicators import calculate_indicators
    from modules.logic.execute_entry import execute_entry
    from modules.logic.strategy_score import select_best_strategy, get_strategy_match_score
    from modules.notify.print_debug_summary import print_debug_summary
    from modules.build_discord_message import build_entry_message
    from modules.notify.discord_push import send_discord_message
    from modules.config import POLYGON_API_KEY, capital_left, WEBHOOK_URL
    import traceback
    import pandas as pd
    import random

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
            if indicators is None or 'close' not in df.columns:
                print(f"[跳過] {symbol} ➜ 指標產生失敗或無 close 欄位")
                continue

            df["ema_5"] = indicators["ema_5"]
            df["ema_20"] = indicators["ema_20"]

            # ✅ EMA 趨勢計算
            ema_up = (df["ema_5"].diff() > 0).sum()
            ema_down = (df["ema_5"].diff() < 0).sum()
            ema_trend = "多" if ema_up > ema_down else "空" if ema_down > ema_up else "盤整"

            latest_price = df['close'].iloc[-1]
            if pd.isna(latest_price) or latest_price <= 0:
                print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
                continue

            # ✅ 選擇最佳策略
            strategy_name, direction, strategy_score = select_best_strategy(df, indicators)
            if strategy_name is None:
                print(f"[略過] {symbol} ➜ 無策略達滿分")
                continue

            # ✅ 三策略命中率統計
            trend_long, trend_short = get_strategy_match_score(df, indicators, "順勢")
            rrov_long, rrov_short   = get_strategy_match_score(df, indicators, "RROV")
            mean_long, mean_short   = get_strategy_match_score(df, indicators, "均值")

            rrov_score  = rrov_long if direction == "多" else rrov_short
            trend_score = trend_long if direction == "多" else trend_short
            mean_score  = mean_long if direction == "多" else mean_short

            # ✅ 組裝技術摘要
            signal_note = (
                f"🎯 命中率 ➜ 順勢：{trend_long:.2f}/{trend_short:.2f}｜"
                f"RROV：{rrov_long:.2f}/{rrov_short:.2f}｜"
                f"均值：{mean_long:.2f}/{mean_short:.2f}\n"
                f"📌 採用策略：{strategy_name}（方向：{direction}）"
            )

            # ✅ 顯示技術摘要
            print_debug_summary(
                symbol, indicators, latest_price, strategy_score,
                rrov_score, trend_score,
                strategy_name, direction, rrov_score,
                trend_long, trend_short, rrov_long, rrov_short, mean_long, mean_short
            )

            # ✅ 嘗試建倉
            shares, capital_used, capital_left = execute_entry(
                symbol, latest_price, direction, strategy_score, strategy_name, indicators, capital_left
            )
            if shares is None:
                print(f"[略過] {symbol} ➜ 建倉失敗")
                continue

            print(f"[✅ 建倉成功] {symbol} ➜ 股數：{shares}｜花費資金：${capital_used:.2f}｜剩餘資金：${capital_left:.2f}")

            # ✅ 推播
            message = build_entry_message(
                symbol=symbol,
                direction=direction,
                strategy_name=strategy_name,
                score=strategy_score,
                rrov_score=rrov_score,
                trend_score=trend_score,
                mean_score=mean_score,
                latest_price=latest_price,
                rsi=indicators["rsi"].iloc[-1],
                zscore=indicators["zscore"].iloc[-1],
                signal_note=signal_note,
                confidence_score=strategy_score,
                shares=shares,
                capital_used=capital_used,
                capital_left=capital_left
            )
            send_discord_message(WEBHOOK_URL, message)

        except Exception as e:
            print(f"[錯誤] {symbol} 掃描錯誤：{e}")
            traceback.print_exc()
