import os
import pandas as pd
import traceback
import random
from dotenv import load_dotenv
from modules.utils.connect_to_gsheet import connect_with_base64_key
# ✅ 載入環境變數
load_dotenv()
sheet_url = os.getenv("GSHEET_URL")
key_base64 = os.getenv("GCP_KEY_BASE64")

# ✅ 模組匯入
from modules.utils.file_loader import load_stock_list
from modules.fetch_stock_data import fetch_stock_data
from modules.get_fundamentals import get_fundamentals
from modules.filter_fundamentals import filter_fundamentals
from modules.indicators.calculate_indicators import calculate_indicators
from modules.utils.validate_indicators import is_invalid
from modules.config.config import POLYGON_API_KEY, capital_left
from modules.utils.connect_to_gsheet import connect_to_gsheet
from modules.utils.gsheet_writer import write_entry_to_sheet
from modules.strategy import (
    detect_trading_signal,
    get_rrov_score,
    get_trend_score,
    get_mean_score,
    compute_confidence_score,
    detect_squeeze_breakout
)
from modules.entry.handle_squeeze_entry import handle_squeeze_entry
from modules.entry.handle_signal_entry import handle_signal_entry
from modules.data.filters import filter_liquidity
from modules.data.loaders import load_stock_sector_csv

df_sector = load_stock_sector_csv()
# ✅ 初始化共用 Google Sheet 分頁
sheet_entry = connect_to_gsheet(sheet_url, "建倉記錄", key_base64)

print(f"[DEBUG] ✅ 已建立 sheet_entry: {sheet_entry}")
# ✅ 股票清單
stock_list = load_stock_list()

# ✅ 主掃描函數
def scan_market(stock_list, sheet_entry, position_manager=None):
    print(f"🧪 DEBUG：scan_market 收到的 webhook = {position_manager.webhook_url}")
    MIN_REQUIRED_CAPITAL = 3000
    if position_manager and position_manager.capital_left < MIN_REQUIRED_CAPITAL:
        print(f"[資金耗盡] 剩餘資金 ${position_manager.capital_left:.2f}，暫停掃描")
        return

    if isinstance(stock_list, pd.DataFrame):
        symbols = stock_list["symbol"].dropna().tolist()
    elif isinstance(stock_list, list):
        symbols = stock_list  # ✅ 補上這行
    else:
        raise TypeError("❌ 傳入的 stock_list 必須是 list 或包含 'symbol' 欄的 DataFrame")

    random.shuffle(symbols)  # ✅ 此時 symbols 一定已定義

    if position_manager and position_manager.capital_left < MIN_REQUIRED_CAPITAL:
        print(f"[資金耗盡] 剩餘資金 ${capital_left:.2f}，暫停掃描")
        return

    for symbol in symbols:
        try:
            print(f"\n📡 掃描中：{symbol}")
            df = fetch_stock_data(symbol, POLYGON_API_KEY)
            if df is None or df.empty:
                print(f"[跳過] {symbol} ➜ 無資料")
                continue

            # ✅ 流動性過濾（5日平均成交額）
            try:
                avg_volume = df["volume"].rolling(5).mean().iloc[-1]
                price = df["close"].iloc[-1]
                if not filter_liquidity(avg_volume, price):
                    print(f"[跳過] {symbol} ➜ 流動性不足（5日均成交額 ${avg_volume * price:,.0f}）")
                    continue
            except Exception as e:
                print(f"[跳過] {symbol} ➜ 流動性檢查失敗：{e}")
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

            # ✅ 技術分數與策略得分
            trend_score, trend_dir = get_trend_score(indicators, latest_price)
            rrov_score = get_rrov_score(indicators, latest_price)
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

            # ✅ 擠壓策略
            squeeze_result = detect_squeeze_breakout(symbol, indicators)
            if squeeze_result:
                result = handle_squeeze_entry(symbol, squeeze_result, sheet_entry)
                if result:
                    position, message, capital_left = result

            # ✅ 技術策略判斷與建倉
            signal_type, strategy_name, signal_note, direction, extra = detect_trading_signal(
                symbol, df, indicators, latest_price
            )
            if signal_type is None:
                print(f"[略過] {symbol} ➜ 無明確訊號")
                continue

            result = handle_signal_entry(
                symbol=symbol,
                direction=direction,
                score=score,
                strategy_name=strategy_name,
                signal_type=signal_type,
                signal_note=signal_note,
                indicators=indicators,
                trend_score=trend_score,
                rrov_score=rrov_score,
                mean_score=mean_score,
                capital_left=position_manager.capital_left,
                sheet=sheet_entry,
                position_manager=position_manager
            )

            if result is None:
                continue  # ✅ 若建倉失敗則跳過

            shares, capital_used = result
            print(f"✅ 建倉完成 ➜ {symbol}｜{shares} 股｜資金 ${capital_used:,.2f}")

        except Exception as e:
            print(f"[錯誤] {symbol} 掃描錯誤：{e}")
            traceback.print_exc()
