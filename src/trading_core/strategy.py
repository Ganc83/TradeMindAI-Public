"""Pure, side-effect-free production strategy evaluation (Phase 3 shadow mode)."""
from dataclasses import dataclass, replace

from .config import StrategyConfig
from .indicators import calculate_atr, calculate_atr_percentage, calculate_rsi, calculate_sma, calculate_volume_average
from .models import MarketContext, Signal, SignalSide, StrategyState


@dataclass(frozen=True, slots=True)
class ScoreResult:
    long_score: int
    short_score: int
    long_reasons: tuple[str, ...]
    short_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StrategyEvaluation:
    signal: Signal
    state: StrategyState
    long_score: int
    short_score: int
    long_reasons: tuple[str, ...]
    short_reasons: tuple[str, ...]
    rsi_zone: str
    atr_ok: bool
    mtf_ok: bool
    signal_cooldown_blocked: bool
    trade_cooldown_blocked: bool
    position_blocked: bool
    countertrend_allowed: bool


class RsiZoneMachine:
    LOW_ENTER, LOW_EXIT, HIGH_ENTER, HIGH_EXIT = 28, 35, 72, 65

    @classmethod
    def transition(cls, rsi, last_zone):
        if rsi is None:
            return last_zone
        if last_zone == "NEUTRAL":
            if rsi <= cls.LOW_ENTER:
                return "OVERSOLD"
            if rsi >= cls.HIGH_ENTER:
                return "OVERBOUGHT"
        elif last_zone == "OVERSOLD" and rsi >= cls.LOW_EXIT:
            return "NEUTRAL"
        elif last_zone == "OVERBOUGHT" and rsi <= cls.HIGH_EXIT:
            return "NEUTRAL"
        return last_zone


def calculate_entry_score(closes, opens, volumes, sma20, sma50, rsi):
    long_score = short_score = 0
    long_reasons, short_reasons = [], []
    if len(closes) < 2 or len(opens) < 1 or len(volumes) < 20:
        return ScoreResult(0, 0, (), ())
    last_close, previous_close, last_open = float(closes[-1]), float(closes[-2]), float(opens[-1])
    last_volume = float(volumes[-1])
    average_volume = calculate_volume_average(volumes, 20)
    if sma20 is not None and sma50 is not None:
        if sma20 > sma50:
            long_score += 35
            long_reasons.append("Trend bullisch")
        if sma20 < sma50:
            short_score += 35
            short_reasons.append("Trend bärisch")
    if rsi is not None:
        if rsi <= 28:
            long_score += 35
            long_reasons.append(f"RSI oversold ({rsi:.1f})")
        if rsi >= 72:
            short_score += 35
            short_reasons.append(f"RSI overbought ({rsi:.1f})")
    if last_close > last_open and last_close > previous_close:
        long_score += 15
        long_reasons.append("Bullish momentum")
    if last_close < last_open and last_close < previous_close:
        short_score += 15
        short_reasons.append("Bearish momentum")
    if last_volume > average_volume:
        long_score += 15
        short_score += 15
        long_reasons.append("Volumen über Durchschnitt")
        short_reasons.append("Volumen über Durchschnitt")
    return ScoreResult(long_score, short_score, tuple(long_reasons), tuple(short_reasons))


class StrategyEvaluator:
    def __init__(self, config=None):
        self.config = config or StrategyConfig()

    def evaluate(self, market: MarketContext, state: StrategyState, *, now_ms: int):
        config = self.config
        candles = market.candles
        closes = [c.close for c in candles]
        opens = [c.open for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        volumes = [c.volume for c in candles]
        base_metadata = {"symbol": market.symbol, "timeframe": market.timeframe, "score": 0, "reasons": (),
                         "rsi": None, "rsi_zone": state.last_rsi_zone, "sma20": None, "sma50": None,
                         "atr": None, "atr_pct": 0.0, "atr_ok": True, "mtf_ok": True,
                         "signal_cooldown_blocked": False, "trade_cooldown_blocked": False,
                         "position_blocked": state.position_open, "countertrend_allowed": False}
        empty = Signal(SignalSide.HOLD, now_ms, closes[-1] if closes else None, source="RSI", metadata=base_metadata)
        if len(closes) < config.sma_slow:
            return StrategyEvaluation(empty, state, 0, 0, (), (), state.last_rsi_zone, True, True, False, False, state.position_open, False)

        sma20 = float(calculate_sma(closes, config.sma_fast)[-1])
        sma50 = float(calculate_sma(closes, config.sma_slow)[-1])
        rsi = calculate_rsi(closes, config.rsi_period)
        history = (*state.rsi_history, rsi)[-200:] if rsi is not None else state.rsi_history
        zone = RsiZoneMachine.transition(rsi, state.last_rsi_zone)
        next_state = replace(state, last_rsi_zone=zone, rsi_history=history)
        score = calculate_entry_score(closes, opens, volumes, sma20, sma50, rsi)

        if config.atr_filter_enabled:
            atr = calculate_atr(highs, lows, closes, config.atr_period)
            atr_pct = calculate_atr_percentage(atr, closes[-1]) if atr is not None else 0.0
            atr_ok = atr is not None and atr_pct >= config.atr_min_percent
        else:
            atr, atr_pct, atr_ok = None, 0.0, True

        signal_blocked = now_ms - (state.last_rsi_signal_timestamp_ms or 0) < config.signal_cooldown_seconds * 1000
        trade_blocked = now_ms - (state.last_trade_close_timestamp_ms or 0) < config.trade_cooldown_seconds * 1000
        previous_rsi = history[-2] if len(history) >= 2 else None
        rebound_long = rsi is not None and previous_rsi is not None and state.last_rsi_zone == "OVERSOLD" and rsi > previous_rsi
        rebound_short = rsi is not None and previous_rsi is not None and state.last_rsi_zone == "OVERBOUGHT" and rsi < previous_rsi
        long_trigger = rsi is not None and ((zone != state.last_rsi_zone and zone == "OVERSOLD") or rebound_long)
        short_trigger = rsi is not None and ((zone != state.last_rsi_zone and zone == "OVERBOUGHT") or rebound_short)
        side, reasons, selected_score = SignalSide.HOLD, (), 0
        mtf_ok, countertrend = True, False
        if long_trigger:
            countertrend = config.mtf_enabled and state.mtf_trend == "BEARISH" and rsi <= 22 and score.long_score >= 65
            mtf_ok = not config.mtf_enabled or state.mtf_trend in ("BULLISH", "NEUTRAL") or countertrend
            required = 65 if countertrend else config.entry_score_threshold
            if ((sma20 > sma50) or countertrend) and mtf_ok and atr_ok and score.long_score >= required and not signal_blocked and not state.position_open and not trade_blocked:
                side, reasons, selected_score = SignalSide.LONG, score.long_reasons, score.long_score
        elif short_trigger:
            countertrend = config.mtf_enabled and state.mtf_trend == "BULLISH" and rsi >= 78 and score.short_score >= 65
            mtf_ok = not config.mtf_enabled or state.mtf_trend in ("BEARISH", "NEUTRAL") or countertrend
            required = 65 if countertrend else config.entry_score_threshold
            if ((sma20 < sma50) or countertrend) and mtf_ok and atr_ok and score.short_score >= required and not signal_blocked and not state.position_open and not trade_blocked:
                side, reasons, selected_score = SignalSide.SHORT, score.short_reasons, score.short_score
        reason = " | ".join(reasons) if reasons else (f"{side.value} score={selected_score}" if side is not SignalSide.HOLD else "")
        metadata = {**base_metadata, "score": selected_score, "reasons": reasons, "rsi": rsi, "rsi_zone": zone,
                    "sma20": sma20, "sma50": sma50, "atr": atr, "atr_pct": atr_pct, "atr_ok": atr_ok,
                    "mtf_ok": mtf_ok, "signal_cooldown_blocked": signal_blocked,
                    "trade_cooldown_blocked": trade_blocked, "position_blocked": state.position_open,
                    "countertrend_allowed": countertrend}
        signal = Signal(side, now_ms, closes[-1], reason, "RSI", metadata=metadata)
        return StrategyEvaluation(signal, next_state, score.long_score, score.short_score, score.long_reasons,
                                  score.short_reasons, zone, atr_ok, mtf_ok, signal_blocked, trade_blocked,
                                  state.position_open, countertrend)
