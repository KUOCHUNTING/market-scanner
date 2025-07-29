class PositionManager:
    def __init__(self, initial_capital=DEFAULT_CAPITAL, max_position_pct=MAX_POSITION_PCT,
                 webhook_url=DEFAULT_WEBHOOK_URL, auto_reset=True):
        self.initial_capital = initial_capital
        self.max_position_pct = max_position_pct
        self.webhook_url = webhook_url
        self.auto_reset = auto_reset

        # ✅ 初始化資金
        if auto_reset:
            self.capital_left = initial_capital
        else:
            self.capital_left = self.load_previous_state()

        # ✅ 無論 auto_reset 與否，一律初始化 positions
        self.positions = {}

        print(f"✅ PositionManager 初始化 ➜ 資金：${self.capital_left:.2f}")
