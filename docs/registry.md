# DNC Specification Registry

Machine-readable registry of all specification namespaces, document states, version
format, and amendments. This file is the authoritative reference for
cross-document identifiers (per PR-13 Namespace Extension Mechanism) and
the document lifecycle state machine (per layer-1-terminology.md).

## Document State Machine

Every specification document progresses through:

```
Draft → Review → Frozen → Amended → Superseded → Archived
```

| State | Meaning |
|---|---|
| Draft | Initial authoring; identifier `Draft DR-<n>` |
| Review | Under governance review (PR-1 to PR-16) |
| Frozen | Approved and immutable; identifier `Baseline v<n>` |
| Amended | Frozen baseline plus `AMEND-<nnn>` |
| Superseded | Replaced by a later baseline |
| Archived | Retained for historical reference only |

## Version Format

- **Draft**: `Draft DR-<n>` (e.g., `Draft DR-1`, `Draft DR-2`)
- **Frozen baseline**: `Baseline v<n>` (e.g., `Baseline v1.0`)
- **Amended**: `Baseline v<n> + AMEND-<nnn>`

## Namespaces (11 subspaces)

| Namespace | Prefix | Range |
|---|---|---|
| Principles | PR- | PR-1 to PR-16 |
| Runtime Invariants | INV- | INV-1 to INV-11 |
| State Invariants | INV-STATE- | INV-STATE-1 to INV-STATE-11 |
| Control Loop Invariants | INV-CTRL- | INV-CTRL-1 to INV-CTRL-15 |
| Learning Invariants | INV-CL- | INV-CL-1 to INV-CL-17 |
| Planner Invariants | INV-PLANNER- | INV-PLANNER-1 to INV-PLANNER-10 |
| Cost Invariants | INV-COST- | INV-COST-1 to INV-COST-8 |
| Theorems | THM- | THM-1 to THM-99 |
| Definitions | DEF- | DEF-1 to DEF-99 |
| Axioms | AX- | AX-1 to AX-20 |
| Lemmas | LEM- | LEM-1 to LEM-99 |

## Specification Documents (Frozen Baseline v1.0)

| Document ID | Title | Layer | State | Version |
|---|---|---|---|---|
| SPEC-FOUND | Specification Foundation | 0 | Frozen | Baseline v1.0 |
| SPEC-TERM | Core Terminology | 1 | Frozen | Baseline v1.0 |
| SPEC-INV | Runtime Invariants | 2 | Frozen | Baseline v1.0 |
| SPEC-CTRL | Control Loop | 3 | Frozen | Baseline v1.0 |
| SPEC-FM | Formal Model | 3 | Frozen | Baseline v1.0 |
| SPEC-EXEC | Execution Model | 3 | Frozen | Baseline v1.0 |
| SPEC-STATE | State Management | 3 | Frozen | Baseline v1.0 |
| SPEC-REPLAN | Replanning Protocol | 3 | Frozen | Baseline v1.0 |
| SPEC-PLANNER | Planner Pipeline | 4 | Frozen | Baseline v1.0 |
| SPEC-SCHED | Scheduler | 4 | Frozen | Baseline v1.0 |
| SPEC-MODLIFE | Module Lifecycle | 4 | Frozen | Baseline v1.0 |
| SPEC-COST | Cost Semantics | 4 | Frozen | Baseline v1.0 |
| SPEC-PROV | Provenance Model | 5 | Frozen | Baseline v1.0 |
| SPEC-FAIL | Failure Taxonomy | 5 | Frozen | Baseline v1.0 |
| SPEC-EVAL | Evaluation Suite | 5 | Frozen | Baseline v1.0 |
| SPEC-CL | Continual Learning | 6 | Frozen | Baseline v1.0 |
| SPEC-ROADMAP | MVP Roadmap | 6 | Frozen | Baseline v1.0 |
| SPEC-DIST | Distributed Handoff Protocol | 7 | Frozen | Baseline v1.0 |
| SPEC-TRANS | Transaction Semantics | 3 / 4 | Frozen | Baseline v1.1 |
| SPEC-DCCL | Dynamic Computation Control Layer | 3 / 4 | Frozen | Baseline v1.1 |

## Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| DIST-AMEND-001 | SPEC-DIST | 2026-07-12 | Baseline v1.0: resolved open issues INV-DIST-3/4/5/6 | No |
| FRZ-001 | All spec docs | 2026-07-12 | Frozen to Baseline v1.0 via tools/freeze_spec.py | No |
| ARCH-AMEND-002 | SPEC-ARCH | 2026-07-13 | Baseline v1.1: reference runtime declared conformant with Architecture v1.0 (ACD-001..ACD-004 resolved, closed by tests/conformance/). Conformance report artifact at docs/conformance-report.md. | No |

## Draft Cognitive Runtime Extensions

These documents are draft governance extensions for the expanded DNC intent. They do not amend or replace the frozen kernel specifications until approved through the normal review process.

| Document ID | Title | State | Related profile |
|---|---|---|---|
| RFC-0001 | DNC Cognitive Runtime Profile | Draft | C |
| DNC-MATURITY-PROFILES | K/C/N/E Maturity Profiles | Draft | K, C, N, E |
| NO-OP-STOP | `NO_OP` and `STOP` Terminology | Draft | K, C |
| PHASE1-KERNEL | Kernel hardening inventory, compatibility, dependency, lint, and SBOM evidence | Draft | K |
| PHASE2-SNAPSHOT | Snapshot manifest, isolation grades, reproducibility grades, and effect ledger | Draft | K |
| PHASE3-COGNITION | Canonical cognitive contracts, epistemic state, schema hashing, import/export, and invalidation | Draft | C |
| PHASE4-CAPABILITIES | Capability registry, auditable broker, provider-neutral adapters, resilience, and backend cards | Draft | C |
| PHASE5-ASSURANCE | Scoped verifiers, delayed outcomes, calibration artifacts, semantic agreement, shift, and risk policy | Draft | C |
| PHASE6-HALTING | Attempt records, safe adaptive inference halting, budgets, baselines, and paired evaluation | Draft | C |
| PHASE7-CONTROL | Authorization-first semantic candidates, Pareto selection, lifecycle, alternatives, and shadow logging | Draft | C |
| PHASE8-SEMANTICS | Capability-bound semantic DNC-IR synthesis, active inquiry, causal validity, and outcome comparison | Draft | C |
