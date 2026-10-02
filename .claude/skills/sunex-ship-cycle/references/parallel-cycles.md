# Parallel cycles

Several roadmap rows can ship at the same time when they do not depend on each other. Each runs in its own git worktree with its own driver session; they meet only at merge time, one at a time, under a lock. This file is the protocol. It also applies, trivially, to a single cycle: the lock and the pending-decision landing cost nothing when nobody else is in flight, and one protocol is easier to keep correct than two.

## Design at a glance

| Concern | Mechanism | Why it cannot collide |
|---|---|---|
| Who is doing what | One heartbeat file per cycle in `<git common dir>/sunex-ship/<slug>.status` | Each cycle writes only its own file; the directory is inside the shared `.git`, never committed, visible from every worktree |
| Decision numbers | Provisional `AD-PENDING-n` in the cycle's `context.md`; final `AD-NNN` assigned by `merge_state.py` while holding the merge lock | Numbers are assigned in merge order by exactly one process at a time, after rebasing on the latest `main` |
| Shared files (STATE.md, ROADMAP.md, `.specs/lessons.json`) | Untouched during the cycle; written only in the landing commit, inside the lock | Two cycles never have competing edits in flight |
| Lessons | `lessons-pending.jsonl` per cycle, replayed through `lessons.py add` at landing | The machine-owned store is only ever written on top of the latest `main` |
| Merge order | First cycle with a clean ship report takes the lock; the others wait | Dependent rows are never parallel in the first place, so order among independent rows does not matter |
| Code conflicts | Rebase onto `origin/main` inside the lock, then full gates | The branch that merges is always tested on top of everything merged before it |

## Choosing parallel rows

A row may run in parallel only when all of these hold. Otherwise it waits for a serial slot.

1. ROADMAP marks it parallel-safe (read ROADMAP's own legend for the marker and the dependency column; a row without the marker is serial).
2. Every row it depends on is merged.
3. No heartbeat claims it.
4. It does not overlap an in-flight cycle in a way rebasing cannot absorb cheaply. Compare the planned areas (from the row and, once written, the other cycle's `spec.md`/`design.md`):
   - both create or alter migrations on the same table;
   - both add or upgrade Composer or npm dependencies (lock files do not merge; one waits);
   - both change the same shared contract: the permission function, the audit writer, `HandleInertiaRequests` shared props, a base model or trait, the agent tool base class;
   - both change the same architecture test rules.

Record the selection and the overlap check in each cycle's `context.md`. Default cap: three cycles in flight; more makes rebases and reviews the bottleneck.

## Starting cycles (coordinator)

The session invoked with `--parallel N` is a coordinator. It does no cycle work itself.

1. Confirm `.worktrees/` is ignored (`git check-ignore -q .worktrees/x`). If not, add `/.worktrees/` to `.git/info/exclude` (local, uncommitted) and say so in the report.
2. For each selected row, from the main checkout root:

   ```bash
   git fetch origin
   git worktree add .worktrees/<slug> -b <type>/<slug> origin/main
   ```

3. Prepare the worktree: copy the main checkout's `.env`, run `composer install` and `npm ci` (or the lockfile-respecting install the repo uses), and create its test database when the suite runs on PostgreSQL (below).
4. Start one driver per cycle as a top-level session whose working directory is the worktree, for example a Houston pane (`pane_spawn` with `cwd` set to the worktree) running `/sunex-ship-cycle auto --cycle <slug>`. A driver must be top-level because it delegates to workers, a Verifier and a reviewer itself; an in-process subagent cannot. If no way to start top-level sessions exists, run the rows serially in this session instead and say so.
5. Write a heartbeat for each cycle (`Stage 0 preflight`), then wait for the drivers to finish (block on the pane inbox; do not poll in a loop). Report each cycle's outcome as the drivers report.

## Heartbeats

```bash
python3 .claude/skills/sunex-ship-cycle/scripts/heartbeat.py beat <slug> --stage 3 --name review --ref 'PR #14' --status 'lanes running'
python3 .claude/skills/sunex-ship-cycle/scripts/heartbeat.py show
```

Each line records the cycle, stage, branch or PR, UTC timestamp, the worktree path and a one-line status. `show` flags lines older than two hours as STALE. A stale heartbeat means "check before assuming": look at the worktree's last commit time and whether its driver session still runs. Only then adopt the cycle (and record the adoption) or leave it.

## Database and ports per worktree

When the test suite runs against PostgreSQL, parallel suites on one database corrupt each other. Give each worktree its own test database on the shared development server, named `sunex_test_<slug with underscores>`, create it at worktree setup, and run gates with it in the environment:

```bash
DB_DATABASE=sunex_test_vacation_split composer test
```

PHPUnit `<env>` entries without `force="true"` do not override a variable already set in the environment, so this works without editing `phpunit.xml`. If the repository later forces the value, set it in the worktree's untracked `.env.testing` instead. Drop the database at Stage 8. Dev servers for a manual check use distinct ports (`php artisan serve --port=80NN`, Vite `--port`), noted in the heartbeat status while running.

## Landing under the lock

Stage 7 of the skill gives the steps. The parallel-specific rules for the rebase inside the lock:

- **Conflicts only in `.specs/` artifacts of other cycles, ROADMAP.md or STATE.md:** take `main`'s version (during a rebase, `git checkout --ours <file>` selects the upstream side), then let `merge_state.py` and the single ROADMAP row edit re-apply this cycle's changes. Never hand-merge the AD numbering.
- **Conflicts in `.specs/lessons.json` or `.specs/LESSONS.md`:** take `main`'s version; this cycle's lessons are still pending and land afterwards. (A conflict here means some cycle wrote the store outside the protocol; say so in the report.)
- **Conflicts in `composer.lock` or `package-lock.json`:** take `main`'s version and re-run the package manager command that added this cycle's dependency, so the lock is regenerated rather than hand-merged.
- **Conflicts in application code, tests or migrations:** resolve them, re-run the full gates, and send the resolved files to a fresh Verifier for the affected acceptance criteria. If the resolution changes behaviour, release the lock, return to Stage 5 for this cycle, and come back through Stage 7.
- **Migration ordering:** a migration whose timestamp is older than the newest migration on `main` is renamed to a current timestamp, so every database applies migrations in merge order.

Always release the lock on the way out, including on failure (`heartbeat.py unlock <slug>`). A cycle that cannot finish its landing writes its heartbeat with the reason before releasing.

## Failure cases

| Situation | Action |
|---|---|
| Lock held (exit 3) | Park with heartbeat `waiting for merge lock`, poll `lock-status` about once a minute with a Monitor until-loop |
| Lock stale (exit 4) | Check the holder's heartbeat and PR; break it only when the holder is gone (`--break-stale`), and record it |
| Driver session died mid-cycle | The coordinator (or the next session) sees a stale heartbeat, inspects the worktree, and adopts the cycle with `--cycle <slug>` |
| Two cycles turn out to overlap after Design | The later one records the overlap in `context.md`, finishes its Design, and waits for the other to merge before Execute (rebase first) |
| `merge_state.py` fails | Fix the cause (usually a malformed pending lesson; the error names its line) and re-run: lessons already replayed are not replayed again. If the run died between writing STATE.md and rewriting the cycle's files, `git restore` both first |
