"""GUI-unabhaengige Persistenz fuer AI-Backtest-Ergebnisse."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


AI_MEMORY_FILE = Path(__file__).with_name("ai_memory.json")


def load_ai_memory() -> dict[str, Any]:
    """Laedt die gespeicherten AI-Backtest-Ergebnisse.

    Falls die JSON-Datei noch nicht existiert oder leer ist, wird sie mit
    einer leeren Datenstruktur angelegt.
    """
    if not AI_MEMORY_FILE.exists():
        save_ai_memory({})
        return {}

    if AI_MEMORY_FILE.stat().st_size == 0:
        save_ai_memory({})
        return {}

    with AI_MEMORY_FILE.open("r", encoding="utf-8") as memory_file:
        data = json.load(memory_file)

    if not isinstance(data, dict):
        return {}

    return data


def save_ai_memory(memory: dict[str, Any] | None = None) -> None:
    """Speichert die AI-Backtest-Ergebnisse dauerhaft in ai_memory.json."""
    if memory is None:
        memory = {}

    with AI_MEMORY_FILE.open("w", encoding="utf-8") as memory_file:
        json.dump(memory, memory_file, indent=4, ensure_ascii=False)


def update_ai_memory(
    coin,
    timeframe,
    score,
    profit_factor,
    winrate,
    pnl_pct,
    max_drawdown,
) -> dict[str, Any]:
    """Aktualisiert die gespeicherten Backtest-Durchschnitte pro Coin/Timeframe."""
    memory = load_ai_memory()
    coin_key = str(coin)
    timeframe_key = str(timeframe)

    coin_memory = memory.setdefault(coin_key, {})
    existing = coin_memory.get(timeframe_key, {})

    backtests = int(existing.get("backtests", 0))
    new_backtests = backtests + 1

    score_value = float(score)
    profit_factor_value = float(profit_factor)
    winrate_value = float(winrate)
    pnl_pct_value = float(pnl_pct)
    max_drawdown_value = float(max_drawdown)

    updated = {
        "backtests": new_backtests,
        "last_score": score_value,
        "avg_score": _updated_average(existing.get("avg_score", 0.0), score_value, backtests),
        "avg_profit_factor": _updated_average(
            existing.get("avg_profit_factor", 0.0),
            profit_factor_value,
            backtests,
        ),
        "avg_winrate": _updated_average(existing.get("avg_winrate", 0.0), winrate_value, backtests),
        "avg_pnl_pct": _updated_average(existing.get("avg_pnl_pct", 0.0), pnl_pct_value, backtests),
        "avg_drawdown": _updated_average(
            existing.get("avg_drawdown", 0.0),
            max_drawdown_value,
            backtests,
        ),
        "last_backtest_date": datetime.now().isoformat(timespec="seconds"),
    }

    coin_memory[timeframe_key] = updated
    save_ai_memory(memory)
    return updated


def build_experience_summary(memory: dict[str, Any], coin, timeframe) -> dict[str, Any]:
    """Erstellt eine kompakte Experience-Zusammenfassung pro Coin/Timeframe."""
    coin_key = str(coin)
    timeframe_key = str(timeframe)
    experience = memory.get(coin_key, {}).get(timeframe_key, {})

    backtests = int(experience.get("backtests", 0))
    last_score = float(experience.get("last_score", 0.0))
    avg_score = float(experience.get("avg_score", 0.0))
    avg_profit_factor = float(experience.get("avg_profit_factor", 0.0))
    avg_winrate = float(experience.get("avg_winrate", 0.0))

    if last_score > avg_score + 3:
        trend = "improving"
    elif last_score < avg_score - 3:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "backtests": backtests,
        "avg_score": avg_score,
        "avg_profit_factor": avg_profit_factor,
        "avg_winrate": avg_winrate,
        "trend": trend,
    }


def _updated_average(previous_average, new_value: float, previous_count: int) -> float:
    """Berechnet einen fortlaufenden Durchschnitt ohne Rohdatenhistorie."""
    previous_average_value = float(previous_average)
    updated_value = ((previous_average_value * previous_count) + new_value) / (previous_count + 1)
    return round(updated_value, 6)
