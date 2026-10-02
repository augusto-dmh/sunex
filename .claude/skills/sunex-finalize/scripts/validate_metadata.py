#!/usr/bin/env python3
"""Validate Sunex branch names, commit messages and PR titles.

Checks, all hard failures:
1. Branch: ``<type>/<optional-issue-number->kebab-summary``.
2. Commit header and PR title: Conventional Commits, lowercase description,
   no trailing period, header at most 72 characters.
3. Commit body: present (it explains why), separated from the header by a
   blank line.
4. Trailers: the final paragraph is exactly ``Assisted-by: Claude Code``.
   No other trailer, no ``Co-Authored-By``, no "Generated with Claude" line.
5. Self-contained history: no internal planning IDs (task, decision or
   requirement IDs, cycle or phase labels, ``.specs/`` paths) in the header,
   body or PR title.

Usage:
  validate_metadata.py --branch feat/employee-record
  validate_metadata.py --pr-title 'feat(people): add employee record'
  validate_metadata.py --message-file .git/COMMIT_EDITMSG
  validate_metadata.py --message "$(git log -1 --format=%B)"
  validate_metadata.py --range origin/main..HEAD

Exit codes: 0 pass, 1 violation, 2 usage error. Standard library only.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field

TYPES = ("feat", "fix", "docs", "refactor", "test", "chore", "build", "ci", "perf", "style", "revert")
TYPE_PATTERN = "|".join(TYPES)
MAX_HEADER = 72
REQUIRED_TRAILER = "Assisted-by: Claude Code"

BRANCH_RE = re.compile(rf"^(?:{TYPE_PATTERN})/(?:[1-9][0-9]*-)?[a-z0-9]+(?:-[a-z0-9]+)*$")
HEADER_RE = re.compile(rf"^(?P<type>{TYPE_PATTERN})(?:\((?P<scope>[a-z0-9]+(?:-[a-z0-9]+)*)\))?!?: (?P<desc>.+)$")
TRAILER_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*: .+$")

# Internal references that must never reach git history or a PR. Kept tight to
# avoid false positives; rephrase in plain terms rather than dodging a real hit.
INTERNAL_REF_PATTERNS = (
    ("task id", re.compile(r"\bT[0-9]{1,3}\b")),
    ("task/phase id", re.compile(r"\b[A-D][0-9]{1,2}\b")),
    ("decision id", re.compile(r"\b(?:AD|ADR|D)-[0-9]+\b")),
    ("requirement id", re.compile(r"\b(?:FR|NFR|AC|RFC|TDD|Gap)-[A-Za-z0-9]")),
    # tlc requirement IDs look like AUTH-01; exactly two digits keeps SHA-256 out.
    ("spec requirement id", re.compile(r"\b(?!UTF-)[A-Z]{2,8}-[0-9]{2}\b")),
    ("cycle label", re.compile(r"\bcycle\s+[0-9]+", re.IGNORECASE)),
    ("phase label", re.compile(r"\bphase\s+[0-9]+", re.IGNORECASE)),
    ("gate label", re.compile(r"\bGate:")),
    ("spec-deviation label", re.compile(r"SPEC_DEVIATION")),
    ("design-section ref", re.compile(r"design\s+§")),
    ("internal spec path", re.compile(r"\.specs/")),
)
# Tool attribution other than the single required trailer. "Generated with" is
# matched only when it names the assistant, so "routes generated with Wayfinder"
# stays legal.
FORBIDDEN_ATTRIBUTION = (
    re.compile(r"co-authored-by\s*:", re.IGNORECASE),
    re.compile(r"generated (?:with|by)\s+\[?claude", re.IGNORECASE),
    re.compile("\U0001F916"),
)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)

    def fail(self, label: str, message: str) -> None:
        self.errors.append(f"{label}: {message}")


def internal_refs(text: str) -> list[str]:
    return [f"{name} {m.group(0)!r}" for name, pattern in INTERNAL_REF_PATTERNS for m in pattern.finditer(text)]


def check_branch(branch: str, report: Report) -> None:
    if not BRANCH_RE.fullmatch(branch):
        report.fail("branch", f"{branch!r} is not <type>/<kebab-summary>, e.g. feat/employee-record")


def check_header(label: str, header: str, report: Report) -> None:
    if len(header) > MAX_HEADER:
        report.fail(label, f"{len(header)} characters, the limit is {MAX_HEADER}")
    match = HEADER_RE.fullmatch(header)
    if not match:
        report.fail(label, f"{header!r} is not 'type(scope): description' with an allowed type")
        return
    desc = match.group("desc")
    if desc[:1].isupper():
        report.fail(label, "description must start lowercase")
    if desc.rstrip().endswith("."):
        report.fail(label, "description must not end with a period")
    for hit in internal_refs(header):
        report.fail(label, f"internal reference {hit}")


def split_paragraphs(lines: list[str]) -> list[list[str]]:
    paragraphs: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line.rstrip())
        elif current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs


def check_message(label: str, message: str, report: Report) -> None:
    lines = [ln for ln in message.splitlines() if not ln.startswith("#")]
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        report.fail(label, "empty message")
        return

    check_header(f"{label} header", lines[0].rstrip(), report)

    rest = lines[1:]
    if rest and rest[0].strip():
        report.fail(label, "a blank line must separate the header from the body")

    paragraphs = split_paragraphs(rest)
    trailer_block = paragraphs[-1] if paragraphs and all(TRAILER_LINE_RE.match(ln) for ln in paragraphs[-1]) else []
    body_paragraphs = paragraphs[:-1] if trailer_block else paragraphs

    if trailer_block != [REQUIRED_TRAILER]:
        found = ", ".join(trailer_block) if trailer_block else "none"
        report.fail(label, f"the only trailer must be {REQUIRED_TRAILER!r} (found: {found})")
    if not body_paragraphs:
        report.fail(label, "missing body: explain why the change is needed")

    full = "\n".join(lines)
    for pattern in FORBIDDEN_ATTRIBUTION:
        if pattern.search(full):
            report.fail(label, f"forbidden attribution matching {pattern.pattern!r}")

    body = "\n".join("\n".join(p) for p in body_paragraphs)
    for hit in internal_refs(body):
        report.fail(f"{label} body", f"internal reference {hit}")


def commits_in_range(rev_range: str) -> list[tuple[str, str]]:
    shas = subprocess.run(
        ["git", "rev-list", "--no-merges", "--reverse", rev_range],
        check=True, capture_output=True, text=True,
    ).stdout.split()
    return [
        (sha, subprocess.run(["git", "log", "-1", "--format=%B", sha], check=True, capture_output=True, text=True).stdout)
        for sha in shas
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--branch")
    parser.add_argument("--pr-title")
    parser.add_argument("--message", help="full commit message (header, body, trailer)")
    parser.add_argument("--message-file")
    parser.add_argument("--range", dest="rev_range", help="validate every non-merge commit in a git range")
    args = parser.parse_args(argv)

    if not any((args.branch, args.pr_title, args.message, args.message_file, args.rev_range)):
        parser.error("provide at least one of --branch, --pr-title, --message, --message-file, --range")

    report = Report()
    if args.branch:
        check_branch(args.branch, report)
    if args.pr_title:
        check_header("PR title", args.pr_title, report)
    if args.message is not None:
        check_message("commit", args.message, report)
    if args.message_file:
        with open(args.message_file, encoding="utf-8") as handle:
            check_message("commit", handle.read(), report)
    if args.rev_range:
        try:
            commits = commits_in_range(args.rev_range)
        except subprocess.CalledProcessError as exc:
            print(f"git failed: {exc.stderr.strip()}", file=sys.stderr)
            return 2
        for sha, message in commits:
            check_message(f"commit {sha[:9]}", message, report)

    for error in report.errors:
        print(f"FAIL {error}", file=sys.stderr)
    if report.errors:
        return 1
    print("validate_metadata: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
