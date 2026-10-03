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
  one JSON object per line: ``{"signal", "source", "text", "scope"?}``. A
  demotion of a confirmed lesson that failed again is queued the same way as
  ``{"penalize": "L-NNN"}`` instead of calling ``lessons.py penalize``.

At merge time, while holding the merge lock and after rebasing on the latest
``main``, this script:

1. numbers the pending decisions after the highest ``AD-NNN`` in STATE.md, in
   order of first appearance, appends them to STATE.md's ``## Decisions``
   section (rows join an existing Markdown table; headings join as blocks), and
   rewrites every ``AD-PENDING-n`` in the cycle's files to its final number;
2. replays each pending line through the tlc-spec-driven ``lessons.py``
   (``add`` or ``penalize``), in order. Each line that succeeds moves from the
   pending file to ``lessons-recorded.jsonl``, so a failed replay can be fixed
   and re-run without applying any line twice.

Running it again after a complete run is a no-op. If a run is interrupted
between writing STATE.md and rewriting the cycle's files, the decisions would
be numbered twice on a re-run: ``git restore`` STATE.md and the feature folder
first (nothing the landing writes is committed yet), then re-run.

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

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PENDING_RE = re.compile(r"\bAD-PENDING-(\d+)\b")
LESSON_ID_RE = re.compile(r"L-[0-9]+")
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


def read_pending(pending: Path) -> list[dict[str, str]]:
    entries = []
    for number, line in enumerate(pending.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{pending}:{number}: not valid JSON ({exc.msg})") from None
        if not isinstance(entry, dict):
            raise ValueError(f"{pending}:{number}: expected a JSON object")
        if "penalize" in entry:
            if not LESSON_ID_RE.fullmatch(str(entry["penalize"])):
                raise ValueError(f"{pending}:{number}: penalize needs a lesson id like L-007")
        else:
            missing = [key for key in ("signal", "source", "text") if not entry.get(key)]
            if missing:
                raise ValueError(f"{pending}:{number} is missing {', '.join(missing)}")
        entries.append(entry)
    return entries


def lessons_command(root: Path, lessons_script: Path, slug: str, entry: dict[str, str]) -> list[str]:
    command = [sys.executable, str(lessons_script), "--root", str(root)]
    if "penalize" in entry:
        return command + ["penalize", "--id", entry["penalize"]]
    command += ["add", "--feature", slug, "--signal", entry["signal"], "--source", entry["source"], "--text", entry["text"]]
    if entry.get("scope"):
        command += ["--scope", entry["scope"]]
    return command


def land_lessons(root: Path, feature: Path, slug: str, lessons_script: Path, dry_run: bool) -> int:
    pending = feature / "lessons-pending.jsonl"
    if not pending.is_file():
        return 0
    entries = read_pending(pending)
    if dry_run:
        return len(entries)
    recorded = feature / "lessons-recorded.jsonl"
    for index, entry in enumerate(entries):
        result = subprocess.run(lessons_command(root, lessons_script, slug, entry), capture_output=True, text=True)
        if result.returncode != 0:
            what = entry.get("penalize") or entry["source"]
            raise RuntimeError(f"lessons.py failed for {what}: {result.stderr.strip() or result.stdout.strip()}")
        # Move the line from pending to recorded at once, so a later failure
        # and re-run never replays it (penalize is not idempotent).
        with recorded.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        pending.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries[index + 1 :]), encoding="utf-8")
    pending.unlink()
    return len(entries)


def slug(value: str) -> str:
    # The slug becomes a path under .specs/features; an absolute or ".." value
    # would make the landing rewrite files outside the cycle's folder.
    if not SLUG_RE.fullmatch(value):
        raise argparse.ArgumentTypeError(f"{value!r} is not a kebab-case cycle slug")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug", type=slug)
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
