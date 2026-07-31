# Dependency Profiles and Lock Snapshot

**Date:** 2026-07-31
**Phase:** Phase 1

## Declared profiles

| Profile | Source | Dependencies |
|---|---|---|
| Core/minimal | `project.dependencies` | none |
| Dev | `project.optional-dependencies.dev` | `pytest>=8`, `pytest-cov>=5`, `ruff>=0.9` |
| Torch | `project.optional-dependencies.torch` | `torch>=2.2` |

## Observed tool lock snapshot

Pinned profile snapshots are stored in `requirements/core.lock`,
`requirements/dev.lock`, and `requirements/torch.lock`. The Torch file pins the
public backend contract; platform-specific transitive wheels must still be
resolved and qualified in each accelerator environment.

| Package | Version |
|---|---|
| Python | `3.12.2` |
| pip | `25.0.1` |
| setuptools | `75.3.0` |
| wheel | `0.44.0` |
| pytest | `9.1.1` |
| pytest-cov | `7.1.0` |
| coverage | `7.15.2` |
| iniconfig | `2.3.0` |
| pluggy | `1.6.0` |
| ruff | `0.16.1` |
| build | `1.5.0` |
| pyproject_hooks | `1.2.0` |

## Reproducibility notes

- `python tools/reproducible_build.py --outdir <directory>` succeeds and fixes
  `SOURCE_DATE_EPOCH` and `PYTHONHASHSEED` for byte-reproducible artifacts.
- Isolated build attempted to create a temporary environment and failed to download `setuptools>=69`.
- The optional Torch backend still requires a platform-specific resolver lock
  when its accelerator environment is selected; it is not installed here.
