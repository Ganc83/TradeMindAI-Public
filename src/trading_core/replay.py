"""Deterministic, GUI-independent candle replay over the existing trading core."""
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from hashlib import sha256
import json

from .config import ExecutionConfig, PositionManagementConfig, RiskConfig, StrategyConfig
from .execution import ExecutionEngine
from .models import (Candle, EngineEvent, EngineEventType, ExitReason, MarketContext,
                     PerformanceMetrics, ReplayResult, SignalSide, StrategyState)
from .portfolio import PortfolioState
from .risk import RiskCalculator
from .strategy import StrategyEvaluator
from .trade_levels import TradeLevelCalculator
from .validation import finite


class FillPolicy(str, Enum):
    HIGH_LOW_STOP_FIRST = "HIGH_LOW_STOP_FIRST"
    CLOSE_STOP_FIRST = "CLOSE_STOP_FIRST"


@dataclass(frozen=True, slots=True)
class ReplayConfig:
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    management: PositionManagementConfig = field(default_factory=PositionManagementConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    fill_policy: FillPolicy = FillPolicy.HIGH_LOW_STOP_FIRST
    close_at_end: bool = True
    management_enabled: bool = True

    def __post_init__(self):
        for name, cls in (("strategy", StrategyConfig), ("risk", RiskConfig),
                          ("management", PositionManagementConfig), ("execution", ExecutionConfig)):
            if not isinstance(getattr(self, name), cls):
                raise ValueError(f"{name} must be {cls.__name__}")
        if not isinstance(self.fill_policy, FillPolicy):
            raise ValueError("fill_policy must be a FillPolicy")
        if not isinstance(self.close_at_end, bool):
            raise ValueError("close_at_end must be boolean")
        if not isinstance(self.management_enabled, bool):
            raise ValueError("management_enabled must be boolean")
        if self.strategy.trade_cooldown_seconds != self.execution.trade_cooldown_seconds:
            raise ValueError("strategy and execution trade cooldowns must agree")

    @property
    def fingerprint(self):
        encoded = json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()


class ReplayRunner:
    """Each timestamp is visited once. Exits use the *previous* stop; updates
    observed at this candle take effect on the next candle. No exit-bar re-entry.
    """

    def __init__(self, config: ReplayConfig, *, initial_balance: float = 10000.0):
        if not isinstance(config, ReplayConfig):
            raise ValueError("config must be ReplayConfig")
        finite("initial_balance", initial_balance, positive=True)
        self.config = config
        self.initial_balance = initial_balance

    def run(self, market: MarketContext) -> ReplayResult:
        if not isinstance(market, MarketContext):
            raise ValueError("market must be MarketContext")
        config = self.config
        engine = ExecutionEngine()
        strategy = StrategyEvaluator(config.strategy)
        levels = TradeLevelCalculator(config.management)
        risk = RiskCalculator(config.risk)
        portfolio = PortfolioState.initial(self.initial_balance)
        strategy_state = StrategyState()
        events = []
        equity = []
        candles = market.candles

        for index, candle in enumerate(candles):
            stamp = candle.timestamp_ms
            exited = False
            equity_emitted = False
            position = portfolio.open_position

            # A pre-existing stop/TP is checked before any same-bar stop update.
            if position is not None:
                decision = self._exit_decision(position, candle)
                if decision is not None:
                    price, reason = decision
                    closed = engine.close_position(
                        portfolio, exit_price=price, timestamp_ms=stamp,
                        exit_reason=reason, fee_rate=config.execution.fee_rate)
                    portfolio = closed.state
                    events.extend(closed.events)
                    equity_emitted = True
                    exited = True
                    strategy_state = replace(strategy_state,
                        position_open=False, last_trade_close_timestamp_ms=stamp)
                elif config.management_enabled:
                    updated = self._manage(engine, portfolio, candle)
                    portfolio = updated.state
                    events.extend(updated.events)

            if not exited and portfolio.open_position is None and self._entries_enabled(stamp):
                # The evaluator computes indicators from this exact historical prefix.
                prefix = MarketContext(market.symbol, market.timeframe, candles[:index + 1])
                evaluated = strategy.evaluate(prefix, strategy_state, now_ms=stamp)
                strategy_state = evaluated.state
                signal = evaluated.signal
                if signal.side is not SignalSide.HOLD:
                    events.append(EngineEvent(EngineEventType.SIGNAL, stamp, signal))
                    try:
                        history = prefix.candles
                        initial_levels = levels.calculate(
                            candle.close, signal.side, [c.high for c in history],
                            [c.low for c in history], [c.close for c in history])
                        sizing = risk.calculate(candle.close, initial_levels.stop_loss,
                                                portfolio.balance)
                    except ValueError as exc:
                        events.append(EngineEvent(EngineEventType.SIGNAL_REJECTED, stamp,
                                                  {"side": signal.side.value, "reason": str(exc)}))
                    else:
                        if sizing.effective_quantity <= 0:
                            events.append(EngineEvent(EngineEventType.SIGNAL_REJECTED, stamp,
                                {"side": signal.side.value, "reason": "zero effective quantity"}))
                        else:
                            opened = engine.open_position(
                                portfolio, symbol=market.symbol, timeframe=market.timeframe,
                                side=signal.side, entry_price=candle.close,
                                stop_loss=initial_levels.stop_loss,
                                take_profit=initial_levels.take_profit, timestamp_ms=stamp,
                                fee_rate=config.execution.fee_rate,
                                quantity=sizing.effective_quantity,
                                notional=sizing.effective_notional, source=signal.source or "",
                                score=signal.score, atr=initial_levels.atr,
                                level_mode=initial_levels.level_mode,
                                metadata={"signal_reason": signal.reason,
                                          "risk_amount": sizing.risk_amount,
                                          "risk_mode": sizing.risk_mode,
                                          "raw_notional": sizing.raw_notional,
                                          "notional_capped": sizing.capped})
                            portfolio = opened.state
                            events.extend(opened.events)
                            strategy_state = replace(strategy_state, position_open=True,
                                last_rsi_signal_timestamp_ms=stamp)

            # Phase-5 EOD closes at the last close. It also closes a last-bar entry.
            if index == len(candles) - 1 and config.close_at_end and portfolio.open_position:
                closed = engine.close_position(portfolio, exit_price=candle.close,
                    timestamp_ms=stamp, exit_reason=ExitReason.END_OF_DATA,
                    fee_rate=config.execution.fee_rate)
                portfolio = closed.state
                events.extend(closed.events)
                equity_emitted = True
            snapshot = portfolio.snapshot(stamp / 1000)
            equity.append(snapshot)
            if not equity_emitted:
                events.append(EngineEvent(EngineEventType.EQUITY_UPDATED, stamp, snapshot))

        metrics = self._metrics(portfolio, equity)
        return ReplayResult(metrics, portfolio.closed_trades, tuple(equity),
            {"start_balance": portfolio.start_balance,
             "end_balance": portfolio.balance,
             "final_position": portfolio.open_position,
             "events": tuple(events),
             "config": config,
             "config_fingerprint": config.fingerprint,
             "final_strategy_state": strategy_state})

    def _entries_enabled(self, timestamp_ms: int) -> bool:
        """Default replay is unrestricted; isolated observers may bound entries."""
        return True

    def _exit_decision(self, position, candle: Candle):
        policy = self.config.fill_policy
        if policy is FillPolicy.HIGH_LOW_STOP_FIRST:
            if position.side is SignalSide.LONG:
                stop_hit = candle.low <= position.stop_loss
                take_hit = candle.high >= position.take_profit
            else:
                stop_hit = candle.high >= position.stop_loss
                take_hit = candle.low <= position.take_profit
            stop_price, take_price = position.stop_loss, position.take_profit
        else:
            if position.side is SignalSide.LONG:
                stop_hit = candle.close <= position.stop_loss
                take_hit = candle.close >= position.take_profit
            else:
                stop_hit = candle.close >= position.stop_loss
                take_hit = candle.close <= position.take_profit
            stop_price = take_price = candle.close
        if stop_hit:
            data = position.metadata
            reason = (ExitReason.TRAILING_STOP if data.get("trailing_active") else
                      ExitReason.BREAK_EVEN if data.get("break_even_active") else
                      ExitReason.STOP_LOSS)
            return stop_price, reason
        if take_hit:
            return take_price, ExitReason.TAKE_PROFIT
        return None

    def _manage(self, engine, portfolio, candle: Candle):
        position = portfolio.open_position
        cfg = self.config.management
        data = position.metadata
        entry = position.entry_price
        close = candle.close
        long = position.side is SignalSide.LONG
        peak = max(data.get("highest", entry), close) if long else data.get("highest", entry)
        trough = min(data.get("lowest", entry), close) if not long else data.get("lowest", entry)
        gain = ((close / entry - 1) if long else (1 - close / entry)) * 100
        stop = position.stop_loss
        be = data.get("break_even_active", False)
        trailing = data.get("trailing_active", False)
        if not be and gain >= cfg.break_even_trigger_percent:
            be = True
            # Preserve the Phase-0 paper offset of 0.1%, with its fee caveat.
            stop = entry * (1.001 if long else .999)
        if not trailing and gain >= cfg.trailing_activation_percent:
            trailing = True
        if trailing:
            candidate = ((peak if long else trough) *
                         (1 - cfg.trailing_distance_percent / 100 if long else
                          1 + cfg.trailing_distance_percent / 100))
            stop = max(stop, candidate) if long else min(stop, candidate)
        return engine.update_position(portfolio, timestamp_ms=candle.timestamp_ms,
            stop_loss=stop, highest=peak, lowest=trough,
            break_even_active=be, trailing_active=trailing)

    @staticmethod
    def _metrics(portfolio, equity):
        trades = portfolio.closed_trades
        pnl = portfolio.balance - portfolio.start_balance
        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [-t.pnl for t in trades if t.pnl < 0]
        factor = sum(wins) / sum(losses) if losses else 0.0
        peak = portfolio.start_balance
        drawdown = 0.0
        for snapshot in equity:
            peak = max(peak, snapshot.equity)
            if peak > 0:
                drawdown = min(drawdown, (snapshot.equity / peak - 1) * 100)
        return PerformanceMetrics(len(trades), portfolio.balance, pnl,
            pnl / portfolio.start_balance * 100,
            len(wins) / len(trades) * 100 if trades else 0.0,
            factor, max(-100.0, drawdown))
