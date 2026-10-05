"""Plain dataclasses passed between pipeline stages (all JSON-serialisable)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_REPO_RE = re.compile(r"github\.com/([^/]+/[^/]+)/(?:issues|pull)/(\d+)")


def parse_issue_url(url: str) -> tuple[str, int]:
    """Return ``(owner/repo, number)`` for a GitHub issue URL."""
    match = _REPO_RE.search(url)
    if not match:
        raise ValueError(f"not a GitHub issue URL: {url!r}")
    return match.group(1), int(match.group(2))


@dataclass
class Issue:
    repo: str
    number: int
    title: str
    body: str
    url: str
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    comments: int = 0
    created_at: str = ""

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Issue:
        url = data.get("html_url", "")
        repo, number = parse_issue_url(url)
        return cls(
            repo=repo,
            number=number,
            title=data.get("title") or "",
            body=data.get("body") or "",
            url=url,
            labels=[label.get("name", "") for label in data.get("labels", [])],
            assignees=[user.get("login", "") for user in data.get("assignees", [])],
            comments=int(data.get("comments") or 0),
            created_at=data.get("created_at") or "",
        )


@dataclass
class Requirements:
    """What the issue actually asks for, split into the parts a contributor needs."""

    problem: str = ""
    expected: str = ""
    where: str = ""
    verify: str = ""
    scope: str = ""
    paths: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    issue_refs: list[int] = field(default_factory=list)
    code_blocks: list[str] = field(default_factory=list)


@dataclass
class Rule:
    category: str
    text: str
    source: str


@dataclass
class RuleSet:
    rules: list[Rule] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    sources_found: list[str] = field(default_factory=list)
    sources_missing: list[str] = field(default_factory=list)
    pr_template: str = ""
    changelog_hint: str = ""


@dataclass
class CodeLocation:
    path: str
    snippet: str
    start_line: int
    matched: list[str] = field(default_factory=list)


@dataclass
class Triage:
    issue: Issue
    score: int
    reasons: list[str] = field(default_factory=list)
    rejected: str = ""
