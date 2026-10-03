---
name: sunex-ship-cycle
description: 'End-to-end orchestrator for Sunex roadmap cycles: pick the next ROADMAP row (or several parallel-safe rows, each in its own git worktree), plan and build it with tlc-spec-driven while auto-deciding with recorded rationale, publish with sunex-finalize, review with pr-review in a fresh context, triage every finding against the code, fix, delete the review comments, land decisions and lessons under a merge lock, and merge when the ship report is clean. Use when asked to "ship the next PR", "run the ship cycle", "ship rows X and Y in parallel", or to resume a cycle after an interruption ("continue"). Not for ad-hoc edits, standalone reviews (pr-review) or publishing only (sunex-finalize).'
license: AGPL-3.0
metadata:
  author: Sunex contributors
  version: 1.0.0
---

# Sunex Ship Cycle

Takes one roadmap row from "what is next?" to a merged pull request, or several rows at once when the roadmap marks them parallel-safe. This skill owns the glue and the rules that hold across stages. The work itself is delegated: planning and building to `tlc-spec-driven` (vendored under `.claude/skills/tlc-spec-driven`), publishing to `sunex-finalize`, review to `pr-review`.

Read before the first run: [references/parallel-cycles.md](references/parallel-cycles.md) when more than one cycle is or may be in flight, [references/models.md](references/models.md) before delegating anything, [references/worker-briefs.md](references/worker-briefs.md) before writing a brief.

## Autonomy contract (binding)

The owner does not approve intermediate decisions. At every decision point:

1. Write the options, each with why-yes and why-not.
2. Pick the recommended option. A recommendation that contradicts an accepted ADR, an active decision in `.specs/project/STATE.md` or the product brief's no-gos is not eligible; choose the best option that conforms.
3. Record it: project-level decisions as pending rows in the cycle's `context.md` (numbered at merge, see Stage 7); every decision, in plain words without IDs, in the PR's Decisions section.

Never ask the user mid-cycle (no AskUserQuestion, no "want me to proceed?"). Stop only for something only the owner can do, and say exactly what is needed:

- **Credentials and access:** a secret, an API key, a GitHub permission, an account the session cannot create.
- **Money:** anything that starts a paid plan, a paid API beyond the session's own model use, or a purchase.
- **Legal:** a licence that may be incompatible with AGPL-3.0, trademark or IP questions, a legal reading of CLT or LGPD that the cited primary source does not settle and the code cannot carry as a stated assumption.
- **No conforming option:** every defensible option contradicts a recorded owner decision.
- **Missing clean-room term list:** the clean-room check fails closed without it.
- **Verifier FAIL** after the bounded fix loop (three iterations), and a dirty ship report in `auto` mode.

Everything else is decided, recorded and continued.

**Continuation contract.** Never end a turn "standing by" between stages. Finish the stage, write the heartbeat, start the next stage in the same turn. Things that need human eyes (a visual check in a browser) go into the ship report, not into a pause.

**Resume contract.** On session start or a bare "continue", run Stage Detection and resume in the same turn. Do not ask what to do.

## Run modes

Arguments, combinable: `[auto | hold | until <row>] [--parallel N] [--cycle <slug>]`.

- `auto` (default): merge when the ship report is clean, then wrap. Clean means all of: Verifier PASS, every gate green on the final head, triage recorded with every accepted fix pushed, review comments deleted, CI green, clean-room check passed. Anything else stops with the report.
- `hold`: run Stages 0 to 6, write the ship report, leave the PR open for the owner to merge.
- `until <row>`: like `auto`, then start the next row; stop after the named row merges.
- `--parallel N`: coordinator mode. Start up to N parallel-safe rows, each in its own worktree with its own driver session (see references/parallel-cycles.md). Without it, cycles run one at a time.
- `--cycle <slug>`: drive exactly this cycle (how a coordinator starts a driver, and how a session resumes one).

The mode holds for the whole invocation.

## Where state lives

| What | Where | Written by |
|---|---|---|
| Roadmap rows, status, parallel-safety, dependencies | `.specs/project/ROADMAP.md` | Stage 7 only (own row) |
| Project decisions `AD-NNN`, handoff | `.specs/project/STATE.md` | Stage 7 only, through `merge_state.py` |
| Cycle artifacts: spec, context (with pending decisions), design, tasks, validation, triage | `.specs/features/<slug>/` | The cycle |
| Pending lessons | `.specs/features/<slug>/lessons-pending.jsonl` | Verifier |
| Heartbeats, merge lock | `<git common dir>/sunex-ship/` via `scripts/heartbeat.py` | Every stage |
| Parallel worktrees | `.worktrees/<slug>/` on branch `<type>/<slug>` | Coordinator |

Where `tlc-spec-driven` says `.specs/STATE.md`, Sunex means `.specs/project/STATE.md`. No cycle writes STATE.md, ROADMAP.md or `.specs/lessons.json` before Stage 7: that is what makes parallel cycles conflict-free.

Helpers (run from the worktree root):

```text
H=.claude/skills/sunex-ship-cycle/scripts
python3 $H/heartbeat.py beat <slug> --stage <N> --name <name> --ref <branch|PR #n> --status '<one line>'
python3 $H/heartbeat.py show                # every cycle in flight, stale ones flagged
python3 $H/heartbeat.py lock <slug>         # merge lock; exit 3 = held, 4 = held and stale
python3 $H/merge_state.py <slug>            # land pending decisions and lessons
```

Write a heartbeat at every stage transition and whenever parking (limit, outage, waiting for the merge lock).

## Gates

Read `composer.json` and `package.json` (`scripts`) for exact names at the start of every cycle; never rely on a remembered list. Expected: Composer scripts for the format check (Pint, check mode), static analysis (Larastan), the refactor dry-run (Rector) and tests (Pest, with architecture tests), plus an aggregate check script; npm scripts for the type check (`vue-tsc`), lint/format check and the production build. Use check variants in gates and fixing variants (for example Pint without `--test`) only before committing.

Scope them: the affected Pest file or filter per task commit; the full set at each phase boundary, before pushing fixes, and on the final head before merge. When parallel cycles share a PostgreSQL server, each worktree uses its own test database (references/parallel-cycles.md).

## Stage Detection (always first)

1. `python3 $H/heartbeat.py show`. With `--cycle <slug>` or inside a cycle worktree, resume that cycle. A cycle with a fresh heartbeat belongs to another session: never drive it from here. A stale heartbeat (default two hours) whose worktree has no running session may be adopted; record the adoption in the cycle's `context.md`.
2. Determine the stage of the cycle being driven:

| Observation | Resume at |
|---|---|
| No cycle in flight for this session | Stage 0 |
| Cycle branch exists; tlc Execute or Verifier incomplete | Stage 1 |
| `validation.md` says PASS; no open PR | Stage 2 |
| PR open; no `<!-- sunex-review:` comments and no `review-triage.md` | Stage 3 |
| Review comments present; no `review-triage.md` | Stage 4 |
| `review-triage.md` exists; accepted fixes not all pushed | Stage 5 |
| Fixes pushed; review comments still present | Stage 6 |
| PR comment-free and unmerged | Stage 7 |
| PR merged; worktree, heartbeat or test database still present | Stage 8 |

State the detected stage, cycle and PR, then continue.

## Stage 0: Preflight and selection

1. Require a clean working tree. If dirty, stop and report: never stash (the stash stack is shared by all worktrees), never discard.
2. `git fetch origin`; serial mode works on a branch cut from `origin/main` in the current checkout; coordinator mode creates worktrees (references/parallel-cycles.md).
3. Read `.specs/project/ROADMAP.md`, the Decisions and Handoff of `.specs/project/STATE.md`, and the docs the next row maps to. The next cycle is the first row not started whose dependencies are merged and which no heartbeat claims. In `--parallel N`, take up to N such rows that ROADMAP marks parallel-safe and that pass the overlap check in references/parallel-cycles.md.
4. Name each cycle: a kebab slug from the row, and a branch `<type>/<slug>` validated with `sunex-finalize`'s `validate_metadata.py --branch`.
5. State the chosen row(s), slice and branch in one short paragraph and continue.

## Stage 1: Plan and build (tlc-spec-driven)

Invoke `tlc-spec-driven` for the cycle, with these Sunex overrides of its interactive points:

- **Discuss and every gray area:** answered by the autonomy contract, not by the user. The option set, choice and rationale go in `context.md`.
- **Project-level decisions:** recorded in `context.md` under `## Project decisions (pending numbers)`, in the format STATE.md already uses, with IDs `AD-PENDING-1`, `AD-PENDING-2`, … Never write STATE.md during the cycle. Apply tlc's three-part test (hard to reverse, surprising, a real trade-off) before recording one.
- **Pause and resume:** tlc's Handoff snapshot goes into a `## Handoff` section of the cycle's `context.md`, not into STATE.md, so two paused cycles never overwrite each other's snapshot. The heartbeat names the stage; the Handoff names the next step.
- **Sub-agent offer:** accepted automatically when tlc would offer it; record that in `context.md`.
- **Approval gates for spec and tasks:** the structural validators replace the human gate (`validate_spec.py`, `validate_tasks.py` from the vendored skill). A failing validator is fixed, not skipped.
- **Verifier:** always a fresh subagent; model per references/models.md. It writes lessons to `.specs/features/<slug>/lessons-pending.jsonl` (one JSON object per line: `signal`, `source`, `text`, optional `scope`, same meaning as `lessons.py add`) instead of calling `lessons.py add`, and queues a demotion of a confirmed lesson that failed again as `{"penalize": "L-NNN"}` instead of calling `lessons.py penalize`; both land at Stage 7.
- **Commits:** every task commit follows `sunex-finalize` (Assisted-by trailer only, no internal IDs in messages). tlc's `check_commit.py` is weaker than `validate_metadata.py`; run the latter.
- **Sunex correctness rules** that every task inherits: tests derive from the acceptance criteria; CLT and eSocial rules cite their primary source and are table-driven; authorization goes through the shared policy; sensitive fields never reach Inertia props unmasked; database constraints back every invariant the database can hold.

Workers get goal-shaped briefs (references/worker-briefs.md). A Verifier FAIL enters tlc's bounded fix loop; still failing after three iterations, stop with the report.

## Stage 2: Publish (sunex-finalize)

Invoke `sunex-finalize` to push and open the PR. The PR contains the code and the cycle's `.specs/features/<slug>/` artifacts; it does not touch STATE.md, ROADMAP.md or `.specs/lessons.json` (Stage 7 does). Capture the PR number.

## Stage 3: Review (fresh context, author is not reviewer)

Spawn one subagent (Agent tool, `general-purpose`, `model: "opus"`) whose prompt contains only: the repository, the PR number, the worktree path, and the instruction to invoke the project-local `pr-review` skill for that PR and follow it exactly. Pass no implementation context, spec summary or reasoning from this session. Its deliverable is comments on the PR.

## Stage 4: Triage

1. Fetch every comment: `gh api repos/{repo}/pulls/{N}/comments --paginate` and `gh api repos/{repo}/issues/{N}/comments --paginate`.
2. For each finding decide, against the code as it exists: real or false; if real, fix or won't-fix, and why. Reject findings that misread the code, contradict a recorded decision, or trade against recorded scope, with the reason. Use the Laravel Boost `search-docs` tool when a finding turns on framework behaviour.
3. Who triages is in references/models.md (a fresh triager for most findings; this session for security-lane findings).
4. Persist `.specs/features/<slug>/review-triage.md` before changing anything: one row per finding with lane, `file:line`, verdict, action and rationale. The comments are deleted in Stage 6; this file is the surviving record.

## Stage 5: Fix

Apply every accepted finding as atomic commits through `sunex-finalize` rules. Run the full gates, then push. A fix that changes behaviour gets a test that fails without it. If fixes touch the code the Verifier checked in a way that changes an acceptance criterion's evidence, re-run the Verifier on the affected criteria.

## Stage 6: Clean comments

Invoking this skill is the owner's standing instruction to delete review comments after triage. Delete every inline comment (`gh api -X DELETE repos/{repo}/pulls/comments/{id}`) and every PR-level comment (`gh api -X DELETE repos/{repo}/issues/comments/{id}`), re-fetch both endpoints and confirm zero remain. A submitted review cannot be deleted: report it as a leftover instead of retrying.

## Stage 7: Land and merge

Write the ship report: cycle, PR, Verifier verdict, triage counts (real/false, fixed/won't-fix), fix commits, gate results on the final head, CI status, comment cleanup, clean-room result, anything a human should look at.

- Verifier FAIL or a dirty report: stop with the report in every mode.
- `hold`: stop with the report.
- `auto` / `until` with a clean report: land and merge, as follows, without asking.

Landing, the same in serial and parallel mode (the lock costs nothing when alone):

1. `python3 $H/heartbeat.py lock <slug>`. Exit 3: another cycle is merging; park with a heartbeat (`waiting for merge lock`) and poll `lock-status` with a Monitor until-loop at about one-minute intervals (never `sleep`). Exit 4: the holder looks stale; check its heartbeat and PR, and only if it is truly dead re-run with `--break-stale`, recording that in the report.
2. Inside the lock: `git fetch origin && git rebase origin/main`. Resolve conflicts per references/parallel-cycles.md. If the rebase brought in new commits, re-run the full gates.
3. `python3 $H/merge_state.py <slug>` to number and land pending decisions and lessons. Mark this cycle's ROADMAP row done with the PR number, editing only that row. If any migration of this cycle is timestamped earlier than the newest migration on `main`, rename it to a current timestamp.
4. Commit the landing (`docs: record the decisions and lessons of <plain-language cycle name>`), run `clean_room.py`, and `git push --force-with-lease` (the feature branch only; never force-push `main`).
5. Wait for CI on the new head (`gh pr checks <N> --watch` as a background task or a Monitor until-loop). Red CI: release the lock, fix, return to step 1.
6. `gh pr merge <N> --merge` (a merge commit keeps the atomic commits and the PR boundary visible).
7. `python3 $H/heartbeat.py unlock <slug>`. Release the lock on every exit path from this stage, including failures.

## Stage 8: Wrap

1. From the main checkout: `git checkout main && git pull`. Remove the cycle's worktree (`git worktree remove .worktrees/<slug>`), delete the local branch, drop the cycle's test database, and `python3 $H/heartbeat.py clear <slug>`.
2. Confirm the merged ROADMAP row shows the cycle done and STATE.md has its decisions; fix on a tiny follow-up PR only if missing.
3. Report, in order: the cycle closed and PR merged; the next roadmap row and its scope in one line; a model recommendation for that row with a one-line reason (references/models.md); per-subagent token use if known, noting that `/cost` is the billed authority.

In `until <row>` mode, go back to Stage 0 unless the named row just merged. In `auto` mode, stop after the wrap report.

## Delegation resilience

- **Idle without a summary is a stall**, not completion. Check observable progress (commits, task state, comment counts). Below expectation: send exactly one nudge naming what is missing. A second idle with no progress: stop that agent and re-dispatch a fresh one with the same brief. No wake-up loops whose only purpose is nudging.
- **Usage-limit failure:** re-dispatch once. If that also fails, do the stage's remaining work inline and record the deviation (for example "author is verifier this cycle") in `context.md` and the ship report. If this session is limited, write the heartbeat with exact resume instructions first.
- **Outages:** after two consecutive 5xx/529 errors from the model provider or connection errors from `gh`, check the provider status page once. If confirmed, write the heartbeat, schedule one long wake-up (15 to 30 minutes) and park with "waiting on <provider>, resuming ~HH:MM". No blind retry loops.
- **Fable refusals or 400s:** fall back to Opus for that unit and record it (references/models.md).

## Hygiene (every stage, every brief)

- Commits and PRs follow `sunex-finalize`: `Assisted-by: Claude Code` as the only trailer, no internal IDs, no attribution anywhere else, clean-room check before every push.
- Multiline `gh` bodies through `--body-file` or `-F body=@file`, never `-f body=@file`. Never `gh pr review`.
- Wait on CI with `gh pr checks --watch` in the background or a Monitor until-loop, never `sleep N && …`.
- Bash cwd resets between calls: absolute paths, git from the worktree root. Read a file before editing it. Pass both rules into every brief.
- Never stash; never touch another cycle's worktree or branch; never commit to `main`.
- Subagents return compact text (well under 10k tokens), never report files.
