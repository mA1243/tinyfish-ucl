"""GitHub access. TinyFish ``fetch`` is the primary transport; a direct HTTPS call is the
fallback (and the only transport in ``--direct`` mode).

Two lessons from running this against real repos:

* Fetching ``raw.githubusercontent.com`` through a markdown extractor loses indentation
  and escapes underscores, which corrupts code. So file contents are read through the
  GitHub *contents API* (JSON, base64) and decoded exactly.
* Markdown extraction also backslash-escapes characters inside JSON, so JSON from the
  fetcher is parsed leniently (:func:`lenient_json`).
"""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .models import Issue, parse_issue_url
from .tinyfish import TinyFish, TinyFishError

API = "https://api.github.com"
_MD_ESCAPE = re.compile(r"\\([_*\[\]()#+.!`>~|{}-])")


def lenient_json(text: str) -> Any:
    """Parse JSON, undoing markdown backslash-escapes if strict parsing fails."""
    try:
        return json.loads(text)
    except ValueError:
        return json.loads(_MD_ESCAPE.sub(r"\1", text))


class GitHub:
    def __init__(self, tinyfish: TinyFish | None = None, token: str | None = None) -> None:
        self.tf = tinyfish
        self.token = token or os.environ.get("GITHUB_TOKEN", "")

    # -- transport ---------------------------------------------------------------
    def _direct(self, url: str) -> Any:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "first-pr-agent"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise TinyFishError(f"GitHub {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise TinyFishError(f"GitHub request failed for {url}: {exc}") from exc

    def get_json(self, url: str) -> Any:
        """GET a GitHub API URL; ``None`` means 404. Falls back to direct on parse failure."""
        if self.tf is None:
            return self._direct(url)
        try:
            text = self.tf.fetch([url]).get(url, "")
            if text:
                data = lenient_json(text)
                if isinstance(data, dict) and data.get("message") == "Not Found":
                    return None
                return data
        except (ValueError, TinyFishError):
            pass
        return self._direct(url)

    # -- issues ------------------------------------------------------------------
    def search_issues(self, language: str = "", limit: int = 15) -> list[Issue]:
        query = 'label:"good first issue" state:open is:issue no:assignee comments:0'
        if language:
            query += f" language:{language}"
        params = urllib.parse.urlencode(
            {"q": query, "sort": "created", "order": "desc", "per_page": limit}
        )
        data = self.get_json(f"{API}/search/issues?{params}") or {}
        return [Issue.from_api(item) for item in data.get("items", [])]

    def get_issue(self, url: str) -> Issue:
        repo, number = parse_issue_url(url)
        data = self.get_json(f"{API}/repos/{repo}/issues/{number}")
        if not data:
            raise TinyFishError(f"issue not found: {url}")
        return Issue.from_api(data)

    # -- repository files --------------------------------------------------------
    def get_file(self, repo: str, path: str) -> str | None:
        data = self.get_json(f"{API}/repos/{repo}/contents/{urllib.parse.quote(path)}")
        if not isinstance(data, dict) or data.get("encoding") != "base64":
            return None
        return base64.b64decode(data["content"]).decode("utf-8", "replace")

    def tree(self, repo: str) -> list[str]:
        data = self.get_json(f"{API}/repos/{repo}/git/trees/HEAD?recursive=1") or {}
        return [node["path"] for node in data.get("tree", []) if node.get("type") == "blob"]
