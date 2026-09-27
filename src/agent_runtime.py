"""Runtime registry and executor for TradeMind agents."""


class AgentRuntime:
    """Manage and execute registered agents."""

    def __init__(self):
        self._agents = {}

    def register(self, agent):
        """Register an agent by its unique name."""
        agent_name = getattr(agent, "name", None)
        if not agent_name:
            raise ValueError("Agent must define a non-empty name.")

        self._agents[agent_name] = agent

    def unregister(self, agent_name):
        """Remove an agent from the runtime by name."""
        self._agents.pop(agent_name, None)

    def get_agents(self):
        """Return all currently registered agents."""
        return list(self._agents.values())

    def run_all(self, context):
        """Run all enabled agents that can run for the supplied context."""
        runnable_agents = [
            agent
            for agent in self._agents.values()
            if getattr(agent, "enabled", False) and agent.can_run(context)
        ]
        runnable_agents.sort(key=lambda agent: getattr(agent, "priority", 100))

        results = {}
        for agent in runnable_agents:
            results[agent.name] = agent.run(context)

        return results
