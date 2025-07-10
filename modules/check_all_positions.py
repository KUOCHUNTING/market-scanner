def check_all_positions():
    if not positions:
        print("[持倉檢查] 目前無持倉，略過出場檢查")
        return

    print(f"[持倉檢查] 共 {len(positions)} 檔持倉 ➜ 開始檢查出場條件")
    for symbol in list(positions.keys()):
        try:
            latest_price = fetch_latest_price(symbol)
            check_exit_and_notify(symbol, latest_price)
        except Exception as e:
            print(f"[錯誤] 檢查 {symbol} 出場條件時出錯：{e}")