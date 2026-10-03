#!/usr/bin/env python3
"""Validate Sunex branch names, commit messages and PR titles.

The repository's own commit-message checker, ``scripts/check-commit-msg.sh``
(run by CI on every commit of a pull request), is the source of truth for the
header shape, the allowed types and scopes, the 72-character limit and the
forbidden co-author and "Generated with" lines. When it exists, every commit
message and PR title is handed to it, and this script adds only the rules it
does not have. Without it, built-in header and attribution rules apply.

Checks, all hard failures:
1. Branch: ``<type>/<optional-issue-number->kebab-summary``.
2. Commit header and PR title: the repository checker (else Conventional
   Commits, lowercase description, header at most 72 characters); no
   trailing period.
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
  validate_metadata.py --range origin/main..HEAD --allow ADR-0015   # adds that ADR

``SUNEX_COMMIT_CHECKER`` overrides the checker path (empty: built-in rules
only), for tests and unusual layouts.

Exit codes: 0 pass, 1 violation, 2 usage error. Standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

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
    # AD-PENDING-n is the provisional form a cycle uses until it merges.
    ("decision id", re.compile(r"\b(?:AD|ADR|D)-(?:PENDING-)?[0-9]+\b")),
    ("requirement id", re.compile(r"\b(?:FR|NFR|AC|RFC|TDD|Gap)-[A-Za-z0-9]")),
    # tlc requirement IDs look like AUTH-01; exactly two digits keeps SHA-256 out.
    # Public code families with the same shape stay legal: CID-10 (disease
    # codes on medical certificates), NR-15 (regulatory norms), PSR-12, ISO-...
    ("spec requirement id", re.compile(r"\b(?!(?:UTF|CID|NR|PSR|ISO)-)[A-Z]{2,8}-[0-9]{2}\b")),
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
ROBOT_EMOJI = re.compile("\U0001F916")
FORBIDDEN_ATTRIBUTION = (
    re.compile(r"co-authored-by\s*:", re.IGNORECASE),
    re.compile(r"generated (?:with|by)\s+\[?claude", re.IGNORECASE),
    ROBOT_EMOJI,
)
COMMIT_CHECKER_REL = Path("scripts/check-commit-msg.sh")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    allowed: frozenset[str] = frozenset()
    checker: Path | None = None

    def fail(self, label: str, message: str) -> None:
        self.errors.append(f"{label}: {message}")


def internal_refs(text: str, allowed: frozenset[str] = frozenset()) -> list[str]:
    return [
        f"{name} {m.group(0)!r}"
        for name, pattern in INTERNAL_REF_PATTERNS
        for m in pattern.finditer(text)
        if m.group(0) not in allowed
    ]


def commit_checker() -> Path | None:
    override = os.environ.get("SUNEX_COMMIT_CHECKER")
    if override is not None:
        return Path(override) if override else None
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return None
    path = Path(top) / COMMIT_CHECKER_REL
    return path if path.is_file() else None


def run_checker(label: str, message: str, report: Report) -> None:
    assert report.checker is not None
    result = subprocess.run(["sh", str(report.checker), "-"], input=message, capture_output=True, text=True)
    if result.returncode != 0:
        detail = " ".join(result.stderr.split()) or f"exit {result.returncode}"
        report.fail(label, f"{report.checker.name}: {detail}")


def check_branch(branch: str, report: Report) -> None:
    if not BRANCH_RE.fullmatch(branch):
        report.fail("branch", f"{branch!r} is not <type>/<kebab-summary>, e.g. feat/employee-record")


def check_header_shape(label: str, header: str, report: Report) -> None:
    """Built-in header rules, used only when the repository checker is absent."""
    if len(header) > MAX_HEADER:
        report.fail(label, f"{len(header)} characters, the limit is {MAX_HEADER}")
    match = HEADER_RE.fullmatch(header)
    if not match:
        report.fail(label, f"{header!r} is not 'type(scope): description' with an allowed type")
    elif match.group("desc")[:1].isupper():
        report.fail(label, "description must start lowercase")


def check_header(label: str, header: str, report: Report, shape_checked: bool = False) -> None:
    if not shape_checked:
        if report.checker:
            run_checker(label, header + "\n", report)
        else:
            check_header_shape(label, header, report)
    if header.rstrip().endswith("."):
        report.fail(label, "description must not end with a period")
    for hit in internal_refs(header, report.allowed):
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

    if report.checker:
        run_checker(label, "\n".join(lines) + "\n", report)
    check_header(f"{label} header", lines[0].rstrip(), report, shape_checked=bool(report.checker))

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
    # The repository checker rejects co-author and "Generated with" lines; the
    # robot emoji on its own is the one attribution it does not look for.
    for pattern in (ROBOT_EMOJI,) if report.checker else FORBIDDEN_ATTRIBUTION:
        if pattern.search(full):
            report.fail(label, f"forbidden attribution matching {pattern.pattern!r}")

    body = "\n".join("\n".join(p) for p in body_paragraphs)
    for hit in internal_refs(body, report.allowed):
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
    parser.add_argument("--allow", action="append", default=[],
                        help="public identifier the internal-reference check accepts, e.g. ADR-0014 in the commit that adds it")
    args = parser.parse_args(argv)

    if not any((args.branch, args.pr_title, args.message, args.message_file, args.rev_range)):
        parser.error("provide at least one of --branch, --pr-title, --message, --message-file, --range")

    report = Report(allowed=frozenset(args.allow), checker=commit_checker())
    if args.branch:
        check_branch(args.branch, report)
    if args.pr_title:
        check_header("PR title", args.pr_title, report)
    if args.message is not None:
        check_message("commit", args.message, report)
    if args.message_file:
        try:
            with open(args.message_file, encoding="utf-8") as handle:
                message = handle.read()
        except OSError as exc:
            print(f"cannot read --message-file: {exc}", file=sys.stderr)
            return 2
        check_message("commit", message, report)
    checked = ""
    if args.rev_range:
        try:
            commits = commits_in_range(args.rev_range)
        except subprocess.CalledProcessError as exc:
            print(f"git failed: {exc.stderr.strip()}", file=sys.stderr)
            return 2
        if not commits:
            # An empty or reversed range must not read like a validated branch.
            print(f"no commits in {args.rev_range}; check the range", file=sys.stderr)
            return 2
        for sha, message in commits:
            check_message(f"commit {sha[:9]}", message, report)
        checked = f" ({len(commits)} commit{'s' if len(commits) != 1 else ''} checked)"

    for error in report.errors:
        print(f"FAIL {error}", file=sys.stderr)
    if report.errors:
        return 1
    print(f"validate_metadata: OK{checked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
