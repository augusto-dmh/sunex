#!/usr/bin/env python3
"""Land a cycle's pending decisions and lessons into the shared project files.

Parallel cycles must not race for ``AD-NNN`` numbers or edit the same lines of
``.specs/project/STATE.md`` and ``.specs/lessons.json``. So during a cycle,
nothing writes those shared files. Instead:

- Project-level decisions go into ``.specs/features/<slug>/context.md`` under a
  heading that starts with ``## Project decisions``, written in the same format
  STATE.md uses, with provisional IDs ``AD-PENDING-1``, ``AD-PENDING-2`` ...
  Other files of the cycle may refer to those IDs.
- Lessons the Verifier distils go into ``.specs/features/<slug>/lessons-pending.jsonl``,
  one JSON object per line: ``{"signal", "source", "text", "scope"?}``.

At merge time, while holding the merge lock and after rebasing on the latest
``main``, this script:

1. numbers the pending decisions after the highest ``AD-NNN`` in STATE.md, in
   order of first appearance, appends them to STATE.md's ``## Decisions``
   section (rows join an existing Markdown table; headings join as blocks), and
   rewrites every ``AD-PENDING-n`` in the cycle's files to its final number;
2. replays each pending lesson through the tlc-spec-driven ``lessons.py add``
   command, then renames the file to ``lessons-recorded.jsonl``.

Running it again is a no-op, so an interrupted landing can simply be re-run.

Usage:
  merge_state.py <slug> [--root .] [--dry-run]

Exit codes: 0 ok (including nothing to land), 1 failure, 2 usage error.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PENDING_RE = re.compile(r"\bAD-PENDING-(\d+)\b")
FINAL_RE = re.compile(r"\bAD-(\d{3,})\b")
SECTION_RE = re.compile(r"^## ")
DECISIONS_HEADING_RE = re.compile(r"^## Decisions\b", re.IGNORECASE)
PENDING_HEADING_RE = re.compile(r"^## Project decisions\b", re.IGNORECASE)
TABLE_SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|\s*$")
STATE_REL = Path(".specs/project/STATE.md")
LESSONS_SCRIPT_REL = Path(".claude/skills/tlc-spec-driven/scripts/lessons.py")


def section_bounds(lines: list[str], heading: re.Pattern[str]) -> tuple[int, int] | None:
    """Return (heading index, end index exclusive) of the first matching ``## `` section."""
    for start, line in enumerate(lines):
        if heading.match(line):
            end = next((i for i in range(start + 1, len(lines)) if SECTION_RE.match(lines[i])), len(lines))
            return start, end
    return None


def pending_block(context: str) -> list[str]:
    lines = context.splitlines()
    bounds = section_bounds(lines, PENDING_HEADING_RE)
    if bounds is None:
        return []
    block = lines[bounds[0] + 1 : bounds[1]]
    while block and not block[0].strip():
        block.pop(0)
    while block and not block[-1].strip():
        block.pop()
    return block


def number_pending(block: list[str], state: str) -> dict[str, str]:
    highest = max((int(n) for n in FINAL_RE.findall(state)), default=0)
    mapping: dict[str, str] = {}
    for match in PENDING_RE.finditer("\n".join(block)):
        token = match.group(0)
        if token not in mapping:
            highest += 1
            mapping[token] = f"AD-{highest:03d}"
    return mapping


def substitute(text: str, mapping: dict[str, str]) -> str:
    return PENDING_RE.sub(lambda m: mapping.get(m.group(0), m.group(0)), text)


def strip_table_header(block: list[str]) -> list[str]:
    """Drop a header row and separator so rows can join an existing table."""
    for i, line in enumerate(block):
        if TABLE_SEPARATOR_RE.match(line):
            return block[:max(i - 1, 0)] + block[i + 1 :]
    return block


def insert_decisions(state: str, block: list[str]) -> str:
    lines = state.splitlines()
    if not lines:
        lines = ["# STATE", ""]
    bounds = section_bounds(lines, DECISIONS_HEADING_RE)
    if bounds is None:
        handoff = next((i for i, line in enumerate(lines) if re.match(r"^## Handoff\b", line, re.IGNORECASE)), len(lines))
        new_section = ["## Decisions", "", *block, ""]
        if handoff and lines[handoff - 1].strip():
            new_section.insert(0, "")
        return "\n".join(lines[:handoff] + new_section + lines[handoff:]).rstrip("\n") + "\n"

    start, end = bounds
    content_end = end
    while content_end > start + 1 and not lines[content_end - 1].strip():
        content_end -= 1
    last = lines[content_end - 1] if content_end > start + 1 else ""
    first_new = next((line for line in block if line.strip()), "")
    if last.lstrip().startswith("|") and first_new.lstrip().startswith("|"):
        addition = strip_table_header(block)
    else:
        addition = [""] + block
    trailing = [""] if end < len(lines) else []
    merged = lines[:content_end] + addition + trailing + lines[end:]
    return "\n".join(merged).rstrip("\n") + "\n"


def land_decisions(root: Path, feature: Path, dry_run: bool) -> dict[str, str]:
    context_path = feature / "context.md"
    if not context_path.is_file():
        return {}
    block = pending_block(context_path.read_text(encoding="utf-8"))
    state_path = root / STATE_REL
    state = state_path.read_text(encoding="utf-8") if state_path.is_file() else ""
    mapping = number_pending(block, state)
    if not mapping:
        return {}
    if not dry_run:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(insert_decisions(state, [substitute(line, mapping) for line in block]), encoding="utf-8")
        for path in sorted(feature.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            updated = substitute(text, mapping)
            if updated != text:
                path.write_text(updated, encoding="utf-8")
    return mapping


def land_lessons(root: Path, feature: Path, slug: str, lessons_script: Path, dry_run: bool) -> int:
    pending = feature / "lessons-pending.jsonl"
    if not pending.is_file():
        return 0
    entries = [json.loads(line) for line in pending.read_text(encoding="utf-8").splitlines() if line.strip()]
    for number, entry in enumerate(entries, start=1):
        missing = [key for key in ("signal", "source", "text") if not entry.get(key)]
        if missing:
            raise ValueError(f"{pending}:{number} is missing {', '.join(missing)}")
    if dry_run:
        return len(entries)
    for entry in entries:
        command = [sys.executable, str(lessons_script), "--root", str(root), "add", "--feature", slug,
                   "--signal", entry["signal"], "--source", entry["source"], "--text", entry["text"]]
        if entry.get("scope"):
            command += ["--scope", entry["scope"]]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"lessons.py add failed for {entry['source']}: {result.stderr.strip() or result.stdout.strip()}")
    pending.rename(feature / "lessons-recorded.jsonl")
    return len(entries)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--lessons-script", type=Path, help=f"default: <root>/{LESSONS_SCRIPT_REL}")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    feature = root / ".specs" / "features" / args.slug
    if not feature.is_dir():
        print(f"no feature directory at {feature}", file=sys.stderr)
        return 2
    lessons_script = args.lessons_script or root / LESSONS_SCRIPT_REL

    try:
        mapping = land_decisions(root, feature, args.dry_run)
        lessons = land_lessons(root, feature, args.slug, lessons_script, args.dry_run)
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"merge_state: {exc}", file=sys.stderr)
        return 1

    prefix = "would land" if args.dry_run else "landed"
    for pending_id, final_id in mapping.items():
        print(f"{prefix} {pending_id} as {final_id}")
    print(f"{prefix} {len(mapping)} decision(s) and {lessons} lesson(s) for {args.slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
