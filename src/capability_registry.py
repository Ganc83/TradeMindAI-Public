"""Central registry for agent capabilities.

This module is GUI-independent and contains no domain-specific logic.
"""


class CapabilityRegistry:
    """Manage available capabilities declared by registered agents."""

    def __init__(self):
        self._agents = {}

    def register(self, agent):
        """Register an agent by its declared name."""
        self._agents[agent.name] = agent

    def unregister(self, agent_name):
        """Remove an agent from the registry by name."""
        self._agents.pop(agent_name, None)

    def get_all_capabilities(self):
        """Return all unique capabilities declared by registered agents."""
        capabilities = set()
        for agent in self._agents.values():
            capabilities.update(agent.get_capabilities())
        return sorted(capabilities)

    def get_agents_for_capability(self, capability):
        """Return agent metadata for agents declaring the capability."""
        return [
            agent.get_metadata()
            for agent in self._agents.values()
            if capability in agent.get_capabilities()
        ]

    def get_capability_summary(self):
        """Return a mapping of capabilities to agent names."""
        summary = {}
        for capability in self.get_all_capabilities():
            summary[capability] = [
                agent.name
                for agent in self._agents.values()
                if capability in agent.get_capabilities()
            ]
        return summary
