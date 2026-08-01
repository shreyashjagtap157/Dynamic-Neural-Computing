# `NO_OP` and `STOP` Terminology

**State:** Draft
**Date:** 2026-07-31
**Related RFC:** `specs/RFC-0001-DNC-COGNITIVE-RUNTIME-PROFILE.md`

## Purpose

The expanded DNC plan requires structural mutation decisions and task-level halting decisions to remain separate. This document freezes the terminology before additional implementation.

## `NO_OP`

`NO_OP` is a structural counterfactual decision.

It answers:

```text
Is the proposed structural mutation better than preserving the current graph state?
```

`NO_OP` belongs to the governed computation kernel. It compares candidate graph or state changes with a same-state preservation baseline. A `NO_OP` decision may prevent a mutation, but it does not by itself mean the task answer is complete.

Required evidence for a mature `NO_OP` claim includes:

- candidate identity;
- source state identity;
- preservation baseline;
- mutation authorization decision;
- assessment metric;
- isolation and reproducibility grade;
- proof or declaration of uncaptured external state.

## `STOP`

`STOP` is a task-level cognitive halting decision.

It answers:

```text
Is the current answer or best-so-far state sufficiently supported, useful, and safe to return under the task policy?
```

`STOP` belongs to the Cognitive Runtime profile. It considers correctness evidence, unresolved contradictions, semantic stability, value of further computation, risk class, verification policy, missing evidence, costs, deadlines, and any required approval or outcome monitoring.

Required evidence for a mature `STOP` claim includes:

- task and policy identity;
- current answer state or best-so-far state;
- evidence and verifier coverage;
- calibrated risk or uncertainty estimate;
- contradiction and missing-information status;
- marginal value-of-computation estimate;
- semantic novelty or saturation assessment when repeated attempts are used;
- mandatory approvals or delayed outcomes still outstanding;
- final halt, continue, abstain, ask, verify, repair, or escalate decision.

## Non-substitution rule

`NO_OP` MUST NOT be used as evidence that a task should stop. `STOP` MUST NOT be used as evidence that a structural mutation was unnecessary.

A valid run may contain both:

```text
Reject candidate mutation with NO_OP
Continue task with VERIFY
Eventually return STOP
```

or:

```text
Accept candidate mutation
Execute and assess changed graph
Return ABSTAIN instead of STOP because evidence remains insufficient
```

The terms are intentionally separate because they govern different objects.
