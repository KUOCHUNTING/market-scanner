from modules.utils.format import safe_float

def build_mean_reversion_message(symbol, price, rsi, zscore, ema5, ema20,
                                  bb_upper, bb_lower, obv, score, confidence_score,
                                  direction, shares, capital_used, capital_left, signal_note):
    return f"""【均值回歸策略觸發】{symbol}

收盤價：${price:.2f}｜Z-score：{safe_float(zscore)}
EMA5：{safe_float(ema5)}｜EMA20：{safe_float(ema20)}
布林通道：上={safe_float(bb_upper)}｜下={safe_float(bb_lower)}
OBV：{safe_float(obv)}

策略摘要：{signal_note}
策略信心：{safe_float(score)}｜技術信心：{safe_float(confidence_score)}

方向：{direction}
股數：{shares} 股｜資金：${capital_used:.2f}
剩餘資金：${capital_left:.2f}
"""

def build_rrov_message(symbol, price, ema5, bb_upper, obv, score, confidence_score,
                       direction, shares, capital_used, capital_left, signal_note):
    return f"""【RROV 突破策略觸發】{symbol}

收盤價：${price:.2f}｜EMA5：{safe_float(ema5)}｜布林上軌：{safe_float(bb_upper)}
OBV：{safe_float(obv)}

策略摘要：{signal_note}
策略信心：{safe_float(score)}｜技術信心：{safe_float(confidence_score)}

方向：{direction}
股數：{shares} 股｜資金：${capital_used:.2f}
剩餘資金：${capital_left:.2f}
"""

def build_trend_message(symbol, price, rsi, ema5, ema20, obv, score, confidence_score,
                        direction, shares, capital_used, capital_left, signal_note):
    return f"""【順勢策略觸發】{symbol}

收盤價：${price:.2f}｜RSI：{safe_float(rsi)}｜EMA5：{safe_float(ema5)}｜EMA20：{safe_float(ema20)}
OBV：{safe_float(obv)}

策略摘要：{signal_note}
策略信心：{safe_float(score)}｜技術信心：{safe_float(confidence_score)}

方向：{direction}
股數：{shares} 股｜資金：${capital_used:.2f}
剩餘資金：${capital_left:.2f}
"""


# ✅ 擠壓策略訊息
def build_breakout_message(symbol, price, direction, strategy_name, score,
                           rsi=None, zscore=None, ema5=None, ema20=None,
                           bb_upper=None, bb_lower=None,
                           signal_note=None, confidence_score=None,
                           shares=None, capital_used=None, capital_left=None):
    message = f"💥【擠壓突破策略觸發】{symbol}\n"
    message += f"📈 收盤價：${safe_float(price)}\n"
    message += f"🔼 EMA5：{safe_float(ema5)}｜EMA20：{safe_float(ema20)}｜RSI：{safe_float(rsi)}｜Z-score：{safe_float(zscore)}\n\n"
    message += f"📝 訊號說明：{signal_note or '無'}\n"
    message += f"📋 策略：{strategy_name}｜方向：{direction}\n"
    message += f"🎯 策略信心分數：{safe_float(score)}\n"
    if shares is not None and capital_used is not None:
        message += f"📌 股數：{shares} 股｜進場資金：${safe_float(capital_used)}\n"
    if capital_left is not None:
        message += f"💰 剩餘資金：${safe_float(capital_left)}"
    return message

def build_entry_message(symbol, price, strategy_type, signal_type, strategy_name,
                        signal_note, direction, score=None, confidence_score=None,
                        rsi=None, zscore=None, ema5=None, ema20=None,
                        bb_upper=None, bb_lower=None, obv=None,
                        trend_score=None, rrov_score=None, mean_score=None,
                        shares=None, capital_used=None, capital_left=None):

    message = f"📌 {direction} 技術策略 ➤ `{symbol}`\n\n"
    message += f"📋 類型：{strategy_type}（方向：{direction}）\n"
    message += f"📈 收盤價：${safe_float(price)}｜RSI：{safe_float(rsi)}｜Z-score：{safe_float(zscore)}\n"
    message += f"📊 EMA5：{safe_float(ema5)}｜EMA20：{safe_float(ema20)}\n"
    message += f"📉 布林通道：上={safe_float(bb_upper)}｜下={safe_float(bb_lower)}\n"
    message += f"📦 OBV：{safe_float(obv)}\n\n"

    message += f"🎯 命中率 ➜ 順勢：{safe_float(trend_score)}｜RROV：{safe_float(rrov_score)}｜均值：{safe_float(mean_score)}\n"
    message += f"🧠 技術信心：{safe_float(confidence_score)}｜策略分數：{safe_float(score)}\n\n"
    message += f"📝 訊號摘要：{signal_note}\n"
    message += f"🔖 策略名稱：{strategy_name}\n\n"
    message += f"📌 股數：{shares} 股｜進場資金：${safe_float(capital_used)}\n"
    message += f"💰 剩餘資金：${safe_float(capital_left)}"

    return message

