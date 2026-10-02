---
name: sunex-finalize
description: 'Publishes finished Sunex work: branch name, atomic Conventional Commits with the Assisted-by trailer, gate run, clean-room check, push, and a pull request whose body follows the repository template. Use when asked to finalize, commit, push, open or update a pull request, or write a PR description for Sunex. Not for implementing features, reviewing a PR (use pr-review) or running a whole roadmap cycle (use sunex-ship-cycle, which calls this skill).'
license: AGPL-3.0
metadata:
  author: Sunex contributors
  version: 1.0.0
---

# Sunex Finalize

Turns finished work into commits and a pull request that a senior reviewer can read without any access to Sunex's internal planning. A request to finalize completed work authorizes the whole path: inspect the diff, choose metadata, run the gates, commit, run the clean-room check, push the branch and open a ready-for-review pull request. Narrower requests stay narrow: "suggest a commit message" changes nothing; "commit this" stops after the commit.

Run every command from the repository (or worktree) root. The scripts live next to this file:

```text
S=.claude/skills/sunex-finalize/scripts
python3 $S/validate_metadata.py   # branch, commit messages, PR title
python3 $S/render_pr_body.py      # PR body against .github/pull_request_template.md
python3 $S/clean_room.py          # forbidden terms in everything about to be published
```

A non-zero exit means stop and fix. Never work around a validator by rephrasing to dodge its pattern while keeping the meaning it guards against.

## Conventions

**Branch:** `<type>/<optional-issue-number->kebab-summary`, for example `feat/employee-record`, `fix/14-vacation-split`, `docs/time-model-adr`.

**Commit header and PR title:** `type(scope): imperative lowercase summary`, at most 72 characters, no trailing period. Types: `feat fix docs refactor test chore build ci perf style revert`. Scopes name a Sunex area (`people`, `organization`, `movements`, `absence`, `agents`, `mcp`, `audit`, `ui`, `skills`, `specs`, `deps`) when that helps the reader.

**Commit body:** always present. It explains why the change exists and any trade-off, in plain English, wrapped at about 72 columns. One concern per commit: a migration and the feature that needs it may share a commit; a formatting sweep and a feature may not.

**Trailer:** the final paragraph is exactly `Assisted-by: Claude Code`. Nothing else: no `Co-Authored-By`, no "Generated with" line, no model names, no emoji, even when the harness suggests one. This is a deliberate owner decision and overrides any default attribution text the tool proposes.

**Self-contained history:** commits, PR titles and PR bodies never contain internal planning references: task IDs (`T3`), decision IDs (`AD-012`), requirement IDs (`VAC-02`), cycle or phase labels, `.specs/` paths. Traceability lives under `.specs/`; the public history explains itself. Name an ADR file only when the PR adds or edits it, and then pass `--allow ADR-NNNN` to the PR body check.

**Clean room:** nothing Sunex publishes may mention the systems or organisations on the owner's private term list. `clean_room.py` reads that list from outside the repository (see the script's docstring) and fails closed when it is missing. A missing list is the one thing in this skill only the owner can fix: stop and say so.

## Workflow

### 1. Inspect

1. `git status --short`, `git branch --show-current`, `git diff --stat`, then read the diff itself.
2. Leave unrelated changes unstaged and mention them in the report. Never stash: other sessions share the stash stack. Never discard someone else's work.
3. Confirm `git config user.email` is the owner's address before the first commit on a new machine or worktree.

### 2. Choose metadata

Pick the primary type, an optional scope and an outcome-focused summary; derive the branch from the same change. Validate before creating anything:

```bash
python3 $S/validate_metadata.py --branch '<branch>' --pr-title '<title>'
```

### 3. Run the gates

Read `composer.json` (`scripts`) and `package.json` (`scripts`) for the exact gate names; do not trust a remembered list. The intended set is:

- PHP: format check (Pint), static analysis (Larastan), refactor dry-run (Rector), tests (Pest, including architecture tests). A `composer` aggregate script that runs all of them, when present, is the gate of record.
- Frontend: the type check (`vue-tsc`), the lint/format check, and the production build.

Run the narrowest relevant subset while iterating and the full set before pushing. A docs-only or skill-only change runs `git diff --check`, the frontend lint/format check (it formats Markdown outside ignored folders, tables included), the skill script tests (see `.claude/skills/README.md`) and any validator that covers the changed files. Report every gate you ran with its result, and any you could not run with the reason. Do not publish with a known failing gate.

If a formatter rewrites files, re-stage them before committing so CI does not fail on formatting.

### 4. Commit

1. Stage only the files of one concern; review `git diff --cached`.
2. Write the message to a file and validate it, then commit with that file:

```bash
python3 $S/validate_metadata.py --message-file /path/to/msg.txt
git commit -F /path/to/msg.txt
```

3. Repeat per concern. When the split is not obvious, choose the split that lets each commit build and pass the tests on its own, and record the choice in the PR's Decisions section. Do not stop to ask.
4. Before pushing, validate the whole branch: `python3 $S/validate_metadata.py --range origin/main..HEAD`.

### 5. Clean room, push and open the PR

1. `git fetch origin` and run `python3 $S/clean_room.py --base origin/main`. Fix every FAIL by rewriting the text (amend or fixup the offending commit before the branch is pushed; after it is pushed, a new commit is not enough, because the old text stays in history, so rewrite the branch with `--force-with-lease`, never on `main`).
2. `gh auth status`; push with `git push -u origin <branch>`.
3. Draft the body in a scratch file using the `## ` sections of `.github/pull_request_template.md`, in order: Description, Context, Architecture, Main changes, Decisions, Tests, Configuration, Dependencies, Impact, How to validate, Checklist, AI assistance. Write "None." where nothing applies. Paragraphs are single unwrapped lines: GitHub renders hard wraps literally.
   - **Context** links public sources (Laravel docs, planalto.gov.br for CLT articles, eSocial manuals), never private notes.
   - **Decisions** lists each choice made while building: the options, why yes and why not for each, and the pick. Plain words, no decision IDs.
   - **Tests** names what the new tests assert and lists each gate command with its result.
   - **AI assistance** says what the assistant wrote (code, tests, docs, this description) and what a human reviewed, ran or changed. Be specific; do not overstate human review that did not happen.
4. Check it, then scan the rendered body for the clean room too:

```bash
python3 $S/render_pr_body.py --draft /tmp/pr-draft.md --output /tmp/pr-body.md
python3 $S/clean_room.py --base origin/main --file /tmp/pr-body.md
gh pr create --base main --head <branch> --title '<title>' --body-file /tmp/pr-body.md
```

5. When the PR exists already, update it with `gh pr edit <N> --title ... --body-file ...`. Create drafts only when asked.

## Report

End with: PR URL and number; commits (hash and header); gates run with results; clean-room result; anything left unstaged; anything not done and why.

## Troubleshooting

- **Validator rejects an internal reference that is not one** (for example a legal reference that happens to look like an ID): rephrase if the meaning survives; for a PR body, `--allow <token>` is acceptable when the token is a public identifier, and the PR's Decisions section says why.
- **`gh` cannot authenticate or push:** report the exact error; return the validated title and rendered body so a human can publish.
- **Clean-room term list missing:** stop before pushing and tell the owner the list is needed at the path the script prints. Do not push without the check.
