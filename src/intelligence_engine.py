"""Zentraler GUI-unabhaengiger Orchestrator fuer TradeMind AI."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ai_narrative import build_market_report

try:
    from agent_runtime import AgentRuntime
except ImportError:
    AgentRuntime = None


INTELLIGENCE_ENGINE_VERSION = "1.0"


def build_intelligence_report(
    advisor_result: dict[str, Any],
    experience_summary: dict[str, Any],
    confidence,
    agent_runtime: AgentRuntime | None = None,
    context=None,
) -> dict[str, Any]:
    """Buendelt Advisor, Experience, Confidence und Market Report."""
    market_report = build_market_report(
        advisor_result,
        experience_summary,
        confidence,
    )
    agent_results = {}
    if agent_runtime is not None:
        agent_results = agent_runtime.run_all(context)

    return {
        "advisor": advisor_result,
        "experience": experience_summary,
        "confidence": confidence,
        "market_report": market_report,
        "agents": agent_results,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "version": INTELLIGENCE_ENGINE_VERSION,
    }
