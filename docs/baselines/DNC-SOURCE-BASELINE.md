# DNC Source Baseline

**Date:** 2026-07-31
**Status:** Phase -1 baseline reconciliation record for the expanded DNC implementation plan
**Plan reference:** `docs/DNC_EXHAUSTIVE_FUTURE_IMPLEMENTATION_MASTER_PLAN.md`, Section 2.3 and Section 25

## Repository identity

| Field | Value |
|---|---|
| Local path | `C:\Users\siddh\Documents\Projects\Dynamic-Neural-Computing` |
| Remote | `https://github.com/shreyashjagtap157/Dynamic-Neural-Computing.git` |
| Branch | `codex/intent_implementation_1` |
| Baseline commit | `999bb4ad7ff55bb0e789a1317784cb6f2445a8b8` |
| Baseline short SHA | `999bb4a` |
| Package version | `0.1.0.dev0` |
| Python observed | `C:\Users\siddh\AppData\Local\Programs\Python\Python312\python.exe` |
| Python version | `Python 3.12.2` |
| Pip version | `pip 25.0.1` |

## Baseline reconciliation

The future implementation plan refers to two source baselines:

| Source | Status in this workspace | Evidence |
|---|---|---|
| Public merge `baa510677b606e95160ced2e27693f62bbcb1855` | Present as repository history | `git log --oneline -n 12` shows `baa5106` |
| Reported commit `5e54c10` with 194 tests | Not present in local object database | `git cat-file -t 5e54c10` returned `fatal: Not a valid object name 5e54c10` |
| Current local branch head | Present and selected as local working baseline | `git rev-parse HEAD` returned `999bb4ad7ff55bb0e789a1317784cb6f2445a8b8` |

Remote refs were refreshed with `git fetch --all --tags --prune`; `5e54c10` remained unavailable after fetch. The reported `5e54c10` revision remains documentary evidence only until recovered or superseded. No future work should claim to have verified the exact same-state candidate sandbox or 194-test result from that revision unless the source is located and tested.

The diff from public `baa510677b606e95160ced2e27693f62bbcb1855` to `999bb4ad7ff55bb0e789a1317784cb6f2445a8b8` contains only:

- `docs/DNC_EXHAUSTIVE_FUTURE_IMPLEMENTATION_MASTER_PLAN.md`;
- `docs/DNC_INTENT_VS_IMPLEMENTATION_REVIEW_HANDOFF.md`.

## Worktree status

Before this baseline record was added, `git status --short` returned no output, indicating a clean worktree at the local branch head.

## Test and tooling commands

| Command | Result |
|---|---|
| `python -m pip install -e .[dev]` | Failed while downloading Ruff from `files.pythonhosted.org` due read timeout |
| `python -m pip install pytest pytest-cov` | Succeeded |
| `python -m pytest` | Passed: `204 passed in 10.01s` |
| `python -m compileall src tests tools scripts` | Passed |
| `$env:PYTHONPATH='src'; python scripts/audits/phase12_system_audit.py` | Passed: `8/8` |
| `$env:PYTHONPATH='src'; python scripts/benchmarks/phase13_harness_tests.py` | Passed: `3/3` |
| `python tools/generate_conformance_report.py` | Passed; conformant with `30/30` invariants and `34/34` conformance tests |
| `python -m pip install ruff build` | Succeeded |
| `python -m ruff check src tools scripts/audits scripts/benchmarks` | Passed |
| `python -m ruff check src tests tools scripts` | Failed with historical findings in legacy scripts/tests; not the production-source gate |
| `python -m build` | Failed in isolated mode because temporary build environment could not download `setuptools>=69` |
| `python -m build --no-isolation` | Passed; built hash-recorded sdist and wheel |

The current local test suite is verified at `204/204` after adding the cognitive-runtime Phase 0/early Phase 1 scaffolding tests. The last repository status document records `186/186` as of 2026-07-27; that is now a historical baseline, not the current workspace count.

Detailed command evidence is recorded in `docs/baselines/PHASE-NEG1-COMMAND-LOG.md`.

## Authoritative starting point

Until the product owner recovers `5e54c10` or selects another source revision, implementation work in this workspace starts from:

```text
999bb4ad7ff55bb0e789a1317784cb6f2445a8b8
```

## Baseline gate conclusion

The Phase -1 baseline gate is partially satisfied:

- current repository, branch, commit, remote, package version, worktree state, and local Python environment are recorded;
- remotes were refreshed and the unavailable `5e54c10` revision is documented as a gap;
- current runnable tests, compile checks, audits, benchmark harness checks, and conformance report were reproduced;
- production-source Ruff and non-isolated wheel/sdist build reproduction are complete;
- isolated build remains blocked by temporary-build-environment network access to `setuptools>=69`;
- final baseline tag/archive and owner approval remain open.

Feature work that depends on `5e54c10` must remain blocked until that revision is recovered or the owner explicitly accepts restarting from the current local baseline.
