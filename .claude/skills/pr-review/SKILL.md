---
name: pr-review
description: 'Multi-agent pull-request review for Sunex (Laravel 13, Pest 5, Inertia 3 + Vue 3 + TypeScript, PostgreSQL): seven parallel review lanes (security and authorization, requirements, tests, architecture, data integrity and performance, domain rules, regression) post inline and summary comments with gh, then a consolidation pass. Use only when explicitly asked to review a pull request ("review PR #N", "code review this PR"), or when sunex-ship-cycle dispatches it. Not for automatic use while coding, for publishing (use sunex-finalize), or for general questions.'
license: AGPL-3.0
metadata:
  author: Sunex contributors
  version: 1.0.0
---

# PR Review: orchestration protocol

Coordinates seven review lanes, each a subagent with a fresh context, then one consolidation subagent. The lanes read Sunex's own decisions instead of a copy of them in this file: the ADRs, the specs and the Boost guidelines are the rulebook, and this skill tells each lane where to look and what to look for.

**What Sunex is, in one paragraph (context for every lane):** a people-management app for Brazilian employers. Laravel 13 on PHP 8.4, PostgreSQL 17 with pgvector, Inertia 3 + Vue 3 + TypeScript, Pest 5. Code lives in domain namespaces (People, Organization, Movements, Absence, Agents and so on) whose boundaries are enforced by Pest architecture tests. Employment history is effective-dated (bitemporal on employment versions); every other entity is effective-dated plus an audit log. One permission function (capabilities from roles, relational reach evaluated as of a date, field groups that mask sensitive data) serves humans, in-app AI agents and MCP clients alike. CLT rules (férias, afastamentos) are encoded with article citations. AI agents are registered users with an owner, a scope and a per-tool-call audit row written in the same transaction as the change.

## Step 1: Initialize

1. PR number from the request or context; `REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)`.
2. `gh pr diff <N> > <scratch>/pr-<N>.diff`. If it exceeds about 200 KB, also split it per file (`gh pr diff <N> --name-only` plus `git diff origin/main...<head> -- <path>`) and hand lanes the chunk list: a Read of a file over 256 KB fails, and seven lanes repeating that failure is expensive.
3. Existing inline comments: `gh api repos/$REPO/pulls/<N>/comments --paginate` to a scratch file; lanes skip `{path, line}` pairs already commented (±3 lines).
4. Intent: `gh pr view <N> --json title,body,headRefName,headRefOid`.
5. Feature slug: the branch name without its type prefix and issue number (`feat/12-vacation-split` → `vacation-split`). It locates `.specs/features/<slug>/`.
6. Rulebook paths, listed once for all lanes: `AGENTS.md` / `CLAUDE.md` and `.ai/` (Boost guidelines), `docs/adr/`, `.specs/project/` (ROADMAP, STATE decisions), `.specs/features/<slug>/`, `tests/Arch*` or `tests/**/Arch*` (architecture tests). Lanes read only the parts their scope needs.

## Step 2: Launch the lanes in parallel

Send one message with seven Agent tool calls (`subagent_type: general-purpose`). Each prompt carries: REPO, PR number, the diff path (or chunk list), the existing-comment file, the PR intent, the slug, the rulebook paths, the lane's section of this file, and the Universal Rules. Do not pass the author's reasoning or any implementation context: independence is the point.

**Models:** every lane runs on Opus (`model: "opus"`). Do not run the Security lane on Fable: Fable's safety classifiers target security content and can refuse mid-review. If a lane's model refuses (`stop_reason` refusal), the lane says so in its summary instead of returning silence. Consolidation is mechanical and runs on Haiku (`model: "haiku"`).

For Laravel, Pest, Inertia or Vue facts, lanes use the Laravel Boost `search-docs` tool (version-aware) before memory. A finding that rests on framework behaviour cites the doc it relied on.

## Severity labels

- 🚨 Critical: will cause wrong behaviour, data loss or a broken deploy
- 🔒 Security: authorization gap, data exposure, injection, secret handling
- ⚖️ Compliance: a CLT, eSocial or LGPD rule implemented wrongly or without its source
- ⚡ Performance: a visible, significant cost (N+1, unbounded query, work in the request that belongs on a queue)
- ⚠️ Warning: maintainability or convention problem
- 💡 Suggestion: optional improvement

## Universal rules (every lane)

1. Comment only on diff lines that start with `+` (not `+++`).
2. Skip a finding when `{path, line}` within ±3 lines already has a comment; reply `<!-- sunex-review:<lane> -->` followed by `[RESOLVED] This appears resolved by the recent changes.` to an existing comment whose issue the diff fixes.
3. Post only findings you hold with at least 80% confidence, and only after reading enough surrounding code (not only the hunk) to know the finding is real.
4. Name at least one thing the change does well.
5. Explain why each finding matters and cite its ground: an ADR, a spec acceptance criterion, a Boost guideline, an architecture test, a Laravel doc page, a CLT article.
6. Never approve or request changes, never push, never edit files.
7. Start every inline comment with `<!-- sunex-review:<lane> -->`.
8. No tool or model attribution in any comment.
9. Write each body to a temp file and post with `gh api repos/$REPO/pulls/<N>/comments -F body=@<file> -f commit_id=<headRefOid> -f path=<path> -F line=<line> -f side=RIGHT` (capital `-F` for `@file` and numbers; lowercase `-f body=@file` posts the literal path).
10. PR-level text is an issue comment (`gh pr comment <N> --body-file <file>`), never a review: a submitted review cannot be deleted, and the ship cycle deletes every review artifact after triage.
11. Never Read the diff whole when it may exceed 256 KB; use the chunks or offset/limit.
12. Bash cwd resets between calls: use absolute paths. Read a file before editing any scratch file.
13. A lane is done only when its findings are posted and it has returned a compact summary (well under 10k tokens): counts per severity, files covered, files deliberately skipped with the reason. Going idle without posting is a stall.

## Lane 1: Security and authorization (`security`)

Scope: every PHP, route, migration, config and Vue/TS file in the diff.

- **Policies and the one door.** Every controller action, Inertia page, MCP tool and agent tool that reads or changes data authorizes through the shared permission function or a Policy (`$this->authorize`, `Gate::authorize`, `can` middleware, `Model::can`). Flag a query that filters by hand instead of through the policy scope, a route without auth middleware, and any path where an agent or MCP client could reach data its sponsor cannot.
- **Company scoping.** Several employers (CNPJs) live in one installation. A query, route-model binding or job that can return another company's rows is 🔒.
- **Mass assignment.** `$fillable`/`$guarded` on new models; `Model::create($request->all())` or `->fill($request->input())` instead of `$request->validated()`; `forceFill` on request data.
- **Validation.** Form Requests (or validated DTOs) on every write; `authorize()` in a Form Request that returns `true` without a check.
- **Inertia props leaking fields.** Props are serialized into the page HTML and visible to anyone who can load the page. Flag a whole model passed as a prop (`Inertia::render('X', ['employee' => $employee])`) instead of a resource or array with chosen fields; sensitive fields (CPF, salary, bank data, health data from afastamentos, addresses, credentials, tokens) reaching a prop without the field-group mask; `$hidden` relied on for one prop while another path serializes the raw model; shared data in `HandleInertiaRequests` that exposes more than the current user may see.
- **Injection and unsafe output.** Raw SQL with interpolation (`DB::raw`, `whereRaw`, `selectRaw` with variables); `v-html` on user data; `{!! !!}` in Blade.
- **Secrets and signatures.** Secrets only from config/env; webhook payloads signed and verified with constant-time comparison; agent credentials hashed and rotatable; nothing sensitive in logs or exceptions.
- **Auth surface.** Fortify, passkeys, sessions, CSRF on non-GET routes, Passport scopes and the audience check for MCP and agent tokens.

Second pass: list every changed file you did not comment on and state why it is clean for this lane.

Comment format:

```text
<!-- sunex-review:security -->
🔒 Security: <short title>
<what is wrong, why it matters, the ground>
**Recommendation:** <specific fix>
```

## Lane 2: Requirements and definition of done (`requirements`)

Posts one PR-level summary, no inline comments.

- **Track A, spec:** `.specs/features/<slug>/` (exact, else fuzzy match on the slug or a path named in the PR body). Read `spec.md`, `tasks.md`, `validation.md`, `context.md` when present. Extract requirement IDs, EARS acceptance criteria, out-of-scope items and the Verifier verdict.
- **Track B, decisions:** ADRs under `docs/adr/` that the change touches or that govern the touched area, and the active decisions in `.specs/project/STATE.md`.
- Evaluate every criterion against the diff: ✅ implemented, ❌ missing or wrong, 🔲 not verifiable from the diff. Re-read the list once more and mark anything not yet assessed.
- Also check the PR body itself: all template sections present, Decisions section shows options with why and why not, How to validate is runnable.
- Post idempotently: if a PR comment containing `<!-- sunex-review:requirements -->` exists, `gh api -X PATCH repos/$REPO/issues/comments/<id> -F body=@<file>`; otherwise `gh pr comment <N> --body-file <file>`.
- No spec and no governing ADR found: post "⚠️ No matching spec or governing ADR found; requirements verification skipped." and stop.

```markdown
<!-- sunex-review:requirements -->
## 📋 Requirements review
**Sources:** <spec path, ADR files, STATE decisions>
### ✅ Implemented
### ❌ Missing or incomplete
### 🔲 Definition of done
### 💬 Notes
```

## Lane 3: Tests (`tests`)

Read the test conventions in the Boost guidelines and the existing `tests/` layout first.

- Every new route, controller action, action/service class, job, listener, policy method, MCP tool and agent tool has a Pest test for the happy path and at least one failure: unauthorized user, other company, invalid input, wrong state. A new endpoint without a test is 🚨.
- Authorization tests assert the denial (403/404 or the policy result), not only the success path. Company scoping has a test with two companies.
- CLT rules are table-driven (Pest datasets) and each case names the article it encodes. Boundary values are present (exactly 14 days, exactly 5 days, the 15th day of afastamento, the day the acquisition period closes).
- Effective-dating tests cover as-of queries before, on and after the change date, and the database constraint that forbids overlaps (a test that the insert fails, not only that the app avoids it).
- Inertia responses are asserted with `assertInertia` on component and prop shape, including that masked fields are absent.
- Architecture tests are updated when a namespace or dependency rule changes, never loosened to make a change pass.
- Anti-patterns: asserting only the status code, `RefreshDatabase` missing where state leaks, factories with hard-coded IDs, `sleep`, tests that mirror the implementation instead of the spec, skipped or `todo()` tests left behind, weakened assertions.

Second pass: list every new or changed behaviour you did not comment on and state which test covers it.

## Lane 4: Architecture and conventions (`architecture`)

Phase 0: read the ADRs that govern the touched areas, the Boost guidelines, the architecture tests and any `CONVENTIONS` document under `.specs/`. Phase 1: turn them into a numbered rule list (do not invent rules the documents do not state). Phase 2: evaluate each changed file against each rule as PASS, VIOLATION or N/A (N/A only when the rule cannot apply to that file type) and comment on the `+` line that evidences each violation, quoting the rule number and source.

Always in scope even when no document states it yet, because Laravel's own docs do:

- Domain boundaries: code in the right namespace; no reach into another domain's internals; cross-domain calls through the owning domain's public actions or events.
- Thin controllers delegating to actions or services; Form Requests for validation; Policies for authorization; API Resources or explicit arrays for Inertia props.
- Laravel conventions for the installed version (check with `search-docs`): model casts via the `casts()` method, enums for states, config over `env()` outside config files, route model binding, Wayfinder for typed routes in the frontend instead of hard-coded URLs.
- Vue 3 + TypeScript: `<script setup lang="ts">`, typed props and page props, no `any` to silence errors, UI strings behind translation keys (English copy now, pt-BR later).
- No new dependency without a reason in the PR body.

## Lane 5: Data integrity and performance (`data`)

Only what is visible in the diff; no speculation.

- **Migrations:** reversible `down()` (or a stated reason it cannot be); constraints in the database, not only in PHP: foreign keys with an explicit `onDelete`, `NOT NULL` where the domain requires a value, unique and check constraints, `daterange` columns with exclusion constraints (`btree_gist`) for effective-dated periods; indexes for every foreign key and for the columns new queries filter or sort on; no destructive change to existing data without a backfill plan; no edits to an already-merged migration.
- **Transactions:** multi-write operations in `DB::transaction`; the audit row written inside the same transaction as the change it records; side effects that must not happen on rollback (events to queues, webhooks, mail) dispatched after commit (`afterCommit`, `ShouldDispatchAfterCommit`).
- **Queues:** slow or external work (webhooks, CSV export, embeddings, LLM calls) in queued jobs, not in the request; jobs idempotent and safe to retry, carrying IDs rather than models with stale state, with `tries`/`backoff` and `ShouldBeUnique` where duplicates would corrupt state.
- **Queries:** N+1 (relation accessed in a loop or in a resource without `with()`/`load()`: the lazy loading `Model::preventLazyLoading()` would reject); unbounded `get()`/`all()` where pagination or chunking belongs; counts via `withCount`; heavy pgvector queries without an index.
- **Bitemporal correctness:** corrections append new versions; nothing updates or deletes a recorded employment fact in place.

## Lane 6: Domain rules (`domain`)

The rules that make Sunex legally and ethically trustworthy.

- **CLT and eSocial correctness:** each rule in the diff cites its source (CLT or social-security law article on planalto.gov.br, eSocial manual for event layouts) in code or test; check the encoded rule against that source, for example férias acquisition and concession periods (arts. 130, 134), split into up to three periods with one of at least 14 days and none under 5 (art. 134 §1), reduction by unjustified absences (art. 130), abono pecuniário of up to one third (art. 143), the 15-day employer-paid threshold for afastamentos (Lei 8.213/1991, art. 60 §3, not the CLT). A rule encoded differently from its cited source is ⚖️ even when tests pass. When a rule is ambiguous in the source, the code should say which reading it implements and why.
- **Effective dating:** every change has an effective date, a recorded date and a reason; as-of queries use both axes correctly; corrections never rewrite history.
- **Agent permission invariants:** an agent never reads or does more than its sponsor could at that moment; on-behalf-of mode evaluates the human's permissions, autonomous mode its own registered scope; no agent write takes effect without the human approval step; MCP tools and in-app tools share the same tool classes and the same policy call.
- **Audit invariants:** every agent tool call writes an audit row (agent, sponsor, tool, input summary, outcome, link to the approval or domain change) in the same transaction as the change; audit rows are append-only; masked fields stay masked in audit payloads.
- **Product no-gos:** no payroll calculation, no eSocial XML or transmission, no SaaS tenant isolation. Code that drifts toward one is ⚠️ with the reason.

## Lane 7: Regression and hallucination (`regression`)

Changes unrelated to the PR's purpose and signs of generated code that was not checked: deleted code unrelated to the change (🚨), calls to classes, methods, config keys, routes or Wayfinder helpers that do not exist (🚨), wrong signatures, facades or helpers used with arguments the installed Laravel version does not accept (verify with `search-docs`), `TODO`/`FIXME` or stub bodies in production code, `@phpstan-ignore`, `@ts-ignore` or `as any` hiding a real error, baseline files grown to absorb new errors, duplicate logic that already exists, loosened validation or authorization, swallowed exceptions, weakened tests, dead code.

Second pass as in the other lanes.

## Step 3: Consolidation

After all lanes return, spawn one consolidation subagent (Haiku) that:

1. Fetches inline comments (`gh api repos/$REPO/pulls/<N>/comments --paginate`) and PR comments (`gh api repos/$REPO/issues/<N>/comments --paginate`), keeps those with a `<!-- sunex-review:` marker and groups them by severity: 🔒 → 🚨 → ⚖️ → ⚡ → ⚠️ → 💡.
2. Merges findings on the same `{path, line}` (±3 lines), naming both lanes.
3. Lists changed files (`gh pr diff <N> --name-only`) with no inline comment from any lane under "Files with no inline comments", except lock files, generated files (`resources/js/actions`, `resources/js/routes`, `resources/js/wayfinder`) and `.specs/` artifacts.
4. Posts or updates (by the `<!-- sunex-review:summary -->` marker) one issue comment:

```markdown
<!-- sunex-review:summary -->
## Review summary

| | |
|---|---|
| **Lanes** | <n> of 7: security, requirements, tests, architecture, data, domain, regression |
| **Rulebook read** | <ADRs, specs, guidelines the lanes cited> |
| **Findings** | <n> across <m> files |

### 🔒 Security (<n>)
- [`path:line`] title
### 🚨 Critical (<n>)
### ⚖️ Compliance (<n>)
### ⚡ Performance (<n>)
### ⚠️ Warnings (<n>)
### 💡 Suggestions (<n>)
### 🔍 Files with no inline comments
### ✅ Highlights
```

With no findings: "✅ No issues found across all review lanes." plus the table.

## Step 4: Teardown and re-run

Everything this review creates is deletable, so a re-run never duplicates and the author can clear the PR after triage. Delete only the review's own comments (the `<!-- sunex-review:` marker, posted by the account `gh` runs as); a contributor's, the owner's or a bot's comment on the same PR is never touched:

```bash
me=$(gh api user --jq .login)
sel=".[] | select(.user.login == \"$me\" and (.body | startswith(\"<!-- sunex-review:\"))) | .id"
for id in $(gh api repos/$REPO/pulls/<N>/comments --paginate --jq "$sel"); do gh api -X DELETE repos/$REPO/pulls/comments/$id; done
for id in $(gh api repos/$REPO/issues/<N>/comments --paginate --jq "$sel"); do gh api -X DELETE repos/$REPO/issues/comments/$id; done
```

To resolve a thread after a fix instead of deleting it, reply and resolve through GraphQL (`addPullRequestReviewThreadReply`, then `resolveReviewThread`, thread IDs from `repository.pullRequest.reviewThreads`). Never create what cannot be removed: no `gh pr review`, no review submissions.
