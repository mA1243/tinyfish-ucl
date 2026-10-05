> **Example output.** Generated offline from the repo's test fixtures (a trimmed copy of a real
> issue and CONTRIBUTING.md), so the rules and code snippet are abbreviated. A live run reads the
> real files through TinyFish.

# Contribution draft: MakazhanAlpamys/Soup#1645

**Preference blend: pin that dpo/ipo terms read dpo_beta/ipo_tau**  
https://github.com/MakazhanAlpamys/Soup/issues/1645
Labels: good first issue, tests, docs

## 1. Requirements extracted from the issue

### Problem
1. **Untested code.** `blend_loss_params` builds each term's parameters from the config.
Its `dpo` and `ipo` entries read `training.dpo_beta` and `training.ipo_tau`
(`src/soup_cli/utils/preference_combine.py`). No committed test reads either field.
2. **Stale sentence.** `docs/training.md` gives the wrong reason.

### Expected
1. A test that fails when either line is changed back to `DEFAULT_BETA`.
2. The sentence uses the same reason as the table row.

### Where
- `src/soup_cli/utils/preference_combine.py`, `blend_loss_params`.
- `tests/test_v05311.py`, next to `test_the_blend_reads_each_loss_parameters_from_the_config`.
- `docs/training.md`, the sentence quoted above.

### How to verify
```python
def test_dpo_and_ipo_terms_read_their_own_config_fields(self):
    assert params["dpo"]["beta"] == 0.5 != DEFAULT_BETA
```

### Scope / non-goals
- Not part of it: making a `dpo` or `ipo` blend train.

Related issues/PRs: #1425, #1556

## 2. Project rules to follow

**changelog**
- [ ] For each user-visible pull request, add its entry to changelog.d/<version>/<n>.<kind>.md instead of editing CHANGELOG.md.  _(CONTRIBUTING.md)_

**commits**
- [ ] Write clear commit messages following Conventional Commits:  _(CONTRIBUTING.md)_

**general**
- [ ] Output: Use rich.console.Console for all output - never bare print()  _(CONTRIBUTING.md)_

**style**
- [ ] Line length: 100 characters (enforced by ruff)  _(CONTRIBUTING.md)_
- [ ] Type hints: Always include type hints for function parameters and return values  _(CONTRIBUTING.md)_
- [ ] Maximum line length is 100  _(pyproject.toml)_
- [ ] Ruff rules enabled: "E", "F", "I", "N", "W"  _(pyproject.toml)_

**testing**
- [ ] You must write tests first (TDD) and then implement to pass them.  _(CONTRIBUTING.md)_

**workflow**
- [ ] Comment on it saying you are taking it. The comment is the claim.  _(CONTRIBUTING.md)_

**Commands to run before pushing**
- `ruff check src/ tests/`
- `pytest tests/ -v --tb=short`

_Read: CONTRIBUTING.md, pyproject.toml_  
_Not present: .github/CONTRIBUTING.md, docs/CONTRIBUTING.md, CONTRIBUTING.rst, AGENTS.md, CLAUDE.md, DEVELOPMENT.md_

## 3. Code to change

### `src/soup_cli/utils/preference_combine.py` (matches: blend_loss_params, DEFAULT_BETA)
```text
   23  # header
   24  # header
   25  # header
   26  # header
   27  # header
   28  # header
   29  # header
   30  # header
   31  def blend_loss_params(cfg) -> dict:
   32      tcfg = getattr(cfg, 'training', None)
   33      return {"dpo": {"beta": float(getattr(tcfg, "dpo_beta", DEFAULT_BETA))}}
```

## 4. Draft implementation

Starting point from the issue's suggested fix:

1. A test that fails when either line is changed back to `DEFAULT_BETA`.
2. The sentence uses the same reason as the table row.

```
def test_dpo_and_ipo_terms_read_their_own_config_fields(self):
    assert params["dpo"]["beta"] == 0.5 != DEFAULT_BETA
```

## 5. Ready-to-use text

**Claim comment**
```text
Hi! I'd like to take this one. My plan: 1. A test that fails when either line is changed back to `DEFAULT_BETA`. 2. The sentence uses the same reason as the table row.

I'll follow CONTRIBUTING.md and open a PR that references this issue. Please let me know if someone is already on it.
```

**Branch** `fix/1645-preference-blend-pin-that-dpo-ipo-terms`  
**Commit** `docs: preference blend pin that dpo ipo terms read dpo beta ipo ta`

**PR body**
```markdown
## What
(describe the change)

## Why
1. **Untested code.** `blend_loss_params` builds each term's parameters from the config.
Its `dpo` and `ipo` entries read `training.dpo_beta` and `training.ipo_tau`
(`src/soup_cli/utils/preference_combine.py`). No committed test reads either field.
2. **Stale sentence.** `docs/training.md` gives the wrong reason.

## Testing
- `ruff check src/ tests/`
- `pytest tests/ -v --tb=short`

Closes #1645

```

> Drafted by first-pr-agent. Nothing has been posted or pushed; review everything.