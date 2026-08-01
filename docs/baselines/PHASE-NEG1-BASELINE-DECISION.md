# Phase -1 Baseline Decision Record

**Date:** 2026-07-31
**Decision status:** Provisional local baseline selected; reported alternate lineage unresolved
**Phase:** `Phase -1 — Recover and certify the actual source baseline`

## Decision

Use commit `999bb4ad7ff55bb0e789a1317784cb6f2445a8b8` on branch `codex/intent_implementation_1` as the provisional local implementation baseline for this workspace.

This is not a final archive/tag decision for the overall project because the reported commit `5e54c10` remains unavailable.

## Rationale

1. Remote refs were refreshed with `git fetch --all --tags --prune`.
2. Commit `5e54c10` is still not present in local or fetched refs.
3. The diff from public `baa510677b606e95160ced2e27693f62bbcb1855` to `999bb4ad7ff55bb0e789a1317784cb6f2445a8b8` contains only the two intent/planning documents.
4. The current workspace verifies successfully for the runnable local gates:
   - pytest: `204/204 passed`;
   - compileall: passed;
   - Phase 12 audit: `8/8 passed`;
   - Phase 13 harness: `3/3 passed`;
   - conformance report: conformant, `30/30` invariants and `34/34` conformance tests.
5. Ruff and build tooling were installed after the initial network timeout.
6. The scoped production-source Ruff gate passes.
7. Non-isolated package build succeeds and produced hash-recorded sdist/wheel artifacts.

## Authoritative test count

For this workspace after the current implementation changes, the authoritative observed count is:

```text
204 passed
```

The prior public repository status count of `186/186` remains historical evidence for the 2026-07-27 baseline. The reported `194`-test count remains unverified because its source commit is unavailable.

## Restrictions

- Do not claim that `5e54c10` was recovered.
- Do not claim that the reported 194-test sandbox was independently verified.
- Do not tag this as the final project-wide baseline until the owner either recovers `5e54c10` or explicitly accepts this lineage.
- Do not claim full Phase -1 exit because alternate-lineage archive/tagging and owner approval remain open.

## Next required owner decision

The owner should choose one of:

1. recover or provide the missing `5e54c10` source;
2. declare `5e54c10` superseded by the current lineage;
3. accept `999bb4ad7ff55bb0e789a1317784cb6f2445a8b8` plus the current workspace changes as the new baseline after review.
