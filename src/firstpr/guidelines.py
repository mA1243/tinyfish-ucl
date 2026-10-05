"""Mine a project's contribution rules from CONTRIBUTING / AGENTS / PR template / configs."""
from __future__ import annotations

import re

from .github import GitHub
from .models import Rule, RuleSet

DOC_FILES = [
    "CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md", "CONTRIBUTING.rst",
    "AGENTS.md", "CLAUDE.md", "DEVELOPMENT.md", "HACKING.md",
]
TEMPLATE_FILES = [
    ".github/PULL_REQUEST_TEMPLATE.md", ".github/pull_request_template.md",
    "PULL_REQUEST_TEMPLATE.md", "docs/pull_request_template.md",
]
CONFIG_FILES = ["pyproject.toml", ".pre-commit-config.yaml", "package.json", ".editorconfig"]
CHANGELOG_HINTS = ["changelog.d/README.md", "CHANGELOG.md", "CHANGES.md", "NEWS.md"]

_FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
_KEYWORD = re.compile(
    r"\b(must|never|always|required|do not|don't|should|only|instead of|ensure|make sure|"
    r"follow\w*|comment on|add (?:its|an?|your)|before (?:you )?(?:push|commit|open))\b",
    re.I,
)
# Bullets under these headings are rules even without a modal verb ("Line length: 100").
_RULE_HEADING = re.compile(
    r"style|guideline|convention|rule|requirement|checklist|standard|must follow", re.I
)
_HEADING_LINE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_CATEGORIES = [
    ("legal", r"licen[sc]e|\bCLA\b|copyright|SPDX|sign-?off|\bDCO\b"),
    ("changelog", r"changelog|release notes?"),
    ("commits", r"commit|conventional"),
    ("testing", r"\btests?\b|pytest|coverage|jest|unittest"),
    ("style", r"ruff|black|flake8|eslint|prettier|line length|lint|format|naming|type hint|import"),
    ("docs", r"\bdocs?\b|readme|docstring"),
    ("workflow", r"branch|pull request|\bPR\b|claim|assign|issue|rebase"),
]
_COMMAND = re.compile(
    r"^\s*(?:\$ )?((?:ruff|pytest|python -m pytest|tox|nox|pre-commit|black|flake8|mypy|"
    r"npm (?:run )?\w+|yarn \w+|pnpm \w+|make \w+|cargo \w+|go (?:test|vet)|"
    r"eslint|prettier)\b[^\n#]*)",
)


def _categorise(text: str) -> str:
    for name, pattern in _CATEGORIES:
        if re.search(pattern, text, re.I):
            return name
    return "general"


def _clean(line: str) -> str:
    line = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line.strip())
    line = re.sub(r"[*_`]{1,3}", "", line)
    return re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line).strip()


def _units(prose: str):
    """Yield ``(text, in_rule_section, is_bullet)`` with wrapped lines joined together."""
    current: list[str] = []
    state = {"rule": False, "bullet": False}

    def flush():
        if current:
            yield " ".join(current), state["rule"], state["bullet"]
            current.clear()

    for raw in prose.splitlines():
        if heading := _HEADING_LINE.match(raw):
            yield from flush()
            state["rule"] = bool(_RULE_HEADING.search(heading.group(1)))
        elif not raw.strip() or raw.lstrip().startswith("|"):  # blank / table rows
            yield from flush()
        elif _BULLET.match(raw):
            yield from flush()
            state["bullet"] = True
            current.append(_clean(raw))
        else:
            if not current:
                state["bullet"] = False
            current.append(_clean(raw))
    yield from flush()


def extract_rules(markdown: str, source: str, cap: int = 40) -> tuple[list[Rule], list[str]]:
    commands = [
        match.group(1).strip()
        for block in _FENCE.findall(markdown)
        for line in block.splitlines()
        if (match := _COMMAND.match(line))
    ]
    rules: list[Rule] = []
    seen: set[str] = set()
    for unit, in_rule_section, is_bullet in _units(_FENCE.sub("", markdown)):
        pieces = [unit] if len(unit) <= 300 else re.split(r"(?<=[.!?])\s+", unit)
        for text in pieces:
            qualifies = _KEYWORD.search(text) or (in_rule_section and is_bullet)
            if not 15 <= len(text) <= 300 or not qualifies or text in seen:
                continue
            seen.add(text)
            rules.append(Rule(_categorise(text), text, source))
    return rules[:cap], commands


def extract_config_rules(name: str, text: str) -> list[Rule]:
    rules: list[Rule] = []
    if name == "pyproject.toml":
        if m := re.search(r"line-length\s*=\s*(\d+)", text):
            rules.append(Rule("style", f"Maximum line length is {m.group(1)}", name))
        if m := re.search(r"^select\s*=\s*\[([^\]]*)\]", text, re.M):
            rules.append(Rule("style", f"Ruff rules enabled: {m.group(1).strip()}", name))
        if m := re.search(r"requires-python\s*=\s*\"([^\"]+)\"", text):
            rules.append(Rule("general", f"Supported Python versions: {m.group(1)}", name))
    elif name == ".pre-commit-config.yaml":
        rules.append(
            Rule("style", "pre-commit hooks are configured; run `pre-commit run -a`", name)
        )
    elif name == ".editorconfig":
        rules.append(
            Rule("style", "An .editorconfig is present; honour its indent/EOL settings", name)
        )
    return rules


def analyse(gh: GitHub, repo: str) -> RuleSet:
    result = RuleSet()

    def grab(path: str) -> str | None:
        text = gh.get_file(repo, path)
        (result.sources_found if text else result.sources_missing).append(path)
        return text

    for path in DOC_FILES:
        text = grab(path)
        if text:
            rules, commands = extract_rules(text, path)
            result.rules.extend(rules)
            result.commands.extend(c for c in commands if c not in result.commands)
    for path in TEMPLATE_FILES:
        text = grab(path)
        if text:
            result.pr_template = text
            break
    for path in CONFIG_FILES:
        text = grab(path)
        if text:
            result.rules.extend(extract_config_rules(path, text))
    for path in CHANGELOG_HINTS:
        text = grab(path)
        if text and path.startswith("changelog.d"):
            result.changelog_hint = text[:1200]
            break
    return result
