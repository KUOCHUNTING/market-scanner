def schedule_exit_check():
    if not positions:
        print("[排程] 無持倉，跳過出場檢查")
        threading.Timer(10, schedule_exit_check).start()
        return

    print(f"[排程] 執行出場掃描...")

    for symbol, pos in positions.items():
        quantity = pos.get("quantity", 0)

        if quantity <= 0:
            print(f"[略過出場] {symbol} ➜ 無持倉")
            continue

        # ✅ 冷卻期判斷
        entry_time = pos.get("entry_time")
        if entry_time:
            elapsed_seconds = (datetime.now() - entry_time).total_seconds()
            if elapsed_seconds < 30:
                print(f"[⏳ 冷卻中] {symbol} ➜ 建倉未滿 30 秒（{elapsed_seconds:.1f}s），略過出場判斷")
                continue

        # ✅ 出場條件判斷
        if should_exit(symbol):  # 請確保你有定義這個函數
            execute_exit(symbol)  # 請確保你有定義這個函數
        else:
            latest_price = get_latest_price(symbol)
            entry_price = pos.get("entry_price")

            # 預設文字
            pnl_text = "（報酬率無法計算）"

            # 計算報酬率（含 emoji）
            if latest_price and entry_price and entry_price > 0:
                pnl_pct = ((latest_price - entry_price) / entry_price) * 100

                if pnl_pct > 10:
                    emoji = "🟢"
                elif pnl_pct < -5:
                    emoji = "🔴"
                else:
                    emoji = "⚪"
                pnl_text = f"（{emoji} {pnl_pct:+.2f}%）"

            # 取得策略名稱
            strategy = pos.get("strategy", "未知策略")

            # 持倉時間（分鐘）
            holding_minutes = 0
            if entry_time:
                holding_minutes = int((datetime.now() - entry_time).total_seconds() / 60)

            # 顯示完整訊息
            if return_rate is None:
                pnl_text = "❓ 無法計算報酬率"
            else:
                pnl_text = f"{emoji} 目前價：{latest_price:.2f}｜報酬率：{return_rate:+.2f}%"
            print(f"✅【持續持有】{symbol} 尚未觸發出場條件 {pnl_text}｜策略={strategy}｜已持有 {holding_minutes} 分鐘")

    threading.Timer(10, schedule_exit_check).start()

# ✅ 主程式區（掃描建倉 + 出場排程）
if __name__ == "__main__":
    # ✅ 啟動定時出場檢查排程
    schedule_exit_check()

    # ✅ 持續執行市場掃描（每 3 分鐘隨機掃一次）
    while True:
        symbol_list = load_stock_list()
        random.shuffle(symbol_list)
        print(f"[掃描啟動] 共 {len(symbol_list)} 檔")
        
        scan_market(symbol_list)  # ⬅️ 執行建倉邏輯

        time.sleep(180)  # ✅ 每 180 秒（3 分鐘）掃一次