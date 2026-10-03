# Sunex skills and delivery workflow

Sunex is built with AI coding agents under the same rules a careful human team would follow: every change starts from a written spec, is verified by someone other than its author, is reviewed in a fresh context, and is published with a history an outside reader can follow. The rules live in the repository as project-local skills under `.claude/skills/`, so every session, local or in the cloud, runs the same process. Provenance and licences are in [.claude/skills/README.md](.claude/skills/README.md).

## Skills

| Skill                                                          | Use it to                                                                                                                                                                                                  | Invoked by                                                                |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [`sunex-ship-cycle`](.claude/skills/sunex-ship-cycle/SKILL.md) | Ship one roadmap row end to end, or several parallel-safe rows at once in separate git worktrees; resume an interrupted cycle                                                                              | "ship the next PR", "run the ship cycle", "continue"                      |
| [`tlc-spec-driven`](.claude/skills/tlc-spec-driven/SKILL.md)   | Specify, design, break into tasks and execute a feature with EARS acceptance criteria, atomic commits and an independent Verifier                                                                          | `sunex-ship-cycle` Stage 1, or directly for a feature outside the roadmap |
| [`sunex-finalize`](.claude/skills/sunex-finalize/SKILL.md)     | Commit, run the gates, pass the clean-room check, push and open a PR with the template's sections                                                                                                          | `sunex-ship-cycle` Stages 2, 5 and 7, or "finalize this"                  |
| [`pr-review`](.claude/skills/pr-review/SKILL.md)               | Review a PR with seven lanes: security and authorization, requirements, tests, architecture, data integrity and performance, domain rules (CLT, effective dating, agent permissions and audit), regression | `sunex-ship-cycle` Stage 3 in a fresh context, or "review PR #N"          |

Framework guidance (Laravel 13, Pest 5, Inertia 3, Vue 3, Tailwind) comes from Laravel Boost's guidelines and its version-aware `search-docs` tool rather than from skills copied into this folder.

## One cycle

```text
ROADMAP row
  -> tlc-spec-driven: spec -> design -> tasks -> execute -> Verifier (fresh context)
  -> sunex-finalize: gates, clean-room check, PR
  -> pr-review (fresh context) -> triage against the code -> fixes -> review comments deleted
  -> under the merge lock: rebase, land decisions and lessons, CI green, merge
```

- **Autonomy:** agents decide with written options, why-yes and why-not, and record the choice in the cycle's `context.md` and the PR's Decisions section. They stop only for what only the owner can do: credentials, money, legal questions, or a conflict with a recorded owner decision.
- **Merge:** automatic when the ship report is clean (Verifier PASS, gates and CI green, triage recorded, accepted fixes pushed, comments cleaned, clean-room check passed); a Verifier FAIL always stops.
- **Parallel cycles:** rows the roadmap marks parallel-safe run in `.worktrees/<slug>`. Each cycle writes its own heartbeat in the shared git directory, keeps decisions provisional (`AD-PENDING-n`) until it merges, and merges one at a time under a lock after rebasing, which is where decision numbers are assigned. Details: [parallel-cycles.md](.claude/skills/sunex-ship-cycle/references/parallel-cycles.md).
- **Models:** Opus 5.5 by default, Fable 5.1 for the Verifier and triage, Haiku 4.5 only for mechanical chores that pass a four-condition test. Details: [models.md](.claude/skills/sunex-ship-cycle/references/models.md).

## Publishing rules in one paragraph

Conventional Commits in English, one concern per commit, a body that explains why, and `Assisted-by: Claude Code` as the only trailer (no co-author lines, no "generated with" lines). No internal planning IDs in commits or PRs; traceability stays under `.specs/`. A clean-room check runs before every push. PR bodies use the sections of [.github/pull_request_template.md](.github/pull_request_template.md). CI's commit checker (`scripts/check-commit-msg.sh`) and the validators in `sunex-finalize`, which defer to it for header and attribution rules, enforce all of this.

## Where things live

| Path                                       | Contents                                                               |
| ------------------------------------------ | ---------------------------------------------------------------------- |
| `.specs/project/ROADMAP.md`                | Roadmap rows, status, dependencies, parallel-safety                    |
| `.specs/project/STATE.md`                  | Project decisions (`AD-NNN`) and the handoff snapshot                  |
| `.specs/features/<slug>/`                  | One cycle's spec, context, design, tasks, validation and review triage |
| `.specs/lessons.json`, `.specs/LESSONS.md` | Lessons distilled by the Verifier (machine-owned)                      |
| `docs/adr/`                                | Accepted architecture decisions                                        |

## Adding a skill

Write it for Sunex from the repository's decisions and official documentation, or vendor it verbatim from a source whose licence allows redistribution, with a `NOTICE.md` naming the source, commit and licence. Never edit a vendored skill in place; wrap it. Add a row to the table above and to `.claude/skills/README.md`, and give any script a standard-library test.
