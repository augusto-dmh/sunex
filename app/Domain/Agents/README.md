# Agents

Owns AI agents as accountable principals: the registry (owner, sponsor, mode, scopes), the
tool gateway and the tool classes that in-app agents and the MCP server share, the audit row
written for every tool call in the same transaction as its change, the `AgentRuntime` port,
the v1 agents and their knowledge base. Tools call the other contexts' contracts instead of
reimplementing their rules.

May depend on: Absence, Movements, People, Organization, Shared.
