# SBOM and Build Provenance

**Date:** 2026-07-31
**Phase:** Phase 3

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
| `dynamic_neural_computing-0.1.0.dev0-py3-none-any.whl` | `25F7FFD76D11E1B63728530C8C40101C6771238BB4A980348FC4F14EC323CAD7` |
| `dynamic_neural_computing-0.1.0.dev0.tar.gz` | `B77CD5BDFC16E88D3A68C6CC6AE3D2195FE1DF96F044889199BB848F083FEEA6` |

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
