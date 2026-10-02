# Worker briefs: state the goal, not the steps

A delegated worker's brief says what must be true when it finishes and leaves how to the worker. An ordered recipe caps the worker at what the orchestrator already thought of, and the expensive defects are the ones nobody enumerated: they live on branches no test executes, and a worker reasoning about what the code can do finds them while a worker transcribing a checklist does not. Over-prescription also measurably degrades Fable, so goal-shaped briefs are the precondition for upshifting at all.

## Always give (context, not prescription)

- **The goal:** the roadmap row and the acceptance criteria this worker's phase must satisfy, by ID inside `.specs/` (IDs are fine in briefs; they stay out of commits and PRs).
- **The seams:** signatures and `file:line` references from the survey, not file bodies.
- **The binding decisions:** the ADRs and active STATE.md decisions the phase must conform to, the cycle's pending decisions in `context.md`, and any assumption it must not relitigate.
- **The invariants, named as invariants,** each needing a sensor (a test that fails when the invariant breaks). Do not dictate the test's shape or name. Sunex examples:
  - "an employee's record as of a date never changes when a later correction is recorded";
  - "a user of company A can neither read nor infer company B's rows, and the failure looks the same as a missing record";
  - "a masked field never appears in an Inertia prop, an API resource or an audit payload for a viewer without the field group";
  - "an agent can never do what its sponsor could not do at that moment";
  - "the audit row and the change it records commit or roll back together";
  - "two vacation periods of one employee can never overlap, enforced by the database".
- **Environment facts** that cost time to rediscover: the worktree path, the gate commands read from `composer.json` and `package.json`, the test database name for this worktree, the baseline test count, services that must be running, the Laravel Boost `search-docs` tool for version-specific framework facts.
- **The definition of done:** tests derive from acceptance criteria; gates green before a task is done; one atomic commit per task following `sunex-finalize` (`Assisted-by: Claude Code` only, no internal IDs, body explains why); decisions recorded with options, why-yes and why-not.
- **The working rules:** Bash cwd resets between calls, so use absolute paths and run git from the worktree root; Read a file before editing it; never stash; never touch another worktree; never ask the user (decide and record).
- **The report contract:** tasks done with commit hashes, test counts before and after, gate results, decisions taken, deviations stated plainly rather than buried, all well under 10k tokens.

## Do not give

An ordered list of edits, an enumerated list of tests to write, "cover each of these points" checklists, or a solution to transcribe. If the brief is turning into the implementation, either the unit is a Haiku chore (where a step list is correct, because it transcribes by design) or the orchestrator is doing the worker's thinking and should hand over the constraint instead.

## Name the traps

A known landmine is knowledge the worker cannot derive from the seams, so it belongs in the brief: state the trap and its consequence, then require a sensor. Traps already known for this stack:

- **Inertia props are public.** Everything passed to `Inertia::render` and the shared props is serialized into the page; passing a model serializes every non-hidden attribute and loaded relation.
- **`$request->all()` into `create` or `fill`** bypasses validation and invites mass assignment; use validated data.
- **Side effects inside a transaction** (dispatching a job, sending a webhook) run even when the transaction later rolls back unless dispatched after commit.
- **Range exclusion constraints need `btree_gist`** when they mix equality on a scalar column (the employee) with overlap on a range; without the extension the migration fails, and without the constraint overlaps slip through under concurrency.
- **`phpunit.xml` `<env>` values do not override** variables already set in the environment unless marked `force`; a test that seems to hit the wrong database is often this.
- **Wayfinder's route helpers are generated and gitignored.** After changing routes or controllers, regenerate them (the Vite build or `php artisan wayfinder:generate`) before trusting `vue-tsc`, or the type check runs against stale helpers.
- **CLT boundaries are inclusive or exclusive by article.** A test at exactly 14 days, exactly 5 days or the 15th day of absence decides which reading the code implements; cite the article in the dataset.

## Gate scoping

Per task commit: the affected Pest file or `--filter`, plus Pint and `vue-tsc` on touched files when relevant. Per phase boundary and before any push: the full gate set. This keeps quality without paying for the whole suite on every small commit.
