# Review triage: quality tooling

Pull request #3 (`chore/quality-tooling`) was reviewed in a fresh context by the `pr-review` skill:
19 inline comments in five lanes (security 1, data 2, architecture 7, regression 7, tests 2), one
PR-level requirements comment (five numbered items R1–R5, definition-of-done items D1–D6 and three
notes N1–N3) and a summary comment that only indexes the others. This file is the surviving record;
the comments are deleted after triage.

Every finding was judged against the code on this branch at `e9a4b49`, the Pest 5 and PostgreSQL
image sources in `vendor/` and the container, and the documents on `docs/foundation` (PR #2), which
owns ARCHITECTURE.md, CONTRIBUTING.md, TDD-0001, ROADMAP and STATE. A finding is false when it
misreads the code, is already answered elsewhere, or contradicts an accepted decision. Who triaged:
the coordinating session, which did not write this branch.

## Counts

| | Count |
|---|---|
| Findings | 33 (19 inline + 5 numbered PR-level items + 6 definition-of-done items + 3 notes) |
| Real / false | 33 / 0; 9 and 17 were already resolved on PR #2 before triage |
| Fix in files | 16 inline (1–8, 11–16, 18, 19), plus R1 and R5 through their duplicates 11 and 7 |
| Fix in the PR body only | 5 (D1–D4, N1) |
| Partly fixed, rest owned elsewhere | 2 (R4, N2) |
| Deferred to roadmap row 02, with a reason | 3 (10, R2, R3) |
| Won't fix | 3 (D5 owner-only setting, D6 by design, N3 informational) |
| No change, resolved before triage | 2 (9, 17) |
| Follow-up recorded for PR #2 | 3 (scope list in CONTRIBUTING, ARCHITECTURE rule 1 wording, TDD §15 wording) |

Duplicates: 9 and 17 (meaning of `composer test`); 11 and R1 (scope list); 10 and R2 (coverage);
7 and R5 (strict types); 18 restates 11–13 as missing test rows.

## Inline findings

| # | Lane | File:line | Finding | Verdict | Action and rationale |
|---|---|---|---|---|---|
| 1 | security | `compose.yaml:9` | Postgres published on every interface with a committed password | Real | **Fix.** A port without a host IP binds `0.0.0.0`, and Docker's iptables rules bypass `ufw`. Bind to `127.0.0.1`; `DB_HOST=127.0.0.1` already matches, so nothing else changes. CI is unaffected (ephemeral runner). |
| 2 | data | `compose.yaml:19` | Healthcheck passes during the image's socket-only init server | Real | **Fix.** The entrypoint's temporary server runs with `listen_addresses=''`; `pg_isready` without `-h` uses the socket and can pass before the TCP server exists, so `--wait` returns early. Probe `-h 127.0.0.1` in Compose and in the CI service. |
| 3 | data | `database/migrations/2026_10_02_000000_enable_postgres_extensions.php:18` | `create extension vector` needs a superuser | Real | **Fix (docblock).** `vector` is not marked trusted; a least-privilege migrating role fails. One docblock line says who must create it; install docs come with the self-hosting docs. |
| 4 | architecture | `tests/Arch/DomainBoundariesTest.php:50` | The rule blocks Shared's documented public surface | Real | **Fix.** ARCHITECTURE calls Shared a shared kernel and names `Authorizer`, `ApprovalEngine`, `Outbox` and value objects as its surface; TDD-0001 places them in `Shared\Access`, `Approvals`, `Audit`, `Identifiers`, `Integration`, `Time`. Options: (a) open all of `Shared`: simplest, but nothing in Shared stays private; (b) allow the documented namespaces besides `Contracts`/`Events`: matches the docs, keeps anything else private; (c) move the surface under `Shared\Contracts`: rewrites TDD and ARCHITECTURE in PR #2 for no gain. **(b).** Follow-up for PR #2: rule 1 in ARCHITECTURE should name the shared-kernel exception. |
| 5 | architecture | `tests/Arch/DomainBoundariesTest.php:22` | Delivery ban misses HTTP helpers, `Foundation\Http`, HTTP facades, `App\Console` | Real | **Fix.** `toUse` matches prefixes and records global functions by name, so `request()`, `FormRequest` and `Facades\Request` pass today. Add them, `to_route`, and `App\Console` (ARCHITECTURE lists it as delivery). Probed with a throwaway class. |
| 6 | architecture | `tests/Arch/PresetsTest.php:15` | `ignoring('App\Domain')` also lifts the `dd`/`env`/`exit` ban and the "own folder" rules | Real | **Fix.** Verified in `vendor/pestphp/pest/src/ArchPresets`: `dd`, `ddd`, `env`, `exit` come only from the Laravel preset, as do the FormRequest, Command, ServiceProvider, Mailable and Notification rules. Restore them for `App\Domain` in `DomainBoundariesTest`. |
| 7 | architecture | `tests/Arch/PresetsTest.php:7` | Dropping strict types contradicts TDD-0001 §15 | Real | **Fix, scoped.** The PR's reason (generated and framework code omit `strict_types`) does not apply to hand-written domain code, where scalar coercion matters for CLT rules. Options: (a) defer to row 02: row 02 does not list it, so it would need a roadmap edit; (b) require strict types in `App\Domain` only: one line, the tree has no PHP yet, so it costs nothing now; (c) strict preset everywhere: fights the generators. **(b).** Follow-up for PR #2: TDD §15 could say "strict types in `app/Domain`". |
| 8 | architecture | `app/Domain/Absence/README.md:6` | README gives holidays to Absence; ARCHITECTURE gives them to Organization | Real | **Fix.** Absence uses the calendar Organization provides. The per-context READMEs keep one line of ownership and point to ARCHITECTURE as the source of truth; the duplication risk is accepted for the index table, which links there. |
| 9 | architecture | `composer.json:90` | `composer test` no longer means what the guidelines say | Resolved before triage | **No change.** PR #2 commit `860b8b6` already describes `composer check` and the five gate names in CONTRIBUTING, README and the agent guidelines; ADR-0003 names `frontend-check`. |
| 10 | architecture | `composer.json:124` | No coverage gate though the row and ADR-0013 rely on one | Real | **Deferred to row 02.** The roadmap on PR #2 already moved the coverage gate to row 02 ("route files, the remaining arch rules and the coverage gate"), recorded with options in STATE. A minimum on `app/Domain` is meaningless while it holds no PHP; row 02 sets it before the first context code lands. Listed under Impact in the PR body. |
| 11 | regression | `scripts/check-commit-msg.sh:11` | Scope list rejects scopes the rulebook and sibling PRs use | Real | **Fixed before triage** by `e9a4b49` (`adr`, `tdd`, `specs`, `skills`, `design`, `i18n`); every commit on #1 and #2 now passes. The closed list is a deliberate decision. Remaining disagreement: CONTRIBUTING lists `organization`, the script `org`. No commit on any branch uses `org`, so **fix**: rename it to `organization`, matching the context name. **Follow-up for PR #2:** CONTRIBUTING's list still lacks `auth`, `db`, `arch`, `i18n`, `design`, `adr`, `tdd`, `skills`, `deps`, `tooling`; it should name the script as the source of truth. F3's free-form validator is PR #1's to align. |
| 12 | regression | `scripts/check-commit-msg.sh:17` | Any `Merge …`/`Revert "…` header skips every check, trailers included | Real | **Fix.** Exempt only git's own merge headers (`Merge branch`, `pull request`, `remote-tracking branch`, `tag`, `commit`) and `Revert "` from the header rules, and still run the trailer check on them. Dataset rows added. |
| 13 | regression | `scripts/check-commit-msg.sh:32` | The footer check matches ordinary prose such as "auto-generated with" | Real | **Fix.** Match the footer only at the start of a line, after optional non-alphanumeric bytes (the emoji). Dataset rows added for prose. |
| 14 | regression | `.github/workflows/ci.yml:16` | Consecutive pushes to `main` cancel each other's run | Real | **Fix.** Cancel in progress only for pull requests, so every merge commit on `main` gets a finished run. |
| 15 | regression | `.github/workflows/ci.yml:151` | CI gates run under Composer's 300 s process timeout; no job timeout | Real | **Fix.** `composer config process-timeout` is 300 here. Disable it in every gate script, as `frontend-check` already does, and put the limit on the job with `timeout-minutes`. |
| 16 | regression | `database/factories/UserFactory.php:52` | `withTwoFactor()` writes columns this app lacks | Real, low impact | **Fix (docblock).** Options: (a) delete the state and its skipped test: diverges from the starter kit and deletes a test; (b) add the 2FA columns: enables a feature nobody decided on; (c) keep the starter kit's state and say in its docblock that it needs the 2FA columns, which the PR enabling 2FA adds. **(c)**; the only caller is skipped while Fortify's 2FA feature is off. |
| 17 | regression | `composer.json:90` | Docs still say `composer test` runs lint and type checks | Resolved before triage | **No change.** Same as 9; README, CONTRIBUTING, the agent guidelines and ADR-0003 on PR #2 already name `composer check`. |
| 18 | tests | `tests/Unit/Tooling/CommitMessageCheckTest.php:27` | Dataset has no rows for the defects in 11–13 | Real | **Fix**, with 11–13: rows for `organization`, `specs`, prose "generated with", a merge header carrying a tool co-author line, and a merge-shaped header that is not git's. |
| 19 | tests | `tests/Arch/DomainBoundariesTest.php:10` | A context missing from the table bypasses every rule | Real | **Fix.** Add the test tying `DOMAIN_CONTEXTS` to the folders under `app/Domain`, and a rule that no class sits directly in `App\Domain`. |

## PR-level requirements comment

| # | Finding | Verdict | Action and rationale |
|---|---|---|---|
| R1 | Commit check contradicts CONTRIBUTING and fails #1 and #2 | Real, resolved | Same as 11: fixed by `e9a4b49` plus the `organization` rename; CONTRIBUTING follow-up recorded for PR #2. |
| R2 | Coverage setup missing | Real | **Deferred to row 02**, same as 10. |
| R3 | ADR-0004 rules 3–5, the Models rule and route files have no test | Real | **Deferred to row 02**, whose scope on PR #2 is exactly these (route files, models used only by their context, which also rules out cross-context Eloquent relationships, the `app/Http/Queries` rule, role-name checks). Rule 5 (thin controllers) is not mechanically checkable beyond the delivery-layer rule; review covers it. They cost more than this PR's scope: each needs fixtures and a decision on allow-lists. |
| R4 | No feature folder or decision log for the cycle | Real, partly | **Partly fixed:** `.specs/features/quality-tooling/` now holds this triage. The decisions stay in the PR body; STATE.md belongs to PR #2 and records the row cut that affects the roadmap. Bootstrap exception: `.specs/` and the ship cycle arrive with F1 and F3, which are unmerged. |
| R5 | Strict types dropped without updating the TDD | Real | **Fix**, same as 7. |
| D1 | Several Decisions entries name only the chosen option | Real | **Fix in the PR body:** every decision lists its options with why and why not. |
| D2 | Dependencies section lacks licences; npm `react` only under Decisions | Real | **Fix in the PR body:** licence per dependency, `react` listed. |
| D3 | Checklist does not use the template's items | Real | **Fix in the PR body:** the template's checklist, each item answered. |
| D4 | "How to validate" runs `artisan` before `composer install` | Real | **Fix in the PR body:** install first. |
| D5 | `main` has no branch protection | Real | **Won't fix here:** a repository setting only the owner can change; listed in the PR body as a post-merge step (make the six job names required). |
| D6 | The script neither requires nor limits the `Assisted-by` trailer to one | Real, by design | **Won't fix:** requiring it would reject commits written without AI help, which CONTRIBUTING allows; a duplicate trailer is harmless and visible in review. |
| N1 | Scope beyond the row: delivers row 01 and part of 02 without saying so | Real | **Fix in the PR body:** Context names rows F2, 01 and the part of 02 it delivers, matching the roadmap on PR #2. |
| N2 | CONTRIBUTING will be stale once this merges | Real, partly resolved | Gate names already fixed on PR #2; the scope list is the follow-up recorded under 11. |
| N3 | `symplify/rule-doc-generator-contracts` is abandoned | Real, informational | **Won't fix:** dev-only, pulled in by `driftingly/rector-laravel`; revisit when Rector is upgraded. |

## Follow-ups for PR #2 (`docs/foundation`)

These files belong to PR #2, so this PR does not edit them:

1. CONTRIBUTING "Branches and commits": replace the scope list with the one in
   `scripts/check-commit-msg.sh` (`people organization movements absence agents shared auth db arch
   ui i18n design docs adr tdd specs skills ci deps tooling`) and name the script as the source of truth.
2. ARCHITECTURE rule 1: say that other contexts use Shared, the shared kernel, through its documented
   namespaces (`Contracts`, `Events`, `Access`, `Approvals`, `Audit`, `Identifiers`, `Integration`,
   `Time`), which the arch test now allows.
3. TDD-0001 §15: "strict types" applies to `app/Domain`, which the arch test enforces; framework and
   generated code keep the generators' style.
