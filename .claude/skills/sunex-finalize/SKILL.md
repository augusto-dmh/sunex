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

**Commit header and PR title:** `type(scope): imperative lowercase summary`, at most 72 characters, no trailing period. Types: `feat fix docs refactor test chore build ci perf style revert`. The scope is optional; use one when it helps the reader. The repository's `scripts/check-commit-msg.sh`, which CI runs on every commit of a pull request, holds the allowed types and scopes and is the source of truth for header shape and attribution lines. `validate_metadata.py` hands every message and title to it when it exists and adds only the Sunex rules below.

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

1. `git fetch origin` and run `python3 $S/clean_room.py --base origin/main`. Fix every FAIL in work that has not been pushed by rewriting the text (amend or fixup the offending commit). A FAIL in anything already pushed or published (a commit, the branch name, a PR title or body) cannot be fixed here: a force push does not unpublish it, because GitHub keeps the old commits reachable from the PR's force-push entry. Stop and report the term's location, the commit SHAs and the PR to the owner; only the owner can ask GitHub to purge it. Treat the term as disclosed. A WARN means a lock-file hash happens to contain a term; confirm it is inside the hash before continuing.
2. `gh auth status`; push with `git push -u origin <branch>`.
3. Draft the body in `$G/sunex-pr-draft.md`, where `G=$(git rev-parse --absolute-git-dir)` is this worktree's own git directory: private to the cycle, never committed, and not shared with parallel cycles the way a fixed `/tmp` name would be. Use the `## ` sections of `.github/pull_request_template.md`, in order: Description, Context, Architecture, Main changes, Decisions, Tests, Configuration, Dependencies, Impact, How to validate, Checklist, AI assistance. Write "None." where nothing applies. Paragraphs are single unwrapped lines: GitHub renders hard wraps literally.
   - **Context** links public sources (Laravel docs, planalto.gov.br for CLT articles, eSocial manuals), never private notes.
   - **Decisions** lists each choice made while building: the options, why yes and why not for each, and the pick. Plain words, no decision IDs.
   - **Tests** names what the new tests assert and lists each gate command with its result.
   - **AI assistance** says what the assistant wrote (code, tests, docs, this description) and what a human reviewed, ran or changed. Be specific; do not overstate human review that did not happen.
4. Check it, then scan the rendered body and the title for the clean room too. Publish exactly the file that was scanned:

```bash
G=$(git rev-parse --absolute-git-dir)
python3 $S/render_pr_body.py --draft $G/sunex-pr-draft.md --output $G/sunex-pr-body.md
python3 $S/clean_room.py --base origin/main --file $G/sunex-pr-body.md --text '<title>'
gh pr create --base main --head <branch> --title '<title>' --body-file $G/sunex-pr-body.md
```

5. When the PR exists already, run the same render and scan, then update it through the REST API (`gh pr edit` currently fails on a GitHub GraphQL deprecation):

```bash
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
gh api -X PATCH repos/$REPO/pulls/<N> -F body=@$G/sunex-pr-body.md -f title='<title>'
```

   Create drafts only when asked.

## Report

End with: PR URL and number; commits (hash and header); gates run with results; clean-room result; anything left unstaged; anything not done and why.

## Troubleshooting

- **Validator rejects an internal reference that is not one** (for example a legal reference that happens to look like an ID): rephrase if the meaning survives; otherwise pass `--allow <token>` (both `validate_metadata.py` and `render_pr_body.py` accept it) when the token is a public identifier, and the PR's Decisions section says why. Public code families such as `CID-10`, `NR-15` and eSocial events (`S-2200`) are already accepted.
- **`gh` cannot authenticate or push:** report the exact error; return the validated title and rendered body so a human can publish.
- **Clean-room term list missing:** stop before pushing and tell the owner the list is needed at the path the script prints. Do not push without the check.
