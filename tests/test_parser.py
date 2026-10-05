import unittest

from firstpr.github import lenient_json
from firstpr.issue_parser import parse_issue

from .fixtures import ISSUE_BODY


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.req = parse_issue(ISSUE_BODY)

    def test_sections_are_split(self):
        self.assertIn("Untested code", self.req.problem)
        self.assertIn("DEFAULT_BETA", self.req.expected)
        self.assertIn("preference_combine.py", self.req.where)
        self.assertIn("def test_dpo_and_ipo", self.req.verify)
        self.assertIn("Not part of it", self.req.scope)

    def test_paths_in_first_mention_order_without_duplicates(self):
        self.assertEqual(
            self.req.paths,
            [
                "src/soup_cli/utils/preference_combine.py",
                "docs/training.md",
                "tests/test_v05311.py",
            ],
        )

    def test_symbols_and_refs(self):
        self.assertIn("blend_loss_params", self.req.symbols)
        self.assertIn("DEFAULT_BETA", self.req.symbols)
        self.assertEqual(self.req.issue_refs, [1425, 1556])

    def test_code_blocks_are_captured_and_not_mined_for_paths(self):
        self.assertEqual(len(self.req.code_blocks), 1)
        self.assertNotIn("params", self.req.paths)

    def test_verify_section_does_not_leak_into_expected(self):
        # "How to verify a fix" contains the word "fix" but is not the suggested fix.
        self.assertNotIn("def test_dpo_and_ipo", self.req.expected)

    def test_empty_body_does_not_crash(self):
        self.assertEqual(parse_issue("").paths, [])
        self.assertEqual(parse_issue("just prose here").problem, "just prose here")

    def test_bold_line_headings(self):
        req = parse_issue("**Where**\n`a/b.py`\n\n**Possible fix**\nChange it.\n")
        self.assertEqual(req.paths, ["a/b.py"])
        self.assertEqual(req.expected, "Change it.")


class LenientJsonTests(unittest.TestCase):
    def test_strict_json_passes_through(self):
        self.assertEqual(lenient_json('{"a": 1}'), {"a": 1})

    def test_markdown_escapes_are_undone(self):
        escaped = '{"html\\_url": "x", "n\\-1": 2}'
        self.assertEqual(lenient_json(escaped), {"html_url": "x", "n-1": 2})

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            lenient_json("<html>nope</html>")


if __name__ == "__main__":
    unittest.main()
