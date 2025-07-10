def get_credentials_from_base64(env_var_key):
    base64_key = os.getenv(env_var_key)
    if not base64_key:
        raise ValueError("Google Sheets 金鑰尚未設定")
    json_data = base64.b64decode(base64_key).decode('utf-8')
    return ServiceAccountCredentials.from_json_keyfile_dict(json.loads(json_data), [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ])

est = pytz.timezone("US/Eastern")
now_est = datetime.now(est)

# ✅ 補上開盤與收盤時間的定義
market_open = est.localize(datetime.combine(now_est.date(), time(9, 30)))
market_close = est.localize(datetime.combine(now_est.date(), time(16, 0)))
# 只在開盤期間運行
if now_est < market_open or now_est > market_close:
    print("[INFO] 非美股盤中時間，跳過掃描")
    exit()