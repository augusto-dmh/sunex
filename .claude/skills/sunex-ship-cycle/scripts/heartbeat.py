#!/usr/bin/env python3
"""Per-cycle heartbeats and the merge lock for parallel Sunex ship cycles.

State lives in ``<git common dir>/sunex-ship/``: the ``.git`` directory of the
main checkout, which every worktree shares. It is never committed, needs no
gitignore entry, and every cycle sees every other cycle's state without
touching another worktree.

- ``<slug>.status``: one line per cycle, overwritten at every stage change:
  ``slug | Stage N name | ref | timestamp | worktree | status``.
- ``merge.lock/``: created with an atomic ``mkdir``; its ``holder`` file names
  the cycle allowed to rebase, land its decisions and merge. One merge at a
  time is what keeps decision numbers and shared files collision-free.

Commands:
  beat <slug> --stage N --name NAME --ref REF --status TEXT
  show [<slug>] [--stale-minutes M]      list heartbeats, flag stale ones
  clear <slug>                           remove a finished cycle's heartbeat
  lock <slug> [--stale-minutes M] [--break-stale]
  unlock <slug> [--force]
  lock-status

Exit codes: 0 ok, 1 not found, 2 usage error, 3 lock held by another cycle,
4 lock held by another cycle and stale (re-run with --break-stale after
checking that cycle's heartbeat). Standard library only.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEP = " | "
LOCK_DIR = "merge.lock"


def now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def state_dir(override: str | None) -> Path:
    if override:
        path = Path(override)
    elif os.environ.get("SUNEX_SHIP_STATE_DIR"):
        path = Path(os.environ["SUNEX_SHIP_STATE_DIR"])
    else:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        path = Path(common) / "sunex-ship"
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_line(line: str) -> dict[str, str]:
    parts = line.rstrip("\n").split(SEP, 5)
    keys = ("slug", "stage", "ref", "timestamp", "worktree", "status")
    return dict(zip(keys, parts + [""] * (len(keys) - len(parts))))


def age_minutes(timestamp: str) -> float | None:
    try:
        then = datetime.fromisoformat(timestamp)
    except ValueError:
        return None
    return (now() - then) / timedelta(minutes=1)


def cmd_beat(root: Path, args: argparse.Namespace) -> int:
    fields = [args.slug, f"Stage {args.stage} {args.name}", args.ref, now().isoformat(), os.getcwd(), args.status]
    if any("\n" in field for field in fields):
        print("heartbeat fields must be single-line", file=sys.stderr)
        return 2
    target = root / f"{args.slug}.status"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(SEP.join(fields) + "\n", encoding="utf-8")
    tmp.replace(target)
    print(SEP.join(fields))
    return 0


def cmd_show(root: Path, args: argparse.Namespace) -> int:
    files = [root / f"{args.slug}.status"] if args.slug else sorted(root.glob("*.status"))
    files = [f for f in files if f.is_file()]
    if not files:
        print("no cycle in flight" if not args.slug else f"no heartbeat for {args.slug}")
        return 0 if not args.slug else 1
    for path in files:
        line = path.read_text(encoding="utf-8").strip()
        age = age_minutes(parse_line(line)["timestamp"])
        stale = age is None or age > args.stale_minutes
        print(("STALE " if stale else "") + line)
    return 0


def cmd_clear(root: Path, args: argparse.Namespace) -> int:
    target = root / f"{args.slug}.status"
    if target.exists():
        target.unlink()
    return 0


def read_holder(lock: Path) -> tuple[str, str]:
    try:
        slug, _, stamp = (lock / "holder").read_text(encoding="utf-8").strip().partition(SEP)
    except FileNotFoundError:
        return "", ""
    return slug, stamp


def write_holder(lock: Path, slug: str) -> None:
    (lock / "holder").write_text(f"{slug}{SEP}{now().isoformat()}\n", encoding="utf-8")


def cmd_lock(root: Path, args: argparse.Namespace) -> int:
    lock = root / LOCK_DIR
    try:
        lock.mkdir()
    except FileExistsError:
        holder, stamp = read_holder(lock)
        if holder == args.slug:
            print(f"merge lock already held by {args.slug}")
            return 0
        age = age_minutes(stamp)
        stale = age is None or age > args.stale_minutes
        if stale and args.break_stale:
            shutil.rmtree(lock)
            return cmd_lock(root, argparse.Namespace(**{**vars(args), "break_stale": False}))
        state = "STALE " if stale else ""
        print(f"{state}merge lock held by {holder or 'unknown'} since {stamp or 'unknown'}", file=sys.stderr)
        return 4 if stale else 3
    write_holder(lock, args.slug)
    print(f"merge lock acquired by {args.slug}")
    return 0


def cmd_unlock(root: Path, args: argparse.Namespace) -> int:
    lock = root / LOCK_DIR
    if not lock.exists():
        return 0
    holder, _ = read_holder(lock)
    if holder != args.slug and not args.force:
        print(f"merge lock is held by {holder or 'unknown'}, not {args.slug}; use --force only after checking", file=sys.stderr)
        return 3
    shutil.rmtree(lock)
    print(f"merge lock released by {args.slug}")
    return 0


def cmd_lock_status(root: Path, args: argparse.Namespace) -> int:
    lock = root / LOCK_DIR
    if not lock.exists():
        print("merge lock free")
        return 0
    holder, stamp = read_holder(lock)
    print(f"merge lock held by {holder or 'unknown'} since {stamp or 'unknown'}")
    return 0


def slug(value: str) -> str:
    if not SLUG_RE.fullmatch(value):
        raise argparse.ArgumentTypeError(f"{value!r} is not a kebab-case cycle slug")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--state-dir", help="override the state directory (tests, unusual layouts)")
    sub = parser.add_subparsers(dest="command", required=True)

    beat = sub.add_parser("beat")
    beat.add_argument("slug", type=slug)
    beat.add_argument("--stage", required=True)
    beat.add_argument("--name", required=True)
    beat.add_argument("--ref", default="-")
    beat.add_argument("--status", required=True)
    beat.set_defaults(fn=cmd_beat)

    show = sub.add_parser("show")
    show.add_argument("slug", nargs="?", type=slug)
    show.add_argument("--stale-minutes", type=float, default=120)
    show.set_defaults(fn=cmd_show)

    clear = sub.add_parser("clear")
    clear.add_argument("slug", type=slug)
    clear.set_defaults(fn=cmd_clear)

    lock = sub.add_parser("lock")
    lock.add_argument("slug", type=slug)
    lock.add_argument("--stale-minutes", type=float, default=90)
    lock.add_argument("--break-stale", action="store_true")
    lock.set_defaults(fn=cmd_lock)

    unlock = sub.add_parser("unlock")
    unlock.add_argument("slug", type=slug)
    unlock.add_argument("--force", action="store_true")
    unlock.set_defaults(fn=cmd_unlock)

    status = sub.add_parser("lock-status")
    status.set_defaults(fn=cmd_lock_status)

    args = parser.parse_args(argv)
    try:
        root = state_dir(args.state_dir)
    except subprocess.CalledProcessError:
        print("not inside a git repository; pass --state-dir", file=sys.stderr)
        return 2
    return args.fn(root, args)


if __name__ == "__main__":
    raise SystemExit(main())
