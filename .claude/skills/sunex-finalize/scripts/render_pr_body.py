#!/usr/bin/env python3
"""Check a Sunex pull request body against the repository template.

The section list comes from ``.github/pull_request_template.md`` so the template
stays the single source of truth. The draft is a Markdown file that uses the
same ``## Section`` headings, filled in.

Hard failures (exit 1):
- a template section is missing, empty, duplicated or out of order, or the draft
  adds a section the template does not have;
- template guidance comments (``<!-- ... -->``) are left in the draft;
- internal planning references (task, decision or requirement IDs, cycle or
  phase labels, ``.specs/`` paths), unless allowed with ``--allow``;
- assistant attribution such as a co-author trailer or a "Generated with
  Claude" line. The AI assistance section describes the help in prose instead.

Warnings (printed, exit 0):
- prose that looks hard-wrapped: GitHub renders the line breaks literally;
- unchecked checklist items: tick them, or strike them through and say why
  they do not apply.

Usage:
  render_pr_body.py --draft /tmp/pr-draft.md --output /tmp/pr-body.md
  render_pr_body.py --draft draft.md --allow ADR-0004   # the PR adds that ADR

Exit codes: 0 pass, 1 violation, 2 usage error. Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_metadata import FORBIDDEN_ATTRIBUTION, INTERNAL_REF_PATTERNS  # noqa: E402

DEFAULT_TEMPLATE = Path(".github/pull_request_template.md")
HEADING_RE = re.compile(r"^## (?P<title>.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
UNCHECKED_RE = re.compile(r"^\s*[-*] \[ \] (?!~~)")
# A line that starts a block on its own: list item, heading, table row, quote,
# fence, HTML, or a numbered item. Two consecutive plain lines are a hard wrap.
BLOCK_START_RE = re.compile(r"^\s*(?:[-*+] |\d+[.)] |#|\||>|```|~~~|<)")


def split_sections(text: str) -> list[tuple[str, str]]:
    """Return (title, body) pairs for every ``## `` heading outside code fences."""
    sections: list[tuple[str, list[str]]] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
        match = None if in_fence else HEADING_RE.match(line)
        if match:
            sections.append((match.group("title"), []))
        elif sections:
            sections[-1][1].append(line)
    return [(title, "\n".join(body).strip()) for title, body in sections]


def template_titles(template: Path) -> list[str]:
    return [title for title, _ in split_sections(template.read_text(encoding="utf-8"))]


def hard_wrapped_lines(body: str) -> list[str]:
    hits: list[str] = []
    previous = ""
    in_fence = False
    for line in body.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            previous = ""
            continue
        if in_fence:
            continue
        plain = bool(line.strip()) and not BLOCK_START_RE.match(line)
        if plain and previous:
            hits.append(line.strip()[:60])
        previous = line if plain else ""
    return hits


def check(draft_text: str, titles: list[str], allowed: set[str]) -> tuple[list[str], list[str], str]:
    errors: list[str] = []
    warnings: list[str] = []
    sections = split_sections(draft_text)
    found = [title for title, _ in sections]

    for title in titles:
        count = found.count(title)
        if count == 0:
            errors.append(f"missing section '## {title}'")
        elif count > 1:
            errors.append(f"section '## {title}' appears {count} times")
    for title in found:
        if title not in titles:
            errors.append(f"section '## {title}' is not in the template")
    ordered = [title for title in found if title in titles]
    expected = [title for title in titles if title in ordered]
    if ordered != expected and len(set(ordered)) == len(ordered):
        errors.append("sections are out of order; follow the template order: " + ", ".join(titles))

    for title, body in sections:
        if not body:
            errors.append(f"section '## {title}' is empty; write 'None.' when nothing applies")
        if "<!--" in body:
            errors.append(f"section '## {title}' still contains a template comment")
        for line in hard_wrapped_lines(body):
            warnings.append(f"section '## {title}' looks hard-wrapped near: {line!r}")
        if title == "Checklist":
            for line in body.splitlines():
                if UNCHECKED_RE.match(line):
                    warnings.append(f"unchecked item: {line.strip()}")

    body_text = "\n\n".join(f"## {title}\n\n{body}" for title, body in sections) + "\n"
    for name, pattern in INTERNAL_REF_PATTERNS:
        for match in pattern.finditer(body_text):
            if match.group(0) not in allowed:
                errors.append(f"internal reference ({name}): {match.group(0)!r}")
    for pattern in FORBIDDEN_ATTRIBUTION:
        if pattern.search(body_text):
            errors.append(f"assistant attribution matching {pattern.pattern!r}; describe the help under '## AI assistance'")
    return errors, warnings, body_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--draft", required=True, type=Path)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow", action="append", default=[], help="token the internal-reference check accepts")
    args = parser.parse_args(argv)

    if not args.template.is_file():
        print(f"template not found: {args.template} (run from the repository root or pass --template)", file=sys.stderr)
        return 2
    titles = template_titles(args.template)
    if not titles:
        print(f"template has no '## ' sections: {args.template}", file=sys.stderr)
        return 2

    try:
        draft = args.draft.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cannot read --draft: {exc}", file=sys.stderr)
        return 2
    errors, warnings, body = check(draft, titles, set(args.allow))
    for warning in warnings:
        print(f"WARN {warning}", file=sys.stderr)
    for error in errors:
        print(f"FAIL {error}", file=sys.stderr)
    if errors:
        return 1

    if args.output:
        args.output.write_text(body, encoding="utf-8")
        print(f"render_pr_body: OK, wrote {args.output}")
    else:
        sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
