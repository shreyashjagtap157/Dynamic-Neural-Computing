# DNC Maturity Profiles

**State:** Draft
**Date:** 2026-07-31
**Related RFC:** `specs/RFC-0001-DNC-COGNITIVE-RUNTIME-PROFILE.md`

## Purpose

The expanded DNC intent cannot be represented by a single maturity number without confusing kernel rigor with cognitive capability. This document defines orthogonal maturity profiles for future claims, tests, and release gates.

## Profile axes

| Axis | Name | Scope |
|---|---|---|
| K | Governed computation kernel | IR, graph mutation, authorization, transactions, rollback, replay, provenance, invariants, execution core |
| C | Cognitive and metacognitive control | task state, evidence, hypotheses, action selection, verification, calibrated stopping, active inquiry, repair, memory, skills |
| N | Neural adaptive computation | tensor-native execution, trainable dynamic depth/routing, local neural backends, optimizer/runtime profiles |
| E | Enterprise operations | tenant isolation, IAM, policy, secrets, persistence, audit, supply chain, observability, SLOs, incident response |

## Claim rule

Every maturity claim MUST identify the relevant axis and evidence. A K-profile result does not imply C, N, or E maturity.

Examples:

- "K profile prototype" may be supported by executable structural invariants and replay tests.
- "C profile prototype" requires typed cognitive state and state-dependent cognitive-action behavior.
- "N profile prototype" requires actual neural compute variation in a compatible local model, not repeated hosted API calls.
- "E profile prototype" requires operational controls in a scoped deployment profile.

## Draft levels

| Level | Meaning |
|---|---|
| 0 | Not implemented |
| 1 | Contract or specification exists |
| 2 | Deterministic reference implementation exists behind a flag |
| 3 | Local tests and replay evidence exist |
| 4 | Hidden or shifted evaluation supports the claim |
| 5 | Hardened scoped deployment evidence exists |

## Current baseline assessment

As of commit `999bb4ad7ff55bb0e789a1317784cb6f2445a8b8`:

| Axis | Baseline assessment | Rationale |
|---|---|---|
| K | At least Level 3 by prior repository status, pending fresh local test verification | The repository status reports 186 passing tests, conformance coverage, transactions, replay, provenance, and lifecycle audits |
| C | Level 1 planning authority, not implementation | Intent handoff and master plan define the required cognitive runtime, but typed cognitive state and action selection are not yet implemented as the default system |
| N | Level 1 to 2 foundations | Neural contracts and optional PyTorch adapter exist, but adaptive depth/routing is not proven |
| E | Level 0 to 1 planning | Enterprise roadmap and plan exist, but production controls are not implemented |

These levels are conservative and MUST be revised only with executable evidence.
