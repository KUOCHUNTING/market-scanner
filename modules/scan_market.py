def scan_market(symbol_list):
    from modules.fetch_stock_data import fetch_stock_data
    from modules.get_fundamentals import get_fundamentals
    from modules.filter_fundamentals import filter_fundamentals
    from modules.calculate_indicators import calculate_indicators
    from modules.strategy.analyze_strategy_scores import analyze_strategy_scores
    from modules.logic.evaluate_signal_and_score import evaluate_signal_and_score
    from modules.logic.execute_entry import execute_entry
    from modules.compute_confidence_score import get_strategy_match_score
    from modules.notify.print_debug_summary import print_debug_summary
    from modules.notify.build_discord_message import build_entry_message
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
            # ✅ 加入 EMA 欄位（放這裡！）
            df["ema_5"] = indicators["ema_5"]
            df["ema_20"] = indicators["ema_20"]

            # ✅ 計算 EMA 趨勢次數
            ema_up = (df["ema_5"].diff() > 0).sum()
            ema_down = (df["ema_5"].diff() < 0).sum()
            ema_trend = "多" if ema_up > ema_down else "空" if ema_down > ema_up else "盤整"
            
            latest_price = df['close'].iloc[-1]
            if pd.isna(latest_price) or latest_price <= 0:
                print(f"[跳過] {symbol} ➜ latest_price 無效 ➜ {latest_price}")
                continue

            # ✅ 三策略命中率
            scores = analyze_strategy_scores(indicators, latest_price)

            # ✅ 訊號偵測與技術分數
            signal_type, strategy_name, signal_note, direction, score, \
                rrov_score, trend_score, mean_score = evaluate_signal_and_score(symbol, df, indicators, latest_price)

            # ✅ 命中率補充
            trend_long, trend_short = get_strategy_match_score(symbol, df, indicators, "順勢")
            rrov_long, rrov_short   = get_strategy_match_score(symbol, df, indicators, "RROV")
            mean_long, mean_short   = get_strategy_match_score(symbol, df, indicators, "均值")

            # ✅ 顯示技術摘要
            print_debug_summary(
                symbol, indicators, latest_price, score,
                rrov_score, trend_score,
                strategy_name, direction, rrov_score,
                trend_long, trend_short, rrov_long, rrov_short, mean_long, mean_short
            )

            if signal_type is None:
                print(f"[略過] {symbol} ➜ 無明確訊號")
                continue

            # ✅ 嘗試建倉
            shares, capital_used, ema_trend = execute_entry(
                symbol, latest_price, direction, score, strategy_name, indicators, capital_left
            )
            if shares is None:
                print(f"[略過] {symbol} ➜ 建倉失敗")
                continue

            print(f"[✅ 建倉成功] {symbol} ➜ 股數：{shares}｜花費資金：${capital_used:.2f}｜剩餘資金：${capital_left:.2f}")

            # ✅ 組裝並推播進場訊息
            message = build_entry_message(
                symbol=symbol,
                strategy_type="📌 技術選股",
                signal_type=signal_type,
                direction=direction,
                score=score,
                win_rate=rrov_score,
                trend_text=direction,
                trend_emoji="📈" if direction == "多" else "📉",
                up_count=0,
                down_count=0,
                ema_trend=ema_trend,
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
