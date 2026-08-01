# Lint and Static Analysis Baseline

**Date:** 2026-07-31
**Phase:** Phase 1

## Passing gate

```text
python -m ruff check src tools scripts/audits scripts/benchmarks
```

Result:

```text
All checks passed!
```

This is the Phase 1 production-source lint gate.

## Known broad-scope baseline

```text
python -m ruff check src tests tools scripts
```

Result:

```text
170 findings
```

The findings are primarily historical unused imports, f-strings without placeholders, and import-position issues in `scripts/legacy` and older tests. They are intentionally baselined rather than mass-rewritten during Phase 1.

## Remediation policy

1. New production source must pass the production-source lint gate.
2. New tests should avoid adding broad-scope Ruff findings.
3. Legacy cleanup should be handled in scoped PRs with tests, not mixed into kernel hardening.
4. Broad lint should be expanded only after each class of findings has a tracked remediation owner.
