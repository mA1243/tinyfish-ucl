"""Rank candidate issues and reject the ones a newcomer cannot or should not take."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import Issue, Triage
from .tinyfish import TinyFish

BLOCKING_LABELS = {
    "on hold", "blocked", "infra-blocked", "wontfix", "duplicate", "invalid",
    "needs discussion", "question", "stale",
}
_BLOCKED_BODY = re.compile(r"\b(blocked by|depends on|waiting (?:on|for))\s+#\d+", re.I)
_HARDWARE = re.compile(r"\b(needs? (?:a )?gpu|cuda device|specific hardware)\b", re.I)
_HAS_PATH = re.compile(r"`[\w./-]+\.\w{1,5}(?::\d+)?`")
_HAS_VERIFY = re.compile(r"(how to verify|acceptance criteria|expected|to reproduce)", re.I)


def triage(issue: Issue, now: datetime | None = None) -> Triage:
    now = now or datetime.now(timezone.utc)
    labels = {label.lower() for label in issue.labels}
    blocked = labels & BLOCKING_LABELS
    if blocked:
        return Triage(issue, 0, rejected=f"blocking label(s): {', '.join(sorted(blocked))}")
    if issue.assignees:
        return Triage(issue, 0, rejected=f"already assigned to {', '.join(issue.assignees)}")
    if _BLOCKED_BODY.search(issue.body):
        return Triage(issue, 0, rejected="body says it is blocked by another issue")
    if _HARDWARE.search(issue.body):
        return Triage(issue, 0, rejected="needs special hardware")

    score, reasons = 0, []
    if _HAS_PATH.search(issue.body):
        score += 3
        reasons.append("names the files to change")
    if _HAS_VERIFY.search(issue.body):
        score += 2
        reasons.append("states expected behaviour / how to verify")
    if "```" in issue.body:
        score += 1
        reasons.append("includes a code sample")
    if issue.comments == 0:
        score += 1
        reasons.append("nobody has commented (unclaimed)")
    words = len(issue.body.split())
    if words < 40:
        score -= 2
        reasons.append("very short body, likely under-specified")
    elif words > 700:
        score -= 1
        reasons.append("long body, may be larger than it looks")
    if issue.created_at:
        try:
            created = datetime.fromisoformat(issue.created_at.replace("Z", "+00:00"))
            if (now - created).days <= 7:
                score += 1
                reasons.append("filed within the last week")
        except ValueError:
            pass
    return Triage(issue, score, reasons)


def rank(issues: list[Issue]) -> tuple[list[Triage], list[Triage]]:
    """Return ``(accepted sorted best-first, rejected)``."""
    results = [triage(issue) for issue in issues]
    accepted = sorted((t for t in results if not t.rejected), key=lambda t: -t.score)
    return accepted, [t for t in results if t.rejected]


_CLAIM_SCHEMA = {
    "type": "object",
    "properties": {
        "already_claimed": {"type": "boolean"},
        "linked_pull_requests": {"type": "array", "items": {"type": "string"}},
        "claim_evidence": {"type": "string"},
    },
    "required": ["already_claimed", "linked_pull_requests"],
}


def check_competition(tf: TinyFish, issue: Issue) -> dict:
    """Live-web check (browser agent): has someone claimed it or opened a PR already?

    This is the step an API cannot do well: it reads the rendered issue page, including
    comments and the 'linked pull requests' sidebar.
    """
    goal = (
        "Open this GitHub issue page. Report whether any comment says someone is working "
        "on or has claimed it, and list the URLs of any linked or referenced pull requests. "
        "Do not log in, comment, or change anything."
    )
    return tf.run_agent(issue.url, goal, _CLAIM_SCHEMA)
