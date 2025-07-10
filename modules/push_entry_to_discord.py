from datetime import datetime
import requests
from .config import TOTAL_CAPITAL, POSITION_RATIO, WEBHOOK_URL
from .analyze_ema_trend import analyze_ema_trend  # ← 若用到，請確保這個檔案存在

def push_entry_to_discord(symbol, direction, price, signal_note, zscore=None, rsi=None, roc=None,
                          obv=None, obv_change=None, ema5=None, ema20=None,
                          vwap=None, strategy=None, confidence_score=None,
                          capital_left=None, df=None):
    """
    發送建倉通知到 Discord（含策略、價格、信心分數、指標資訊）

    Parameters:
        symbol (str): 股票代號
        direction (str): 多 or 空
        price (float): 進場價
        signal_note (str): 條件說明文字
        zscore, rsi, roc, obv, ema5, ema20, vwap: 技術指標
        confidence_score (float): 信心評分
        capital_left (float): 剩餘資金
        df (DataFrame): 用於計算 EMA 趨勢（均值策略時）
    """
    emoji = "🐸" if direction == "多" else "🐶"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    capital_used = TOTAL_CAPITAL * POSITION_RATIO
    quantity = int(capital_used // price)

    # === EMA 趨勢統計（僅均值策略需要）
    ema_trend_text = "N/A"
    if strategy == "均值回歸策略" and df is not None:
        try:
            ema_trend_text = analyze_ema_trend(df)
        except Exception as e:
            ema_trend_text = "統計失敗"
            print(f"[⚠️ EMA 趨勢統計失敗] {symbol}：{e}")

    # === 基礎資訊區 ===
    content = f"{emoji} **[建倉訊號 - {direction}單]** {symbol}\n"
    content += f"💵 價格：${price:.2f}｜方向：{direction}\n"
    content += f"📈 資金投入：${capital_used:,.0f}｜股數：約 {quantity} 股\n"
    if capital_left is not None:
        content += f"💼 剩餘資金：${capital_left:,.0f}\n"

    # === 策略標籤 ===
    strategy_label = {
        "均值回歸策略": "🎯 均值回歸策略",
        "RROV 策略": "📊 RROV 策略",
        "順勢策略": "📈 順勢交易策略"
    }.get(strategy, "📌 未知策略")

    # === 策略細節區 ===
    if strategy == "均值回歸策略":
        if zscore is not None:
            label = "超跌" if zscore < -2 else "超漲" if zscore > 2 else "偏離中"
            content += f"📊 Z-score：{zscore:.2f}（{label}）\n"
        if ema5 is not None and ema20 is not None:
            diff = ema5 - ema20
            content += f"📈 EMA 差值：{diff:.2f}（5日 - 20日）\n"
        if rsi is not None:
            content += f"📉 RSI：{rsi:.1f}\n"

    elif strategy == "RROV 策略":
        rsi_text = f"📉 RSI：{rsi:.1f}" if rsi is not None else ""
        roc_text = f"ROC：{roc:.2f}" if roc is not None else ""
        line = "｜".join([x for x in [rsi_text, roc_text] if x])
        if line:
            content += f"{line}\n"
        if vwap is not None and vwap > 0:
            vwap_deviation = abs(price - vwap) / vwap * 100
            content += f"📊 VWAP 乖離：{vwap_deviation:.2f}%\n"
        if obv_change is not None:
            content += f"📈 OBV 變化：{obv_change:.2f}\n"

    elif strategy == "順勢策略":
        if ema5 is not None and ema20 is not None:
            trend_diff = ema5 - ema20
            content += f"📈 EMA 順勢：{trend_diff:.2f}（5日 - 20日）\n"
        if rsi is not None:
            content += f"📉 RSI：{rsi:.1f}\n"
        if obv_change is not None:
            content += f"📈 OBV 趨勢變化：{obv_change:.2f}\n"
        if vwap is not None:
            position = "高於" if price > vwap else "低於"
            content += f"📊 價格{position} VWAP：{price:.2f} vs {vwap:.2f}\n"

    # === 通用附加項目 ===
    if confidence_score is not None:
        content += f"🔍 信心分數：{confidence_score:.2f}\n"

    content += f"📌 策略：{strategy_label}\n"
    content += f"📝 條件說明：{signal_note}\n"
    content += f"🕒 時間：{time_str}"

    # === 發送 Discord ===
    try:
        requests.post(WEBHOOK_URL, json={"content": content})
        print(f"[✅推播成功] {symbol} 建倉通知已送出")
    except Exception as e:
        print(f"[❌推播失敗] {symbol}：{e}")
