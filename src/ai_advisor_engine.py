"""GUI-unabhaengige AI-Advisor-Engine fuer Backtest-Kennzahlen."""

from __future__ import annotations

from typing import Any


def calculate_ai_score(
    trades: int,
    pnl_pct: float,
    winrate: float,
    profit_factor: float,
    max_drawdown: float,
) -> int:
    """Berechnet einen AI-Score von 0 bis 100 aus Backtest-Kennzahlen.

    Args:
        trades: Anzahl abgeschlossener Backtest-Trades.
        pnl_pct: Gewinn oder Verlust in Prozent bezogen auf das Startkapital.
        winrate: Anteil gewonnener Trades in Prozent.
        profit_factor: Bruttogewinn geteilt durch Bruttoverlust.
        max_drawdown: Maximaler Drawdown in Prozent. Positive und negative
            Werte werden akzeptiert.

    Returns:
        Ganzzahliger Score zwischen 0 und 100.
    """
    drawdown_abs = abs(max_drawdown)
    score = 0.0

    if trades >= 50:
        score += 15
    elif trades >= 25:
        score += 10
    elif trades >= 10:
        score += 5

    if pnl_pct >= 20:
        score += 25
    elif pnl_pct >= 10:
        score += 20
    elif pnl_pct > 0:
        score += 12
    elif pnl_pct > -5:
        score += 5

    if winrate >= 65:
        score += 20
    elif winrate >= 55:
        score += 15
    elif winrate >= 45:
        score += 8

    if profit_factor >= 2.0:
        score += 25
    elif profit_factor >= 1.5:
        score += 18
    elif profit_factor >= 1.1:
        score += 10

    if drawdown_abs <= 5:
        score += 15
    elif drawdown_abs <= 10:
        score += 10
    elif drawdown_abs <= 20:
        score += 5

    return max(0, min(100, round(score)))


def classify_setup(
    trades: int,
    pnl_pct: float,
    winrate: float,
    profit_factor: float,
    max_drawdown: float,
) -> str:
    """Klassifiziert ein Setup anhand der Backtest-Kennzahlen.

    Args:
        trades: Anzahl abgeschlossener Backtest-Trades.
        pnl_pct: Gewinn oder Verlust in Prozent bezogen auf das Startkapital.
        winrate: Anteil gewonnener Trades in Prozent.
        profit_factor: Bruttogewinn geteilt durch Bruttoverlust.
        max_drawdown: Maximaler Drawdown in Prozent. Positive und negative
            Werte werden akzeptiert.

    Returns:
        Eine textuelle Setup-Klassifikation.
    """
    score = calculate_ai_score(
        trades=trades,
        pnl_pct=pnl_pct,
        winrate=winrate,
        profit_factor=profit_factor,
        max_drawdown=max_drawdown,
    )

    if score >= 80:
        return "EXCELLENT"
    if score >= 65:
        return "GOOD"
    if score >= 45:
        return "NEUTRAL"
    if score >= 25:
        return "WEAK"
    return "AVOID"


def build_ai_recommendation(
    trades: int,
    pnl_pct: float,
    winrate: float,
    profit_factor: float,
    max_drawdown: float,
) -> str:
    """Erstellt eine Handlungsempfehlung aus Backtest-Kennzahlen.

    Args:
        trades: Anzahl abgeschlossener Backtest-Trades.
        pnl_pct: Gewinn oder Verlust in Prozent bezogen auf das Startkapital.
        winrate: Anteil gewonnener Trades in Prozent.
        profit_factor: Bruttogewinn geteilt durch Bruttoverlust.
        max_drawdown: Maximaler Drawdown in Prozent. Positive und negative
            Werte werden akzeptiert.

    Returns:
        Kurzer Empfehlungstext fuer die weitere Nutzung des Setups.
    """
    score = calculate_ai_score(
        trades=trades,
        pnl_pct=pnl_pct,
        winrate=winrate,
        profit_factor=profit_factor,
        max_drawdown=max_drawdown,
    )
    classification = classify_setup(
        trades=trades,
        pnl_pct=pnl_pct,
        winrate=winrate,
        profit_factor=profit_factor,
        max_drawdown=max_drawdown,
    )
    drawdown_abs = abs(max_drawdown)

    warnings: list[str] = []
    if trades < 20:
        warnings.append("zu wenige Trades fuer hohe Aussagekraft")
    if profit_factor < 1.1:
        warnings.append("Profit Factor ist schwach")
    if pnl_pct <= 0:
        warnings.append("Setup ist nicht profitabel")
    if drawdown_abs > 20:
        warnings.append("Drawdown ist hoch")

    if classification == "EXCELLENT":
        recommendation = "Setup ist stark und kann weiter beobachtet oder vorsichtig skaliert werden."
    elif classification == "GOOD":
        recommendation = "Setup ist brauchbar, sollte aber vor groesserem Einsatz weiter validiert werden."
    elif classification == "NEUTRAL":
        recommendation = "Setup ist nur bedingt interessant und sollte optimiert werden."
    elif classification == "WEAK":
        recommendation = "Setup ist schwach und sollte nicht ohne Anpassungen genutzt werden."
    else:
        recommendation = "Setup vermeiden, bis Profitabilitaet und Risiko deutlich besser sind."

    if warnings:
        recommendation += " Hinweise: " + "; ".join(warnings) + "."

    return recommendation


def build_ai_reasons(
    trades: int,
    pnl_pct: float,
    winrate: float,
    profit_factor: float,
    max_drawdown: float,
) -> list[str]:
    """Erzeugt nachvollziehbare Einzelgruende fuer die AI-Bewertung.

    Args:
        trades: Anzahl abgeschlossener Backtest-Trades.
        pnl_pct: Gewinn oder Verlust in Prozent bezogen auf das Startkapital.
        winrate: Anteil gewonnener Trades in Prozent.
        profit_factor: Bruttogewinn geteilt durch Bruttoverlust.
        max_drawdown: Maximaler Drawdown in Prozent. Positive und negative
            Werte werden akzeptiert.

    Returns:
        Liste einzelner Begruendungen als Strings.
    """
    drawdown_abs = abs(max_drawdown)
    reasons: list[str] = []

    if trades >= 50:
        reasons.append("Genuegend Trades fuer eine belastbare Statistik.")
    elif trades >= 20:
        reasons.append("Trade-Anzahl ist brauchbar, aber weitere Daten waeren besser.")
    elif trades > 0:
        reasons.append("Zu wenige Trades fuer eine belastbare Statistik.")
    else:
        reasons.append("Es wurden keine Trades im Backtest gefunden.")

    if pnl_pct > 0:
        reasons.append("Profitabilitaet ist positiv.")
    elif pnl_pct < 0:
        reasons.append("Profitabilitaet ist negativ.")
    else:
        reasons.append("Profitabilitaet ist neutral.")

    if winrate >= 60:
        reasons.append("Winrate ist stark.")
    elif winrate >= 50:
        reasons.append("Winrate ist solide.")
    else:
        reasons.append("Winrate ist schwach.")

    if profit_factor >= 1.5:
        reasons.append("Profit Factor ist stark.")
    elif profit_factor >= 1.1:
        reasons.append("Profit Factor ist positiv, aber noch nicht stark.")
    else:
        reasons.append("Profit Factor ist schwach.")

    if drawdown_abs <= 5:
        reasons.append("Drawdown ist niedrig.")
    elif drawdown_abs <= 15:
        reasons.append("Drawdown ist moderat.")
    else:
        reasons.append("Drawdown ist hoch.")

    return reasons


def calculate_confidence(
    score,
    classification,
    experience_summary: dict[str, Any],
) -> int:
    """Berechnet eine adaptive Confidence aus aktuellem Score und Experience-Daten."""
    score_value = float(score)
    avg_score = float(experience_summary.get("avg_score", score_value))
    backtests = int(experience_summary.get("backtests", 0))
    trend = str(experience_summary.get("trend", "stable")).lower()
    classification_key = str(classification).upper()

    confidence = score_value
    confidence += (avg_score - score_value) * 0.25

    if classification_key == "EXCELLENT":
        confidence += 5
    elif classification_key == "GOOD":
        confidence += 2
    elif classification_key == "WEAK":
        confidence -= 5
    elif classification_key == "AVOID":
        confidence -= 10

    if backtests >= 20:
        confidence += 10
    elif backtests >= 10:
        confidence += 7
    elif backtests >= 5:
        confidence += 4
    elif backtests >= 2:
        confidence += 2

    if trend == "improving":
        confidence += 5
    elif trend == "declining":
        confidence -= 5

    return max(0, min(100, round(confidence)))
