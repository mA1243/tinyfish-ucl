import unittest

from firstpr.draft import branch_name, commit_type, render
from firstpr.guidelines import analyse, extract_config_rules, extract_rules
from firstpr.issue_parser import parse_issue
from firstpr.locate import locate
from firstpr.models import Issue

from .fixtures import CONTRIBUTING, ISSUE_BODY, PREF_COMBINE, PYPROJECT, FakeGitHub


class RuleTests(unittest.TestCase):
    def test_rules_and_commands_extracted(self):
        rules, commands = extract_rules(CONTRIBUTING, "CONTRIBUTING.md")
        text = " | ".join(r.text for r in rules)
        self.assertIn("Line length", text)
        self.assertIn("never bare print()", text)
        self.assertIn("changelog.d", text)
        self.assertIn("ruff check src/ tests/", commands)
        self.assertIn("pytest tests/ -v --tb=short", commands)

    def test_wrapped_lines_become_one_rule(self):
        rules, _ = extract_rules(CONTRIBUTING, "CONTRIBUTING.md")
        joined = [r.text for r in rules if "changelog.d" in r.text]
        self.assertEqual(len(joined), 1)
        self.assertIn("instead of editing CHANGELOG.md", joined[0])

    def test_table_rows_are_not_rules(self):
        rules, _ = extract_rules(CONTRIBUTING, "CONTRIBUTING.md")
        self.assertFalse(any("table row" in r.text for r in rules))

    def test_categories(self):
        rules, _ = extract_rules(CONTRIBUTING, "CONTRIBUTING.md")
        cats = {r.category for r in rules}
        self.assertTrue({"style", "changelog", "testing"} <= cats)

    def test_pyproject_rules(self):
        out = extract_config_rules("pyproject.toml", PYPROJECT)
        self.assertEqual(out[0].text, "Maximum line length is 100")
        self.assertIn("E", out[1].text)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.gh = FakeGitHub({
            "CONTRIBUTING.md": CONTRIBUTING,
            "pyproject.toml": PYPROJECT,
            "src/soup_cli/utils/preference_combine.py": PREF_COMBINE,
        })
        self.issue = Issue("o/soup", 1645, "Pin dpo/ipo beta fields", ISSUE_BODY,
                           "https://github.com/o/soup/issues/1645", ["good first issue", "tests"])

    def test_analyse_tolerates_missing_files(self):
        rules = analyse(self.gh, "o/soup")
        self.assertIn("CONTRIBUTING.md", rules.sources_found)
        self.assertIn(".github/PULL_REQUEST_TEMPLATE.md", rules.sources_missing)
        self.assertTrue(rules.rules)

    def test_locate_cuts_snippet_around_symbol(self):
        req = parse_issue(self.issue.body)
        found = locate(self.gh, "o/soup", req)
        self.assertEqual(len(found), 1)  # the two other files do not exist in the fake repo
        self.assertEqual(found[0].path, "src/soup_cli/utils/preference_combine.py")
        self.assertIn("blend_loss_params", found[0].snippet)
        self.assertIn("blend_loss_params", found[0].matched)

    def test_locate_falls_back_to_tree_by_basename(self):
        gh = FakeGitHub({"pkg/deep/preference_combine.py": PREF_COMBINE})
        req = parse_issue("`preference_combine.py` and `blend_loss_params`")
        found = locate(gh, "o/r", req)
        self.assertEqual(found[0].path, "pkg/deep/preference_combine.py")

    def test_render_end_to_end(self):
        req = parse_issue(self.issue.body)
        rules = analyse(self.gh, "o/soup")
        text = render(self.issue, req, rules, locate(self.gh, "o/soup", req))
        for needle in ("Closes #1645", "Maximum line length is 100", "blend_loss_params",
                       "Claim comment", "Nothing has been posted"):
            self.assertIn(needle, text)

    def test_commit_type_and_branch(self):
        self.assertEqual(commit_type(self.issue), "test")
        self.assertEqual(branch_name(self.issue), "fix/1645-pin-dpo-ipo-beta-fields")


if __name__ == "__main__":
    unittest.main()
