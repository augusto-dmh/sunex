---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
---

# ADR-0008: Run agents in-process on laravel/ai and laravel/mcp; Agno evaluated and deferred

## Context and Problem Statement

[ADR-0007](0007-agents-as-principals-one-toolset.md) fixes *what* an agent is in Sunex: a principal
whose tool calls pass one gateway that authorizes, masks, calls the domain and writes the audit row
inside the domain transaction. This ADR decides *what runs the agent loop* (model calls, tool
calling, streaming, conversation memory, human tool approval, retrieval) and how external
assistants reach the same tools over MCP.

The candidates in September 2026 are the first-party Laravel packages, a Python sidecar on Agno,
a hybrid of both, and other PHP agent libraries. `laravel/ai` reached 1.0 on 2026-09-23 and
`laravel/mcp` 1.0 on 2026-09-14, so both are a week or two old.

## Decision Drivers

- The policy, masking, approval and audit design already lives in Laravel; the runtime must not
  force it to be duplicated.
- Both v1 agents must be covered: retrieval with citations over pgvector (read path) and drafting a
  férias request that a human approves (write path).
- One runtime, one CI pipeline, one deploy for a solo project with a 12-week appetite.
- Testability in one suite: fakes for models, pending approvals and MCP calls.
- Churn and security risk of each dependency.
- Portfolio legibility for Laravel reviewers.

## Considered Options

- **A.** `laravel/ai` 1.x + `laravel/mcp` 1.x in-process, behind an `AgentRuntime` port.
- **B.** An Agno (Python) sidecar called by Laravel, with three tool placements: B1 tools in Python
  querying Postgres directly; B2 Python tools calling a Laravel internal REST API; B3 Agno
  `MCPTools` pointed at Sunex's MCP server.
- **C.** Hybrid: Laravel owns tools, policy, audit and the MCP server; an Agno worker takes chosen
  workloads later by consuming the MCP server.
- **D.** Another PHP runtime: Prism, Neuron AI or LarAgent.

## Decision Outcome

Chosen: **A**, with a documented seam towards **C**. The agent loop is the commodity part; the hard
part (principal, policy as of a date, field groups, audit, domain approval) has to live in Laravel
under every option, and `laravel/ai` 1.0 covers both v1 agents natively.

The design answers the known gaps of the 1.0 packages explicitly:

| Gap (public issue or spec) | Design answer |
|---|---|
| `laravel/ai` #981: tool results persisted only at turn completion; #1060: agent middleware no longer wraps tool execution | The audit row is written by the gateway inside the shared tool's database transaction, never derived from the conversation store or SDK middleware |
| MCP spec 2026-07-28: servers MUST validate that tokens were issued for them (RFC 8707); Passport has no audience check | One `EnsureTokenAudience` middleware on the MCP route rejects tokens whose client was not registered for this resource |
| `laravel/mcp` OAuth uses a single `mcp:use` scope; custom Passport scopes are not supported | `mcp:use` only gates entry; real scopes come from the agent registry and the permission model ([ADR-0006](0006-permission-model-roles-reach-field-groups.md)) |
| Structured output can silently return `[]` (#1062 Anthropic, #1068 and #1018 Gemini; #189 validation open) | Every structured response is validated against its schema; an empty or invalid result is an error (retry once, then abstain) |
| `continue` / `continueOrStart` do not verify that the participant owns the conversation | Conversation ownership is checked against the principal before resuming |
| No tracing, no Nightwatch AI view | An `agent_runs` table filled from SDK events (`InvokingTool`, `ToolInvoked`, `StepCompleted`, `AgentFailed`) with `TextUsage` |
| SDK tool approval pauses the conversation, not the business process | SDK `Approvable` is used only for the chat user's "submit this draft?" confirmation; the manager's approval is the domain workflow, shared by UI, agents and MCP, and its id is what the audit row links |

The `AgentRuntime` port exposes `prompt`, `stream`, `queue` and `resume`; `LaravelAiRuntime` is the
only adapter in v1. MCP access uses Passport OAuth 2.1 through `Mcp::oauthRoutes()`, a middleware
that maps the Passport client to the agent registry row and the token user to the acting user, and
the audience middleware above.

### Consequences

- Good, because policy, masking, the domain write and the audit row share one process and one
  Postgres transaction.
- Good, because `laravel/ai` wraps `Laravel\Mcp\Server\Tool` classes natively, so one tool class
  serves in-app agents and MCP clients ([ADR-0007](0007-agents-as-principals-one-toolset.md)).
- Good, because tests stay in one Pest suite: `Agent::fake()`, `preventStrayPrompts()`,
  `AgentResponse::fakeWithPendingApprovals()`, MCP test responses, and Pest 5 evals.
- Good, because there is one deploy, one CI and one migration tool.
- Bad, because both packages are one to three weeks past 1.0 after 50 pre-1.0 releases with
  breaking upgrades; pin minor versions and re-run the agent suite on every bump.
- Bad, because observability and the audience check are ours to build and maintain.
- Neutral, because hybrid lexical plus vector search is not an SDK feature; v1 uses vector search
  with `whereVectorSimilarTo` and adds Postgres full-text search only if evals demand it.

### Confirmation

- Pest architecture test: only `App\Domain\Agents\Runtime` imports `Laravel\Ai\*` agent classes;
  the rest of the code depends on the `AgentRuntime` port.
- Feature tests: a token issued for another resource is rejected by the MCP route; an empty
  structured response is treated as an error; resuming another user's conversation is refused;
  every run writes an `agent_runs` row with usage.
- The audit tests from ADR-0007 pass on both paths.

## Pros and Cons of the Options

### A. laravel/ai + laravel/mcp in-process (chosen)

- Good, because it has approvable tools (approve, reject, edit), conversations owned by any
  Eloquent model, pgvector querying, `SimilaritySearch`, reranking, failover, unified usage and 37
  events, all in 1.0.
- Good, because Laravel's own products use both packages in production.
- Bad, because there is no workflow or graph engine and no per-run middleware.
- Bad, because of the open issues listed above.

### B. Agno sidecar

- Good, because Agno is mature and broad: workflows with human-in-the-loop at every step type,
  persisted approvals, OpenTelemetry tracing, an eval catalogue (Apache-2.0, release 3.0.11).
- Bad, because of the tool-placement trilemma: **B1** re-implements reach, field groups and masking
  in Python (violates one toolset); **B2** duplicates the contract in Pydantic and splits paused-run
  state from the domain approval; **B3** is clean but leaves Agno as a loop around Sunex's MCP
  server, which `laravel/ai` already provides.
- Bad, because a second runtime, CI, deploy, migration tool, auth bridge and run-id correlation
  roughly double the maintenance surface.
- Bad, because of churn and risk: breaking changes in patch releases (3.0.5, 3.0.7, 3.0.10), a
  manual v3 database migration with open bugs, pause-and-resume bugs on exactly the draft-and-approve
  path (#9448 double execution on concurrent continue), three CVEs in about ten months, and audit
  logs and end-user identity on the paid enterprise tier.

### C. Hybrid later

- Good, because it keeps every v1 benefit of A and lets a workload that truly needs durable
  workflows move later, with Agno consuming the MCP server and never touching the database.
- Bad, because it pays B's operating cost as soon as one workload moves. Not needed for v1.

### D. Other PHP runtimes

- Prism: pre-1.0, quiet upstream since March 2026, no vector store, approvals or MCP server; it is
  the layer `laravel/ai` dropped.
- Neuron AI: the strongest alternative (approval middleware, resumable workflows, observability),
  but no pgvector store, no MCP server, and 4.0 shipped on 2026-09-30.
- LarAgent: slowed down, no documented fakes, approvals left to the app.

## More Information

Sources (read 2026-09-30):

- `laravel/ai`: [releases](https://github.com/laravel/ai/releases),
  [UPGRADE.md](https://github.com/laravel/ai/blob/1.x/UPGRADE.md),
  [composer.json](https://github.com/laravel/ai/blob/1.x/composer.json),
  [docs 13.x](https://laravel.com/docs/13.x/ai-sdk),
  [v1.0 announcement](https://laravel.com/blog/introducing-laravel-ai-sdk-v1),
  [open issues](https://github.com/laravel/ai/issues) (#981, #1060, #1062, #1068, #1018, #189, #133).
- `laravel/mcp`: [releases](https://github.com/laravel/mcp/releases),
  [docs 13.x](https://laravel.com/docs/13.x/mcp),
  [searchable catalogs post](https://laravel.com/blog/a-better-way-to-build-mcp-servers-with-laravel);
  [MCP authorization spec 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization).
- Laravel products using the SDK and MCP:
  [Laravel blog, 2026-03-04](https://laravel.com/blog/laravel-ai-sdk-boost-or-mcp-which-tool-do-you-need).
- Pest 5 evals: [pest5-now-available](https://pestphp.com/docs/pest5-now-available),
  [v5.0.0](https://github.com/pestphp/pest/releases/tag/v5.0.0).
- Agno: [releases](https://github.com/agno-agi/agno/releases), [PyPI](https://pypi.org/pypi/agno/json),
  [pricing](https://www.agno.com/pricing), [approval docs](https://docs.agno.com/hitl/approval.md),
  [workflow HITL](https://docs.agno.com/workflows/hitl/overview.md),
  [v3 migration](https://docs.agno.com/other/v3-migration.md),
  [security advisories](https://github.com/agno-agi/agno/security/advisories),
  [issues](https://github.com/agno-agi/agno/issues).
- PHP alternatives: [Prism](https://github.com/prism-php/prism),
  [Neuron AI 4.0.0](https://github.com/neuron-core/neuron-ai/releases/tag/4.0.0),
  [Neuron vector stores](https://docs.neuron-ai.dev/rag/vector-store.md),
  [LarAgent](https://github.com/maestroerror/laragent).

Related: [ADR-0002](0002-laravel-13-php-84-postgresql.md), [ADR-0006](0006-permission-model-roles-reach-field-groups.md),
[ADR-0007](0007-agents-as-principals-one-toolset.md), [TDD-0001](../tdd/0001-v1-architecture.md).

**Conditions that would move to C** (an Agno worker behind the MCP server, never on the database):
a later workload, such as meeting-transcript intake or an autonomous admission-readiness agent,
needs durable multi-step workflows that pause and resume across days, and neither queued SDK steps
with a state machine nor a first-party Laravel workflow feature is good enough after a spike; or
evaluation needs outgrow Pest 5 evals and are cheaper in Python.

**Conditions that would move back from A** (towards Neuron AI or a sidecar): `laravel/ai` 1.x
regresses badly (data loss in the conversation store, an approval-resume bug unfixed for a month),
or #981 and #1060 stay open *and* the gateway workaround proves insufficient.

**What strengthens A:** `laravel/ai` closing #981 and #1060; Passport or `laravel/mcp` adding RFC
8707 audience binding and per-tool scopes; Nightwatch adding AI-run tracing.
