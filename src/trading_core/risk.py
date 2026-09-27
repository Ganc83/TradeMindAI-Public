"""Pure, GUI-independent legacy risk and position-sizing calculations."""
from dataclasses import dataclass

from .config import RiskConfig
from .validation import finite


@dataclass(frozen=True, slots=True)
class PositionSizingResult:
    risk_amount: float
    raw_quantity: float
    raw_notional: float
    effective_quantity: float
    effective_notional: float
    capped: bool
    risk_mode: str


class RiskCalculator:
    """Reproduce the AUTO_PAPER FIXED/PERCENT semantics without leverage."""

    def __init__(self, config: RiskConfig):
        self.config = config

    def risk_amount(self, balance: float) -> float:
        finite("balance", balance, minimum=0)
        if self.config.risk_mode == "FIXED":
            return min(self.config.fixed_amount, balance)
        return balance * (self.config.risk_percent / 100.0)

    def calculate(self, entry_price: float, stop_loss: float, balance: float,
                  available_capital: float | None = None) -> PositionSizingResult:
        finite("entry_price", entry_price, positive=True)
        finite("stop_loss", stop_loss, positive=True)
        return self.calculate_from_distance(
            entry_price, abs(entry_price - stop_loss), balance, available_capital
        )

    def calculate_from_distance(self, entry_price: float, stop_distance: float,
                                balance: float,
                                available_capital: float | None = None
                                ) -> PositionSizingResult:
        finite("entry_price", entry_price, positive=True)
        finite("stop_distance", stop_distance, minimum=0)
        finite("balance", balance, minimum=0)
        if available_capital is None:
            available_capital = balance
        finite("available_capital", available_capital, minimum=0)

        risk_amount = self.risk_amount(balance)
        if stop_distance == 0:
            return PositionSizingResult(risk_amount, 0.0, 0.0, 0.0, 0.0, False,
                                        self.config.risk_mode)

        raw_quantity = risk_amount / stop_distance
        raw_notional = raw_quantity * entry_price
        capital_cap = min(balance, available_capital)
        notional_cap = capital_cap * (self.config.max_notional_percent / 100.0)
        effective_notional = min(raw_notional, notional_cap)
        effective_quantity = effective_notional / entry_price
        return PositionSizingResult(
            risk_amount, raw_quantity, raw_notional, effective_quantity,
            effective_notional, raw_notional > notional_cap, self.config.risk_mode,
        )


def calculate_position_size(entry_price: float, stop_loss: float, balance: float,
                            config: RiskConfig = RiskConfig(),
                            available_capital: float | None = None) -> PositionSizingResult:
    return RiskCalculator(config).calculate(entry_price, stop_loss, balance, available_capital)


def calculate_position_size_from_distance(
        entry_price: float, stop_distance: float, balance: float,
        config: RiskConfig = RiskConfig(),
        available_capital: float | None = None) -> PositionSizingResult:
    return RiskCalculator(config).calculate_from_distance(
        entry_price, stop_distance, balance, available_capital
    )
