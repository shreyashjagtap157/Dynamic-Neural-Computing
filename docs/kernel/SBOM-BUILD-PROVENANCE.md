# SBOM and Build Provenance

**Date:** 2026-07-31
**Phase:** Phase 4

## Build command

```text
python tools/reproducible_build.py --outdir <directory>
```

Result:

```text
Successfully built dynamic_neural_computing-0.1.0.dev0.tar.gz and dynamic_neural_computing-0.1.0.dev0-py3-none-any.whl
```

## Build artifacts

Artifacts were generated, hash-recorded, and then removed from the working tree.

| Artifact | SHA256 |
|---|---|
| `dynamic_neural_computing-0.1.0.dev0-py3-none-any.whl` | `53153673DCC5D4EA0A8A5DF58D55874B7A69C5CA36936B951D2C6B2691FB8C7A` |
| `dynamic_neural_computing-0.1.0.dev0.tar.gz` | `D3976C5ADBF2CC42B75B752E4C99214453FCDA5FDA56E0DC3CDFD90C2D5A2CE2` |

Two independent builds produced these same hashes for both artifacts.

## Minimal SBOM

| Component | Version | Scope |
|---|---|---|
| `dynamic-neural-computing` | `0.1.0.dev0` | project package |
| Python | `3.12.2` | runtime |
| setuptools | `75.3.0` | build backend/runtime environment |
| wheel | `0.44.0` | build support |
| build | `1.5.0` | build frontend |
| pyproject_hooks | `1.2.0` | build frontend dependency |

## Dependency statement

The core package declares no required runtime dependencies. Development and optional backend dependencies are outside the minimal runtime SBOM.
