from __future__ import annotations

import io
import os
import subprocess
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from helpers import GIT_ENV, TempRepo

import clean_room

# Stand-in terms; the real list never enters the repository.
TERMS = "acmecorp\n# a comment line\nzebraware  # trailing comment\nbig widget\n"
INTEGRITY = "sha512-" + "Q" * 40 + "ACMECORP" + "z" * 40 + "=="


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

    def assertFails(self, where: str, *extra: str) -> None:
        code, err = run(self.repo, *extra)
        self.assertEqual(code, 1, err)
        self.assertIn(where, err)

    def test_clean_branch_passes_and_ignores_existing_mentions(self) -> None:
        self.repo.commit("feat: add file", **{"app.php": "<?php // fine\n"})
        self.assertEqual(run(self.repo)[0], 0)

    def test_added_line_is_case_insensitive_and_located(self) -> None:
        self.repo.commit("feat: add file", **{"app.php": "ok\n// built for AcmeCorp\n"})
        self.assertFails("FAIL app.php:2")

    def test_added_line_starting_with_plus_plus_is_content_not_a_header(self) -> None:
        self.repo.commit("feat: add file", **{"a.md": "ok\n++ acmecorp in a diff sample\n"})
        self.assertFails("FAIL a.md:2")

    def test_commit_message_and_extra_file_are_scanned(self) -> None:
        self.repo.commit("feat: port the zebraware flow")
        self.assertFails("commit")
        self.repo.git("commit", "-q", "--amend", "--allow-empty", "-m", "feat: neutral")
        body = self.repo.write("../body.md", "## Context\n\nLike zebraware.\n")
        self.assertFails("body.md:3", "--file", str(body))

    def test_text_option_scans_the_pr_title(self) -> None:
        self.assertFails("--text 1", "--text", "feat: port the AcmeCorp importer")

    def test_branch_name_is_scanned(self) -> None:
        self.repo.git("checkout", "-q", "-b", "feat/acmecorp-port")
        self.assertFails("branch name")

    def test_path_of_a_new_file_is_scanned(self) -> None:
        self.repo.commit("feat: add file", **{"docs/acmecorp-notes.md": "neutral\n"})
        self.assertFails("path docs/acmecorp-notes.md")

    def test_author_and_committer_identity_are_scanned(self) -> None:
        env = {**GIT_ENV, "GIT_AUTHOR_EMAIL": "dev@acmecorp.com"}
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "feat: x"], cwd=self.repo.path, env=env, check=True)
        self.assertFails("author/committer")

    def test_uncommitted_tracked_and_untracked_changes_are_scanned(self) -> None:
        self.repo.write("README.md", "mentions acmecorp before the branch\nand zebraware now\n")
        self.assertFails("README.md:2")
        self.repo.git("checkout", "--", "README.md")
        self.repo.write("notes.md", "acmecorp\n")
        self.assertFails("notes.md:1")

    def test_wrapped_and_unicode_variants_match(self) -> None:
        self.repo.commit("feat: x\n\nWritten for the big\nwidget team.")
        self.assertFails("commit")
        self.repo.git("commit", "-q", "--amend", "--allow-empty", "-m", "feat: neutral")
        self.repo.commit("feat: add file", **{"a.md": "built for ＡＣＭＥcorp\n"})
        self.assertFails("a.md:1")

    def test_binary_files_are_scanned_as_bytes(self) -> None:
        self.repo.write("doc.pdf", "")
        (self.repo.path / "doc.pdf").write_bytes(b"%PDF\x00\x01 /Author (AcmeCorp)\n")
        self.repo.commit("feat: add fixture")
        self.assertFails("doc.pdf (binary)")

    def test_non_utf8_text_does_not_crash(self) -> None:
        (self.repo.path / "latin.txt").write_bytes(b"caf\xe9 is fine\n")
        self.repo.commit("feat: add file")
        self.assertEqual(run(self.repo)[0], 0)

    def test_lockfile_hits_inside_hashes_only_warn(self) -> None:
        self.repo.commit("build: lock", **{"package-lock.json": f'{{"integrity": "{INTEGRITY}"}}\n'})
        code, err = run(self.repo)
        self.assertEqual(code, 0, err)
        self.assertIn("WARN", err)

    def test_lockfile_hits_outside_hashes_fail(self) -> None:
        lock = '{"resolved": "https://npm.acmecorp.com/lodash/-/lodash-4.17.21.tgz"}\n'
        self.repo.commit("build: lock", **{"package-lock.json": lock})
        self.assertFails("FAIL package-lock.json:1")

    def test_missing_term_list_fails_closed(self) -> None:
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"SUNEX_CLEAN_ROOM_TERMS": "/nonexistent/terms"}), redirect_stderr(err):
            self.assertEqual(clean_room.main(["--base", "main"]), 2)
        self.assertIn("fails closed", err.getvalue())

    def test_missing_extra_file_is_a_usage_error(self) -> None:
        self.assertEqual(run(self.repo, "--file", "/nonexistent/body.md")[0], 2)


if __name__ == "__main__":
    unittest.main()
