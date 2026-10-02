# Sunex project guide

Sunex is an open-source (AGPL-3.0-only) people-management application for Brazilian companies:
a bitemporal employment record, movements with approvals, férias and afastamentos checked against
the CLT, eSocial-shaped signed events for the payroll system, and AI agents that act as audited
principals. Read `docs/brief.md` for the vision, values and no-gos before any product change.

This section is Sunex's own guidance. Laravel Boost renders it into `AGENTS.md` and `CLAUDE.md`
from `.ai/guidelines/sunex.md`; edit that file, never the generated ones (see "Maintaining this
guide").

## Current status

- Pre-alpha. `main` holds the Laravel 13 Vue starter-kit scaffold plus the foundation documents.
- v1 is designed in `docs/tdd/0001-v1-architecture.md` (phases 0–11) and cut into PR-sized rows in
  `.specs/project/ROADMAP.md`. The next rows are in the Handoff section of `.specs/project/STATE.md`.
- No roadmap row may start before the rows it depends on are merged.

## Working in this repo

- Local database: PostgreSQL 17 with pgvector on host port **54329** (`docker run … pgvector/pgvector:pg17`,
  see README); row `postgres-platform` replaces it with a Compose file. Tests always run on
  PostgreSQL, never SQLite: range types, exclusion constraints and pgvector are part of the design.
- Commands: `composer setup` (install, key, migrate, build), `composer dev` (server, queue, logs,
  Vite), `composer test` (lint check, type check, Pest). Run the gates before every push.
- Use the Boost MCP tools: `search-docs` before using any Laravel 13, Inertia 3, Pest 5,
  `laravel/ai` or `laravel/mcp` API; `database-schema` before writing a migration.
- Parallel rows run in separate git worktrees under `.worktrees/`, one branch and one agent per
  row. Only edit the files your row owns.
- Business dates are `date` in the employer's calendar; ranges are inclusive in the domain and
  stored half-open. Recorded time comes from the injected `Clock`, so tests travel in time with it.

## Durable decisions (ADRs in `docs/adr/`; do not reopen them inside a feature PR)

- Laravel 13, PHP 8.4, PostgreSQL 17 + pgvector, Inertia 3 + Vue 3 + TypeScript (ADR-0002, 0003).
- Bounded contexts under `app/Domain/{Shared,Organization,People,Movements,Absence,Agents}`;
  other contexts are used only through their `Contracts` and `Events`; Pest arch tests enforce
  the dependency table in `ARCHITECTURE.md` (ADR-0004).
- Only employment versions are bitemporal (`valid_period` + `recorded_period`, exclusion
  constraint, append-only trigger); corrections are new rows; everything else is effective-dated
  plus the audit log (ADR-0005).
- One policy function, `Shared\Access\Authorizer::decide(principal, capability, subject, asOf)`:
  roles grant capabilities, reach is evaluated as of a date, field groups mask attributes on the
  server. Never check role names; never send a masked field to the browser or a tool (ADR-0006).
- Agents are principals with owner, sponsor, mode and scopes. In-app agents and MCP clients share
  one set of tool classes that go through the `AgentToolGateway`, which writes the audit row in
  the same transaction as the domain change. No agent approves or changes data without a human
  approval in v1 (ADR-0007, 0008).
- No payroll, no eSocial XML, no transmission. Lifecycle facts leave through the transactional
  outbox as HMAC-signed webhooks and eSocial-shaped CSV (ADR-0009, 0010).
- Several companies (CNPJs) in one installation; company-owned rows carry `company_id` (ADR-0011).
- UI copy in English behind translation keys (`lang/en/<context>.php`); pt-BR is a later row
  (ADR-0012).
- CLT rules cite their rule id and article (`// F-12, CLT art. 134 §1`) and are tested with
  datasets copied from `docs/compliance/clt-rules.md`. eSocial categories 101 and 103 only in v1.

## Workflow

- Every roadmap row runs the ship cycle (ADR-0013): spec-driven plan and build with an
  independent verifier, PR, review in a fresh context, triage of every finding, fixes, comment
  cleanup, gated merge (automatic only when the report is clean).
- Decisions taken inside a cycle are recorded as `AD-NNN` rows in `.specs/project/STATE.md` with
  the options, why yes and why not for each, and the choice. A decision that changes an ADR needs
  a new ADR that supersedes it.
- Every behaviour ships with its test in the same PR. New models come with factories; demo-facing
  models with seeders.
- Planning artifacts for a row live in `.specs/features/<row>/`.

## Progressive documentation loading

Read only what the task needs:

- Orientation: this guide, then `ARCHITECTURE.md`.
- Product intent and no-gos: `docs/brief.md`.
- Design of the part you are touching: the matching section of `docs/tdd/0001-v1-architecture.md`.
- Why something is the way it is: the relevant file in `docs/adr/` (index in `docs/adr/README.md`).
- What to build next and what can run in parallel: `.specs/project/ROADMAP.md`, then the Handoff
  in `.specs/project/STATE.md`.
- CLT and eSocial rules: `docs/compliance/clt-rules.md` (once row `clt-rulebook` lands).
- Contributor rules for humans: `CONTRIBUTING.md`; vulnerabilities: `SECURITY.md`.

## Conventions

- English for code, identifiers, docs, ADRs, commits and PRs. Brazilian legal terms (férias,
  afastamento, período aquisitivo, CLT, eSocial, CNPJ, CPF) stay in Portuguese and are glossed on
  first use.
- Never copy code, schema or text from any employer's system, and never name the author's
  employer in code, docs, commits, branches or PRs. Ideas only.
- Health data minimization: store an afastamento's eSocial motive code and dates, never a
  diagnosis or CID code.

## Commits and pull requests

- Never commit to `main`. Branch from an up-to-date `main` as `<type>/<slug>`.
- Conventional Commits in English: `type(scope): lowercase imperative summary`, header ≤ 72
  characters, a body that explains why. Types: build chore ci docs feat fix perf refactor revert
  style test. One concern per commit.
- AI assistance is disclosed with exactly one trailer: `Assisted-by: Claude Code` (or the tool
  used). Never `Co-Authored-By` for a tool, never "Generated with", never a session link.
- PR title follows the commit rule. PR body in English with the sections Description, Context,
  Architecture, Main changes, Decisions, Tests, Configuration, Dependencies, Impact, How to
  validate, Checklist, AI assistance (what the agent wrote, what a human reviewed). No internal
  task or decision numbers in commits or PR bodies; link ADRs, TDD sections and roadmap rows.
- Do not merge your own PR outside the ship cycle's gate; never force-push `main`.

## Maintaining this guide

`AGENTS.md` and `CLAUDE.md` are generated by Laravel Boost and rewritten by `boost:install` and
`boost:update`. Change `.ai/guidelines/sunex.md`, run `php artisan boost:update`, and commit the
regenerated files with `git add -f AGENTS.md CLAUDE.md` (the scaffold's `.gitignore` lists them).
Boost only loads when `APP_ENV=local` or debug is on; in a checkout without `.env`, run
`APP_ENV=local php artisan boost:update`. Text outside the `<laravel-boost-guidelines>` block
survives regeneration, but keep guidance in `.ai/guidelines/` so there is one source.
