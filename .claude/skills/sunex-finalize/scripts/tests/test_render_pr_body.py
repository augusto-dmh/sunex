from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from helpers import SCRIPTS

import render_pr_body

TEMPLATE = SCRIPTS.parents[3] / ".github" / "pull_request_template.md"
TITLES = render_pr_body.template_titles(TEMPLATE)


def draft(**overrides: str) -> str:
    bodies = {title: f"Text for {title.lower()}." for title in TITLES}
    bodies["Checklist"] = "- [x] Everything is done"
    bodies.update(overrides)
    return "\n\n".join(f"## {title}\n\n{body}" for title, body in bodies.items() if body is not None) + "\n"


def run(text: str, *extra: str) -> tuple[int, str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(text, encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = render_pr_body.main(["--draft", str(path), "--template", str(TEMPLATE), *extra])
    return code, out.getvalue(), err.getvalue()


class TemplateTest(unittest.TestCase):
    def test_template_has_the_twelve_sunex_sections(self) -> None:
        self.assertEqual(
            TITLES,
            ["Description", "Context", "Architecture", "Main changes", "Decisions", "Tests", "Configuration",
             "Dependencies", "Impact", "How to validate", "Checklist", "AI assistance"],
        )


class RenderTest(unittest.TestCase):
    def test_complete_draft_passes_and_is_printed(self) -> None:
        code, out, _ = run(draft())
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("## Description"))

    def test_missing_and_empty_sections_fail(self) -> None:
        missing = draft().replace("## Impact\n\nText for impact.\n\n", "")
        self.assertIn("missing section '## Impact'", run(missing)[2])
        self.assertIn("is empty", run(draft(Impact=""))[2])

    def test_extra_and_reordered_sections_fail(self) -> None:
        self.assertEqual(run(draft() + "\n## Summary\n\nMore.\n")[0], 1)
        swapped = draft().replace("## Description", "## TMP").replace("## Context", "## Description").replace("## TMP", "## Context")
        self.assertIn("out of order", run(swapped)[2])

    def test_leftover_template_comment_fails(self) -> None:
        self.assertEqual(run(draft(Impact="<!-- Who is affected -->"))[0], 1)

    def test_internal_reference_fails_unless_allowed(self) -> None:
        text = draft(Decisions="Adds ADR-0004 for the time model.")
        self.assertEqual(run(text)[0], 1)
        self.assertEqual(run(text, "--allow", "ADR-0004")[0], 0)

    def test_assistant_attribution_fails(self) -> None:
        self.assertEqual(run(draft(**{"AI assistance": "Generated with Claude Code"}))[0], 1)

    def test_hard_wrap_and_unchecked_items_only_warn(self) -> None:
        text = draft(Context="This sentence was wrapped\nat a column width.", Checklist="- [ ] Browser test")
        code, _, err = run(text)
        self.assertEqual(code, 0)
        self.assertIn("hard-wrapped", err)
        self.assertIn("unchecked item", err)

    def test_headings_inside_code_fences_are_not_sections(self) -> None:
        self.assertEqual(run(draft(Tests="```md\n## Not a section\n```"))[0], 0)


if __name__ == "__main__":
    unittest.main()
