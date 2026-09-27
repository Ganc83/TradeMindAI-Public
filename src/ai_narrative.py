"""GUI-unabhaengige Berichtserstellung fuer TradeMind AI."""

from __future__ import annotations

from typing import Any


def build_market_report(
    advisor_result: dict[str, Any],
    experience_summary: dict[str, Any],
    confidence,
) -> str:
    """Erzeugt einen professionellen mehrzeiligen Analysebericht."""
    score = _to_float(advisor_result.get("score", 0.0))
    classification = str(advisor_result.get("classification", "UNKNOWN"))
    recommendation = str(advisor_result.get("recommendation", "")).strip()
    trades = int(_to_float(advisor_result.get("trades", 0)))
    pnl_pct = _to_float(advisor_result.get("pnl_pct", 0.0))
    winrate = _to_float(advisor_result.get("winrate", 0.0))
    profit_factor = _to_float(advisor_result.get("profit_factor", 0.0))
    max_drawdown = _to_float(advisor_result.get("max_drawdown", 0.0))

    backtests = int(_to_float(experience_summary.get("backtests", 0)))
    avg_score = _to_float(experience_summary.get("avg_score", 0.0))
    avg_profit_factor = _to_float(experience_summary.get("avg_profit_factor", 0.0))
    avg_winrate = _to_float(experience_summary.get("avg_winrate", 0.0))
    trend = str(experience_summary.get("trend", "stable"))
    confidence_value = int(round(_to_float(confidence)))

    if score >= 80:
        quality = "Die Backtest-Qualitaet ist stark und zeigt ein belastbares Setup."
    elif score >= 65:
        quality = "Die Backtest-Qualitaet ist solide, aber weitere Validierung bleibt sinnvoll."
    elif score >= 45:
        quality = "Die Backtest-Qualitaet ist gemischt und sollte vorsichtig interpretiert werden."
    else:
        quality = "Die Backtest-Qualitaet ist schwach und aktuell nicht belastbar."

    if pnl_pct > 0 and profit_factor >= 1.1:
        profitability = (
            f"Das Setup war profitabel mit {pnl_pct:+.2f}% PnL, "
            f"{winrate:.1f}% Winrate und einem Profit Factor von {profit_factor:.2f}."
        )
    elif pnl_pct > 0:
        profitability = (
            f"Das Setup schliesst positiv mit {pnl_pct:+.2f}% PnL, "
            f"der Profit Factor von {profit_factor:.2f} ist aber noch nicht stark."
        )
    else:
        profitability = (
            f"Das Setup war nicht profitabel ({pnl_pct:+.2f}% PnL) "
            f"und zeigt einen Profit Factor von {profit_factor:.2f}."
        )

    experience_hint = (
        f"Experience basiert auf {backtests} gespeicherten Backtests. "
        f"Der Durchschnitt liegt bei Score {avg_score:.1f}, "
        f"Profit Factor {avg_profit_factor:.2f} und Winrate {avg_winrate:.1f}%. "
        f"Der aktuelle Trend ist {trend}."
    )

    if recommendation:
        clear_recommendation = recommendation
    elif classification in ("EXCELLENT", "GOOD"):
        clear_recommendation = "Setup weiter beobachten und nur kontrolliert skalieren."
    elif classification == "NEUTRAL":
        clear_recommendation = "Setup optimieren und vor Einsatz erneut testen."
    else:
        clear_recommendation = "Setup aktuell nicht verwenden."

    if classification in ("EXCELLENT", "GOOD") and confidence_value >= 70:
        next_action = "Next Action: Setup auf weiteren Timeframes und Marktphasen gegenpruefen."
    elif classification == "NEUTRAL":
        next_action = "Next Action: Parameter optimieren und zusaetzliche Backtests sammeln."
    else:
        next_action = "Next Action: Risikoquellen analysieren und Setup erst nach Verbesserung erneut bewerten."

    return "\n".join(
        [
            "TRADEMIND AI MARKET REPORT",
            "",
            f"Backtest Quality: {quality}",
            f"Classification: {classification} | Score: {score:.0f}/100 | Trades: {trades}",
            f"Profitability: {profitability}",
            f"Risk: Max Drawdown lag bei {max_drawdown:.2f}%.",
            f"Experience: {experience_hint}",
            f"Confidence: {confidence_value}%",
            f"Recommendation: {clear_recommendation}",
            next_action,
        ]
    )


def _to_float(value) -> float:
    """Konvertiert numerische Eingaben defensiv zu float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
