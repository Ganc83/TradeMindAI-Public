"""Explicit realized-balance portfolio; marks never silently change equity."""
from dataclasses import dataclass
from .models import PortfolioSnapshot, Position, Trade
from .validation import finite


@dataclass(frozen=True, slots=True)
class PortfolioState:
    start_balance: float
    balance: float
    open_position: Position | None = None
    closed_trades: tuple[Trade, ...] = ()
    total_fees: float = 0.0
    realized_pnl: float = 0.0

    def __post_init__(self):
        finite("start_balance", self.start_balance, minimum=0)
        finite("balance", self.balance)
        finite("total_fees", self.total_fees, minimum=0)
        finite("realized_pnl", self.realized_pnl)
        object.__setattr__(self, "closed_trades", tuple(self.closed_trades))

    @classmethod
    def initial(cls, balance=10000.0):
        return cls(balance, balance)

    @property
    def equity(self):
        # Legacy equity curves contain realized balances only.
        return self.balance

    def snapshot(self, timestamp):
        return PortfolioSnapshot(timestamp, self.balance, self.equity)
