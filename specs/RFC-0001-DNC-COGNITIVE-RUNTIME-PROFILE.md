# RFC-0001: DNC Cognitive Runtime Profile

**State:** Draft
**Date:** 2026-07-31
**Depends on:** `specs/DNC-V2-ARCHITECTURE-FREEZE.md`, `specs/DCCL-FREEZE.md`, `specs/DNC-IR-FREEZE.md`
**Intent source:** `docs/DNC_INTENT_VS_IMPLEMENTATION_REVIEW_HANDOFF.md`
**Implementation plan:** `docs/DNC_EXHAUSTIVE_FUTURE_IMPLEMENTATION_MASTER_PLAN.md`

## Purpose

This RFC defines the broader DNC Cognitive Runtime profile without rewriting the frozen structural-kernel specifications. The frozen documents remain authoritative for the governed computation kernel. This RFC adds a versioned target profile for dynamic cognition above that kernel.

## North star

DNC is intended to become a governed cognitive and computation runtime that dynamically chooses:

- what kind of cognitive work to perform;
- how much computation to spend;
- which capabilities to use;
- what evidence is sufficient;
- when to repair, restructure, stop, escalate, or abstain;
- what verified work should become reusable knowledge or procedure.

The current repository primarily implements the governed computation-kernel foundation. It MUST NOT claim complete dynamic thinking solely from graph mutation, lifecycle control, synthetic evaluation, or provider routing.

## Profile boundaries

| Profile | Scope |
|---|---|
| DNC Kernel profile | Governed graph representation, authorization, mutation, transaction, replay, invariants, projection, provenance, and execution substrate |
| DNC Cognitive Runtime profile | Task semantics, epistemic state, cognitive action selection, calibrated halting, verification, active inquiry, hypothesis management, repair, capability self-model, memory, and skill lifecycle |
| Owner-bound AI profile | Owner identity, command authority, delegation, cancellation, mandate enforcement, and product interaction above DNC |

DNC may support the owner-bound AI profile, but owner identity and human-command authority are not kernel mutation semantics.

## Required action vocabulary

The Cognitive Runtime profile defines these typed cognitive actions:

```text
REASON
CONTINUE
BRANCH
VERIFY
RETRIEVE
OBSERVE_OR_TEST
ASK
REPAIR
REUSE_SKILL
RESTRUCTURE
ESCALATE
RESUME
STOP
ABSTAIN
```

Every cognitive action MUST be represented as a governed proposal with:

- stable identity;
- preconditions;
- expected effects;
- evidence requirements;
- estimated cost and latency;
- risk and reversibility;
- authorization decision;
- execution record;
- observed outcome or closure state.

Unsupported action types MUST be rejected or reported as unsupported. They MUST NOT be silently collapsed into generic graph execution.

## Goal-preserving plasticity

DNC may dynamically revise methods, representations, strategies, graph topology, compute allocation, and reusable procedures. It MUST NOT silently revise:

- the task objective;
- success criteria;
- user or system constraints;
- authority and permissions;
- risk class;
- mandatory verification policy;
- data-use or side-effect boundaries.

Changing any of those invariants is a governance event, not an ordinary cognitive optimization.

## Evidence and confidence

Evidence, agreement, calibrated correctness, verifier outcome, and halting decision are distinct objects.

DNC MUST NOT treat self-reported model confidence as verified correctness. Agreement among repeated generations MAY support semantic stability, but it is not proof of truth.

Adaptive stopping MUST be calibrated by risk class, domain, capability version, verifier coverage, and distribution-shift state. A global hard-coded `0.90` confidence threshold is not a valid stopping policy.

## Initial implementation obligations

The first compatible implementation slice MUST define:

- source-baseline reconciliation;
- K/C/N/E maturity profiles;
- `NO_OP` and `STOP` terminology;
- an intent traceability matrix;
- schemas or dataclasses for task, policy context, epistemic items, cognitive proposals, decisions, outcomes, and halting records before learned control affects decisions.

## Non-claims

This RFC does not claim that the current codebase already implements the Cognitive Runtime profile. It creates the governance target needed to implement it without corrupting historical frozen specifications.
