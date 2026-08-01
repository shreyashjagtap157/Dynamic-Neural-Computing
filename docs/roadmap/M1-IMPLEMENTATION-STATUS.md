# M1 Reliable Generic Runtime — Implementation Status

**Updated:** 2026-08-01

**Branch:** `phase/m1-reliable-generic-runtime`

**Starting commit:** `2b5fb84`

**Current state:** M1 in progress; `M1-IR-001` complete

## Completed work package

### M1-IR-001 — Versioned Generic DNC-IR and schemas

- Packages the canonical Draft 2020-12 structural-graph schema with the Python distribution.
- Validates complete schema headers before deserialization and rejects partial, foreign, malformed,
  future, or otherwise unshipped versions.
- Preserves only the frozen headerless legacy compatibility path, including its original defaults.
- Validates the stable graph envelope without introducing a mandatory runtime dependency.
- Leaves graph semantics and invariant validation under `DNCIRValidator`; this point does not merge
  interchange validation with execution authorization.

The completion commit is the commit titled `Add versioned Generic DNC-IR schema validation`; resolve
its exact ID with `git log --oneline --grep='Add versioned Generic DNC-IR schema validation' -1`.

## Verification evidence

- `python -W error -m pytest -q`: 410 passed, 2 intentional environment-dependent skips.
- `python -m compileall -q src`: passed.
- `python -m ruff check src tests tools/generate_conformance_report.py`: passed.
- `PYTHONPATH=src python scripts/audits/phase12_system_audit.py`: 8/8 passed.
- Specification reference and RFC 2119 checks: passed.
- Architecture conformance: 30/30 invariants covered, 34/34 tests passed, 4/4 ACDs resolved.
- A locally built wheel contains `dnc/schemas/structural-graph-1.1.0.schema.json`.

## Claims and residual risks

This work supports a versioned and packaged Generic DNC-IR envelope. It does not yet support schema
migration between versioned formats, nor does it complete M1's typed port, edge, effect, placement,
security, SDK, registry, property, fuzz, concurrency, or failure-testing commitments. The headerless
legacy path is intentionally less strict and should be migrated before any future removal.

Rollback is a revert of the completion commit; serialized output remains byte-identical because the
canonical 1.1.0 header and graph payload were not changed.

## Exact next point

Implement `M1-IR-002`: typed input/output ports and validated data, control, state, and resource edge
contracts. Preserve current `Edge(source, target, edge_type, metadata)` construction through additive
defaults or an explicit migration adapter, add canonical serialization/golden vectors, and reject
port-direction, kind, schema, and cardinality mismatches before executable projection.
