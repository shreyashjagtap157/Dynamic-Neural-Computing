# Phase -1 Verified Command Log

**Date:** 2026-07-31
**Workspace:** `C:\Users\siddh\Documents\Projects\Dynamic-Neural-Computing`
**Phase:** `Phase -1 — Recover and certify the actual source baseline`

## Source discovery

| Command | Result |
|---|---|
| `git rev-parse HEAD` | `999bb4ad7ff55bb0e789a1317784cb6f2445a8b8` |
| `git remote -v` | `origin https://github.com/shreyashjagtap157/Dynamic-Neural-Computing.git` for fetch and push |
| `git fetch --all --tags --prune` | Succeeded after permission to update `.git/FETCH_HEAD` |
| `git cat-file -t 5e54c10` | Failed: `fatal: Not a valid object name 5e54c10` |
| `git branch -a --contains 5e54c10` | Failed: `error: malformed object name 5e54c10` |
| `git tag --contains 5e54c10` | Failed: `error: malformed object name 5e54c10` |
| `git log --all --oneline --decorate --grep="5e54c10\|194\|same-state\|NO_OP" -n 50` | Found only `6169136 DNC v2.1: Phase 13C counterfactual decision model and R=30 sensitivity campaign` |
| `git diff --stat baa510677b606e95160ced2e27693f62bbcb1855..999bb4ad7ff55bb0e789a1317784cb6f2445a8b8` | Two docs added, 3501 insertions |
| `git diff --name-status baa510677b606e95160ced2e27693f62bbcb1855..999bb4ad7ff55bb0e789a1317784cb6f2445a8b8` | Added `docs/DNC_EXHAUSTIVE_FUTURE_IMPLEMENTATION_MASTER_PLAN.md` and `docs/DNC_INTENT_VS_IMPLEMENTATION_REVIEW_HANDOFF.md` |

## Environment and install

| Command | Result |
|---|---|
| `python --version` | `Python 3.12.2` |
| `python -m pip --version` | `pip 25.0.1` under Python 3.12 |
| `python -m pip install -e .[dev]` | Failed while downloading Ruff: `ReadTimeoutError` from `files.pythonhosted.org` |
| `python -m pip install pytest pytest-cov` | Succeeded; installed `pytest 9.1.1`, `pytest-cov 7.1.0`, `coverage 7.15.2`, `iniconfig 2.3.0`, `pluggy 1.6.0` |
| `python -m pip install ruff build` | Succeeded; installed `ruff 0.16.1`, `build 1.5.0`, `pyproject_hooks 1.2.0` |
| `python -m pip show ruff build dynamic-neural-computing` | `ruff` and `build` found; `dynamic-neural-computing` not installed as an editable package |

## Verification commands

| Command | Result |
|---|---|
| `python -m pytest` | `204 passed in 10.01s` |
| `python -m compileall src tests tools scripts` | Passed |
| `$env:PYTHONPATH='src'; python scripts/audits/phase12_system_audit.py` | `8/8 passed` |
| `$env:PYTHONPATH='src'; python scripts/benchmarks/phase13_harness_tests.py` | `3/3 passed` |
| `python tools/generate_conformance_report.py` | Wrote `docs/conformance-report.md`; `Invariants: 30/30 covered, Conformance: 34/34 passed, ACDs: 4/4 resolved, Spec tooling: PASS, Conformant: YES` |
| `python -m ruff check src tools scripts/audits scripts/benchmarks` | Passed: `All checks passed!` |
| `python -m ruff check src tests tools scripts` | Failed with 170 findings, primarily historical unused imports/f-string issues in `scripts/legacy` and tests; this is not the production-source Ruff gate |
| `python -m build` | Failed in isolated mode because the temporary build environment could not download `setuptools>=69` |
| `python -m build --no-isolation` | Succeeded; built sdist and wheel |

## Artifact hashes

| File | SHA256 |
|---|---|
| `pyproject.toml` | `C6D6A4583C814691DD3B668BFEBB7BCEB467F2D332CCB3F98BEE444BBDA5A5D1` |
| `README.md` | `75337AEA3177CD4D50EA2EBAE26943250A82CE24166B4A910DC36EE39DEFD838` |
| `docs/DNC_EXHAUSTIVE_FUTURE_IMPLEMENTATION_MASTER_PLAN.md` | `A7FB311907C5AC1367053C05B526EA9D2ABED7CF53FC46621F389DF34560577F` |
| `docs/DNC_INTENT_VS_IMPLEMENTATION_REVIEW_HANDOFF.md` | `BA2829D0F68D233EEA829B74523AB39E225CEC305F348C332CB166A873FF38CD` |
| `dist/dynamic_neural_computing-0.1.0.dev0-py3-none-any.whl` | `ED96E3565C2370A89736D34C402093A9E9F01A2D482B2D3E9C78383B5A1B7B1B` |
| `dist/dynamic_neural_computing-0.1.0.dev0.tar.gz` | `5F0EA0BFC6A339E6D2DED6079FCF1109D1CB9C1F48C536FA065D0DBDAEAD8CE1` |

## Notes

- `pytest` was installed into the active Python 3.12 environment during this phase because the repository had no local lockfile, virtual environment, or vendored dev dependencies.
- Build artifacts were hash-recorded and then removed from the working tree.
- The isolated build failure is environmental: the temporary build venv could not download `setuptools>=69`; non-isolated build succeeded with the active environment's installed `setuptools`.
- Plain scripts require `PYTHONPATH=src`; pytest uses `pythonpath = ["src"]` from `pyproject.toml`.
