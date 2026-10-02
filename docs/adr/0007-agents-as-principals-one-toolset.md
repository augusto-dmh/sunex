---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
---

# ADR-0007: Agents are principals with an owner, a sponsor, a mode and a per-call audit, sharing one toolset

## Context and Problem Statement

Sunex v1 ships two AI agents (a policy and férias-balance Q&A agent, and an agent that drafts férias
requests) and exposes the same capabilities to external assistants such as Claude or ChatGPT
through an MCP server. These agents read personal data (salaries, CPF, absences) and start changes
that affect pay. The product values say "one door for everyone": an agent never sees or does what
its sponsor could not ([brief](../brief.md), value 2).

Two questions follow. **Who is the agent** when it calls a tool: a shared service account, the user
in disguise, or an identity of its own? And **where does a tool live**: one implementation per
channel (in-app agent, MCP client) or one shared implementation?

## Decision Drivers

- Every action must be attributable to an accountable human and to the agent that took it.
- The same policy function decides for humans, in-app agents and MCP clients
  ([ADR-0006](0006-permission-model-roles-reach-field-groups.md)); no second permission model.
- Agent access must follow the employee lifecycle Sunex already owns (a sponsor who leaves must not
  leave a working agent behind).
- One implementation per capability, so the in-app path and the MCP path cannot drift apart.
- v1 no-go: no agent action changes data without a human approval.
- The audit trail must survive SDK limitations: `laravel/ai` stores tool results only when a turn
  completes, and agent middleware no longer wraps tool execution
  ([ADR-0008](0008-agent-runtime-laravel-ai-and-mcp.md)).

## Considered Options

1. A shared service account or API key per integration.
2. The agent impersonates the invoking user and has no identity of its own.
3. The agent is a principal: a registry row with owner, sponsor, mode, scopes, status and a
   per-call audit.

Sub-decision on tools:

- A. Separate tool implementations for in-app agents and for the MCP server.
- B. One toolset: one `Laravel\Mcp\Server\Tool` class per capability, used by both channels through
  one gateway.

## Decision Outcome

Chosen: **option 3 with sub-option B**. It is the only combination where the actor is identifiable,
its rights are bounded by a human's, and the rule is enforced once.

**Agent registry** (`agents`, owned by the Agents context):

| Field | Meaning |
|---|---|
| `name`, `kind` | Display name; `in_app` (runs inside Sunex on `laravel/ai`) or `mcp_client` (an external assistant) |
| `company_id` | Company scope; an agent never acts outside its company ([ADR-0011](0011-multi-company-single-installation.md)) |
| `owner_user_id` | The administrator accountable for the agent's existence and configuration |
| `sponsor_user_id` | The human accountable for its actions; required, never null |
| `mode` | `on_behalf_of`: acts for the user who invoked it; `autonomous`: acts with its own grants, bounded by the sponsor's rights |
| `scopes` | Capabilities from ADR-0006 the agent may use (for example `employees.view`, `absence.request`); approval capabilities are human-only and can never be scopes |
| `status` | `pending` (an MCP client that registered itself and has no owner, sponsor or scopes yet), `active`, `suspended` or `revoked`; only `active` agents pass the gateway |
| credential | MCP clients: a Passport OAuth client issuing short-lived tokens; in-app agents have none (they run in-process) |
| `created_at`, `credential_rotated_at` | Lifecycle evidence |

**Effective rights** = the agent's scopes ∩ the rights of the human it acts for (the invoking user
in `on_behalf_of` mode, the sponsor in `autonomous` mode), evaluated **as of a date** by the same
`Authorizer::decide()` that humans use. Field-group masking applies to the intersection too.

**Lifecycle tied to employment.** When a termination movement is applied to the sponsor's
employment, the Agents context listens to the domain event and suspends every agent that person
sponsors until an administrator transfers sponsorship. No orphaned agents.

**One toolset, one gateway.** Each capability is one `Laravel\Mcp\Server\Tool` class. In-app agents
return the same classes from `tools()`, filtered by scopes; the MCP server registers them. Each
tool's `handle()` only builds input and calls `AgentToolGateway`, which runs:

1. resolve the `AgentPrincipal` from the container (set by MCP middleware or by the run
   orchestrator, never from `$request->user()` alone, which differs between the two paths);
2. authorize through `Authorizer::decide()`;
3. open a database transaction;
4. call the domain action through the owning context's contract;
5. mask the output by field groups;
6. write one `agent_tool_calls` row: run id (SDK invocation id or MCP request id), agent, acting
   user, sponsor, tool, SHA-256 of the canonical input, redacted input, policy decision and reason,
   approval request id, before/after diff, result status;
7. commit.

Denied calls are audited too, in their own transaction. Filtering the tool list per agent
(`withTools`, `shouldRegister`, searchable catalogs) is a convenience for the model's context
window, never the enforcement: **a search result is never a capability grant**.

**Human approval in v1.** Agents never hold an approve capability. Write tools create drafts or
submit requests (for example a férias request in `submitted`), which a human approves in the domain
workflow. The audit row links that approval's id.

### Consequences

- Good, because every row in `agent_tool_calls` answers who acted, for whom, under which policy
  decision, and what changed, and the row exists if and only if the change committed.
- Good, because the in-app path and the MCP path cannot diverge: a parity test calls the same tool
  through both and compares decisions and audit rows.
- Good, because agent access shrinks automatically when the human's access shrinks (role change,
  transfer, termination), since rights are computed as of a date from the same data.
- Good, because the design matches what identity vendors converged on in 2026, which makes it
  legible to reviewers.
- Bad, because every tool call pays for a policy evaluation and an audit insert; acceptable next to
  model latency, but reach sets must be cached per request.
- Bad, because the gateway replaces two framework conveniences (`shouldRegister` as enforcement and
  `$request->user()`), so contributors must learn the principal context.
- Neutral, because in-app agents still need a registry row even though they have no credential.

### Confirmation

- Pest architecture test: classes under `App\Domain\Agents\Tools` extend `Laravel\Mcp\Server\Tool`
  and use no Eloquent model from another context; they depend only on the gateway and contracts.
- Feature tests: denied call writes an audit row and returns no data; a failed domain write rolls
  back its audit row; a suspended agent is refused; terminating a sponsor suspends their agents;
  masked fields are absent from tool output.
- Parity test: the same tool through an in-app agent (`Agent::fake()`) and through the MCP server
  test client produces the same decision and an equivalent audit row.

## Pros and Cons of the Options

### 1. Shared service account or API key

- Good, because it is the least work and every SDK supports it.
- Bad, because the actor is "the integration", not a person; audit rows cannot answer "for whom".
- Bad, because a service account's rights are not bounded by any human's, which breaks value 2.
- Bad, because revocation is all-or-nothing and nothing ties it to an employee leaving.

### 2. Agent impersonates the user

- Good, because rights are naturally bounded by the user's ("every request runs as you", as
  BambooHR's AI connector puts it).
- Bad, because the audit cannot tell what the person did from what the agent did on their behalf.
- Bad, because the agent cannot be restricted below the user's rights (no scopes) and cannot be
  suspended without suspending the user.
- Bad, because autonomous work (no invoking user) has no identity at all.

### 3. Agent as principal (chosen)

- Good, because it separates identity (the agent), accountability (owner, sponsor) and authority
  (scopes ∩ human rights), exactly the split identity vendors ship.
- Good, because status and credential rotation allow a kill switch per agent.
- Bad, because it adds a registry, a principal type and an administration screen to v1.

### A. Separate tool implementations per channel

- Good, because each channel can use its framework's idioms freely.
- Bad, because policy, masking and audit are implemented twice and drift; one bug becomes a data
  leak on only one path, which tests rarely cover.

### B. One shared toolset through one gateway (chosen)

- Good, because `laravel/ai` wraps `Laravel\Mcp\Server\Tool` classes natively, so the reuse is
  first-party rather than an adapter of ours.
- Bad, because the internal path skips `shouldRegister` and resolves users differently, so the
  gateway must own principal resolution.

## More Information

Evidence (research on agent identity and HR agents, read 2026-09-30):

- Microsoft Entra Agent ID: owners, sponsors and managers as administrative relationships;
  on-behalf-of vs autonomous access packages; automatic sponsorship transfer "to prevent orphaned
  agents" — [Microsoft Learn](https://learn.microsoft.com/en-us/entra/agent-id/whats-new-agent-id).
- Okta for AI Agents (GA 2026-04-30): agents as first-class identities, gateway, kill switch,
  credential rotation — [Okta](https://www.okta.com/newsroom/press-releases/showcase-2026/);
  Auth0 "Agent as Principal", distinct from the users it serves so actions are independently
  permissioned and audited — [Okta newsroom](https://www.okta.com/newsroom/articles/auth0-may-2026-product-innovations/).
- Workday Agent System of Record: who owns each agent, its role, its cost and its interactions with
  data — [Workday blog](https://blog.workday.com/en-us/managing-ai-powered-future-of-work.html).
- Rippling: agent identities with owners and a delegated-or-own identity mode; "Before a tool call
  runs, Rippling checks who is making the request and whether the relevant policy allows it. The
  call is then recorded for review" — [Rippling](https://www.rippling.com/blog/introducing-rippling-ai-governance).
- Salesforce: identity propagation enforced at the gateway layer, giving user-attributable audit
  trails — [Salesforce Architects](https://architect.salesforce.com/docs/architect/fundamentals/guide/end-user-identity-propagation).
- Laravel MCP 1.0: searchable catalogs; "Conditional registration is re-checked at execution, not
  just at search, so a search result is never a capability grant" —
  [Laravel blog, 2026-09-11](https://laravel.com/blog/a-better-way-to-build-mcp-servers-with-laravel).
- Audit-log schema guidance (vendor blogs): sponsor, agent, tool call, policy decision, approval
  status, resource diff, correlation ids — [Permit.io](https://www.permit.io/blog/govern-ai-agents-cloud-api-control-planes-mcp),
  [CubeAPM](https://cubeapm.com/blog/mcp-server-security-monitoring-audit-logs-compliance/).
- Human final say in HR products: "AI cannot submit reviews independently" —
  [Lattice](https://lattice.com/blog/lattice-spring-summer-2026-product-release); BambooHR's AI
  connector "Every request runs as you" — [BambooHR docs](https://documentation.bamboohr.com/docs/bamboohr-and-ai).

Related: [ADR-0006](0006-permission-model-roles-reach-field-groups.md) (the policy function),
[ADR-0008](0008-agent-runtime-laravel-ai-and-mcp.md) (runtime, MCP OAuth and audience check),
[ADR-0010](0010-transactional-outbox-signed-webhooks.md) (events the approved changes emit),
[TDD-0001](../tdd/0001-v1-architecture.md) (tables and phases).

**What would reverse or amend this decision:** a first-party Laravel or MCP standard for agent
identity and per-call audit that covers owner, sponsor and mode (adopt it behind the gateway);
`laravel/ai` restoring a run-level middleware that wraps tool execution and persisting steps
transactionally (the audit could move there, the principal model stays); a later decision to let
autonomous agents write without approval, which needs its own ADR.
