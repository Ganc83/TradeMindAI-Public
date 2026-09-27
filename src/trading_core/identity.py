"""Deterministic identifiers for core domain entities."""

from hashlib import sha256

from .validation import text


def position_id_from_entry(symbol: str, timeframe: str, entry_timestamp_ms: int) -> str:
    """Return the stable position ID for one market entry.

    Normalization makes equivalent symbol/timeframe spellings produce the same
    ID. The full SHA-256 digest avoids random state and process-dependent hashes.
    """
    text("symbol", symbol)
    text("timeframe", timeframe)
    if (
        isinstance(entry_timestamp_ms, bool)
        or not isinstance(entry_timestamp_ms, int)
        or entry_timestamp_ms < 0
    ):
        raise ValueError("entry_timestamp_ms must be a non-negative integer")

    canonical = f"{symbol.strip().upper()}|{timeframe.strip().lower()}|{entry_timestamp_ms}"
    return f"pos_{sha256(canonical.encode('utf-8')).hexdigest()}"
