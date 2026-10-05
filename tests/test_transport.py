"""Exercise the real HTTP code paths against a local stub server (no network needed)."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from firstpr.cli import build_draft
from firstpr.github import GitHub
from firstpr.tinyfish import TinyFish, TinyFishError

from .fixtures import CONTRIBUTING, ISSUE_BODY, contents_api

SEEN: list[dict] = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep test output quiet
        pass

    def _send(self, payload):
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        SEEN.append({"method": "GET", "path": self.path, "key": self.headers.get("X-API-Key")})
        self._send({"results": [{"title": "t", "url": "https://x", "snippet": "s"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append({"method": "POST", "path": self.path, "body": body})
        if self.path == "/agent":
            return self._send({"result": {"already_claimed": False, "linked_pull_requests": []}})
        results, errors = [], []
        for url in body["urls"]:
            if url.endswith("/contents/CONTRIBUTING.md"):
                # Simulate a markdown extractor that backslash-escapes underscores.
                text = contents_api(CONTRIBUTING).replace("_", "\\_")
                results.append({"url": url, "text": text})
            elif url.endswith("/issues/7"):
                issue = {"html_url": "https://github.com/o/r/issues/7", "title": "Pin beta fields",
                         "body": ISSUE_BODY, "labels": [{"name": "good first issue"}],
                         "assignees": [], "comments": 0, "created_at": "2026-10-04T00:00:00Z"}
                results.append({"url": url, "text": json.dumps(issue).replace("_", "\\_")})
            else:
                errors.append({"url": url, "error": "page_not_found", "status": 404})
        self._send({"results": results, "errors": errors})


class TransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        SEEN.clear()
        self.tf = TinyFish("k", search_url=self.base + "/search", fetch_url=self.base + "/fetch",
                           agent_url=self.base + "/agent")

    def test_missing_key_is_a_clear_error(self):
        import os
        old = os.environ.pop("TINYFISH_API_KEY", None)
        try:
            with self.assertRaises(TinyFishError):
                TinyFish()
        finally:
            if old:
                os.environ["TINYFISH_API_KEY"] = old

    def test_search_sends_key_and_domain(self):
        out = self.tf.search("good first issue", include_domains="github.com")
        self.assertEqual(out[0]["url"], "https://x")
        self.assertEqual(SEEN[0]["key"], "k")
        self.assertIn("include_domains=github.com", SEEN[0]["path"])

    def test_fetch_collects_partial_failures(self):
        urls = ["https://api.github.com/repos/o/r/contents/CONTRIBUTING.md",
                "https://api.github.com/repos/o/r/contents/NOPE.md"]
        out = self.tf.fetch(urls)
        self.assertEqual(list(out), [urls[0]])
        self.assertEqual(self.tf.last_errors[0]["status"], 404)

    def test_agent_payload_has_session_id_and_schema(self):
        self.tf.run_agent("https://github.com/o/r/issues/7", "goal", {"type": "object"})
        body = SEEN[0]["body"]
        self.assertEqual(body["goal"], "goal")
        self.assertEqual(len(body["session_id"]), 36)
        self.assertEqual(body["output_schema"], {"type": "object"})

    def test_github_reads_escaped_json_through_tinyfish(self):
        gh = GitHub(self.tf)
        text = gh.get_file("o/r", "CONTRIBUTING.md")
        self.assertIn("Conventional Commits", text)  # decoded exactly, underscores intact
        self.assertIn("rich.console.Console", text)
        issue = gh.get_issue("https://github.com/o/r/issues/7")
        self.assertEqual(issue.title, "Pin beta fields")
        self.assertEqual(issue.labels, ["good first issue"])

    def test_full_draft_through_stub_transport(self):
        gh = GitHub(self.tf)
        gh._direct = lambda url: None  # 404 for everything the stub does not serve
        issue = gh.get_issue("https://github.com/o/r/issues/7")
        markdown, data = build_draft(gh, issue, use_llm=False)
        self.assertIn("Closes #7", markdown)
        self.assertIn("never bare print()", markdown)
        self.assertEqual(data["issue"]["number"], 7)


if __name__ == "__main__":
    unittest.main()
