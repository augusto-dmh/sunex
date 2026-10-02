#!/usr/bin/env python3
"""Clean-room check: forbidden terms must not enter the public repository.

Sunex is built in public by an author who also works on other systems. A short,
private list of terms (names of systems and organisations that must never be
mentioned) is kept OUTSIDE the repository, so the list itself never becomes
public. This script scans everything a branch is about to publish:

- lines added on the branch since ``--base`` (``git diff base...HEAD``), in the
  working tree (staged and unstaged) and in untracked files, with the paths of
  every changed or new file;
- every commit message in ``base..HEAD``;
- the branch name;
- any extra file, such as the PR body, passed with ``--file``.

Matching is case-insensitive substring matching, the same as ``grep -i``.
Hits inside lock files are reported as warnings, because hashes in a lock file
can contain any short letter sequence; confirm each one is inside a hash.

Term list, first match wins: ``--terms-file``, the ``SUNEX_CLEAN_ROOM_TERMS``
environment variable, then ``~/.config/sunex/clean-room-terms``. One term per
line, ``#`` starts a comment. A missing or empty list is an error (exit 2): the
check fails closed. Only the repository owner can provide the list.

Exit codes: 0 clean, 1 forbidden term found, 2 usage or setup error.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TERMS = Path("~/.config/sunex/clean-room-terms")
LOCKFILE_GLOBS = ("composer.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "*.lock")


@dataclass(frozen=True)
class Hit:
    where: str
    term: str
    excerpt: str
    lockfile: bool = False


def load_terms(cli_path: str | None) -> list[str]:
    source = cli_path or os.environ.get("SUNEX_CLEAN_ROOM_TERMS") or str(DEFAULT_TERMS)
    path = Path(source).expanduser()
    if not path.is_file():
        raise FileNotFoundError(path)
    terms = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        term = raw.split("#", 1)[0].strip()
        if term:
            terms.append(term.lower())
    return terms


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def added_lines(diff: str) -> list[tuple[str, int, str]]:
    """Parse a unified diff (``-U0``) into (path, line number, text) for added lines."""
    result: list[tuple[str, int, str]] = []
    path = ""
    line_no = 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            path = target[2:] if target.startswith("b/") else target
        elif line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            line_no = int(match.group(1)) if match else 0
        elif line.startswith("+") and not line.startswith("+++"):
            result.append((path, line_no, line[1:]))
            line_no += 1
    return result


def is_lockfile(path: str) -> bool:
    name = Path(path).name
    return any(fnmatch.fnmatch(name, pattern) for pattern in LOCKFILE_GLOBS)


def scan_text(where: str, text: str, terms: list[str], lockfile: bool = False) -> list[Hit]:
    lowered = text.lower()
    return [Hit(where, term, text.strip()[:80], lockfile) for term in terms if term in lowered]


def scan(base: str, terms: list[str], extra_files: list[Path]) -> list[Hit]:
    hits: list[Hit] = []
    diffs = (git("diff", "-U0", "--no-color", f"{base}...HEAD"), git("diff", "-U0", "--no-color", "HEAD"))
    for diff in diffs:
        for path, line_no, text in added_lines(diff):
            hits += scan_text(f"{path}:{line_no}", text, terms, is_lockfile(path))
    untracked = git("ls-files", "--others", "--exclude-standard", "-z").split("\0")
    for path in filter(None, untracked):
        try:
            content = Path(path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, text in enumerate(content.splitlines(), start=1):
            hits += scan_text(f"{path}:{number}", text, terms, is_lockfile(path))
    changed = git("diff", "--name-only", f"{base}...HEAD") + git("diff", "--name-only", "HEAD")
    for path in sorted(set(changed.split()) | set(filter(None, untracked))):
        hits += scan_text(f"path {path}", path, terms)
    for sha in git("rev-list", f"{base}..HEAD").split():
        hits += scan_text(f"commit {sha[:9]}", git("log", "-1", "--format=%B", sha), terms)
    hits += scan_text("branch name", git("rev-parse", "--abbrev-ref", "HEAD").strip(), terms)
    for extra in extra_files:
        for number, text in enumerate(extra.read_text(encoding="utf-8").splitlines(), start=1):
            hits += scan_text(f"{extra}:{number}", text, terms)
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="origin/main", help="branch point to compare against (default: origin/main)")
    parser.add_argument("--terms-file")
    parser.add_argument("--file", action="append", type=Path, default=[], help="extra file to scan, e.g. the PR body")
    args = parser.parse_args(argv)

    try:
        terms = load_terms(args.terms_file)
    except FileNotFoundError as missing:
        print(f"clean_room: term list not found at {missing}. The owner keeps it outside the repository; "
              "ask the owner to create it. The check fails closed.", file=sys.stderr)
        return 2
    if not terms:
        print("clean_room: the term list is empty; the check fails closed.", file=sys.stderr)
        return 2

    try:
        hits = scan(args.base, terms, args.file)
    except subprocess.CalledProcessError as exc:
        print(f"clean_room: git failed: {exc.stderr.strip()}", file=sys.stderr)
        return 2

    failures = [hit for hit in hits if not hit.lockfile]
    for hit in hits:
        level = "WARN" if hit.lockfile else "FAIL"
        print(f"{level} {hit.where}: forbidden term {hit.term!r} in {hit.excerpt!r}", file=sys.stderr)
    if failures:
        print(f"clean_room: {len(failures)} forbidden occurrence(s); rewrite them before pushing.", file=sys.stderr)
        return 1
    print(f"clean_room: OK ({len(terms)} terms checked against {args.base}...HEAD)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
