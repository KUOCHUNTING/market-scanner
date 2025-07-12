def push_to_discord(
    symbol=None, price=None, rsi=None, roc=None, vwap=None, volume_ratio=None,
    ema_cross=None, candle_type=None,
    signal_type=None, signal_note=None, confidence_score=None,
    direction=None, strategy_name=None, zscore=None, obv=None,
    obv_change=None, vwap_deviation=None, bb_deviation=None,
    content=None  # ✅ 支援純文字推播
):
    try:
        # ✅ 如果是純文字訊息（如診斷、簡報等）
        if content and str(content).strip() != "":
            response = requests.post(WEBHOOK_URL, json={"content": content})
            
            if response.status_code == 429:
                retry_after = response.json().get("retry_after", 1.5)
                print(f"[限速] 診斷推播限速 ➜ 等待 {retry_after:.2f} 秒後重發")
                time.sleep(retry_after)
                requests.post(WEBHOOK_URL, json={"content": content})
            elif response.status_code != 204:
                print(f"[⚠️診斷推播失敗] ➜ {response.status_code} - {response.text}")
            else:
                print("[✅推播] 純文字訊息已發送")
            return  # ✅ 傳送完就不執行下面格式化訊息

        # ✅ 若非 content 模式，則為格式化訊息推播
        if not signal_note or str(signal_note).strip() == "":
            print("[⚠️] 推播內容為空，略過發送")
            return

        # === 組合格式化內容 ===
        emoji = "🐸" if direction == "多" else "🐶" if direction == "空" else "❔"

        rsi_text = f"{rsi:.1f}" if rsi is not None else "N/A"
        roc_text = f"{roc:.2f}" if roc is not None else "N/A"
        vwap_text = f"{vwap:.2f}" if vwap is not None else "N/A"
        zscore_text = f"{zscore:.2f}" if zscore is not None else "N/A"
        obv_text = f"{int(obv):,}" if obv is not None else "N/A"
        volume_text = f"{volume_ratio:.2f}x" if volume_ratio is not None else "N/A"
        confidence_text = f"{confidence_score:.2f}" if confidence_score is not None else "N/A"

        msg = (
            f"{emoji} **[{strategy_name}]** {symbol}\n"
            f"💵 價格：${price:.2f} | RSI：{rsi_text} | ROC：{roc_text} | Z-score：{zscore_text}\n"
            f"📊 VWAP：{vwap_text} | 成交量：{volume_text} | OBV：{obv_text}\n"
        )

        if vwap_deviation is not None:
            msg += f"📉 VWAP 乖離：{vwap_deviation:+.2f}%\n"
        if bb_deviation is not None:
            msg += f"📈 布林乖離：{bb_deviation:+.2f}%\n"
        if obv_change is not None:
            msg += f"🔄 OBV 變化量：{obv_change:+,.0f}\n"

        msg += (
            f"📈 EMA：{ema_cross}\n"
            f"🧠 信心分數：{confidence_text}\n"
            f"🔔 **訊號類型**：{signal_note}"
        )

        response = requests.post(WEBHOOK_URL, json={"content": msg})

        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 1.5)
            print(f"[限速] 格式化推播限速 ➜ 等待 {retry_after:.2f} 秒後重發")
            time.sleep(retry_after)
            requests.post(WEBHOOK_URL, json={"content": msg})
        elif response.status_code != 204:
            print(f"[⚠️警告] Discord 推播失敗 ➜ {response.status_code} - {response.text}")
        else:
            print("[✅推播] 格式化訊息已發送")

    except Exception as e:
        print(f"[❌錯誤] 推播失敗：{e}")