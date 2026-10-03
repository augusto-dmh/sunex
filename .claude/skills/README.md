# Sunex project-local skills

Sunex keeps the skills its delivery process depends on inside the repository, so any session (local, cloud or a contributor's) runs the same process without relying on someone's global `~/.claude/skills`. `SKILLS.md` at the repository root is the index and explains when to use each one; this file records where each skill came from.

## Provenance

| Skill              | Origin                                                                                                                                  | Licence                            | Notes                                                                                          |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------------------------------- |
| `sunex-ship-cycle` | Written for Sunex, adapted from the owner's ship-cycle process in an earlier project                                                    | AGPL-3.0-only (repository licence) | Orchestrates one roadmap cycle; adds parallel cycles in git worktrees                          |
| `sunex-finalize`   | Written for Sunex, same origin                                                                                                          | AGPL-3.0-only                      | Branch, commit, clean-room and PR conventions, with validators                                 |
| `pr-review`        | Written for Sunex, same origin                                                                                                          | AGPL-3.0-only                      | Seven review lanes tuned to Laravel, Inertia and the Sunex domain                              |
| `tlc-spec-driven`  | Vendored verbatim from [tech-leads-club/agent-skills](https://github.com/tech-leads-club/agent-skills), commit `916a867`, version 3.3.0 | CC-BY-4.0 (text), MIT (scripts)    | See `tlc-spec-driven/NOTICE.md` for attribution, the pinned tree hash and the update procedure |

## Policy

- A skill under `.claude/skills` is either written for Sunex from the repository's own decisions and official documentation, or vendored verbatim from a source whose licence allows redistribution, with a `NOTICE.md` that names the source, the commit and the licence.
- Vendored skills are never edited in place. Sunex-specific behaviour goes into a Sunex skill that wraps or overrides the vendored one, so updating the vendored copy stays a file replacement.
- Third-party blog posts and unofficial best-practice collections are not accepted as project skills without an explicit review recorded in the pull request that adds them.
- Laravel, Pest, Inertia and Vue guidance comes from Laravel Boost (`.ai/` guidelines and its `search-docs` tool) rather than from copies here, because Boost tracks the installed package versions.

## Tests

The Python helpers ship with standard-library tests. Run them from the repository root:

```bash
python3 -m unittest discover -s .claude/skills/sunex-finalize/scripts/tests
python3 -m unittest discover -s .claude/skills/sunex-ship-cycle/scripts/tests
```
