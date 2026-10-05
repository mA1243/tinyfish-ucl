"""Assemble the contribution bundle: summary, rules checklist, code, claim, PR body."""
from __future__ import annotations

import json
import os
import re
import urllib.request

from .models import CodeLocation, Issue, Requirements, RuleSet

LLM_MODEL = os.environ.get("FIRSTPR_MODEL", "claude-sonnet-5-5")


def slugify(text: str, limit: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:limit].strip("-")


def commit_type(issue: Issue) -> str:
    labels = " ".join(issue.labels).lower()
    title = issue.title.lower()
    if "doc" in labels or title.startswith("docs"):
        return "docs"
    if "test" in labels or title.startswith("test"):
        return "test"
    if "bug" in labels or "fix" in title:
        return "fix"
    if "enhancement" in labels or "feature" in labels or title.startswith(("add", "implement")):
        return "feat"
    return "fix"


def branch_name(issue: Issue) -> str:
    kind = "fix" if commit_type(issue) in {"fix", "test", "docs"} else "feature"
    return f"{kind}/{issue.number}-{slugify(issue.title)}"


def claim_comment(issue: Issue, req: Requirements) -> str:
    plan = req.expected.strip().splitlines()[:3]
    plan_text = " ".join(line.strip("-* ") for line in plan if line.strip()) or "see issue"
    return (
        f"Hi! I'd like to take this one. My plan: {plan_text[:280]}\n\n"
        "I'll follow CONTRIBUTING.md and open a PR that references this issue. "
        "Please let me know if someone is already on it."
    )


def pr_body(issue: Issue, req: Requirements, rules: RuleSet) -> str:
    if rules.pr_template:
        header = "<!-- Fill in the project's own PR template below. -->\n\n" + rules.pr_template
    else:
        header = (
            "## What\n(describe the change)\n\n## Why\n"
            f"{req.problem[:400].strip()}\n\n## Testing\n"
            + ("\n".join(f"- `{c}`" for c in rules.commands[:4]) or "- (add test output)")
        )
    return f"{header.rstrip()}\n\nCloses #{issue.number}\n"


def render(
    issue: Issue,
    req: Requirements,
    rules: RuleSet,
    locations: list[CodeLocation],
    llm_patch: str = "",
) -> str:
    out: list[str] = [f"# Contribution draft: {issue.repo}#{issue.number}", ""]
    out += [f"**{issue.title}**  \n{issue.url}", f"Labels: {', '.join(issue.labels) or '-'}", ""]

    out += ["## 1. Requirements extracted from the issue", ""]
    for title, value in [
        ("Problem", req.problem), ("Expected", req.expected), ("Where", req.where),
        ("How to verify", req.verify), ("Scope / non-goals", req.scope),
    ]:
        if value:
            out += [f"### {title}", value.strip(), ""]
    if req.issue_refs:
        out += [f"Related issues/PRs: {', '.join('#' + str(n) for n in req.issue_refs)}", ""]

    out += ["## 2. Project rules to follow", ""]
    by_cat: dict[str, list[str]] = {}
    for rule in rules.rules:
        by_cat.setdefault(rule.category, []).append(f"- [ ] {rule.text}  _({rule.source})_")
    for category in sorted(by_cat):
        out += [f"**{category}**", *by_cat[category][:8], ""]
    if rules.commands:
        out += ["**Commands to run before pushing**", *(f"- `{c}`" for c in rules.commands[:8]), ""]
    if rules.changelog_hint:
        out += ["**Changelog convention**", "```text", rules.changelog_hint[:600], "```", ""]
    out += [
        f"_Read: {', '.join(rules.sources_found) or 'nothing'}_  ",
        f"_Not present: {', '.join(rules.sources_missing[:6]) or 'none'}_",
        "",
    ]

    out += ["## 3. Code to change", ""]
    if not locations:
        out += ["_No files could be located automatically; start from the issue text._", ""]
    for loc in locations:
        syms = f" (matches: {', '.join(loc.matched)})" if loc.matched else ""
        out += [f"### `{loc.path}`{syms}", "```text", loc.snippet, "```", ""]

    out += ["## 4. Draft implementation", ""]
    if req.expected:
        out += ["Starting point from the issue's suggested fix:", "", req.expected.strip(), ""]
    for block in req.code_blocks[:3]:
        out += ["```", block, "```", ""]
    if llm_patch:
        out += ["### Model-proposed patch (UNVERIFIED: review and run the tests)", llm_patch, ""]

    kind = commit_type(issue)
    out += [
        "## 5. Ready-to-use text", "",
        "**Claim comment**", "```text", claim_comment(issue, req), "```", "",
        f"**Branch** `{branch_name(issue)}`  ",
        f"**Commit** `{kind}: {slugify(issue.title, 60).replace('-', ' ')}`", "",
        "**PR body**", "```markdown", pr_body(issue, req, rules), "```", "",
        "> Drafted by first-pr-agent. Nothing has been posted or pushed; review everything.",
    ]
    return "\n".join(out)


def llm_patch(
    issue: Issue, req: Requirements, rules: RuleSet, locations: list[CodeLocation]
) -> str:
    """Optional: ask Claude for a unified diff. Needs ANTHROPIC_API_KEY; output is advisory."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return ""
    prompt = (
        f"Issue: {issue.title}\n\n{issue.body[:3000]}\n\nProject rules:\n"
        + "\n".join(f"- {r.text}" for r in rules.rules[:25])
        + "\n\nRelevant code:\n"
        + "\n\n".join(f"{loc.path}\n{loc.snippet}" for loc in locations)
        + "\n\nPropose the minimal change as a unified diff. Stay inside the issue's scope. "
        "If the snippets are insufficient, say what you need instead of guessing."
    )
    body = json.dumps(
        {"model": LLM_MODEL, "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]}
    ).encode()
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            reply = json.loads(response.read().decode())
    except (OSError, ValueError):
        return ""
    return "".join(part.get("text", "") for part in reply.get("content", []))
