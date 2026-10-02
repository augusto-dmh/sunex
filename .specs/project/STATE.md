# STATE — project memory

Decision log, blockers and handoff for the ship cycles. Durable architecture lives in
[docs/adr/](../../docs/adr/) and the design in [TDD-0001](../../docs/tdd/0001-v1-architecture.md);
this file references them and records the smaller choices taken while planning or building a row.

## Decisions log

Each row: the options considered (with why yes and why not), the choice and its rationale. New
rows are appended by each ship cycle; an `AD` never changes once written, a later `AD` supersedes
it.

### Locked by ADRs (not re-decided here)

| Topic | Source |
|---|---|
| Stack: Laravel 13, PHP 8.4, PostgreSQL 17 + pgvector; Inertia 3 + Vue 3 + TypeScript | ADR-0002, ADR-0003 |
| Domain namespaces with Pest architecture tests | ADR-0004 |
| Bitemporal employment versions only | ADR-0005 |
| One policy function: roles, reach as of a date, field groups | ADR-0006 |
| Agents as principals, one toolset; laravel/ai + laravel/mcp in-process | ADR-0007, ADR-0008 |
| No payroll, no eSocial transmission; signed outbox webhooks and CSV | ADR-0009, ADR-0010 |
| Multi-company in one installation | ADR-0011 |
| English UI copy behind keys, pt-BR later; ship cycle; AGPL-3.0-only | ADR-0012, ADR-0013, ADR-0014 |

### Decisions taken while writing the foundation documents (2026-10-02)

| ID | Decision | Options (why yes / why not) | Choice and rationale |
|---|---|---|---|
| AD-001 | Where the contexts live | (a) `app/Domain/<Context>`: yes, keeps Laravel's `app/Http`, `app/Providers` intact, one PSR-4 root; not, slightly deeper paths. (b) `app/<Context>`: yes, short; not, mixes with framework folders (`app/Models`, `app/Http`). (c) `src/` or `app-modules/` with composer packages: yes, hard boundaries; not, package ceremony ADR-0004 rejected | **(a)**. Delivery code (controllers, requests, Inertia pages) stays in `app/Http` and `resources/js`, grouped by context folder |
| AD-002 | Home of the approval engine | (a) Inside Movements, used by Absence through a contract: yes, close to its first user; not, Absence would depend on Movements and module 2 would too. (b) In Shared as a generic engine: yes, no HR knowledge, reused by férias and later 1:1/PDI flows; not, Shared grows. (c) Its own context: yes, clean; not, a seventh context for one engine | **(b)**, with approver resolution through the `ReachResolver` interface so Shared stays free of People |
| AD-003 | How Shared's policy function learns reach without depending on People | (a) Shared queries People's tables: breaks the dependency rule. (b) An interface in Shared implemented by People (dependency inversion): yes, testable with a fake resolver, keeps the arrow pointing down; not, one indirection. (c) Move the Authorizer into People: yes, simple; not, Organization and Agents would depend on People for every check | **(b)**, `Shared\Access\ReachResolver` |
| AD-004 | Reads that span contexts (list screens) | (a) Only contracts returning DTOs: yes, purest; not, N+1 and slow lists. (b) Eloquent relationships across contexts: yes, convenient; not, couples models of different contexts. (c) Read-only query classes in `app/Http/Queries` using the query builder; writes only through actions: yes, fast lists, boundaries kept for writes; not, query classes know several schemas | **(c)**. Foreign keys across contexts are allowed for integrity; Eloquent relationships across contexts are not |
| AD-005 | A change inserted before an existing future-dated version | (a) Block it until the future version is cancelled: yes, simple; not, HR must undo and redo work. (b) Never propagate: yes, simple; not, a retroactive raise silently disappears on the future transfer date. (c) Propagate the changed attributes only into later versions that still hold the replaced value: yes, matches intent and keeps deliberate later changes; not, a rule users must learn | **(c)**, explained in the UI and pinned by planner tests (TDD §7.4) |
| AD-006 | Source of recorded time | (a) PostgreSQL `transaction_timestamp()`: yes, one clock; not, tests cannot travel in time. (b) Application clock captured once per command: yes, testable and identical for every row of a write; not, clock skew between servers | **(b)**, read **after** the row lock so a writer that waited never closes a row with an older timestamp (found in review); skew cannot corrupt history because inverted ranges are rejected by PostgreSQL and empty ones by a check constraint and the trigger |
| AD-007 | Storing férias, afastamentos and faltas | (a) Separate tables with application checks for overlaps: not, overlaps across tables are not enforced by the database. (b) One `absence_records` table with one partial exclusion constraint, each request type keeping its own detail table: yes, the database forbids two absences on the same day | **(b)** |
| AD-008 | Where the contract type lives | (a) On `employments`: yes, simple; not, a fixed-term contract becoming indeterminate is an S-2206 change that needs a date. (b) On the version with `contract_end_date`: yes, dated and bitemporal like other contract terms | **(b)**, matching ADR-0005's attribute list |
| AD-009 | Employee and Manager roles | (a) Assigned like HR roles: not, they drift from reality after every movement. (b) Derived as of the date from employments and versions: yes, follow movements automatically and answer "who could see X on D" | **(b)**; HR analyst, HR admin and Auditor are assigned, company-scoped and dated |
| AD-010 | Avoiding merge conflicts between parallel rows | (a) Each row adds its capabilities, translations and routes to shared files: not, constant conflicts in the enum and `lang/en.json`. (b) Row 06 defines the full v1 `Capability` enum; translations and routes split per context | **(b)**, written as rules at the top of ROADMAP.md |
| AD-011 | MCP clients that register themselves (RFC 7591) | (a) Disable dynamic registration: yes, safest; not, Claude and ChatGPT connectors expect it. (b) Accept it, but the client becomes a `pending` agent with no owner, sponsor or scopes until an admin activates it | **(b)**; pending agents' tokens are rejected |
| AD-012 | When the CLT 30-day notice (rule F-14) is checked | (a) At request: not, the notice is the employer's act. (b) At approval, with the approval date as the notice date | **(b)**: approval later than start − 30 days is rejected with `notice_lt_30_days` |
| AD-013 | When outbound events fire for future-dated facts | (a) At approval, carrying `effective_date`: yes, payroll can plan; one event per fact. (b) On the effective date: yes, matches "it happened"; not, needs a scheduler and delays information. (c) Both | **(a)** in v1; "effective today" events are later row 40 |
| AD-014 | AGPL-3.0-only or -or-later | (a) -or-later: yes, FSF default, future-proof; not, accepts terms not yet written. (b) -only: yes, the owner decides on any future version | **(b)**, see ADR-0014 |
| AD-015 | Statutory rulebook is kept in private research notes | (a) Reference the private file only: not, a public reader cannot follow `// F-12`. (b) Import it into `docs/compliance/clt-rules.md` before rule code ships | **(b)**: row 05 `clt-rulebook` in wave A; the TDD names the private source by path |
| AD-016 | Size of the bitemporal row | (a) One row for planner and persistence: not, L+ and blocks on Organization and People. (b) Split the pure planner (row 08, wave B) from persistence (row 14) | **(b)**: the riskiest logic starts in week 1 with no database |
| AD-017 | Movement lifecycle mechanism | (a) `spatie/laravel-model-states`: yes, transition classes; not, a dependency for six states. (b) A PHP enum plus an explicit transition table tested exhaustively | **(b)**; revisit if flows grow per type |
| AD-018 | Queue backend in v1 | (a) Redis + Horizon: yes, production-grade; not, one more service before it is needed. (b) The database driver the scaffold configured | **(b)**; Redis and Horizon come with row 41 |
| AD-019 | Local PostgreSQL before row 01 | (a) Wait for the Compose row: not, the README must run today. (b) A documented `docker run` of `pgvector/pgvector:pg17` on host port 54329 | **(b)** in README; row 01 replaces it |
| AD-020 | Where Sunex's agent guidance lives | (a) Edit `AGENTS.md`/`CLAUDE.md` directly: not, Boost rewrites its block on `boost:install`/`boost:update`. (b) Custom guidelines in `.ai/guidelines/`, which Boost 2.x composes into its block on every run (`GuidelineComposer::$userGuidelineDir`) | **(b)**; both files are regenerated and committed with `git add -f` because the scaffold's `.gitignore` lists them |
| AD-021 | Order of the ADR list | (a) One ADR per grilling decision (19 files): not, product decisions (wedge, appetite, module 2) are not architecture. (b) One ADR per durable technical or process choice (14 files); product decisions stay in the brief and the TDD | **(b)** |
| AD-022 | Source for the Absence and eSocial design | (a) Earlier secondary-source research: not, aggregators contradict each other on deadlines and it assumed anniversary-based PAs. (b) The primary-source rulebook (`research/12`, 2026-10-02) wherever they differ | **(b)**. It changed four things: chained PAs that restart or pause; the 15-day threshold per illness episode; effective-dated leave durations from 2027; deadline shifts per event |
| AD-023 | Modelling the 15-day employer-paid threshold | (a) A flag per afastamento: not, spells of the same cause within 60 days add up (Decreto 3.048 art. 75 §§3–5). (b) An `illness_episodes` row with an employer-day counter, fed by one "same cause as an absence in the last 60 days?" question: yes, no diagnosis stored, and the answer also fills `infoMesmoMtv` (mandatory from 2026-10-26) | **(b)** |
| AD-024 | Leave durations that change by date (paternity 5 → 10 → 15 → 20 days) | (a) Constants in code changed by a release: not, an event's date decides the rule and old events must keep theirs. (b) `leave_type_rules` with a `valid_period` per motive code | **(b)**, the same effective-dating pattern as the rest of the model |
| AD-025 | A birth (or any afastamento) starting during approved férias | (a) Reject and make HR cancel the férias first: not, eSocial expects the férias to end the day before and the employee loses nothing. (b) Truncate the férias the day before, return unused days to the ledger, emit the corrected events, in one transaction | **(b)**; other overlaps are still rejected by the exclusion constraint |
| AD-026 | Where the eSocial deadline logic lives | (a) Inside each row that needs a deadline (admission, termination, afastamentos): not, three copies of the business-day rules. (b) One pure `EsocialDeadlines` service with the shift direction per event, as its own small row (36) in wave B | **(b)**; rows 24, 25 and 28 depend on it |
| AD-027 | eSocial categories in v1 | (a) All CLT categories: not, 104/106/111 change férias and eSocial rules. (b) 101 only: not, apprentices (103) follow the same rules and are common. (c) 101 and 103 | **(c)**, following the rulebook's scoping |
| AD-028 | Splitting afastamentos | (a) One row for every afastamento type: not, L+ with maternity, paternity and their 2027 changes. (b) Illness and leave in row 28; family leaves with effective-dated rules and férias truncation in row 37 | **(b)** |
| AD-029 | Numbering rows added after the first cut | (a) Renumber every row: not, links and references break. (b) Row numbers are stable ids; new rows take the next free number and their wave says when they run | **(b)** |

## Blockers

None for the next rows. Items only the owner can do:

- **Trademark.** INPI and domain availability for "Sunex" are unchecked.
- **Employment contract and IP.** The IP clause of the owner's employment contract should be
  checked (Lei 9.609/1998 art. 4); the repository is already public.

## Follow-ups outside this row's files

| Item | Owner |
|---|---|
| `composer.json` still says `"license": "MIT"`, `"name": "laravel/vue-starter-kit"` and `php ^8.3`; ADR-0014 and ADR-0002 call for `AGPL-3.0-only` and `^8.4` | the row that owns composer files (quality tooling or row 01) |
| `.gitignore` lists `AGENTS.md`, `CLAUDE.md` and `boost.json`; the first two are force-added. Versioning `boost.json` would let anyone regenerate the same guidance | whoever owns `.gitignore` |

## Handoff

Foundation PRs F1 (`docs-foundation`), F2 (`quality-tooling`) and F3 (`delivery-harness`) are in
review. As soon as F1 and F2 merge, **wave A** can start in five parallel worktrees:

1. `postgres-platform` (row 01): the Compose file and the CI service unblock every database row.
2. `domain-boundaries` (row 02): the arch tests must exist before the first context code lands.
3. `shared-value-objects` (row 03): pure, no database; unblocks the planner and the rules engine.
4. `translation-keys` (row 04): do it before any new screen exists.
5. `clt-rulebook` (row 05): documentation only; the private rulebook is complete (2026-10-02), so
   this is an import with public links.

Then wave B: `principals-and-roles` (06), `audit-log` (07), `timeline-planner` (08),
`vacation-rules-engine` (09) and `esocial-deadlines` (36). Watch the week-5 checkpoint on row 14 (ROADMAP, critical path).
