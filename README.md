# first-pr-agent

**From "good first issue" to a rule-compliant PR draft, powered by TinyFish.**

Open-source newcomers lose hours on the same steps: finding an issue nobody has claimed,
working out what it really asks for, digging the project's rules out of `CONTRIBUTING.md`,
and locating the code. `first-pr-agent` does that legwork on the live web and hands back a
reviewable draft. It never posts, pushes, or comments for you.

```
scout ─► triage ─► extract requirements ─► mine contribution rules ─► locate code ─► draft
 (TinyFish   (reject blocked,   (problem / expected /   (CONTRIBUTING, AGENTS,    (read the files   (claim comment,
  search +    assigned, hardware  where / verify /       PR template, pyproject,   the issue names,  branch, commit,
  fetch)      or short issues)    scope, paths, symbols) changelog convention)     cut snippets)     PR body, patch)
```

## What TinyFish does here

| Stage | TinyFish capability | Why |
| --- | --- | --- |
| Discover | `search`, `fetch` | find fresh, unassigned `good first issue`s across GitHub |
| Read project rules and code | `fetch` | pull `CONTRIBUTING.md`, templates, configs and the files an issue names |
| Verify nobody beat you to it | browser agent (`--verify-live`) | reads the *rendered* issue page: claim comments and linked PRs |

## Quick start

```bash
pip install -e ".[dev]"
export TINYFISH_API_KEY=...          # live mode
export GITHUB_TOKEN=...              # optional, raises GitHub rate limits

firstpr scout --lang python                       # ranked candidates + why others were rejected
firstpr draft https://github.com/OWNER/REPO/issues/123 --out out/
firstpr run --lang python --out out/ --verify-live   # scout, pick the best, draft it
firstpr draft URL --llm                           # also ask Claude for a patch (ANTHROPIC_API_KEY)
firstpr scout --direct                            # no TinyFish: plain GitHub API (offline dev)
```

Output is `draft.md` (human readable) and `draft.json` (every stage's structured result).
See [`examples/example-draft.md`](examples/example-draft.md).

## What a draft contains

1. **Requirements**: problem, expected behaviour, where, how to verify, non-goals, related issues.
2. **Project rules** as a checklist, grouped (style, testing, commits, changelog, workflow, legal),
   plus the commands to run before pushing, and which rule files exist or are missing.
3. **Code to change**: the files and symbols the issue names, with line-numbered snippets.
4. **Draft implementation**: the issue's own suggested fix, and optionally a model-proposed diff
   clearly labelled *unverified*.
5. **Ready-to-use text**: claim comment, branch name, Conventional-Commit message, PR body
   (the project's own PR template when one exists, with `Closes #N`).

## Design notes (learned from running it on real repos)

* **Read code through the contents API, not raw URLs.** A markdown extractor drops indentation
  and escapes underscores, which corrupts code. File bodies are fetched as JSON and
  base64-decoded, so snippets are exact.
* **Parse JSON leniently.** Extractors also backslash-escape characters inside JSON;
  `lenient_json` undoes that only when strict parsing fails.
* **Missing files are normal.** A repo may have no PR template or `AGENTS.md`. Absence is
  reported, not fatal.
* **Reject early.** `On Hold` / `blocked` labels, "blocked by #N", assignees, and hardware
  requirements are filtered out before anything else is spent on an issue.
* **Rules need context.** Wrapped lines are joined into one rule, table rows are ignored, and
  bullets under headings like "Style Guidelines" count as rules even without a modal verb.

## Safety

Read-only by design: no login, no comments, no pushes. The browser-agent check is instructed
not to log in or change anything. Drafts are labelled as machine-generated: review them, and
respect any project policy on AI-assisted contributions before you submit.

## Status and honest limits

* The pipeline is covered by 33 offline tests, including a stub HTTP server that exercises the
  real client code. CI runs ruff and the tests on Python 3.10–3.12.
* **Not yet verified against live TinyFish.** The client's request shapes mirror the TinyFish MCP
  tool schemas (`search`, `fetch_content`, `run_web_automation`), but the REST base URLs and auth
  header are assumptions. Override them with `TINYFISH_SEARCH_URL`, `TINYFISH_FETCH_URL` and
  `TINYFISH_AGENT_URL` if the docs say otherwise. Everything is isolated in
  [`src/firstpr/tinyfish.py`](src/firstpr/tinyfish.py).
* Requirement and rule extraction is heuristic (regex plus structure). It handles common issue and
  CONTRIBUTING layouts well, and it will miss rules phrased unusually.
* The patch step is advisory. The agent does not execute the target project's tests.

## Roadmap

Sandboxed `ruff` / `pytest` run against the proposed patch; GitLab/Codeberg support; a
`--watch` mode that monitors for new matching issues.

## License

MIT
