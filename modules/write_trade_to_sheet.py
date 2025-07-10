from datetime import datetime

def write_trade_to_sheet(strategy_type, symbol, direction, entry_price, shares,
                         invested_capital, rsi, zscore, roc, obv, vwap,
                         confidence_score, signal_note, sheet_webhook_url,
                         return_rate=None, holding_minutes=None, pnl=None):

    from datetime import datetime
    import requests

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_today = datetime.now().strftime("%Y-%m-%d")

    payload = {
        "action": "append",
        "strategy": strategy_type,
        "symbol": symbol,
        "direction": direction,
        "price": entry_price,
        "shares": shares,
        "capital": invested_capital,
        "rsi": round(rsi, 2),
        "zscore": round(zscore, 2),
        "roc": round(roc, 2),
        "obv": int(obv),
        "vwap": round(vwap, 2),
        "confidence_score": round(confidence_score, 2),
        "signal_note": signal_note,
        "datetime": now,
        "date": date_today
    }

    if return_rate is not None:
        payload["return_rate"] = round(return_rate, 2)
        payload["holding_minutes"] = holding_minutes
        payload["pnl"] = round(pnl, 2)

    try:
        response = requests.post(sheet_webhook_url, json=payload)
        if response.ok:
            print(f"[✅ 寫入成功] {symbol} ➜ {strategy_type}")
        else:
            print(f"[⚠️ 寫入失敗] {symbol} ➜ 狀態碼：{response.status_code} ➜ {response.text}")
    except Exception as e:
        print(f"[❌ 錯誤] 無法寫入 Google Sheets ➜ {symbol} ➜ {e}")
