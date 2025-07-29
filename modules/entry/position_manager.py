import os
from datetime import datetime
from dotenv import load_dotenv
from modules.notify.discord_push import send_discord_message
from modules.notify.build_discord_message import build_entry_message_from_position
from modules.utils.gsheet_writer import write_entry_to_sheet

# ✅ 載入環境變數
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env")
load_dotenv(dotenv_path)

DEFAULT_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
DEFAULT_CAPITAL = float(os.getenv("CAPITAL_LEFT", "100000"))
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "0.2"))  # ✅ 單筆資金比例上限（預設 20%
MIN_REQUIRED_CAPITAL = 3000  # ✅ 設定最低建倉門檻

class PositionManager:
    def __init__(self, initial_capital=DEFAULT_CAPITAL, max_position_pct=MAX_POSITION_PCT,
                 webhook_url=DEFAULT_WEBHOOK_URL, auto_reset=True):
        self.initial_capital = initial_capital
        self.max_position_pct = max_position_pct
        self.webhook_url = webhook_url
        self.auto_reset = auto_reset

        if auto_reset:
            self.capital_left = initial_capital
            self.positions = {}
        else:
            self.capital_left = self.load_previous_state()

        print(f"✅ PositionManager 初始化 ➜ 資金：${self.capital_left:.2f}")

    def get_capital_left(self):
        # ✅ 若資金不足，自動重置（僅測試階段用）
        if self.capital_left < MIN_REQUIRED_CAPITAL and self.auto_reset:
            print(f"[🔁 自動重置資金] ➜ 原資金 ${self.capital_left:.2f} → ${self.initial_capital:.2f}")
            self.capital_left = self.initial_capital
        return self.capital_left

    def get_positions(self):
        return self.positions

    def reset_capital(self, amount=None):
        self.capital_left = amount if amount else self.initial_capital
        print(f"🔁 手動重置資金 ➜ 資金：${self.capital_left:.2f}")

    def has_position(self, symbol):
        return symbol in self.positions

    def add_position(self,
                     symbol, price, direction, score, confidence_score, strategy_name,
                     rsi=None, zscore=None, roc=None, obv=None,
                     vwap=None, ema5=None, ema20=None,
                     bb_upper=None, bb_lower=None,
                     signal_note=None, trend_score=None,
                     rrov_score=None, mean_score=None,
                     trend_dir=None, rrov_dir=None, mean_dir=None,
                     signal_type=None, strategy_type=None,
                     take_profit_pct=0.08, stop_loss_pct=0.03,
                     sheet=None, sector=None):

        if self.has_position(symbol):
            msg = f"[略過] {symbol} 已持有倉位"
            print(msg)
            return None, msg, self.capital_left

        if self.capital_left < MIN_REQUIRED_CAPITAL:
            msg = f"[略過] 資金不足 ➜ 剩餘 ${self.capital_left:.2f}"
            print(msg)
            return None, msg, self.capital_left

        quantity = int(self.capital_left // price)
        if quantity == 0:
            msg = f"[略過] 單價過高，無法進場 ➜ {symbol} at ${price:.2f}"
            print(msg)
            return None, msg, self.capital_left

        max_allowed_capital = self.initial_capital * self.max_position_pct
        if quantity * price > max_allowed_capital:
           quantity = int(max_allowed_capital // price)
            if quantity == 0:
                msg = f"[略過] 單價過高且超過配置上限 ➜ {symbol} at ${price:.2f}"
                print(msg)
                return None, msg, self.capital_left

        capital_used = quantity * price
        entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        position = {
            "symbol": symbol,
            "entry_time": entry_time,
            "entry_price": price,
            "price": price,
            "direction": direction,
            "shares": quantity,
            "capital_used": capital_used,
            "strategy_name": strategy_name,
            "strategy_type": strategy_type,
            "signal_type": signal_type,
            "score": score,
            "confidence_score": confidence_score,
            "take_profit_pct": take_profit_pct,
            "stop_loss_pct": stop_loss_pct,
            "rsi": rsi,
            "zscore": zscore,
            "roc": roc,
            "obv": obv,
            "vwap": vwap,
            "ema5": ema5,
            "ema20": ema20,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower,
            "trend_score": trend_score,
            "trend_dir": trend_dir,
            "rrov_score": rrov_score,
            "rrov_dir": rrov_dir,
            "mean_score": mean_score,
            "mean_dir": mean_dir,
            "signal_note": signal_note,
            "sector": sector
        }

        # ✅ 正確位置：計算完 capital_used 後再扣資金
        self.capital_left -= capital_used
        if self.capital_left < 0:
            self.capital_left = 0

        self.positions[symbol] = position

        # ✅ 推播訊息
        message = build_entry_message_from_position(position)
        if self.webhook_url and "discord.com" in self.webhook_url:
            send_discord_message(message, webhook_url=self.webhook_url)
        else:
            print("[⚠️ 略過推播] Webhook URL 無效或未設定")

        # ✅ 寫入 Google Sheets
        if sheet:
            write_entry_to_sheet(entry=position, sheet=sheet, shares=quantity)

        print(f"✅ 建倉成功：{symbol}｜方向：{direction}｜股數：{quantity}｜價格：${price:.2f}｜策略：{strategy_name}")
        return position, message, self.capital_left
