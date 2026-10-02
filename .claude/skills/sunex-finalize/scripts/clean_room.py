#!/usr/bin/env python3
"""Clean-room check: forbidden terms must not enter the public repository.

Sunex is built in public by an author who also works on other systems. A short,
private list of terms (names of systems and organisations that must never be
mentioned) is kept OUTSIDE the repository, so the list itself never becomes
public. This script scans everything a branch is about to publish:

- lines added on the branch since ``--base`` (``git diff base...HEAD``), in the
  working tree (staged and unstaged) and in untracked files, with the paths of
  every changed or new file;
- binary files among those, as bytes, for each term in UTF-8 and UTF-16LE;
- every commit in ``base..HEAD``: its message and its author and committer
  name and email;
- the branch name;
- any extra file, such as the PR body, passed with ``--file``, and any literal
  text, such as the PR title, passed with ``--text``.

Matching is case-insensitive substring matching after Unicode NFKC
normalisation, with every run of whitespace read as one space, so a two-word
term still matches when a commit body wraps between its words. Commit
messages, extra files, texts and untracked files are also matched as a whole.
A hit inside a lock file is a warning, not a failure, only when every
occurrence of the term sits inside an integrity hash or a long hex digest;
any other lock-file hit (a registry URL, for example) fails.

Not covered, so check them by hand when they apply: content inside compressed
binaries (Office documents, PDF streams, archives); a term split across two
separate added lines of a diff; anything written on GitHub itself (PR
comments, review text).

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
import unicodedata
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TERMS = Path("~/.config/sunex/clean-room-terms")
LOCKFILE_GLOBS = ("composer.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "*.lock")
WHITESPACE_RE = re.compile(r"\s+")
# Integrity hashes (sha512-<base64>) and hex digests (commit references,
# shasums) in normalised, case-folded text.
HASH_TOKEN_RE = re.compile(r"sha(?:1|256|384|512)-[a-z0-9+/=]+|\b[0-9a-f]{40,}\b")
BINARY_SNIFF = 8000


@dataclass(frozen=True)
class Hit:
    where: str
    term: str
    excerpt: str
    warn: bool = False


def normalise(text: str) -> str:
    return WHITESPACE_RE.sub(" ", unicodedata.normalize("NFKC", text).casefold())


def load_terms(cli_path: str | None) -> list[str]:
    source = cli_path or os.environ.get("SUNEX_CLEAN_ROOM_TERMS") or str(DEFAULT_TERMS)
    path = Path(source).expanduser()
    if not path.is_file():
        raise FileNotFoundError(path)
    terms = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        term = normalise(raw.split("#", 1)[0]).strip()
        if term:
            terms.append(term)
    return terms


def git_bytes(*args: str) -> bytes:
    return subprocess.run(["git", "-c", "core.quotePath=false", *args], check=True, capture_output=True).stdout


def git(*args: str) -> str:
    return git_bytes(*args).decode("utf-8", errors="replace")


def added_lines(diff: str) -> list[tuple[str, int, str]]:
    """Parse a unified diff (``-U0``) into (path, line number, text) for added lines.

    A ``+++ `` line names the file only inside a file header (between
    ``diff --git`` and the first hunk); inside a hunk it is an added line whose
    content starts with ``++``.
    """
    result: list[tuple[str, int, str]] = []
    path = ""
    line_no = 0
    in_header = False
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            in_header = True
        elif in_header and line.startswith("+++ "):
            target = line[4:]
            path = target[2:] if target.startswith("b/") else target
        elif line.startswith("@@"):
            in_header = False
            match = re.search(r"\+(\d+)", line)
            line_no = int(match.group(1)) if match else 0
        elif not in_header and line.startswith("+"):
            result.append((path, line_no, line[1:]))
            line_no += 1
    return result


def is_lockfile(path: str) -> bool:
    name = Path(path).name
    return any(fnmatch.fnmatch(name, pattern) for pattern in LOCKFILE_GLOBS)


def is_binary(content: bytes) -> bool:
    return b"\0" in content[:BINARY_SNIFF]


def inside_hash(text: str, start: int, end: int) -> bool:
    return any(m.start() <= start and end <= m.end() for m in HASH_TOKEN_RE.finditer(text))


def scan_text(where: str, text: str, terms: list[str], lockfile: bool = False) -> list[Hit]:
    norm = normalise(text)
    hits = []
    for term in terms:
        starts = [m.start() for m in re.finditer(re.escape(term), norm)]
        if not starts:
            continue
        hashed = lockfile and all(inside_hash(norm, s, s + len(term)) for s in starts)
        excerpt = norm[max(starts[0] - 30, 0) : starts[0] + len(term) + 30].strip()
        hits.append(Hit(where, term, excerpt, hashed))
    return hits


def scan_document(where: str, text: str, terms: list[str], lockfile: bool = False) -> list[Hit]:
    """Scan line by line for locations, then as a whole for terms that span lines."""
    hits: list[Hit] = []
    for number, line in enumerate(text.splitlines(), start=1):
        hits += scan_text(f"{where}:{number}", line, terms, lockfile)
    found = {hit.term for hit in hits}
    hits += [hit for hit in scan_text(f"{where} (across lines)", text, terms, lockfile) if hit.term not in found]
    return hits


def scan_bytes(where: str, content: bytes, terms: list[str]) -> list[Hit]:
    lowered = content.lower()
    hits = []
    for term in terms:
        for encoding in ("utf-8", "utf-16-le"):
            if term.encode(encoding) in lowered:
                hits.append(Hit(where, term, f"binary content ({encoding})"))
                break
    return hits


def file_content(path: str) -> bytes | None:
    """The bytes about to be published for ``path``: the working tree, else HEAD."""
    target = Path(path)
    if target.is_file():
        return target.read_bytes()
    try:
        return git_bytes("show", f"HEAD:{path}")
    except subprocess.CalledProcessError:
        return None  # deleted: nothing new is published


def scan(base: str, terms: list[str], extra_files: list[Path], texts: list[str]) -> list[Hit]:
    hits: list[Hit] = []
    for diff in (git("diff", "-U0", "--no-color", f"{base}...HEAD"), git("diff", "-U0", "--no-color", "HEAD")):
        for path, line_no, text in added_lines(diff):
            hits += scan_text(f"{path}:{line_no}", text, terms, is_lockfile(path))

    changed = set(filter(None, (git("diff", "--name-only", "-z", f"{base}...HEAD") + git("diff", "--name-only", "-z", "HEAD")).split("\0")))
    for path in sorted(changed):
        content = file_content(path)
        if content is not None and is_binary(content):
            hits += scan_bytes(f"{path} (binary)", content, terms)

    untracked = set(filter(None, git("ls-files", "--others", "--exclude-standard", "-z").split("\0")))
    for path in sorted(untracked):
        try:
            content = Path(path).read_bytes()
        except OSError:
            continue
        if is_binary(content):
            hits += scan_bytes(f"{path} (binary)", content, terms)
        else:
            hits += scan_document(path, content.decode("utf-8", errors="replace"), terms, is_lockfile(path))

    for path in sorted(changed | untracked):
        hits += scan_text(f"path {path}", path, terms)
    for sha in git("rev-list", f"{base}..HEAD").split():
        hits += scan_text(f"commit {sha[:9]}", git("log", "-1", "--format=%B", sha), terms)
        hits += scan_text(f"commit {sha[:9]} author/committer", git("log", "-1", "--format=%an <%ae> %cn <%ce>", sha), terms)
    hits += scan_text("branch name", git("rev-parse", "--abbrev-ref", "HEAD").strip(), terms)
    for extra in extra_files:
        hits += scan_document(str(extra), extra.read_text(encoding="utf-8", errors="replace"), terms)
    for number, text in enumerate(texts, start=1):
        hits += scan_text(f"--text {number}", text, terms)
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="origin/main", help="branch point to compare against (default: origin/main)")
    parser.add_argument("--terms-file")
    parser.add_argument("--file", action="append", type=Path, default=[], help="extra file to scan, e.g. the PR body")
    parser.add_argument("--text", action="append", default=[], help="literal text to scan, e.g. the PR title")
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
    missing_files = [str(path) for path in args.file if not path.is_file()]
    if missing_files:
        print(f"clean_room: --file not found: {', '.join(missing_files)}", file=sys.stderr)
        return 2

    try:
        hits = scan(args.base, terms, args.file, args.text)
    except subprocess.CalledProcessError as exc:
        print(f"clean_room: git failed: {exc.stderr.decode('utf-8', errors='replace').strip()}", file=sys.stderr)
        return 2

    failures = [hit for hit in hits if not hit.warn]
    for hit in hits:
        level = "WARN" if hit.warn else "FAIL"
        print(f"{level} {hit.where}: forbidden term {hit.term!r} in {hit.excerpt!r}", file=sys.stderr)
    if failures:
        print(f"clean_room: {len(failures)} forbidden occurrence(s); rewrite them before pushing.", file=sys.stderr)
        return 1
    print(f"clean_room: OK ({len(terms)} terms checked against {args.base}...HEAD)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
