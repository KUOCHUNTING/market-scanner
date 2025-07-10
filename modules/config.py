# === API & 常數設定 ===
POLYGON_API_KEY = "3Oa52hFieaUvTyToZudJanq39Rw9zApi"
STOCK_LIST_CSV = "filtered_us_stocks_common_only.csv"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1389605152838647909/c2S7EkfYiFBUMF4WWNyk3XrgcsmGA1-8mqXZ19a5vXn-Ti0yY366L3h77SF7M47GOzej")
FMP_API_KEY = "RkRQwAwDCPHSTg1QE4MjIwsqWd0iHtd7"

# === 交易設定 ===
TOTAL_CAPITAL = 1_000_000
POSITION_RATIO = 0.05
MAX_CAPITAL_PER_POSITION = 50_000
MAX_SHARES_PER_POSITION = 6000
MAX_ACTIVE_POSITIONS = 10

# === 🛡️ 出場風控參數（含三段鎖利）===
TRAIL_TRIGGER = 0.03            # +3% 啟動移動停利
TRAIL_MARGIN = 0.015            # 回落 1.5% 停利出場
DEFAULT_STOP_LOSS = 0.02        # -2% 強制停損
DEFAULT_TAKE_PROFIT = 0.05      # +5% 預設停利

# 在 config.py 裡
STOCK_LIST_CSV = "filtered_us_stocks_common_only.csv"

# 建立美東時間
eastern = pytz.timezone("US/Eastern")
now_est = datetime.now(eastern)
print("建倉時間（美東）:", now_est.strftime("%Y-%m-%d %H:%M:%S"))
