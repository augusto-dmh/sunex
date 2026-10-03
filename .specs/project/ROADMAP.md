# ROADMAP

The design is [TDD-0001](../../docs/tdd/0001-v1-architecture.md); its phases (§18) are the
authority on *what* v1 contains. This file only cuts those phases into **rows**: one row is one
pull request, built by one ship cycle ([ADR-0013](../../docs/adr/0013-delivery-process-ship-cycle.md)),
small enough to review in one sitting. Do not copy TDD content here.

## How to read the table

- **Depends on**: rows that must be **merged** before this row starts.
- **Parallel-safe with**: rows that can be built **at the same time** in separate git worktrees,
  because neither depends on the other and they do not edit the same files (beyond appending a
  migration, a seeder call or a translation file of their own context).
- **Wave**: the earliest point a row can start if every earlier wave merges. Rows in one wave are
  normally parallel-safe with each other.
- **Size**: S ≈ under a day of focused work, M ≈ one to two days, L ≈ three days. No row is
  larger than L; when one grows, split it before starting.
- **Status**: Not started → In progress (`<branch>`) → In review (PR #) → Done (PR #).

Rules that keep parallel rows from colliding:

1. Row 06 defines the **whole v1 `Capability` enum** up front (the complete list in TDD §12.2), so later rows never
   edit that file.
2. Translation keys live in one file per context (`lang/en/<context>.php`), routes in one file
   per context (`routes/<context>.php`, loaded by row 02), so UI rows touch only their own files.
3. Each context's factories and seeders are its own classes; `DatabaseSeeder` only lists them.

## Phase 0: Foundation (in flight)

F2 grew while it was built: its pull request also delivers all of row 01 and the skeleton and
dependency-table tests of row 02, so those rows below describe only what remains.

| # | Row | Scope | Depends on | Parallel-safe with | Size | Status |
|---|---|---|---|---|---|---|
| F1 | `docs-foundation` | README, ARCHITECTURE, brief, TDD-0001, ADR 0000–0014, this roadmap, STATE, AGENTS/CLAUDE through Boost guidelines, license and policies | — | F2, F3 | L | Done (PR #2) |
| F2 | `quality-tooling` | Pint, Larastan level 9 (the scaffold's defects fixed, no baseline), Rector, Pest presets, one Composer script per gate (`lint`, `analyse`, `refactor-check`, `test`, `frontend-check`) plus `composer check`, one CI job per gate, the commit-message check in CI; also all of row 01 (PostgreSQL 17 + pgvector in `compose.yaml` on host port 54329, the `sunex_testing` database, the extensions migration and its test, Pest on PostgreSQL locally and in CI) and part of row 02 (the empty `app/Domain/*` contexts and arch tests for the ARCHITECTURE dependency table and the delivery-layer rule). The coverage gate moved to row 02 | — | F1, F3 | L | Done (PR #3) |
| F3 | `delivery-harness` | Ship-cycle skills, PR template, the commit and PR metadata validator the skills run (the CI commit-message check is in F2) | — | F1, F2 | M | Done (PR #1) |

## v1 rows

| # | Row | TDD phase | Scope | Depends on | Parallel-safe with | Wave | Size | Status |
|---|---|---|---|---|---|---|---|---|
| 01 | `postgres-platform` | 1 | Delivered inside F2 (PR #3); nothing remains. Rows that depend on 01 are unblocked when F2 merges | F2 | — | A | — | In review (PR #3, inside F2) |
| 02 | `domain-boundaries` | 1 | What F2 left: per-context route files (`routes/<context>.php`) loaded from `bootstrap/app.php`; arch tests for the rules F2 did not encode (no role-name checks outside `Shared\Access`; `app/Http/Queries` never calls actions or writes; a context's models used only by that context, with an allow-list for its factories, seeders and tests); the Pest coverage gate with a minimum on `app/Domain` | F2 | 03, 04, 05 | A | S | Not started |
| 03 | `shared-value-objects` | 1 | `Cpf`, `Cnpj` (numeric and alphanumeric), `CboCode`, `Matricula`, inclusive `DateRange` with half-open conversion and its Eloquent cast (`daterange` ↔ value object), `Clock` with a test clock that advances one microsecond per read, the `Calendar` interface (holidays, weekly rest day, business days); pure unit tests with check-digit vectors | F2 | 02, 04, 05 | A | S | Not started |
| 04 | `translation-keys` | 1 | English copy of the starter-kit pages moved behind keys; Vue `t()` helper fed by Inertia shared props; per-context `lang/en` files; test failing on a key used in `resources/js` or PHP but missing from `lang/en` | F2 | 02, 03, 05 | A | M | Not started |
| 05 | `clt-rulebook` | 8 | Import the primary-source rulebook into `docs/compliance/clt-rules.md`: conventions C-, férias F-, afastamentos A-, eSocial E- rules with verbatim sources and example cases, the effect of each afastamento on the PA, the unverified items and interpretations, and the v1 scope (categories 101 and 103); reconcile F-17's "one third is a maximum" with U-07 and add the dataset case "abono 5 of 30 → invalid" | F1 | 02, 03, 04, and every row that does not depend on it | A | S | Not started |
| 06 | `principals-and-roles` | 2 | `Principal`, the full v1 `Capability` enum, assigned roles with company reach and `valid_period`, `Authorizer::decide()` and `scope()` with the `ReachResolver` seam, access always decided as of today and the `couldSee` audit query, `Decision` with field groups (all visible for now), policies delegating to it; role assignments carry `company_id` without a foreign key until row 10; decision-matrix tests for company reach | 02 | 07, 08, 09 | B | M | Not started |
| 07 | `audit-log` | 2 | `spatie/laravel-activitylog` 5 with the acting user as causer and a `Shared\Audit` causer seam (Shared never names the Agents model), reason capture, audit component for a subject | 02 | 06, 08, 09 | B | S | Not started |
| 08 | `timeline-planner` | 4 | Pure `TimelinePlanner` for change (split + forward propagation), correction and rescission; table-driven tests including the TDD §7.4 worked example; no database | 02, 03 | 06, 07, 09, 10, 11, 12, 13 | B | M | Not started |
| 09 | `vacation-rules-engine` | 8 | `Absence\Rules`: PA and PC (F-01, C-02, C-03), entitlement (F-02 to F-05), loss (F-08 to F-10), split (F-12), start restriction (F-13), notice (F-14), payment date (F-16), abono (F-17), concessive risk (F-11, F-15), PA chain with loss and pause; datasets from the rulebook's example cases plus "manager-drafted split without the employee's consent → `split_requires_consent`" | 02, 03, 05 | 06 to 21 | B | L | Not started |
| 36 | `esocial-deadlines` | 7 | Pure `EsocialDeadlines` service: S-2200, S-2206, S-2230 and S-2299 deadlines (E-02 to E-05) on the business-day `Calendar`, with the shift direction per event; datasets from the rulebook's deadline examples. Numbered after the v1 rows because it was added when the rulebook landed; row numbers are stable ids, not order | 02, 03, 05 | 06, 07, 08, 09, 10, 11 | B | S | Not started |
| 10 | `companies-establishments` | 3 | Companies (CNPJ root, Empresa Cidadã flag) and establishments (full CNPJ, weekly rest day, union CNPJ), foreign key from row 06's role-assignment `company_id` to `companies`, factories, admin screens under `organization.manage` | 03, 06, 07 | 08, 09 | C | M | Not started |
| 11 | `approval-engine` | 6 | `Shared\Approvals`: requests and sequential steps, approver rules through `ReachResolver`, segregation-of-duties constraints (check, unique index, human-only capabilities), notifications, "My approvals" inbox | 06, 10 | 08, 09, 12 to 18 | D | M | Not started |
| 12 | `org-units-positions` | 3 | Org units with effective-dated tree (no overlaps, no cycles), positions with CBO and effective-dated attributes, national holidays seeded and company holidays implementing `Calendar`, `OrgTree` and `PositionDirectory` contracts, org chart as of a date | 10 | 08, 09, 11, 13 | D | L | Not started |
| 13 | `persons-employments` | 4 | Persons (CPF), employments (matrícula per company, eSocial category), `users.person_id`, factories, people list and profile (basic fields) | 10 | 08, 09, 11, 12 | D | M | Not started |
| 14 | `employment-versions` | 4 | `employment_versions` DDL, exclusion constraint, append-only trigger, `EmploymentWriter` (row lock, injected clock, planner from row 08), `EmploymentReader` (as of, known at), `current_employment_versions(:on)` function; constraint, as-of and two-connection manager-cycle tests | 08, 12, 13 | 09, 11, 15 | E | L | Not started |
| 15 | `field-groups-masking` | 5 | Field-group registry mapping every column of TDD §7–§9, grants with visible groups, the `FieldMask` serializer as an allow-list for Inertia props and exports, per-row visible sets on lists; tests on serialized JSON and a test failing on an unmapped attribute | 06, 13 | 09, 11, 14, 18 | E | M | Not started |
| 16 | `employment-history-ui` | 4 | Timeline screen with "effective on" and "known at" pickers, version diffs, corrections shown as new facts; access decided as of today whatever date is picked | 14, 15 | 09, 11, 17, 18 | F | M | Not started |
| 17 | `reach-as-of-date` | 5 | People's `ReachResolver`: self, direct reports, manager chain, org-unit subtree as of a date (recursive CTEs), derived Employee and Manager roles (Manager only while their own employment is active), request memoization; future-dated transfer and terminated-manager cases | 06, 14, 15 | 09, 11, 16, 18 | F | M | Not started |
| 18 | `outbox-relay` | 7 | `outbox_messages` with per-aggregate sequence, `Outbox::record()`, mapping of `EmploymentVersionRecorded` to `employment.*` events, relay with `SKIP LOCKED`, pruning, JSON Schemas in `docs/events/` | 14 | 09, 11, 15, 16, 17 | F | M | Not started |
| 19 | `movement-framework` | 6 | Movement lifecycle (enum + transition table), type registry, approval through row 11, application through `EmploymentWriter`, cancellation of future-dated movements; `transfer` and `salary_change` types with screens | 11, 15, 17 | 20, 21, 22, 23 | G | L | Not started |
| 20 | `signed-webhooks` | 7 | Subscriptions, deliveries with exponential backoff and disabling, HMAC-SHA256 `t=,v1=` signatures, secret rotation with grace, admin screen, published test vector and verification snippet | 18 | 19, 21, 22, 23 | G | M | Not started |
| 21 | `esocial-csv-export` | 7 | CSV export framework from outbox messages; S-2200, S-2206 and S-2299 shapes with tags checked against the leiaute in `docs/esocial/csv-columns.md`; `esocial.export` screen, audited downloads | 18 | 19, 20, 22, 23 | G | M | Not started |
| 22 | `acquisition-periods-ledger` | 8 | PA chain (running, completed, lost, paused) extended by the scheduler, ledger entries, balance query, `absence_records` with the exclusion constraint, faltas recorded by HR with `counts_as_falta`, re-derivation when an absence is recorded late inside a completed PA | 09, 12, 14 | 16, 17, 18, 19, 20, 21, 23 | F | M | Not started |
| 23 | `agent-registry` | 9 | `agents` table, owner/sponsor/mode/scopes/status, `AgentPrincipal`, effective rights = scopes ∩ the human it acts for ∩ the sponsor, as of the date (matrix case: the invoker's rights exceed the sponsor's), the `field_groups` ceiling (default `basic`), a fail-closed check that the sponsor and acting user hold a role valid today, suspension when a sponsor's employment ends (listening to People's `EmploymentVersionRecorded` with reason `termination`, so it does not wait for row 25) or their last role assignment ends, the agent causer registered through the `Shared\Audit` seam, admin screens | 15, 17 | 19, 20, 21, 22, 27, 28 | G | M | Not started |
| 24 | `admission-readiness` | 6 | `admission` movement creating person, employment and first version; readiness checklist (rule E-01, categories 101 and 103, union and establishment CNPJ); S-2200 deadline; HR dashboard of upcoming admissions | 19, 36 | 25, 26, 27, 28, 29, 37 | H | M | Not started |
| 25 | `termination` | 6 | `termination` movement with reason code, closing versions, `employment.terminated` with its S-2299 deadline (moved earlier on non-business days) | 19, 36 | 24, 26, 27, 28, 29, 37 | H | S | Not started |
| 26 | `movement-change-types` | 6 | `promotion`, `schedule_change`, `manager_change`, `cost_centre_change` and HR `correction` (two HR approvers) types with screens; S-2206-relevant attribute map | 19 | 24, 25, 27, 28, 29, 37 | H | M | Not started |
| 27 | `vacation-requests` | 8 | Draft, submit, approve (≥ 30 days before start), cancel; ledger debits and reversals; `vacation.scheduled` and `vacation.cancelled`; balances and rule results labelled "calculated by Sunex; payroll is the system of record"; employee and manager screens; two-connection overspend test | 11, 15, 17, 18, 22 | 19, 20, 21, 23, 24, 25, 26, 28, 29 | G | L | Not started |
| 28 | `afastamentos` | 8 | Illness and accident afastamentos (codes 01, 03) and paid or unpaid leave (16, 21, 29): open end, illness episodes with the same-cause question and the 15-day counter (A-01 to A-05), `infoMesmoMtv` (E-07), PA loss and pause, conflicts with approved férias, `leave.*` events with deadlines | 15, 18, 22, 36 | 19, 20, 21, 23, 24, 25, 26, 27, 29 | G | L | Not started |
| 29 | `tool-gateway-audit` | 9 | `laravel/ai` installed behind `AgentRuntime`; `AgentToolGateway`; `agent_runs` and `agent_tool_calls`; first read tools (`GetMyEmployment`, `GetVacationBalance`); the chat screen with streaming and the SDK approval prompt; rollback, failed-call and denied-call tests; usage from SDK events | 22, 23 | 24, 25, 26, 27, 28, 37 | H | L | Not started |
| 30 | `mcp-server-oauth` | 9 | `laravel/mcp` and Passport, `Mcp::oauthRoutes()`, RFC 8707 audience middleware (spike first), pending agents from dynamic registration, principal middleware, parity test in-app versus MCP, `SubmitVacationRequest` refused on the MCP channel. Second cut candidate | 29 | 31, 32, 33, 37 | I | L | Not started |
| 31 | `policy-qa-agent` | 10 | Policy documents and chunks with embeddings, the `SearchPolicies` tool, structured output with citation validation and abstention, balance answers labelled "calculated by Sunex", opt-in eval golden set | 29 | 30, 32, 33, 37 | I | M | Not started |
| 32 | `vacation-drafting-agent` | 10 | `DraftVacationRequest` and `SubmitVacationRequest` tools, SDK approval pause for the employee's confirmation, audit linked to the domain approval. First cut candidate | 27, 29 | 30, 31, 33, 37 | I | M | Not started |
| 33 | `demo-seed` | 11 | Demo group with two CNPJs and about 40 employees (histories with a retroactive correction, afastamentos, approved férias), registered agents; one command that starts the database, migrates and seeds the demo (the brief's "runs one command") | 23, 24, 27, 28 | 30, 31, 32, 37 | I | M | Not started |
| 37 | `family-leaves` | 8 | `leave_type_rules` with effective-dated durations and funding (maternity 120 days and extensions, paternity 5 days until 2026 and 10/15/20 from 2027, codes 17–20, 35, 43, 46–52), Empresa Cidadã extensions, truncation of approved férias by a birth with the unused days returned; the S-2230 CSV shape for every motive (férias, illness, leaves) in `docs/esocial/csv-columns.md` | 21, 27, 28 | 24, 25, 26, 29, 30, 31, 32, 33 | H | M | Not started |
| 34 | `golden-path-browser-test` | 11 | Pest browser test of the brief's demo path: agent draft → employee confirmation → manager approval → signed webhook received by a test endpoint → audit trail visible. If row 32 is cut, the path starts with the employee drafting in the UI and the agent step returns in v1.1 | 20, 33, and 32 unless it is cut (then 27) | 37, 38 | J | M | Not started |
| 35 | `v1-release` | 11 | Docs pass (README quickstart and screenshots, ARCHITECTURE, TDD updated to what was built), CHANGELOG, `v1.0.0` tag, retrospective | 01–34, 36, 37 | — | J | S | Not started |

Critical path: F2 → 02 → 06 → 10 → 12/13 → 14 → 17 → 19 → 24 → 33 → 34 → 35. The absence
path runs beside it (14 → 18 and 22 → 27/28 → 33), and the agent path joins at 17 → 23 → 29 → 32
→ 34. **Checkpoint:** row 14 (`employment-versions`) merged by the
end of week 5; if not, row 32 moves to v1.1, then row 30 if the schedule still slips (TDD §18).

Parallel groups at a glance:

| Wave | Rows that can run at the same time |
|---|---|
| A | 02, 03, 04, 05 (as soon as F1 and F2 merge; row 01 shipped inside F2) |
| B | 06, 07, 08, 09, 36 |
| C | 10 (08 and 09 may still be running) |
| D | 11, 12, 13 |
| E | 14, 15 |
| F | 16, 17, 18, 22 |
| G | 19, 20, 21, 23, 27, 28 |
| H | 24, 25, 26, 29, 37 |
| I | 30, 31, 32, 33 |
| J | 34, then 35 |

## Later rows (after v1)

| # | Row | Scope | Depends on | Parallel-safe with | Size | Status |
|---|---|---|---|---|---|---|
| 38 | `pt-br-locale` | pt-BR translations of every key, per-user locale switch, Brazilian date and number formats, glossary of CLT terms for the English UI ([ADR-0012](../../docs/adr/0012-english-ui-copy-behind-translation-keys.md)). Can start any time after 04; cheapest after 33, when screens are stable | 04 (33 recommended) | any row that adds no UI copy | M | Not started |
| 39 | `sensitive-read-log` | LGPD access log for reads of `identifiers`, `compensation` and `absence_details` | 15 | 38, 40 | M | Not started |
| 40 | `effective-date-events` | Daily "effective today" events for future-dated changes and absences | 18 | 38, 39 | S | Not started |
| 41 | `operations-and-deploy` | Redis and Horizon, production observability choice, deploy to a small VPS (decided when v1 is close) | 35 | 38, 39, 40 | L | Not started |
| 42 | `contract-lifecycle-pack` | Experiência, aviso prévio, desligamento deadlines: the next Brazil pack, needing its own rulebook section | 35 | 38 to 41 | L | Not started |
| 43 | `module-2-design` | TDD for module 2 (dyad-scoped 1:1s, check-ins, PDI, eNPS) | 35 | 38 to 42 | M | Not started |
