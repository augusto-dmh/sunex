"""Shared helpers for the sunex-finalize script tests."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


class TempRepo:
    """A throwaway git repository; use as a context manager that also chdirs into it."""

    def __enter__(self) -> "TempRepo":
        self._dir = tempfile.TemporaryDirectory()
        # The repository sits one level down so tests can write files "../" outside it.
        self.path = Path(self._dir.name) / "repo"
        self.path.mkdir()
        self._cwd = os.getcwd()
        os.chdir(self.path)
        self.git("init", "-q", "-b", "main")
        return self

    def __exit__(self, *exc: object) -> None:
        os.chdir(self._cwd)
        self._dir.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.path, env=GIT_ENV, check=True, capture_output=True, text=True).stdout

    def write(self, name: str, content: str) -> Path:
        target = self.path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def commit(self, message: str, **files: str) -> None:
        for name, content in files.items():
            self.write(name, content)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)


def valid_message(header: str = "feat(people): add the employee record") -> str:
    return (
        f"{header}\n\n"
        "HR needs one place to read an employee's dated history, so the record\n"
        "stores each change with its effective date.\n\n"
        "Assisted-by: Claude Code\n"
    )
