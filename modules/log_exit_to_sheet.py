def log_exit_to_sheet(symbol, latest_price, return_pct, profit_dollar, reason, strategy_name, direction, qty):
    try:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Google Sheets 連線
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GCP_JSON_PATH, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SPREADSHEET_URL).worksheet(SHEET_NAME_EXIT)  # 例如 "出場紀錄"

        sheet.append_row([
            time_str,           # 時間
            symbol,             # 股票代碼
            direction,          # 多 / 空
            latest_price,       # 出場價格
            qty,                # 出場數量
            return_pct,         # 報酬率
            profit_dollar,      # 損益金額
            reason,             # 出場原因
            strategy_name       # 策略名稱
        ])

        print(f"[✅ 已寫入出場紀錄] {symbol}｜{strategy_name}｜{reason}")
    except Exception as e:
        print(f"[❌ 出場寫入錯誤] {symbol} ➜ {type(e).__name__}：{e}")