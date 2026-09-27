"""Pure indicator calculations mirroring the production legacy formulas."""
from __future__ import annotations
from collections.abc import Sequence
import numpy as np

def _finite_values(values: Sequence[float], name: str) -> np.ndarray:
    try:
        result = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain only numeric values") from exc
    if result.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return result.copy()

def _period(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or int(value) <= 0:
        raise ValueError("period must be a positive integer")
    return int(value)

def calculate_rsi(closes: Sequence[float], period: int = 14) -> float | None:
    """Legacy trailing RSI; short data returns None; zero loss returns 100."""
    period = _period(period)
    closes = _finite_values(closes, "closes")
    if len(closes) <= period:
        return None
    delta = np.diff(closes)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain, avg_loss = np.mean(gain[-period:]), np.mean(loss[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))

def calculate_sma(values: Sequence[float], period: int) -> np.ndarray | None:
    """All legacy valid SMA values, or None when data is too short."""
    period = _period(period)
    values = _finite_values(values, "values")
    if len(values) < period:
        return None
    return np.convolve(values, np.ones(period) / period, mode="valid")

def calculate_atr(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14) -> float | None:
    """Legacy trailing mean true range, or None when data is too short."""
    period = _period(period)
    highs = _finite_values(highs, "highs")
    lows = _finite_values(lows, "lows")
    closes = _finite_values(closes, "closes")
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows and closes must have equal lengths")
    if len(closes) < period + 1:
        return None
    previous_closes = closes[:-1]
    true_range = np.maximum.reduce([highs[1:] - lows[1:], np.abs(highs[1:] - previous_closes), np.abs(lows[1:] - previous_closes)])
    return float(np.mean(true_range[-period:]))

def calculate_atr_percentage(atr: float, last_price: float) -> float:
    """Legacy ATR percentage derivation used by the filter."""
    atr, last_price = _finite_values([atr, last_price], "atr and last_price")
    return float((atr / last_price) * 100) if last_price > 0 else 0.0

def calculate_volume_average(volumes: Sequence[float], period: int = 20) -> float | None:
    """Mean of the last period volumes, or None when data is too short."""
    period = _period(period)
    volumes = _finite_values(volumes, "volumes")
    if len(volumes) < period:
        return None
    return float(np.mean(volumes[-period:]))
