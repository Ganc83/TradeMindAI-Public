"""Pure initial TP/SL calculation with legacy ATR fallback semantics."""
from dataclasses import dataclass
from typing import Iterable

from .config import PositionManagementConfig
from .indicators import calculate_atr
from .models import SignalSide
from .validation import finite


@dataclass(frozen=True, slots=True)
class TradeLevels:
    entry_price: float
    stop_loss: float
    take_profit: float
    atr: float | None
    level_mode: str
    stop_distance: float
    take_profit_distance: float


class TradeLevelCalculator:
    def __init__(self, config: PositionManagementConfig):
        self.config = config

    def calculate(self, entry_price: float, side: SignalSide | str,
                  highs: Iterable[float] | None = None,
                  lows: Iterable[float] | None = None,
                  closes: Iterable[float] | None = None) -> TradeLevels:
        finite("entry_price", entry_price, positive=True)
        try:
            parsed_side = side if isinstance(side, SignalSide) else SignalSide(side)
        except (TypeError, ValueError) as exc:
            raise ValueError("side must be LONG or SHORT") from exc
        if parsed_side is SignalSide.HOLD:
            raise ValueError("side must be LONG or SHORT")

        atr = None
        if (self.config.use_atr_stop and highs is not None and lows is not None
                and closes is not None):
            atr = calculate_atr(highs, lows, closes, self.config.atr_period)
            if atr is not None and atr > 0:
                sl_distance = atr * self.config.atr_stop_multiplier
                tp_distance = atr * self.config.atr_take_profit_multiplier
                return self._result(entry_price, parsed_side, sl_distance, tp_distance,
                                    atr, "ATR")

        sl_distance = entry_price * self.config.stop_loss_percent / 100.0
        tp_distance = entry_price * self.config.take_profit_percent / 100.0
        return self._result(entry_price, parsed_side, sl_distance, tp_distance,
                            None, "PERCENT")

    @staticmethod
    def _result(entry: float, side: SignalSide, sl_distance: float,
                tp_distance: float, atr: float | None, mode: str) -> TradeLevels:
        if side is SignalSide.LONG:
            stop_loss, take_profit = entry - sl_distance, entry + tp_distance
        else:
            stop_loss, take_profit = entry + sl_distance, entry - tp_distance
        finite("stop_loss", stop_loss, positive=True)
        finite("take_profit", take_profit, positive=True)
        return TradeLevels(entry, stop_loss, take_profit, atr, mode,
                           abs(entry - stop_loss), abs(take_profit - entry))


def calculate_trade_levels(entry_price: float, side: SignalSide | str,
                           config: PositionManagementConfig = PositionManagementConfig(),
                           highs=None, lows=None, closes=None) -> TradeLevels:
    return TradeLevelCalculator(config).calculate(entry_price, side, highs, lows, closes)
