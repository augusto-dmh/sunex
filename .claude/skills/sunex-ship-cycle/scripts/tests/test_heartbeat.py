from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import heartbeat


class HeartbeatTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.state = Path(self._tmp.name)

    def run_cmd(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = heartbeat.main(["--state-dir", str(self.state), *argv])
        return code, out.getvalue(), err.getvalue()

    def age_lock(self, minutes: int) -> None:
        holder = self.state / "merge.lock" / "holder"
        slug, _, stamp = holder.read_text().strip().partition(" | ")
        old = heartbeat.now() - heartbeat.timedelta(minutes=minutes)
        holder.write_text(f"{slug} | {old.isoformat()}\n")

    def test_each_cycle_has_its_own_heartbeat(self) -> None:
        self.run_cmd("beat", "employee-record", "--stage", "1", "--name", "build", "--status", "task 3 of 7")
        self.run_cmd("beat", "org-chart", "--stage", "3", "--name", "review", "--ref", "PR #12", "--status", "lanes running")
        code, out, _ = self.run_cmd("show")
        self.assertEqual(code, 0)
        self.assertIn("employee-record | Stage 1 build | - |", out)
        self.assertIn("org-chart | Stage 3 review | PR #12 |", out)
        self.assertNotIn("STALE", out)

    def test_beat_overwrites_and_records_the_worktree(self) -> None:
        self.run_cmd("beat", "org-chart", "--stage", "1", "--name", "build", "--status", "a")
        self.run_cmd("beat", "org-chart", "--stage", "2", "--name", "publish", "--status", "b")
        line = (self.state / "org-chart.status").read_text()
        self.assertEqual(line.count("\n"), 1)
        fields = heartbeat.parse_line(line)
        self.assertEqual(fields["stage"], "Stage 2 publish")
        self.assertEqual(fields["worktree"], os.getcwd())
        self.assertEqual(fields["status"], "b")

    def test_status_text_may_contain_the_separator(self) -> None:
        self.run_cmd("beat", "org-chart", "--stage", "1", "--name", "build", "--status", "x | y")
        self.assertEqual(heartbeat.parse_line((self.state / "org-chart.status").read_text())["status"], "x | y")

    def test_separator_outside_the_status_is_rejected(self) -> None:
        for flag in ("--ref", "--name"):
            with self.subTest(flag=flag):
                argv = {"--stage": "1", "--name": "build", "--ref": "PR #1", "--status": "a"} | {flag: "x | y"}
                code, _, err = self.run_cmd("beat", "org-chart", *[part for pair in argv.items() for part in pair])
                self.assertEqual(code, 2)
                self.assertIn("only --status", err)
        self.assertFalse((self.state / "org-chart.status").exists())

    def test_old_heartbeats_are_flagged_stale_and_clear_removes_them(self) -> None:
        self.run_cmd("beat", "org-chart", "--stage", "1", "--name", "build", "--status", "a")
        self.assertIn("STALE", self.run_cmd("show", "--stale-minutes", "-1")[1])
        self.run_cmd("clear", "org-chart")
        self.assertEqual(self.run_cmd("show", "org-chart")[0], 1)

    def test_rejects_slugs_that_are_not_kebab_case(self) -> None:
        with self.assertRaises(SystemExit):
            self.run_cmd("beat", "Org Chart", "--stage", "1", "--name", "build", "--status", "a")

    def test_merge_lock_admits_one_cycle_at_a_time(self) -> None:
        self.assertEqual(self.run_cmd("lock", "employee-record")[0], 0)
        self.assertEqual(self.run_cmd("lock", "employee-record")[0], 0)
        code, _, err = self.run_cmd("lock", "org-chart")
        self.assertEqual(code, 3)
        self.assertIn("held by employee-record", err)
        self.assertEqual(self.run_cmd("unlock", "org-chart")[0], 3)
        self.assertEqual(self.run_cmd("unlock", "employee-record")[0], 0)
        self.assertEqual(self.run_cmd("lock", "org-chart")[0], 0)

    def test_stale_lock_is_reported_and_only_broken_on_request(self) -> None:
        self.run_cmd("lock", "employee-record")
        self.age_lock(200)
        self.assertEqual(self.run_cmd("lock", "org-chart")[0], 4)
        self.assertEqual(self.run_cmd("lock", "org-chart", "--break-stale")[0], 0)
        self.assertIn("held by org-chart", self.run_cmd("lock-status")[1])

    def test_holder_relocking_refreshes_the_stamp(self) -> None:
        self.run_cmd("lock", "employee-record")
        self.age_lock(200)
        self.assertEqual(self.run_cmd("lock", "employee-record")[0], 0)
        self.assertEqual(self.run_cmd("lock", "org-chart")[0], 3)

    def test_lock_without_a_holder_yet_is_held_not_stale(self) -> None:
        (self.state / "merge.lock").mkdir()
        code, _, err = self.run_cmd("lock", "org-chart", "--break-stale")
        self.assertEqual(code, 3)
        self.assertNotIn("STALE", err)

    def test_fresh_lock_is_not_broken_by_break_stale(self) -> None:
        self.run_cmd("lock", "employee-record")
        self.assertEqual(self.run_cmd("lock", "org-chart", "--break-stale")[0], 3)

    def test_default_state_dir_is_shared_by_worktrees(self) -> None:
        import subprocess

        env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@e.x",
               "GIT_COMMITTER_NAME": "T", "GIT_COMMITTER_EMAIL": "t@e.x"}
        env.pop("SUNEX_SHIP_STATE_DIR", None)
        repo = self.state / "repo"
        repo.mkdir()
        run = lambda *a, cwd=repo: subprocess.run(a, cwd=cwd, env=env, check=True, capture_output=True, text=True)
        run("git", "init", "-q", "-b", "main")
        run("git", "commit", "-q", "--allow-empty", "-m", "init")
        run("git", "worktree", "add", "-q", "-b", "feat/x", str(self.state / "wt"))
        cwd = os.getcwd()
        try:
            os.chdir(self.state / "wt")
            with redirect_stdout(io.StringIO()):
                heartbeat.main(["beat", "x", "--stage", "1", "--name", "build", "--status", "from worktree"])
        finally:
            os.chdir(cwd)
        self.assertTrue((repo / ".git" / "sunex-ship" / "x.status").is_file())


if __name__ == "__main__":
    unittest.main()
