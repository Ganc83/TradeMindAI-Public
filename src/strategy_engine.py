from dataclasses import dataclass
from typing import Optional
import time

@dataclass
class Signal:
    side: str              # "BUY" | "SELL" | "HOLD"
    reason: str            # Debug-Text
    price: float
    ts: float

class StrategyEngine:
    def __init__(self):
        # State
        self.in_position = False
        self.entry_price: Optional[float] = None

        # Cooldown / Debounce
        self.last_signal_ts = 0.0
        self.signal_cooldown_sec = 30.0

        # Risk
        self.tp_pct = 0.05
        self.sl_pct = 0.02
        self.trailing_pct = 0.02
        self.trailing_active = True
        self.peak_price: Optional[float] = None

    def can_fire(self, now: float) -> bool:
        return (now - self.last_signal_ts) >= self.signal_cooldown_sec

    def compute_signal(
        self,
        price: float,
        cross_up: bool,
        cross_down: bool,
        rsi: Optional[float],
    ) -> Signal:
        now = time.time()

        # Default
        if not self.can_fire(now):
            return Signal("HOLD", "Cooldown aktiv", price, now)

        # RSI Filter (optional)
        rsi_ok_buy = True
        rsi_ok_sell = True
        if rsi is not None:
            rsi_ok_buy = rsi > 50
            rsi_ok_sell = rsi < 50

        # LONG-only: BUY nur wenn nicht in Position, SELL nur wenn in Position
        if cross_up and (not self.in_position) and rsi_ok_buy:
            return Signal("BUY", f"SMA Cross Up + RSI ok ({rsi})", price, now)

        if cross_down and self.in_position and rsi_ok_sell:
            return Signal("SELL", f"SMA Cross Down + RSI ok ({rsi})", price, now)

        return Signal("HOLD", "Keine Bedingung erfüllt", price, now)

    def execute_signal(self, sig: Signal) -> Optional[str]:
        """
        Führt nur Positionswechsel aus.
        Gibt eine Log-Zeile zurück (oder None).
        """
        if sig.side == "HOLD":
            return None

        self.last_signal_ts = sig.ts

        if sig.side == "BUY":
            self.in_position = True
            self.entry_price = sig.price
            self.peak_price = sig.price
            return f"✅ SIM BUY @ {sig.price:.2f} | {sig.reason}"

        if sig.side == "SELL":
            self.in_position = False
            self.entry_price = None
            self.peak_price = None
            return f"✅ SIM SELL @ {sig.price:.2f} | {sig.reason}"

        return None

    def check_tp_sl_trailing(self, price: float) -> Optional[str]:
        """
        Läuft 1x pro Update – unabhängig davon, ob es ein Signal gab.
        """
        if not self.in_position or self.entry_price is None:
            return None

        entry = self.entry_price

        # TP / SL
        tp_price = entry * (1.0 + self.tp_pct)
        sl_price = entry * (1.0 - self.sl_pct)

        if price >= tp_price:
            self.in_position = False
            self.entry_price = None
            self.peak_price = None
            return f"🏁 TAKE PROFIT @ {price:.2f} (TP {self.tp_pct*100:.1f}%)"

        if price <= sl_price:
            self.in_position = False
            self.entry_price = None
            self.peak_price = None
            return f"🛑 STOP LOSS @ {price:.2f} (SL {self.sl_pct*100:.1f}%)"

        # Trailing
        if self.trailing_active:
            if self.peak_price is None or price > self.peak_price:
                self.peak_price = price

            trail_stop = self.peak_price * (1.0 - self.trailing_pct)
            if price <= trail_stop:
                self.in_position = False
                self.entry_price = None
                self.peak_price = None
                return f"🔁 TRAILING STOP @ {price:.2f} (Trail {self.trailing_pct*100:.1f}%)"

        return None