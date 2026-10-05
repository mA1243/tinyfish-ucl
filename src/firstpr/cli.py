"""Command line: ``firstpr scout | draft | run``."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from . import draft as drafting
from .github import GitHub
from .guidelines import analyse
from .issue_parser import parse_issue
from .locate import locate
from .models import Issue
from .tinyfish import TinyFish, TinyFishError
from .triage import check_competition, rank


def _clients(direct: bool) -> tuple[TinyFish | None, GitHub]:
    tf = None if direct else TinyFish()
    return tf, GitHub(tf)


def cmd_scout(args: argparse.Namespace) -> int:
    tf, gh = _clients(args.direct)
    accepted, rejected = rank(gh.search_issues(args.lang, args.limit))
    if args.json:
        payload = {
            "accepted": [{**asdict(t.issue), "score": t.score, "reasons": t.reasons}
                         for t in accepted],
            "rejected": [{"url": t.issue.url, "why": t.rejected} for t in rejected],
        }
        print(json.dumps(payload, indent=2))
        return 0
    print(f"{len(accepted)} candidate(s), {len(rejected)} rejected\n")
    for t in accepted:
        print(f"[{t.score:>2}] {t.issue.repo}#{t.issue.number}  {t.issue.title}")
        print(f"     {t.issue.url}\n     + " + "; ".join(t.reasons))
    for t in rejected:
        print(f"[--] {t.issue.repo}#{t.issue.number}  rejected: {t.rejected}")
    return 0


def build_draft(gh: GitHub, issue: Issue, use_llm: bool) -> tuple[str, dict]:
    req = parse_issue(issue.body)
    rules = analyse(gh, issue.repo)
    locations = locate(gh, issue.repo, req)
    patch = drafting.llm_patch(issue, req, rules, locations) if use_llm else ""
    markdown = drafting.render(issue, req, rules, locations, patch)
    data = {"issue": asdict(issue), "requirements": asdict(req), "rules": asdict(rules),
            "locations": [asdict(loc) for loc in locations]}
    return markdown, data


def _emit(markdown: str, data: dict, issue: Issue, out: str | None) -> None:
    if not out:
        print(markdown)
        return
    folder = Path(out) / f"{issue.repo.replace('/', '__')}-{issue.number}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "draft.md").write_text(markdown, encoding="utf-8")
    (folder / "draft.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"wrote {folder}/draft.md and draft.json")


def cmd_draft(args: argparse.Namespace) -> int:
    tf, gh = _clients(args.direct)
    issue = gh.get_issue(args.url)
    if args.verify_live and tf:
        print("live claim check:", json.dumps(check_competition(tf, issue)), file=sys.stderr)
    markdown, data = build_draft(gh, issue, args.llm)
    _emit(markdown, data, issue, args.out)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    tf, gh = _clients(args.direct)
    accepted, _ = rank(gh.search_issues(args.lang, args.limit))
    if not accepted:
        print("no suitable issues found", file=sys.stderr)
        return 1
    best = accepted[0].issue
    print(f"picked {best.url} (score {accepted[0].score})", file=sys.stderr)
    if args.verify_live and tf:
        print("live claim check:", json.dumps(check_competition(tf, best)), file=sys.stderr)
    markdown, data = build_draft(gh, best, args.llm)
    _emit(markdown, data, best, args.out)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="firstpr", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--direct", action="store_true",
                       help="skip TinyFish; call GitHub directly (degraded, for offline dev)")
        p.add_argument("--llm", action="store_true", help="also ask Claude for a patch (advisory)")
        p.add_argument("--verify-live", action="store_true",
                       help="use a TinyFish browser agent to check for existing claims/PRs")
        p.add_argument("--out", help="write draft.md/draft.json under this directory")

    scout = sub.add_parser("scout", help="list ranked good-first-issues")
    scout.add_argument("--lang", default="")
    scout.add_argument("--limit", type=int, default=15)
    scout.add_argument("--json", action="store_true")
    scout.add_argument("--direct", action="store_true")
    scout.set_defaults(func=cmd_scout)

    draft = sub.add_parser("draft", help="draft a contribution for one issue URL")
    draft.add_argument("url")
    common(draft)
    draft.set_defaults(func=cmd_draft)

    run = sub.add_parser("run", help="scout, pick the best issue, draft it")
    run.add_argument("--lang", default="")
    run.add_argument("--limit", type=int, default=15)
    common(run)
    run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except TinyFishError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
