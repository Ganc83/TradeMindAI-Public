"""Deterministic execution arithmetic. No exit selection or candle orchestration."""
from copy import deepcopy
from math import isclose
from dataclasses import dataclass, replace
from .models import (Position, Trade, SignalSide, ExitReason, EngineEvent,
                     EngineEventType, _ts)
from .portfolio import PortfolioState
from .validation import finite


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    state: PortfolioState
    events: tuple[EngineEvent, ...] = ()
    position: Position | None = None
    trade: Trade | None = None


def calculate_pnl(entry, exit_price, quantity, side, fee_rate):
    """Keep the legacy combined-notional operation order (including rounding)."""
    for name, value in (("entry", entry), ("exit_price", exit_price),
                        ("quantity", quantity)):
        finite(name, value, positive=True)
    finite("fee_rate", fee_rate, minimum=0)
    side = SignalSide(side)
    if side is SignalSide.HOLD:
        raise ValueError("cannot execute HOLD")
    gross = ((exit_price - entry) if side is SignalSide.LONG
             else (entry - exit_price)) * quantity
    entry_fee = entry * quantity * fee_rate
    exit_fee = exit_price * quantity * fee_rate
    fees = (entry * quantity + exit_price * quantity) * fee_rate
    return gross, entry_fee, exit_fee, fees, gross - fees


def estimate_preview_fees(entry, exit_price, quantity, fee_rate):
    # Preserve the preview's separate-leg summation and nonpositive fallback.
    if entry <= 0 or exit_price <= 0 or quantity <= 0:
        return 0.0
    return entry * quantity * fee_rate + exit_price * quantity * fee_rate


class ExecutionEngine:
    def open_position(self, state, *, symbol, timeframe, side, entry_price,
                      stop_loss, take_profit, timestamp_ms, fee_rate,
                      quantity=None, notional=None, source="", score=None,
                      atr=None, level_mode="PERCENT", metadata=None,
                      opened_at=None):
        if state.open_position is not None:
            return ExecutionResult(state)  # Legacy double-open is a no-op.
        _ts("timestamp_ms", timestamp_ms)
        finite("entry_price", entry_price, positive=True)
        finite("fee_rate", fee_rate, minimum=0)
        if quantity is None:
            finite("notional", notional, positive=True)
            quantity = notional / entry_price
        finite("quantity", quantity, positive=True)
        if notional is None:
            notional = entry_price * quantity
        finite("notional", notional, positive=True)
        if not isclose(notional, entry_price * quantity, rel_tol=1e-12):
            raise ValueError("quantity and notional disagree")
        side = SignalSide(side)
        data = deepcopy(dict(metadata or {}))
        explicit_open_time = opened_at is not None
        opened_at = timestamp_ms / 1000 if opened_at is None else opened_at
        finite("opened_at", opened_at, minimum=0)
        if explicit_open_time and int(opened_at * 1000) != timestamp_ms:
            raise ValueError("opened_at must correspond to timestamp_ms")
        data.update(source=source, score=score, atr_at_entry=atr,
                    level_mode=level_mode, fee_rate=fee_rate,
                    entry_fee=entry_price * quantity * fee_rate,
                    open_time=opened_at, time=opened_at,
                    highest=entry_price, lowest=entry_price,
                    break_even_active=False, trailing_active=False)
        position = Position(symbol, timeframe, timestamp_ms, side, entry_price,
                            quantity, take_profit, stop_loss, reason=source,
                            notional=notional, metadata=data)
        updated = replace(state, open_position=position)
        return ExecutionResult(updated, (EngineEvent(
            EngineEventType.POSITION_OPENED, timestamp_ms, position),), position)

    def close_position(self, state, *, exit_price, timestamp_ms, exit_reason,
                       fee_rate=None, closed_at=None):
        position = state.open_position
        if position is None:
            return ExecutionResult(state)
        _ts("timestamp_ms", timestamp_ms)
        explicit_close_time = closed_at is not None
        closed_at = timestamp_ms / 1000 if closed_at is None else closed_at
        finite("closed_at", closed_at, minimum=0)
        if explicit_close_time and int(closed_at * 1000) != timestamp_ms:
            raise ValueError("closed_at must correspond to timestamp_ms")
        rate = position.metadata.get("fee_rate", 0.001) if fee_rate is None else fee_rate
        gross, entry_fee, exit_fee, fees, net = calculate_pnl(
            position.entry_price, exit_price, position.quantity, position.side, rate)
        opened_at = position.metadata.get("open_time", position.entry_timestamp_ms / 1000)
        data = deepcopy(dict(position.metadata))
        for key in ("symbol", "side", "entry", "exit", "qty", "pnl", "why", "reason",
                    "balance", "hold_time_sec", "open_time", "close_time"):
            data.pop(key, None)
        data.update(position_id=position.position_id, trade_id=position.position_id,
                    timeframe=position.timeframe, notional=position.notional,
                    gross_pnl=gross, entry_fee=entry_fee, exit_fee=exit_fee,
                    total_fees=fees, fees=fees, fee_rate=rate)
        trade = Trade(position.symbol, position.side, position.entry_price,
                      exit_price, position.quantity, net, ExitReason(exit_reason),
                      position.reason, state.balance + net, opened_at, closed_at,
                      closed_at - position.metadata.get("time", opened_at), data)
        updated = replace(state, balance=trade.balance, open_position=None,
                          closed_trades=state.closed_trades + (trade,),
                          total_fees=state.total_fees + fees,
                          realized_pnl=state.realized_pnl + net)
        events = (EngineEvent(EngineEventType.POSITION_CLOSED, timestamp_ms, trade),
                  EngineEvent(EngineEventType.EQUITY_UPDATED, timestamp_ms,
                              updated.snapshot(closed_at)))
        return ExecutionResult(updated, events, position, trade)

    def update_position(self, state, *, timestamp_ms, stop_loss=None,
                        highest=None, lowest=None, break_even_active=None,
                        trailing_active=None):
        """Apply caller-selected state changes; deliberately selects no triggers."""
        _ts("timestamp_ms", timestamp_ms)
        position = state.open_position
        if position is None:
            return ExecutionResult(state)
        data = deepcopy(dict(position.metadata))
        events = []
        for name, value in (("highest", highest), ("lowest", lowest)):
            if value is not None:
                finite(name, value, positive=True)
                data[name] = value
        for name, value, event in (
            ("break_even_active", break_even_active, EngineEventType.BREAK_EVEN_ACTIVATED),
            ("trailing_active", trailing_active, EngineEventType.TRAILING_ACTIVATED)):
            if value is not None:
                if not isinstance(value, bool):
                    raise ValueError(name + " must be boolean")
                if value and not data.get(name, False):
                    events.append(EngineEvent(event, timestamp_ms, position.position_id))
                data[name] = value
        stop = position.stop_loss if stop_loss is None else stop_loss
        updated_position = replace(position, stop_loss=stop, metadata=data)
        if stop != position.stop_loss:
            events.append(EngineEvent(EngineEventType.STOP_UPDATED, timestamp_ms,
                                      {"position_id": position.position_id, "stop_loss": stop}))
        return ExecutionResult(replace(state, open_position=updated_position),
                               tuple(events), updated_position)
