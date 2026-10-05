"""Find the code the issue is talking about and cut a readable snippet around it."""
from __future__ import annotations

import os

from .github import GitHub
from .models import CodeLocation, Requirements

CONTEXT = 8


def _snippet(text: str, symbols: list[str]) -> tuple[str, int, list[str]]:
    lines = text.splitlines()
    matched = [s for s in symbols if s and s in text]
    start = 0
    for symbol in matched:
        for index, line in enumerate(lines):
            if symbol in line:
                start = max(0, index - CONTEXT)
                break
        else:
            continue
        break
    chunk = lines[start : start + 2 * CONTEXT + 12]
    numbered = "\n".join(f"{start + i + 1:>5}  {line}" for i, line in enumerate(chunk))
    return numbered, start + 1, matched


def _resolve(
    gh: GitHub, repo: str, path: str, tree: list[str] | None
) -> tuple[str, str, list[str]]:
    """Return ``(resolved_path, text, tree)``; text is empty when nothing was found."""
    text = gh.get_file(repo, path)
    if text is not None:
        return path, text, tree or []
    tree = tree or gh.tree(repo)
    base = os.path.basename(path)
    candidates = [p for p in tree if p == path or p.endswith("/" + path)]
    candidates = candidates or [p for p in tree if os.path.basename(p) == base]
    if candidates:
        text = gh.get_file(repo, candidates[0])
        if text is not None:
            return candidates[0], text, tree
    return path, "", tree


def locate(gh: GitHub, repo: str, req: Requirements, max_files: int = 6) -> list[CodeLocation]:
    found: list[CodeLocation] = []
    tree: list[str] | None = None
    for path in req.paths[:max_files]:
        resolved, text, tree = _resolve(gh, repo, path, tree)
        if not text:
            continue
        snippet, start, matched = _snippet(text, req.symbols)
        found.append(CodeLocation(resolved, snippet, start, matched))
    return found
