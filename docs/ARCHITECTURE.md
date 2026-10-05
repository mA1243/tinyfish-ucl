# Architecture

```
cli.py ── scout ─► github.search_issues ─► triage.rank
       ── draft ─► github.get_issue
                    ├─► issue_parser.parse_issue   → Requirements
                    ├─► guidelines.analyse         → RuleSet
                    ├─► locate.locate              → [CodeLocation]
                    └─► draft.render (+ llm_patch) → draft.md / draft.json
```

| Module | Responsibility |
| --- | --- |
| `tinyfish.py` | Only place that talks to TinyFish: `search`, `fetch` (batched, partial failures kept), `run_agent` |
| `github.py` | GitHub reads through TinyFish with a direct fallback; exact file decoding; lenient JSON |
| `triage.py` | Reject/score issues; `check_competition` runs the live browser-agent claim check |
| `issue_parser.py` | Split an issue into sections; mine paths, symbols, refs, code blocks |
| `guidelines.py` | Rules + commands from contribution docs, PR template, `pyproject.toml`, changelog convention |
| `locate.py` | Resolve paths (falls back to tree search by basename), snippet around matched symbols |
| `draft.py` | Render the bundle; optional Claude patch proposal |

All stages exchange the dataclasses in `models.py`, so each can be tested in isolation. The tests
use a `FakeGitHub` for pipeline logic and a local HTTP server for transport behaviour.

## Extending

* **New forge** (GitLab, Codeberg): implement the five methods of `GitHub` for that API.
* **New rule source**: add the filename to `guidelines.py` and, if it is structured config, a
  branch in `extract_config_rules`.
* **Better ranking**: `triage.triage` is a small scoring function; add signals there.
