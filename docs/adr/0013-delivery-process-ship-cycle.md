---
status: accepted
date: 2026-10-02
decision-makers: Augusto Henriques
consulted: research notes on how reviewers judge portfolio projects
informed:
---

# ADR-0013: Deliver every roadmap row through a ship cycle with fresh-context review

## Context and Problem Statement

Sunex is built by one maintainer with a 12-week appetite for v1, and much of the code is written
by coding agents, several of them in parallel. Agent output is fast but needs verification: the
Boost announcement itself advises to "treat all generated code as a draft: run your tests, review
the diffs" ([Laravel blog](https://laravel.com/blog/announcing-laravel-boost)). The repository is
also public evidence of how its author works: "a consistent contribution graph, well-structured
pull requests, and substantive code-review comments are the highest-fidelity signals available"
([Standout](https://standout.work/blog/portfolio-for-senior-software-engineers)).

How does a change get from a roadmap row to `main` so that it is verified, reviewed by someone who
did not write it, and merged without the maintainer becoming the bottleneck?

## Decision Drivers

- Author ≠ reviewer, also when both are agents.
- Every decision taken during a cycle is written down and auditable without the conversation.
- The maintainer approves only what needs judgement; clean work merges without waiting.
- Parallel rows must not collide.
- The commit and pull request history should read as the story of the project.

## Considered Options

- Direct commits to `main`
- Pull requests with human-only review
- A ship cycle per row with fresh-context review and automatic merge when clean (chosen)

## Decision Outcome

Chosen option: "a ship cycle per row with fresh-context review and automatic merge when clean",
because it puts independent verification on every change while reserving the maintainer's time for
the reports that are not clean.

The cycle, per roadmap row:

1. **Plan and build** with spec-driven development: requirements (EARS form) traced to tests, a
   design that cites the TDD phase and ADRs, atomic tasks, implementation with atomic commits, and
   an **independent verifier** that checks the requirements against evidence. A verifier failure
   stops the cycle.
2. **Record decisions.** Each choice is written with its options, the reasons for and against
   each, and the pick, as an `AD-NNN` row in `.specs/project/STATE.md`
   ([ADR-0001](0001-record-architecture-decisions.md)).
3. **Open a pull request** with the standard body sections (Description, Context, Architecture,
   Main changes, Decisions, Tests, Configuration, Dependencies, Impact, How to validate,
   Checklist, AI assistance).
4. **Review in a fresh context.** A reviewer agent that has seen none of the implementation
   conversation reviews the pull request and comments on it.
5. **Triage** every finding against the code: accept with a fix, or reject with a written reason.
6. **Fix** accepted findings in new commits.
7. **Clean up** the review comments once resolved, so the pull request reads as a finished record.
8. **Gated merge.** When the report is clean (all gates green, verifier pass, every finding
   triaged, comments cleaned), the merge runs automatically. Anything else (a red gate, a verifier
   failure, a finding that needs a product decision) waits for the maintainer.

Parallel work: rows marked parallel-safe in the roadmap run at the same time in separate git
worktrees, one agent per pull request, each with an explicit list of files it owns.

Commit conventions: Conventional Commits in English, one concern per commit, and exactly one AI
trailer, `Assisted-by: <tool>`; never `Co-Authored-By` for tools.

### Consequences

- Good, because every merged change has been verified against its requirements and read by a
  reviewer who did not write it.
- Good, because the maintainer's attention goes to dirty reports and product decisions only.
- Good, because the decision log and review threads show trade-off reasoning, which reviewers of
  senior work look for ([whatisthesalary.com](https://whatisthesalary.com/guides/software-engineer-portfolio/)).
- Bad, because each row pays for planning, verification and a second review even when small;
  rows are sized so this overhead stays proportionate.
- Bad, because automatic merge trusts the gates; a gap in the gates (an untested behaviour) can
  reach `main`. The rule "every behaviour has a test" and the coverage gate mitigate this.
- Neutral, because an agent reviewer may miss what a human would catch; the maintainer can still
  review any merged pull request and open a fix row.

### Confirmation

- Branch protection on `main`: pull requests only, required status checks.
- CI runs the commit-message check (the single `Assisted-by` trailer, no tool co-author lines) on
  every commit of a pull request.
- Each row's `.specs/features/<row>/` holds the requirements, the verifier report and the review
  triage; their absence blocks the merge.

## Pros and Cons of the Options

### Direct commits to `main`

- Good, because it is the fastest path.
- Bad, because nothing independent checks agent-written code, parallel agents collide on `main`,
  and the history shows no review at all.

### Pull requests with human-only review

- Good, because the maintainer sees every line.
- Bad, because with several agents producing rows in parallel the maintainer becomes the
  bottleneck, and a 12-week appetite cannot absorb that queue.

### Ship cycle with fresh-context review and automatic merge when clean

- Good, because independence (author ≠ reviewer) holds even when both are agents.
- Good, because clean work does not wait, and dirty work cannot merge.
- Bad, because the process itself must be maintained (skills, templates, CI checks).

## More Information

- "3-5 polished projects outperform 10+ basic ones" ([hakia](https://hakia.com/skills/building-portfolio/)):
  the process trades raw throughput for finished, reviewed rows.
- The harness that runs the cycle (skills, pull request template, commit-message check) is added
  by the delivery-harness foundation pull request; `CONTRIBUTING.md` describes it for humans.
- Related: [ADR-0001](0001-record-architecture-decisions.md),
  [ADR-0004](0004-domain-namespaces-with-architecture-tests.md) (boundaries that keep parallel rows
  apart).
- Revisit if: automatic merges let a regression reach `main` that a human review would have
  caught (then require maintainer approval for the affected kind of change); or contributors
  other than the maintainer join (then human review becomes part of the gate).
