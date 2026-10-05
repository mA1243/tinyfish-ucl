"""Thin TinyFish client (stdlib only).

Request shapes mirror the TinyFish MCP tool schemas (``search``, ``fetch_content``,
``run_web_automation``). Base URLs are overridable through environment variables so
they can be pointed at whatever the TinyFish docs currently list:

    TINYFISH_API_KEY      required for live calls
    TINYFISH_SEARCH_URL   default https://api.search.tinyfish.ai
    TINYFISH_FETCH_URL    default https://api.fetch.tinyfish.ai
    TINYFISH_AGENT_URL    default https://agent.tinyfish.ai/v1/automation/run
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

DEFAULT_SEARCH = "https://api.search.tinyfish.ai"
DEFAULT_FETCH = "https://api.fetch.tinyfish.ai"
DEFAULT_AGENT = "https://agent.tinyfish.ai/v1/automation/run"


class TinyFishError(RuntimeError):
    """Raised on transport or API errors."""


class TinyFish:
    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 90.0,
        search_url: str | None = None,
        fetch_url: str | None = None,
        agent_url: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("TINYFISH_API_KEY", "")
        if not self.api_key:
            raise TinyFishError("TINYFISH_API_KEY is not set (use --direct for GitHub-only mode)")
        self.timeout = timeout
        self.search_url = search_url or os.environ.get("TINYFISH_SEARCH_URL", DEFAULT_SEARCH)
        self.fetch_url = fetch_url or os.environ.get("TINYFISH_FETCH_URL", DEFAULT_FETCH)
        self.agent_url = agent_url or os.environ.get("TINYFISH_AGENT_URL", DEFAULT_AGENT)
        self.last_errors: list[dict[str, Any]] = []

    # -- transport ---------------------------------------------------------------
    def _request(self, url: str, payload: dict[str, Any] | None = None) -> Any:
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            method="POST" if payload is not None else "GET",
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            raise TinyFishError(f"{exc.code} from {url}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            raise TinyFishError(f"request to {url} failed: {exc}") from exc

    # -- capabilities ------------------------------------------------------------
    def search(self, query: str, include_domains: str | None = None, **extra: Any) -> list[dict]:
        """Web search. Returns a list of ``{title, url, snippet}`` dicts."""
        params = {"query": query, **extra}
        if include_domains:
            params["include_domains"] = include_domains
        reply = self._request(f"{self.search_url}?{urllib.parse.urlencode(params)}")
        return list(reply.get("results", []))

    def fetch(self, urls: list[str], fmt: str = "markdown") -> dict[str, str]:
        """Fetch pages (JS-rendered if needed). Returns ``{url: text}``; failures go to
        :attr:`last_errors` so one bad URL never sinks a batch."""
        out: dict[str, str] = {}
        self.last_errors = []
        for start in range(0, len(urls), 10):
            batch = urls[start : start + 10]
            reply = self._request(self.fetch_url, {"urls": batch, "format": fmt})
            for item in reply.get("results", []):
                out[item.get("url", "")] = item.get("text") or ""
            self.last_errors.extend(reply.get("errors", []))
        return out

    def run_agent(self, url: str, goal: str, output_schema: dict | None = None) -> dict:
        """Run a browser agent on a live page (metered). Returns the raw run result."""
        payload: dict[str, Any] = {"url": url, "goal": goal, "session_id": str(uuid.uuid4())}
        if output_schema:
            payload["output_schema"] = output_schema
        return self._request(self.agent_url, payload)
