from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from helpers import TempRepo, valid_message

import validate_metadata

# A stand-in for the repository's scripts/check-commit-msg.sh: it only
# rejects the scope "payroll", so a test can tell which rules ran.
FAKE_CHECKER = """#!/bin/sh
msg=$(cat)
case "$msg" in *"(payroll)"*) echo "unknown scope payroll" >&2; exit 1 ;; esac
exit 0
"""


def setUpModule() -> None:
    # Most tests pin the built-in rules; DelegationTest switches the checker on.
    patcher = mock.patch.dict(os.environ, {"SUNEX_COMMIT_CHECKER": ""})
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


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
        for title in ("feat(absence): implement AD-012 split rule", "feat(absence): apply AD-PENDING-2 split rule"):
            with self.subTest(title=title):
                code, err = run("--pr-title", title)
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

    def test_rejects_attribution_outside_the_trailer_paragraph(self) -> None:
        # The trailer stays valid, so only the attribution patterns can fail these.
        for line in ("Co-Authored-By: Someone <a@b.c>", "\U0001F916 Generated with [Claude Code](https://claude.com)",
                     "Written with help \U0001F916"):
            with self.subTest(line=line):
                message = valid_message().replace("stores each", f"stores each\n{line}\nand")
                code, err = run("--message", message)
                self.assertEqual(code, 1)
                self.assertIn("forbidden attribution", err)

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
        for token in ("T12", "AD-007", "AD-PENDING-1", "VAC-03", "phase 2", ".specs/features/x"):
            with self.subTest(token=token):
                message = valid_message().replace("stores each", f"see {token}; stores each")
                self.assertEqual(run("--message", message)[0], 1)

    def test_keeps_public_codes_and_hashes_legal(self) -> None:
        codes = "maps S-2200 and S-2230 with SHA-256 signatures, CID-10 codes, NR-15 grades and PSR-12; stores each"
        self.assertEqual(run("--message", valid_message().replace("stores each", codes))[0], 0)
        self.assertEqual(run("--pr-title", "feat(absence): store the CID-10 code of medical certificates")[0], 0)

    def test_allow_accepts_a_named_public_identifier(self) -> None:
        title = "docs(adr): record the time model in ADR-0015"
        self.assertEqual(run("--pr-title", title)[0], 1)
        self.assertEqual(run("--pr-title", title, "--allow", "ADR-0015")[0], 0)


class RangeTest(unittest.TestCase):
    def test_validates_every_commit_in_a_range(self) -> None:
        with TempRepo() as repo:
            repo.commit("chore: initial")
            repo.git("checkout", "-q", "-b", "feat/x")
            repo.commit(valid_message(), **{"a.txt": "a"})
            self.assertEqual(run("--range", "main..HEAD")[0], 0)
            repo.commit("feat: no body", **{"b.txt": "b"})
            self.assertEqual(run("--range", "main..HEAD")[0], 1)

    def test_reports_the_number_of_commits_checked(self) -> None:
        with TempRepo() as repo:
            repo.commit("chore: initial")
            repo.git("checkout", "-q", "-b", "feat/x")
            repo.commit(valid_message(), **{"a.txt": "a"})
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                self.assertEqual(validate_metadata.main(["--range", "main..HEAD"]), 0)
            self.assertIn("(1 commit checked)", out.getvalue())

    def test_empty_range_is_a_usage_error(self) -> None:
        with TempRepo() as repo:
            repo.commit("chore: initial")
            repo.git("checkout", "-q", "-b", "feat/x")
            code, err = run("--range", "main..HEAD")
            self.assertEqual(code, 2)
            self.assertIn("no commits", err)


class InputTest(unittest.TestCase):
    def test_missing_message_file_is_a_usage_error(self) -> None:
        self.assertEqual(run("--message-file", "/nonexistent/msg.txt")[0], 2)


class DelegationTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.checker = Path(tmp.name) / "check-commit-msg.sh"
        self.checker.write_text(FAKE_CHECKER)

    def run_with_checker(self, *argv: str) -> tuple[int, str]:
        with mock.patch.dict(os.environ, {"SUNEX_COMMIT_CHECKER": str(self.checker)}):
            return run(*argv)

    def test_header_rules_come_from_the_repository_checker(self) -> None:
        code, err = self.run_with_checker("--pr-title", "feat(payroll): add salaries")
        self.assertEqual(code, 1)
        self.assertIn("check-commit-msg.sh: unknown scope payroll", err)
        # The built-in shape rule (lowercase) no longer applies; the checker decides.
        self.assertEqual(self.run_with_checker("--pr-title", "feat(people): Add persons")[0], 0)

    def test_whole_message_goes_to_the_checker(self) -> None:
        message = valid_message().replace("stores each", "(payroll) stores each")
        self.assertIn("unknown scope payroll", self.run_with_checker("--message", message)[1])

    def test_sunex_only_rules_still_apply(self) -> None:
        self.assertEqual(self.run_with_checker("--message", "fix(people): correct\n\nAssisted-by: Claude Code\n")[0], 1)
        self.assertEqual(self.run_with_checker("--pr-title", "feat(people): apply AD-007")[0], 1)
        self.assertEqual(self.run_with_checker("--pr-title", "feat(people): add persons.")[0], 1)

    def test_checker_is_found_at_the_repository_root(self) -> None:
        with TempRepo() as repo:
            repo.write("scripts/check-commit-msg.sh", FAKE_CHECKER)
            with mock.patch.dict(os.environ, clear=False) as env:
                env.pop("SUNEX_COMMIT_CHECKER", None)
                self.assertEqual(run("--pr-title", "feat(payroll): add salaries")[0], 1)
                self.assertEqual(run("--pr-title", "feat(people): add persons")[0], 0)


if __name__ == "__main__":
    unittest.main()
