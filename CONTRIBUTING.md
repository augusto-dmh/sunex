# Contributing to Sunex

Thank you for looking. Sunex is built in small, reviewable pull requests that each implement one
row of the [roadmap](.specs/project/ROADMAP.md). This file is the contract for every change,
whether a person or a coding agent writes it.

## Before you start

1. Read [ARCHITECTURE.md](ARCHITECTURE.md) and the phase of
   [TDD-0001](docs/tdd/0001-v1-architecture.md) your change belongs to.
2. Pick a roadmap row whose dependencies are merged. Rows marked parallel-safe with each other can
   be built at the same time in separate git worktrees.
3. If your change contradicts an accepted ADR, write a new ADR that supersedes it first
   ([ADR-0001](docs/adr/0001-record-architecture-decisions.md)). Do not reopen a decision inside a
   feature PR.

## Delivery process

Every roadmap row runs the same ship cycle ([ADR-0013](docs/adr/0013-delivery-process-ship-cycle.md)):

1. **Plan and build** with spec-driven development: requirements in EARS form, a design, atomic
   tasks, tests written from the acceptance criteria, an independent verifier. Planning artifacts
   live in `.specs/features/<row>/`.
2. **Decide and record.** Each decision taken during the cycle is written with its options, the
   reasons for and against each, and the choice, as an `AD-NNN` row in
   [STATE.md](.specs/project/STATE.md).
3. **Open a pull request** with the body sections listed below.
4. **Review in a fresh context.** The reviewer has not seen the implementation conversation.
5. **Triage** every finding against the code (accept, reject with a reason), apply accepted fixes.
6. **Clean up** review comments once they are resolved.
7. **Merge** through the gate: all checks green and a clean review report. Clean reports merge
   automatically; anything else waits for the maintainer.

## Quality gates

A pull request is mergeable only when all of these pass locally and in CI:

```bash
composer check        # runs every gate below, in order
```

| Gate | Runs |
|---|---|
| `composer lint` | Pint in check mode (`composer lint:fix` applies it) |
| `composer analyse` | Larastan at level 9, no baseline |
| `composer refactor-check` | Rector dry run (`composer refactor` applies it) |
| `composer test` | Pest: unit, feature and architecture suites on PostgreSQL |
| `composer frontend-check` | Wayfinder generation, lint and format check, `vue-tsc`, production build |

Each gate is also one CI job, and CI checks every commit message of a pull request. A coverage
gate and Pest browser tests arrive with later roadmap rows. The CI workflow is the source of truth
for the exact list.

Rules that the gates cannot check:

- **Every behaviour has a test** in the same pull request. Rules taken from the CLT cite the
  article in the test dataset.
- Tests run against **PostgreSQL**, never SQLite: range types, exclusion constraints and pgvector
  are part of the design.
- New models come with a factory and, where they appear in the demo, a seeder.
- User-visible text goes through a **translation key**, never a literal string in a Vue component
  or a controller ([ADR-0012](docs/adr/0012-english-ui-copy-behind-translation-keys.md)).
- Cross-context calls go through the target context's `Contracts` namespace; the architecture tests
  enforce it ([ADR-0004](docs/adr/0004-domain-namespaces-with-architecture-tests.md)).

## Branches and commits

- Never commit to `main`. Branch from an up-to-date `main` as `<type>/<slug>`, for example
  `feat/employment-versions`.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) in
  English: `type(scope): lowercase imperative summary`, header at most 72 characters, a body that
  explains **why**. Types: `build chore ci docs feat fix perf refactor revert style test`. Scopes
  are context or area names: `people`, `organization`, `movements`, `absence`, `agents`, `shared`,
  `ui`, `docs`, `specs`, `ci`.
- One concern per commit. A reviewer should be able to read the history as the story of the change.
- **AI assistance is disclosed with exactly one trailer:** `Assisted-by: <tool>` (for example
  `Assisted-by: Claude Code`). Do not add `Co-Authored-By` lines for tools, "Generated with"
  footers or session links.

## Pull requests

- One pull request per roadmap row or per theme. The title follows the commit rule.
- The body is in English with these sections: **Description, Context, Architecture, Main changes,
  Decisions, Tests, Configuration, Dependencies, Impact, How to validate, Checklist, AI assistance**
  (what an agent wrote, what a person reviewed and how).
- Do not reference private trackers or internal identifiers; link ADRs, the TDD phase and the
  roadmap row instead.

## Reporting bugs and proposing features

Open an issue with the steps to reproduce, or with the problem a feature solves. Proposals that
add a module or change a no-go in the [brief](docs/brief.md) need an ADR. Security issues follow
[SECURITY.md](SECURITY.md), never a public issue.

## License of contributions

By contributing you agree that your contribution is licensed under the
[AGPL-3.0-only](LICENSE), the license of the project.
