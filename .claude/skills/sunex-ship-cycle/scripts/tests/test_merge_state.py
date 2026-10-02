from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import merge_state

LESSONS_SCRIPT = SCRIPTS.parents[1] / "tlc-spec-driven" / "scripts" / "lessons.py"

HEADING_STATE = """# STATE

## Decisions

### AD-001
- **Decision**: Use PostgreSQL range types for effective dating
- **Status**: active

### AD-002
- **Decision**: Domain namespaces enforced by architecture tests
- **Status**: active

## Handoff

- **Feature**: none
"""

TABLE_STATE = """# STATE

## Decisions Log

| ID | Decision | Source |
|---|---|---|
| AD-001 | Effective dating with range types | ADR |
| AD-007 | Agents act through the shared policy | ADR |

## Handoff

nothing in flight
"""


class MergeStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.feature = self.root / ".specs" / "features" / "vacation-split"
        self.feature.mkdir(parents=True)
        self.state = self.root / ".specs" / "project" / "STATE.md"
        self.state.parent.mkdir(parents=True)

    def run_cmd(self, *extra: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = merge_state.main(["vacation-split", "--root", str(self.root), "--lessons-script", str(LESSONS_SCRIPT), *extra])
        return code, out.getvalue(), err.getvalue()

    def write_context(self, decisions: str) -> None:
        (self.feature / "context.md").write_text(
            "# Vacation split context\n\n## Gray areas\n\nSee AD-PENDING-2 below.\n\n"
            f"## Project decisions (pending numbers)\n\n{decisions}\n\n## Out of scope\n\nNothing.\n"
        )

    def test_heading_entries_are_numbered_after_the_highest_and_placed_before_handoff(self) -> None:
        self.state.write_text(HEADING_STATE)
        self.write_context(
            "### AD-PENDING-1\n- **Decision**: Split rules live in the Absence domain\n\n"
            "### AD-PENDING-2\n- **Decision**: Article 134 reading recorded in code\n- **Supersedes**: AD-PENDING-1"
        )
        (self.feature / "design.md").write_text("Follows AD-PENDING-2.\n")
        code, out, _ = self.run_cmd()
        self.assertEqual(code, 0, out)
        state = self.state.read_text()
        self.assertLess(state.index("### AD-003"), state.index("### AD-004"))
        self.assertLess(state.index("### AD-004"), state.index("## Handoff"))
        self.assertIn("- **Supersedes**: AD-003", state)
        self.assertIn("### AD-002\n- **Decision**: Domain namespaces enforced by architecture tests\n- **Status**: active\n\n### AD-003", state)
        self.assertNotIn("PENDING", state)
        self.assertEqual((self.feature / "design.md").read_text(), "Follows AD-004.\n")
        self.assertIn("See AD-004 below.", (self.feature / "context.md").read_text())

    def test_table_rows_join_the_existing_table(self) -> None:
        self.state.write_text(TABLE_STATE)
        self.write_context("| ID | Decision | Source |\n|---|---|---|\n| AD-PENDING-1 | Split rules in Absence | context.md |")
        self.assertEqual(self.run_cmd()[0], 0)
        state = self.state.read_text()
        self.assertIn("| AD-007 | Agents act through the shared policy | ADR |\n| AD-008 | Split rules in Absence | context.md |\n\n## Handoff", state)
        self.assertEqual(state.count("| ID | Decision | Source |"), 1)

    def test_creates_the_decisions_section_when_state_is_missing(self) -> None:
        self.write_context("### AD-PENDING-1\n- **Decision**: First decision")
        self.assertEqual(self.run_cmd()[0], 0)
        self.assertIn("## Decisions\n\n### AD-001\n- **Decision**: First decision\n", self.state.read_text())

    def test_second_run_is_a_no_op(self) -> None:
        self.state.write_text(HEADING_STATE)
        self.write_context("### AD-PENDING-1\n- **Decision**: Once")
        self.run_cmd()
        first = self.state.read_text()
        code, out, _ = self.run_cmd()
        self.assertEqual(code, 0)
        self.assertEqual(self.state.read_text(), first)
        self.assertIn("landed 0 decision(s)", out)

    def test_dry_run_changes_nothing(self) -> None:
        self.state.write_text(HEADING_STATE)
        self.write_context("### AD-PENDING-1\n- **Decision**: Maybe")
        code, out, _ = self.run_cmd("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("would land AD-PENDING-1 as AD-003", out)
        self.assertEqual(self.state.read_text(), HEADING_STATE)

    def test_pending_lessons_are_replayed_through_lessons_py(self) -> None:
        lesson = {"signal": "surviving_mutant", "source": "app/Absence/SplitRule.php:42",
                  "text": "Assert the 14-day minimum at exactly 14 and 13 days.", "scope": "absence"}
        (self.feature / "lessons-pending.jsonl").write_text(json.dumps(lesson) + "\n")
        code, out, err = self.run_cmd()
        self.assertEqual(code, 0, err)
        self.assertIn("1 lesson(s)", out)
        store = json.loads((self.root / ".specs" / "lessons.json").read_text())
        self.assertIn("14-day minimum", json.dumps(store))
        self.assertFalse((self.feature / "lessons-pending.jsonl").exists())
        self.assertTrue((self.feature / "lessons-recorded.jsonl").exists())

    def test_incomplete_lesson_fails_without_writing(self) -> None:
        (self.feature / "lessons-pending.jsonl").write_text(json.dumps({"signal": "gate_fail"}) + "\n")
        code, _, err = self.run_cmd()
        self.assertEqual(code, 1)
        self.assertIn("missing source, text", err)
        self.assertTrue((self.feature / "lessons-pending.jsonl").exists())

    def test_slug_that_is_a_path_is_rejected(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "context.md").write_text("## Project decisions\n\n### AD-PENDING-1\n- **Decision**: Escaped\n")
        for value in (str(outside), "../outside"):
            with self.subTest(slug=value), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                merge_state.main([value, "--root", str(self.root)])
            self.assertEqual(raised.exception.code, 2)
        self.assertFalse(self.state.exists())

    def test_unknown_feature_is_a_usage_error(self) -> None:
        with redirect_stderr(io.StringIO()):
            self.assertEqual(merge_state.main(["nope", "--root", str(self.root)]), 2)


if __name__ == "__main__":
    unittest.main()
