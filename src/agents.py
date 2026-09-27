"""Central definitions for future AI agents.

This module is intentionally GUI-independent and contains only architectural
foundations for later extensions.
"""


class BaseAgent:
    """Base class for all future agents."""

    name = "BaseAgent"
    version = "0.1.0"
    description = "Base class for future AI agents."
    enabled = True
    priority = 100
    capabilities = []

    def can_run(self, context):
        """Return whether the agent can run for the supplied context."""
        return True

    def get_metadata(self):
        """Return metadata used by the intelligence engine."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "priority": self.priority,
            "enabled": self.enabled,
            "capabilities": self.get_capabilities(),
        }

    def get_capabilities(self):
        """Return the capabilities declared by this agent."""
        return self.capabilities

    def run(self, context):
        """Run the agent with the supplied context.

        Specializations may override this method with concrete behavior.
        """
        raise NotImplementedError("Agent implementations must override run().")


class AdvisorAgent(BaseAgent):
    capabilities = [
        "analysis",
        "strategy_evaluation",
        "recommendation",
    ]


class MemoryAgent(BaseAgent):
    capabilities = [
        "memory",
        "experience",
        "trend_analysis",
    ]


class NarrativeAgent(BaseAgent):
    capabilities = [
        "report",
        "summary",
        "explanation",
    ]


class StrategistAgent(BaseAgent):
    capabilities = [
        "prioritization",
        "decision_support",
    ]


class OpportunityAgent(BaseAgent):
    name = "OpportunityAgent"
    version = "1.0"
    description = "Detects and ranks potential trading opportunities."
    enabled = True
    priority = 40
    capabilities = [
        "market_scan",
        "opportunity_detection",
        "ranking",
    ]

    def run(self, context):
        return {
            "status": "ready",
            "message": "OpportunityAgent is ready for future market scanning.",
            "opportunities": [],
        }
