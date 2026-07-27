# DNC Specification Project

## Project Overview

This is the Dynamic Neural Computation (DNC) specification project — a formal specification for researching and developing dynamic neural computing systems.

**Specification Version**: 0.1.0 (Draft DR-2)
**Purpose**: Research and develop runtime systems that synthesize and execute dynamic computation graphs with runtime planning, state management, and continual learning.

## Suitability for Dynamic Neural Computing Research

**YES** — This project is designed for DNC research. The specification defines:
- Execution graphs (DAGs) of module instances with structural analogy to neural circuits
- Dynamic runtime planning (planner synthesizes graphs at runtime) with O(|V|²) complexity bounds
- Control loop (Observe → Decide → Act → Assess) with two-tier async execution
- State management with checkpoints, state migration, and rollback
- Formal trace semantics for reasoning about execution
- Continual learning with clustering-based bounded drift, invariant preservation, and root-cause KB rollback
- Full provenance tracking and hierarchical failure taxonomy
- Explicit neural computation definition: structural analogy to neural circuits, not neuron-level simulation

## Directory Structure

```
DNC/
├── docs/                       # Project documentation
│   └── registry.md             # Machine-readable specification registry (11 namespaces, 12 amendments)
├── specs/                      # Formal specification documents
│   ├── layer-0-foundation/    # Governance, 16 principles (PR-1 to PR-16)
│   ├── layer-1-terminology/    # Single authoritative vocabulary + neural computation terms
│   ├── layer-2-invariants/     # 11 constitutional runtime invariants
│   ├── layer-3-execution/      # Formal model, execution model, state management, control loop
│   ├── layer-4-mechanisms/      # Planner pipeline, scheduler, module lifecycle, cost semantics
│   ├── layer-5-observability/  # Provenance model, failure taxonomy, evaluation suite
│   ├── layer-6-evolution/       # Continual learning, MVP roadmap (4 phases)
│   └── layer-7-distributed/     # Distributed handoff protocol (stub, not frozen)
├── tools/                       # Utility scripts
│   └── fix_refs.py             # Cross-reference fixer, PR-4 verifier, RFC 2119 linter
└── research/                    # Research artifacts (empty, for future use)
```

## Specification Architecture

The specification is organized into 7+1 layers where each layer may only reference lower layers (DAG structure enforced by PR-4):

- **Layer 0** (Governance): How the specification is written and evolved
- **Layer 1** (Vocabulary): What every term means
- **Layer 2** (Constitution): What properties must never be violated
- **Layer 3** (Semantics): How execution proceeds mathematically
- **Layer 4** (Mechanisms): How components are implemented
- **Layer 5** (Observability): How runtime behavior is measured and tracked
- **Layer 6** (Evolution): How the runtime improves from experience
- **Layer 7** (Distributed): Inter-process and inter-node handoffs (stub — not frozen)

## Key Documents

| Document | Layer | Purpose |
|----------|-------|---------|
| specification-foundation.md | 0 | 16 governance principles (PR-1 to PR-16) |
| core-terminology.md | 1 | All vocabulary + neural computation definitions |
| runtime-invariants.md | 2 | 11 invariants (INV-1 to INV-11) |
| formal-model.md | 3 | Mathematical execution model with trace semantics |
| state-management.md | 3 | ES(t) = (W,M,C,H,R), checkpoints, migration |
| control-loop.md | 3 | O→D→A→Assess, async neural exclusion (INV-CTRL-9b), backpressure (INV-CTRL-9c) |
| planner-pipeline.md | 4 | Runtime graph synthesis with INV-PLANNER-10 complexity bounds |
| cost-semantics.md | 4 | Resource accounting with staged checkpoint protocol (INV-COST-8) |
| continual-learning.md | 6 | Clustering-based bounded drift (DEF-CL-9 distance metric), root-cause rollback (INV-CL-13), rollback circuit-breaker (INV-CL-17) |
| failure-taxonomy.md | 5 | INVALID_OUTPUT, GPU recovery, PARTIAL_FAILURE classes |

## Identifier Namespaces (11 subspaces)

| Namespace | Prefix | Range |
|-----------|--------|-------|
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

## Tools

**fix_refs.py** — Multi-mode tool for DNC spec file management:

```bash
# Fix cross-references after file moves
python tools/fix_refs.py

# Verify PR-4 compliance (all cross-refs point to lower layers)
python tools/fix_refs.py --verify

# Check RFC 2119 keyword discipline across all spec files
python tools/fix_refs.py --rfc2119
```

## Known Formal Gaps (pre-Baseline v1 resolution tracking)

| Gap | Status | Resolution |
|-----|--------|------------|
| G-12.1 ValidCheckpoint invariant-satisfaction | ✅ RESOLVED | Condition 5 added; INV-STATE-2 now references DEF-FM-11 |
| G-12.4 RNG state in ES(t) | ✅ RESOLVED | R(t) added to execution record |
| G-12.1 cross-file DEF-3 vs DEF-FM-11 | ✅ RESOLVED | INV-REPLAN-9 and INV-STATE-2 both reference DEF-FM-11 |
| G-12.3 INV-8 bootstrapping | ⚠️ OPEN | Requires verified verifier; cannot be resolved in spec |
| G-12.2 byte-exact memory | ⚠️ OPEN | Acceptable as implementation constraint |

## Specification State Machine

Documents progress through: Draft → Review → Frozen → Amended → Superseded → Archived

## Version Format

- Draft: `Draft DR-<n>` (e.g., Draft DR-1, Draft DR-2)
- Frozen baseline: `Baseline v<n>`
- Amended: `Baseline v<n> + AMEND-<nnn>`

## Implementation Phases (from mvp-roadmap.md)

1. **Phase 0**: Specification freeze (8-12 weeks)
2. **Phase 1**: Core execution engine (16-24 weeks)
3. **Phase 2**: Dynamic planning and scheduling (20-32 weeks)
4. **Phase 3**: Observability and self-improvement (24-40 weeks)
5. **Phase 4**: Production hardening (12-20 weeks)

Total estimated: 80-128 weeks for a team of 3-5 engineers.

## Governance Principles (PR-1 to PR-16)

- PR-1: Single-Ownership Rule
- PR-2: Single-Vocabulary Rule
- PR-3: Single-Notation Rule
- PR-4: Lower-Layers-Only Rule (enforced by --verify)
- PR-5: Verification-Mechanism Rule
- PR-6: No-Undefined-Behavior Rule
- PR-7: Normative-Wording Rule (enforced by --rfc2119)
- PR-8: Preservation-under-Extension Rule
- PR-9: Evidence Principle
- PR-10: Version Consistency Rule
- PR-11: External Authority Structure (regulated deployments)
- PR-12: Minimum Safety Bounds
- PR-13: Namespace Extension Mechanism
- PR-14: Algorithmic Transparency
- PR-15: Bias and Fairness Evaluation
- **PR-16: Principle Conflict Resolution** (CONFIG_OVERRIDE mechanism for PR-10 vs PR-12 tension)