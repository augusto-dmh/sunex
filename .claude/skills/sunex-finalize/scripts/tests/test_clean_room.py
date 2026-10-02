from __future__ import annotations

import io
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from helpers import TempRepo

import clean_room

# Stand-in terms; the real list never enters the repository.
TERMS = "acmecorp\n# a comment line\nzebraware  # trailing comment\n"


def run(repo: TempRepo, *extra: str) -> tuple[int, str]:
    terms = repo.write("../terms.txt", TERMS)
    err = io.StringIO()
    with redirect_stderr(err), redirect_stdout(io.StringIO()):
        code = clean_room.main(["--base", "main", "--terms-file", str(terms), *extra])
    return code, err.getvalue()


class CleanRoomTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = TempRepo().__enter__()
        self.addCleanup(self.repo.__exit__, None, None, None)
        self.repo.commit("chore: base", **{"README.md": "mentions acmecorp before the branch\n"})
        self.repo.git("checkout", "-q", "-b", "feat/x")

    def test_clean_branch_passes_and_ignores_existing_mentions(self) -> None:
        self.repo.commit("feat: add file", **{"app.php": "<?php // fine\n"})
        self.assertEqual(run(self.repo)[0], 0)

    def test_added_line_is_case_insensitive_and_located(self) -> None:
        self.repo.commit("feat: add file", **{"app.php": "ok\n// built for AcmeCorp\n"})
        code, err = run(self.repo)
        self.assertEqual(code, 1)
        self.assertIn("app.php:2", err)

    def test_commit_message_branch_and_extra_file_are_scanned(self) -> None:
        self.repo.commit("feat: port the zebraware flow")
        self.assertIn("commit", run(self.repo)[1])
        self.repo.git("commit", "-q", "--amend", "--allow-empty", "-m", "feat: neutral")
        body = self.repo.write("../body.md", "## Context\n\nLike zebraware.\n")
        self.assertIn("body.md:3", run(self.repo, "--file", str(body))[1])

    def test_uncommitted_and_untracked_changes_are_scanned(self) -> None:
        self.repo.write("notes.md", "acmecorp\n")
        self.assertEqual(run(self.repo)[0], 1)

    def test_lockfile_hits_only_warn(self) -> None:
        self.repo.commit("build: lock", **{"package-lock.json": '{"integrity": "sha512-xxACMECORPyy"}\n'})
        code, err = run(self.repo)
        self.assertEqual(code, 0)
        self.assertIn("WARN", err)

    def test_missing_term_list_fails_closed(self) -> None:
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"SUNEX_CLEAN_ROOM_TERMS": "/nonexistent/terms"}), redirect_stderr(err):
            self.assertEqual(clean_room.main(["--base", "main"]), 2)
        self.assertIn("fails closed", err.getvalue())


if __name__ == "__main__":
    unittest.main()
