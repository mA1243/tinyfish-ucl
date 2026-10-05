"""Offline fixtures modelled on a real issue (Soup #1645) and its CONTRIBUTING.md."""
import base64
import json

ISSUE_BODY = """Follow-up to #1556. Refs #1425.

## What happens

1. **Untested code.** `blend_loss_params` builds each term's parameters from the config.
Its `dpo` and `ipo` entries read `training.dpo_beta` and `training.ipo_tau`
(`src/soup_cli/utils/preference_combine.py`). No committed test reads either field.
2. **Stale sentence.** `docs/training.md` gives the wrong reason.

## Expected

1. A test that fails when either line is changed back to `DEFAULT_BETA`.
2. The sentence uses the same reason as the table row.

## Where

- `src/soup_cli/utils/preference_combine.py`, `blend_loss_params`.
- `tests/test_v05311.py`, next to `test_the_blend_reads_each_loss_parameters_from_the_config`.
- `docs/training.md`, the sentence quoted above.

## How to verify a fix

```python
def test_dpo_and_ipo_terms_read_their_own_config_fields(self):
    assert params["dpo"]["beta"] == 0.5 != DEFAULT_BETA
```

## Scope

- Not part of it: making a `dpo` or `ipo` blend train.
"""

CONTRIBUTING = """# Contributing

## Code Style
We use **ruff**. Before committing, run:

```bash
ruff check src/ tests/
```

- **Line length:** 100 characters (enforced by ruff)
- **Output:** Use `rich.console.Console` for all output - never bare `print()`
- **Type hints:** Always include type hints for function parameters and return values
- You must write tests first (TDD) and then implement to pass them.

For each user-visible pull request, add its entry to `changelog.d/<version>/<n>.<kind>.md`
instead of editing `CHANGELOG.md`.

Write clear commit messages following Conventional Commits:

```bash
pytest tests/ -v --tb=short
git commit -m "fix: resolve Y when Z"
```

## Claiming an Issue
Comment on it saying you are taking it. The comment is the claim.

| File | Covers |
|------|--------|
| test_x.py | you must never treat this table row as a rule |
"""

PYPROJECT = """[tool.ruff]
line-length = 100
[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
"""

PREF_COMBINE = "\n".join(
    ["# header"] * 30
    + [
        "def blend_loss_params(cfg) -> dict:",
        "    tcfg = getattr(cfg, 'training', None)",
        '    return {"dpo": {"beta": float(getattr(tcfg, "dpo_beta", DEFAULT_BETA))}}',
    ]
)


def contents_api(text: str) -> str:
    return json.dumps({"encoding": "base64", "content": base64.b64encode(text.encode()).decode()})


class FakeGitHub:
    """Duck-types firstpr.github.GitHub for offline tests."""

    def __init__(self, files: dict[str, str]) -> None:
        self.files = files

    def get_file(self, repo: str, path: str):
        return self.files.get(path)

    def tree(self, repo: str):
        return list(self.files)
