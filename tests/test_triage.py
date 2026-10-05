import unittest
from datetime import datetime, timezone

from firstpr.models import Issue
from firstpr.triage import rank, triage

from .fixtures import ISSUE_BODY

NOW = datetime(2026, 10, 5, tzinfo=timezone.utc)


def make(**kw) -> Issue:
    base = dict(
        repo="o/r", number=1, title="t", body=ISSUE_BODY,
        url="https://github.com/o/r/issues/1", labels=["good first issue"],
        assignees=[], comments=0, created_at="2026-10-04T00:00:00Z",
    )
    base.update(kw)
    return Issue(**base)


class TriageTests(unittest.TestCase):
    def test_well_specified_issue_scores_high(self):
        result = triage(make(), NOW)
        self.assertFalse(result.rejected)
        self.assertGreaterEqual(result.score, 8)

    def test_blocking_label_rejected(self):
        result = triage(make(labels=["good first issue", "On Hold"]), NOW)
        self.assertIn("on hold", result.rejected)

    def test_assigned_rejected(self):
        self.assertIn("assigned", triage(make(assignees=["bob"]), NOW).rejected)

    def test_blocked_by_body_rejected(self):
        self.assertIn("blocked", triage(make(body="blocked by #302 " + "word " * 50), NOW).rejected)

    def test_hardware_rejected(self):
        self.assertIn("hardware", triage(make(body="This needs a GPU to test"), NOW).rejected)

    def test_short_body_penalised(self):
        self.assertLess(triage(make(body="add --quiet"), NOW).score, 3)

    def test_rank_orders_best_first(self):
        good, thin = make(number=1), make(number=2, body="add --quiet")
        accepted, rejected = rank([thin, good, make(number=3, assignees=["x"])])
        self.assertEqual([t.issue.number for t in accepted], [1, 2])
        self.assertEqual(len(rejected), 1)


if __name__ == "__main__":
    unittest.main()
