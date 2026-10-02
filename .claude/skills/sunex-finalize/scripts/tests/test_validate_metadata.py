from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from helpers import TempRepo, valid_message

import validate_metadata


def run(*argv: str) -> tuple[int, str]:
    err = io.StringIO()
    with redirect_stderr(err), redirect_stdout(io.StringIO()):
        code = validate_metadata.main(list(argv))
    return code, err.getvalue()


class BranchTest(unittest.TestCase):
    def test_accepts_type_and_kebab_summary(self) -> None:
        self.assertEqual(run("--branch", "feat/employee-record")[0], 0)
        self.assertEqual(run("--branch", "fix/12-vacation-split")[0], 0)

    def test_rejects_unknown_type_and_uppercase(self) -> None:
        self.assertEqual(run("--branch", "feature/employee-record")[0], 1)
        self.assertEqual(run("--branch", "feat/Employee-Record")[0], 1)


class HeaderTest(unittest.TestCase):
    def test_accepts_conventional_title(self) -> None:
        self.assertEqual(run("--pr-title", "feat(absence): enforce the vacation split rules")[0], 0)

    def test_rejects_long_uppercase_or_period(self) -> None:
        self.assertEqual(run("--pr-title", "feat(absence): " + "x" * 60)[0], 1)
        self.assertEqual(run("--pr-title", "feat(absence): Enforce rules")[0], 1)
        self.assertEqual(run("--pr-title", "feat(absence): enforce rules.")[0], 1)

    def test_rejects_internal_ids_in_title(self) -> None:
        code, err = run("--pr-title", "feat(absence): implement AD-012 split rule")
        self.assertEqual(code, 1)
        self.assertIn("internal reference", err)


class MessageTest(unittest.TestCase):
    def test_accepts_header_body_and_single_trailer(self) -> None:
        self.assertEqual(run("--message", valid_message())[0], 0)

    def test_requires_the_assisted_by_trailer(self) -> None:
        code, err = run("--message", valid_message().replace("Assisted-by: Claude Code\n", ""))
        self.assertEqual(code, 1)
        self.assertIn("Assisted-by: Claude Code", err)

    def test_rejects_co_author_trailer(self) -> None:
        message = valid_message().replace(
            "Assisted-by: Claude Code", "Assisted-by: Claude Code\nCo-Authored-By: Someone <a@b.c>"
        )
        self.assertEqual(run("--message", message)[0], 1)

    def test_rejects_generated_with_claude_but_not_other_generators(self) -> None:
        bad = valid_message().replace("stores each", "Generated with Claude Code, stores each")
        fine = valid_message().replace("stores each", "routes generated with Wayfinder; stores each")
        self.assertEqual(run("--message", bad)[0], 1)
        self.assertEqual(run("--message", fine)[0], 0)

    def test_requires_a_body(self) -> None:
        code, err = run("--message", "fix(people): correct the hire date\n\nAssisted-by: Claude Code\n")
        self.assertEqual(code, 1)
        self.assertIn("missing body", err)

    def test_rejects_internal_ids_in_body(self) -> None:
        for token in ("T12", "AD-007", "VAC-03", "phase 2", ".specs/features/x"):
            with self.subTest(token=token):
                message = valid_message().replace("stores each", f"see {token}; stores each")
                self.assertEqual(run("--message", message)[0], 1)

    def test_keeps_esocial_event_codes_and_hashes_legal(self) -> None:
        message = valid_message().replace("stores each", "maps S-2200 and S-2230 with SHA-256 signatures; stores each")
        self.assertEqual(run("--message", message)[0], 0)


class RangeTest(unittest.TestCase):
    def test_validates_every_commit_in_a_range(self) -> None:
        with TempRepo() as repo:
            repo.commit("chore: initial")
            repo.git("checkout", "-q", "-b", "feat/x")
            repo.commit(valid_message(), **{"a.txt": "a"})
            self.assertEqual(run("--range", "main..HEAD")[0], 0)
            repo.commit("feat: no body", **{"b.txt": "b"})
            self.assertEqual(run("--range", "main..HEAD")[0], 1)


if __name__ == "__main__":
    unittest.main()
