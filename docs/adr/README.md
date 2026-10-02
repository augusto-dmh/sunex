# Architecture decision records

Durable decisions for Sunex, one file each, in [MADR 4.0](https://adr.github.io/madr/) form
([ADR-0001](0001-record-architecture-decisions.md)). Copy [the template](0000-template.md) for a new
one. An accepted decision is never edited to say something else: a new ADR supersedes it.

Cycle-level choices (a library for one row, a naming detail) are `AD-NNN` rows in
[STATE.md](../../.specs/project/STATE.md); the design detail is in
[TDD-0001](../tdd/0001-v1-architecture.md).

| ADR | Decision | Status |
|---|---|---|
| [ADR-0001](0001-record-architecture-decisions.md) | Record architecture decisions as MADR files in the repository | accepted |
| [ADR-0002](0002-laravel-13-php-84-postgresql.md) | Build on Laravel 13, PHP 8.4 and PostgreSQL 17 with pgvector | accepted |
| [ADR-0003](0003-inertia-vue-typescript-frontend.md) | Build the UI with Inertia 3, Vue 3 and TypeScript | accepted |
| [ADR-0004](0004-domain-namespaces-with-architecture-tests.md) | Split the code into domain namespaces enforced by Pest architecture tests | accepted |
| [ADR-0005](0005-bitemporal-employment-versions.md) | Make employment versions bitemporal, and only them | accepted |
| [ADR-0006](0006-permission-model-roles-reach-field-groups.md) | One policy function with roles, reach as of a date, and field groups | accepted |
| [ADR-0007](0007-agents-as-principals-one-toolset.md) | Agents are principals with an owner, a sponsor, a mode and a per-call audit, sharing one toolset | accepted |
| [ADR-0008](0008-agent-runtime-laravel-ai-and-mcp.md) | Run agents in-process on laravel/ai and laravel/mcp; Agno evaluated and deferred | accepted |
| [ADR-0009](0009-no-payroll-no-esocial-transmission.md) | No payroll and no eSocial transmission; Sunex is the structured source, via signed events and eSocial-shaped CSV | accepted |
| [ADR-0010](0010-transactional-outbox-signed-webhooks.md) | Deliver lifecycle events through a transactional outbox with HMAC-signed webhooks | accepted |
| [ADR-0011](0011-multi-company-single-installation.md) | Several companies as data in one installation, no SaaS tenancy | accepted |
| [ADR-0012](0012-english-ui-copy-behind-translation-keys.md) | Write UI copy in English behind translation keys; add pt-BR later | accepted |
| [ADR-0013](0013-delivery-process-ship-cycle.md) | Deliver every roadmap row through a ship cycle with fresh-context review | accepted |
| [ADR-0014](0014-agpl-license-public-repository.md) | License Sunex under AGPL-3.0-only and develop it in public | accepted |
