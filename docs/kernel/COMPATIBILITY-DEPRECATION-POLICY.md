# Compatibility and Deprecation Policy

**Date:** 2026-07-31
**Phase:** Phase 1

## Version identifiers

| Identifier | Current value | Source |
|---|---|---|
| DNC-IR schema ID | `dnc.ir.structural_graph` | `dnc.kernel.versioning` |
| DNC-IR schema version | `1.1.0` | `dnc.kernel.versioning` |
| Kernel compatibility version | `2026.07.phase1` | `dnc.kernel.versioning` |
| Compatibility policy version | `1` | `dnc.kernel.versioning` |

## Compatibility rules

1. Frozen kernel APIs remain importable through their existing modules.
2. Additive fields in serialized data must be ignored or tolerated by older-compatible readers when possible.
3. `DNWIRSerializer.from_dict` must continue to load legacy graph dictionaries that lack schema headers.
4. Canonical JSON output must remain byte-stable for golden vectors unless the schema version changes.
5. DNC cognitive-runtime contracts are additive and must not change DNC-IR identity or graph hashes.
6. Reference implementations must be labeled as reference or synthetic when used in reports.
7. Optional backends and tools must stay behind optional dependency profiles or adapter boundaries.

## Deprecation rules

1. New replacements must be introduced before old APIs are removed.
2. Deprecated APIs must keep a compatibility facade for at least one minor compatibility version.
3. A deprecation notice must identify replacement API, migration path, and removal eligibility.
4. Removal requires tests proving old serialized fixtures still migrate or fail with explicit errors.
5. Historical frozen specifications must not be rewritten to claim broader cognitive-runtime semantics.

## Facade policy

The root package `dnc.__init__` remains a compatibility facade for the canonical system API. New Phase 1 hardening surfaces live under `dnc.kernel` and do not require callers to import cognitive-layer modules.
