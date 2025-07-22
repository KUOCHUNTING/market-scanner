from datetime import datetime
from modules.utils.format import safe_float

# === 安全處理字串 ===

def safe_symbol(symbol):
    """
    安全格式化股票代號，移除不可列印字元
    """
    try:
        return ''.join(c for c in str(symbol) if c.isprintable())
    except Exception:
        return "[無效代碼]"

def clean_string(s: str) -> str:
    """
    最終推播字串清洗，移除非法控制符與 emoji 崩潰字元
    """
    return ''.join(c for c in s if c.isprintable()).strip()

# === 均值回歸訊息 ===

def build_mean_reversion_message(symbol, price, rsi, zscore, ema5, ema20,
                                  bb_upper, bb_lower, obv, score, confidence_score,
                                  direction, shares, capital_used, capital_left, signal_note):
    message = f"""【均值回歸策略觸發】{safe_symbol(symbol)}

收盤價：${safe_float(price)}｜Z-score：{safe_float(zscore)}
EMA5：{safe_float(ema5)}｜EMA20：{safe_float(ema20)}
布林通道：上={safe_float(bb_upper)}｜下={safe_float(bb_lower)}
OBV：{safe_float(obv)}

策略摘要：{signal_note}
策略信心：{safe_float(score)}｜技術信心：{safe_float(confidence_score)}

方向：{direction}
股數：{shares} 股｜資金：${safe_float(capital_used)}
剩餘資金：${safe_float(capital_left)}
"""
    return clean_string(message)

# === RROV 突破訊息 ===

def build_rrov_message(symbol, price, ema5, bb_upper, obv, score, confidence_score,
                       direction, shares, capital_used, capital_left, signal_note):
    message = f"""【RROV 突破策略觸發】{safe_symbol(symbol)}

收盤價：${safe_float(price)}｜EMA5：{safe_float(ema5)}｜布林上軌：{safe_float(bb_upper)}
OBV：{safe_float(obv)}

策略摘要：{signal_note}
策略信心：{safe_float(score)}｜技術信心：{safe_float(confidence_score)}

方向：{direction}
股數：{shares} 股｜資金：${safe_float(capital_used)}
剩餘資金：${safe_float(capital_left)}
"""
    return clean_string(message)

# === 順勢策略訊息 ===

def build_trend_message(symbol, price, rsi, ema5, ema20, obv, score, confidence_score,
                        direction, shares, capital_used, capital_left, signal_note):
    message = f"""【順勢策略觸發】{safe_symbol(symbol)}

收盤價：${safe_float(price)}｜RSI：{safe_float(rsi)}｜EMA5：{safe_float(ema5)}｜EMA20：{safe_float(ema20)}
OBV：{safe_float(obv)}

策略摘要：{signal_note}
策略信心：{safe_float(score)}｜技術信心：{safe_float(confidence_score)}

方向：{direction}
股數：{shares} 股｜資金：${safe_float(capital_used)}
剩餘資金：${safe_float(capital_left)}
"""
    return clean_string(message)

# === 擠壓突破訊息 ===

def build_breakout_message(symbol, price, direction, strategy_name, score,
                           rsi=None, zscore=None,
                           ema5=None, ema20=None,
                           bb_upper=None, bb_lower=None,
                           obv=None, vwap=None, roc=None,
                           signal_note=None, confidence_score=None,
                           shares=None, capital_used=None, capital_left=None):
    message = f"💥【擠壓突破策略觸發】{safe_symbol(symbol)}\n"
    message += f"📈 收盤價：${safe_float(price)}\n"
    message += f"📊 EMA5：{safe_float(ema5)}｜EMA20：{safe_float(ema20)}｜RSI：{safe_float(rsi)}｜Z-score：{safe_float(zscore)}\n"
    message += f"📉 布林通道：上={safe_float(bb_upper)}｜下={safe_float(bb_lower)}｜OBV：{safe_float(obv)}\n"
    message += f"🧮 VWAP：{safe_float(vwap)}｜ROC：{safe_float(roc)}\n\n"
    message += f"📝 訊號說明：{signal_note or '無'}\n"
    message += f"📋 策略：{strategy_name}｜方向：{direction}\n"
    message += f"🎯 策略信心分數：{safe_float(score)}"
    if confidence_score is not None:
        message += f"｜技術信心：{safe_float(confidence_score)}"
    if shares is not None and capital_used is not None:
        message += f"\n📌 股數：{shares} 股｜進場資金：${safe_float(capital_used)}"
    if capital_left is not None:
        message += f"\n💰 剩餘資金：${safe_float(capital_left)}"

    return clean_string(message)



# === 統一技術策略推播格式（整合雷達分數） ===

from modules.utils.format import safe_float

def build_entry_message(symbol, price, strategy_type, signal_type, strategy_name,
                        score, signal_note, direction, confidence_score,
                        rsi=None, zscore=None, ema5=None, ema20=None,
                        bb_upper=None, bb_lower=None, obv=None,
                        trend_score=None, rrov_score=None, mean_score=None,
                        shares=None, capital_used=None, capital_left=None,
                        sector=None):  # ✅ 加入 sector

    emoji = "🟢" if direction == "做多" else "🔴"
    confidence_emoji = "🔥 高信心" if confidence_score >= 6 else "🔶 中信心" if confidence_score >= 4 else "⚠️ 低信心"

    message = f"""📌 {emoji}【{direction} 技術策略】➤ {symbol}
📋 類型：{strategy_type}｜策略：{strategy_name}
🧠 信心：{safe_float(confidence_score, 2)}/7（{confidence_emoji}）｜總分：{safe_float(score)}
🎯 策略命中：順勢：✅ {safe_float(trend_score)}/5｜RROV：✅ {safe_float(rrov_score)}/5｜均值：✅ {safe_float(mean_score)}/5
━━━━━━━━━━━━━━━━━━━━━
📈 價格：${safe_float(price)}｜RSI：{safe_float(rsi)}｜Z-score：{safe_float(zscore)}
📊 EMA5：{safe_float(ema5)}｜EMA20：{safe_float(ema20)}｜OBV：{safe_float(obv)}
📉 BB通道：上={safe_float(bb_upper)}｜下={safe_float(bb_lower)}
━━━━━━━━━━━━━━━━━━━━━
📂 產業分類：{sector or '未分類'}
📝 摘要：{signal_note}
📌 股數：{shares or '--'}｜資金：${safe_float(capital_used) or '--'}
💰 剩餘資金：${safe_float(capital_left)}
"""
    return message
# === Position dict 自動轉訊息 ===

def build_entry_message_from_position(position: dict):
    return build_entry_message(
        symbol=position["symbol"],
        price=position["entry_price"],
        strategy_type=position.get("strategy_type", "技術策略"),
        signal_type=position.get("signal_type", "技術信號"),
        strategy_name=position["strategy_name"],
        signal_note=position["signal_note"],
        direction=position["direction"],
        score=position.get("score"),
        confidence_score=position.get("confidence_score"),
        rsi=position.get("rsi"),
        zscore=position.get("zscore"),
        ema5=position.get("ema5"),
        ema20=position.get("ema20"),
        bb_upper=position.get("bb_upper"),
        bb_lower=position.get("bb_lower"),
        obv=position.get("obv"),
        trend_score=position.get("trend_score"),
        rrov_score=position.get("rrov_score"),
        mean_score=position.get("mean_score"),
        shares=position.get("shares"),
        capital_used=position.get("capital_used"),
        capital_left=position.get("capital_left"),
    )

# === 出場推播訊息 ===

def build_exit_message(symbol, direction, entry_price, exit_price, return_rate, shares, reason, strategy_name):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    strategy_map = {
        '均值回歸': "🎯 均值回歸策略",
        '順勢策略': "🔥 順勢策略",
        '擠壓突破': "💥 擠壓突破策略"
    }
    strategy_label = strategy_map.get(strategy_name, "📊 RROV 策略")

    emoji = "🐸" if direction == "多" else "🐶"

    msg = f"""{emoji} **[出場 - {direction}單]** {safe_symbol(symbol)}
📌 策略：{strategy_label}
💵 出場價格：${safe_float(exit_price)}｜進場價格：${safe_float(entry_price)}
📊 報酬率：{safe_float((return_rate or 0) * 100)}%｜股數：{shares}
🔄 出場原因：{reason}
🕒 時間：{now}"""

    return clean_string(msg)

# === 簡化推播格式（精簡版） ===

def build_entry_message(
    symbol, price, direction, strategy_name,
    score=None, confidence_score=None, signal_note=None,
    shares=None, capital_used=None, capital_left=None,
    rsi=None, zscore=None, ema5=None, ema20=None,
    bb_upper=None, bb_lower=None, obv=None,
    trend_score=None, rrov_score=None, mean_score=None,
    signal_type=None,
    strategy_type=None
):
    """
    精簡推播格式：顯示方向、策略、信心、摘要、收盤價、股數、資金等資訊
    """
    try:
        lines = []
        lines.append("```")  # ✅ Discord code block 開始
        lines.append(f"📌 🟢 **{direction} 技術策略** ➤ **{symbol}**")

        if strategy_type or signal_type:
            lines.append(f"📋 類型：{strategy_type or '技術策略'}｜訊號：{signal_type or '技術'}")

        lines.append(f"🔖 策略名稱：{strategy_name}")
        lines.append(f"🧠 信心分數：{confidence_score or 'N/A'} / 7")
        if signal_note:
            lines.append(f"📝 訊號摘要：{signal_note}")

        lines.append(f"📈 收盤價：${price:,.2f}")
        lines.append(f"📌 股數：{shares or 'N/A'}｜進場資金：${capital_used or 0:,.2f}｜剩餘資金：${capital_left or 0:,.2f}")
        lines.append("```")  # ✅ Discord code block 結尾
        return "\n".join(lines)

    except Exception as e:
        return f"[❌ 建立訊息失敗] {e}"
