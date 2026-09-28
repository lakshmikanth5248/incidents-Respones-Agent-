"""
Agent Tool Registry & Autonomous Action Prohibition.
Conforms strictly to PRD Part 1 §12.6 (FR-043), Part 3 §0.2 (NG-02, NG-03), and Feature 08.

Critical Invariant:
The agent recommends; the agent does NOT execute production actions.
There must be NO:
- kubectl
- rollback API
- delete production resource
- restart production service
- database mutation tool
in the agent tool registry.
"""

from typing import Dict, Any, List, Callable, Optional


PROHIBITED_TOOLS = {
    "kubectl",
    "rollback",
    "rollback_api",
    "delete_production_resource",
    "delete_resource",
    "restart_production_service",
    "restart_service",
    "database_mutation_tool",
    "db_mutation",
    "execute_command",
    "apply_fix",
}


class AutonomousActionProhibitedError(Exception):
    """Raised when an attempt is made to register or invoke a production execution action."""
    pass


class AgentTool:
    """Read-only or advisory tool accessible by the agent."""

    def __init__(
        self,
        name: str,
        description: str,
        func: Optional[Callable] = None,
        is_read_only: bool = True,
    ):
        name_clean = name.strip().lower()
        if name_clean in PROHIBITED_TOOLS:
            raise AutonomousActionProhibitedError(
                f"Prohibited tool '{name}' cannot be registered. Agent is strictly advisory and cannot execute production mutations."
            )
        if not is_read_only:
            raise AutonomousActionProhibitedError(
                f"Tool '{name}' cannot have is_read_only=False. Agent is strictly advisory and cannot execute production mutations."
            )
        self.name = name
        self.description = description
        self.func = func
        self.is_read_only = is_read_only


class ToolRegistry:
    """Registry managing advisory and diagnostic tools available to the reasoning agent."""

    def __init__(self):
        self._tools: Dict[str, AgentTool] = {}
        self._register_default_advisory_tools()

    def _register_default_advisory_tools(self):
        """Register safe, read-only diagnostic and retrieval tools."""
        self.register(AgentTool("recall_memory", "Query Hindsight for relevant prior operational experiences.", is_read_only=True))
        self.register(AgentTool("search_runbooks", "Search runbook reference set for matching procedures.", is_read_only=True))
        self.register(AgentTool("inspect_telemetry", "Read current metrics and telemetry facts.", is_read_only=True))
        self.register(AgentTool("read_logs", "Inspect log excerpts and error signatures.", is_read_only=True))
        self.register(AgentTool("generate_comparison", "Compare current evidence against historical experience.", is_read_only=True))
        self.register(AgentTool("generate_hypotheses", "Formulate candidate root-cause explanations.", is_read_only=True))
        self.register(AgentTool("generate_recommendations", "Formulate advisory investigation and resolution guidance.", is_read_only=True))

    def register(self, tool: AgentTool):
        """Register an advisory tool."""
        if tool.name.lower() in PROHIBITED_TOOLS or not tool.is_read_only:
            raise AutonomousActionProhibitedError(
                f"Tool '{tool.name}' is prohibited. Agent has no execution permissions."
            )
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[AgentTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "is_read_only": t.is_read_only,
            }
            for t in self._tools.values()
        ]

    def has_prohibited_tools(self) -> bool:
        """Verify that no prohibited mutation tools exist."""
        for name in self._tools.keys():
            if name.lower() in PROHIBITED_TOOLS:
                return True
        return False


# Global agent tool registry instance
agent_tool_registry = ToolRegistry()
