"""Turn a free-form issue body into structured requirements."""
from __future__ import annotations

import re

from .models import Requirements

_HEADING = re.compile(r"^\s{0,3}(?:#{1,6}\s+(?P<h>.+?)|\*\*(?P<b>[^*]+?)\*\*:?)\s*$")
_FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
_BACKTICK = re.compile(r"`([^`\n]+)`")
_PATH = re.compile(
    r"^[\w./-]+\.(?:py|js|jsx|ts|tsx|md|html|css|yml|yaml|toml|json|rs|go|java|rb|c|h)$"
)
_PATH_LINE = re.compile(r":\d+(?:-\d+)?$")
_SYMBOL = re.compile(r"^[A-Za-z_][\w.]*(?:\(\))?$")
_REF = re.compile(r"(?<![\w/])#(\d{1,6})\b")

_KEYS = {
    "problem": ("what happens", "problem", "description", "what problem", "summary", "current"),
    "expected": (
        "expected", "acceptance", "proposed solution", "possible fix", "suggested fix",
        "proposed fix",
    ),
    "where": ("where", "location", "files"),
    "verify": ("how to verify", "verify", "to reproduce", "reproduce", "steps"),
    "scope": ("scope", "out of scope", "non-goal"),
}


def _split_sections(body: str) -> tuple[str, dict[str, str]]:
    preamble: list[str] = []
    sections: dict[str, list[str]] = {}
    current: str | None = None
    in_fence = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        match = None if in_fence else _HEADING.match(line)
        if match:
            current = (match.group("h") or match.group("b")).strip().lower()
            sections.setdefault(current, [])
        elif current is None:
            preamble.append(line)
        else:
            sections[current].append(line)
    return "\n".join(preamble).strip(), {k: "\n".join(v).strip() for k, v in sections.items()}


def _pick(sections: dict[str, str], keys: tuple[str, ...]) -> str:
    chunks = [text for title, text in sections.items() if any(k in title for k in keys) and text]
    return "\n\n".join(chunks)


def parse_issue(body: str) -> Requirements:
    body = (body or "").replace("\r\n", "\n")
    preamble, sections = _split_sections(body)
    req = Requirements(
        problem=_pick(sections, _KEYS["problem"]),
        expected=_pick(sections, _KEYS["expected"]),
        where=_pick(sections, _KEYS["where"]),
        verify=_pick(sections, _KEYS["verify"]),
        scope=_pick(sections, _KEYS["scope"]),
    )
    if not req.problem:
        req.problem = preamble or body[:600]
    req.code_blocks = [block.strip("\n") for block in _FENCE.findall(body)]

    prose = _FENCE.sub("", body)
    paths: list[str] = []
    symbols: list[str] = []
    for token in _BACKTICK.findall(prose):
        token = token.strip()
        candidate = _PATH_LINE.sub("", token)
        if _PATH.match(candidate) and "://" not in candidate:
            if candidate not in paths:
                paths.append(candidate)
        elif _SYMBOL.match(token) and ("_" in token or "(" in token or "." in token):
            name = token.removesuffix("()")
            if name not in symbols and not _PATH.match(name):
                symbols.append(name)
    req.paths = paths
    req.symbols = symbols[:12]
    req.issue_refs = sorted({int(n) for n in _REF.findall(prose)})
    return req
