# Specification Foundation

## Metadata

| Field | Value |
|---|---|
| Document | specification-foundation.md |
| Title | Specification Foundation |
| Document ID | SPEC-FOUND |
| State | Frozen |
| Version | Architecture v1.0 |
| Owner | DNC Specification |
| Layer | 0 |
| Owner Question | How is this specification governed? |
| Last Updated | 2026-07-11 |

---

## Section 0 — References

### 0.A Normative References

The following documents, through their normative requirements, are essential for the interpretation of this specification. Readers MUST understand and follow these references for correct interpretation of any DNC specification document.

- **RFC 2119** — Bradner, S. (1997). *Key words for use in RFCs to Indicate Requirement Levels*. IETF. Defines the normative requirement keywords: MUST, SHALL, MUST NOT, SHOULD, MAY, etc.
- **RFC 8174** — Leiba, B. (2017). *Ambiguity of Uppercase vs. Lowercase in RFC 2119 Key Words*. IETF. Clarifies that capitalized keyword forms (MUST, SHALL, SHOULD) are to be interpreted as RFC 2119 specifies; uncapitalized forms carry no normative implication.

### 0.B Informative References

The following provide architectural precedent, motivation, or illustrative examples. They are informative and not required for the interpretation of DNC specification documents.

- **RISC-V ISA Specification** — Waterman, A. & Asanović, K. (eds.). *The RISC-V Instruction Set Manual*. Demonstrates the separation of operational description from formal semantics across multiple specification layers.
- **L4 Microkernel Family** — Liedtke, J. (1995). *On Microkernel Construction*. USENIX. Demonstrates fault-domain isolation and privileged exception handling as a foundation for trusted system layers.
- **Compilers: Principles, Techniques, and Tools (2nd ed.)** — Aho, A., Lam, M., Sethi, R., & Ullman, J. (2006). The Dragon Book. Informative precedent for specification structure: separating syntax, semantics, and execution model.

---

## Section 1 — Concept Taxonomy

This section defines the four concept classes that appear throughout DNC specification documents. Each class has distinct governance, verification obligations, and allowed cross-references.

| Concept | Governs | Verified By | May Reference |
|---|---|---|---|
| **Principle** | The specification itself | Specification review, static consistency | Nothing above Layer 0 |
| **Invariant** | The runtime | Formal proof, runtime assertion, replay, model checking | Principles, terminology |
| **Mechanism** | Implementation | Tests, benchmarks, profiling | Principles, invariants |
| **Evaluation** | Evidence | Statistical protocol | Everything below Layer 5 |

A **Principle** constrains how the specification is written and evolved. A **Principle** exists independently of whether any runtime has been implemented.

An **Invariant** constrains runtime behavior. An **Invariant** is verified against actual executions or formal proofs of all possible executions.

A **Mechanism** is an implemented component. Verification is empirical: tests, benchmarks, profiling.

An **Evaluation** is a claim about system properties supported by evidence. Verification is statistical: protocol, baselines, significance testing.

---

## Section 2 — Identifier Namespaces

All specification identifiers are assigned permanent, stable namespaces. Once allocated, an identifier MUST NOT be reassigned to a different object within its lifetime. Future allocations reserve ranges to prevent conflicts.

| Namespace | Prefix | Allocation | Registry |
|---|---|---|---|
| Principles | PR- | PR-1 through PR-10 (reserved up to PR-99) | This document |
| Invariants | INV- | INV-1 through INV-10 (reserved up to INV-99) | runtime-invariants.md |
| Runtime Invariants | INV-RT-* | INV-RT-1, INV-RT-2, ... | execution-semantics.md |
| Evaluation Invariants | INV-EV-* | INV-EV-1, INV-EV-2, ... | evaluation-framework.md |
| Replay Invariants | INV-REP-* | INV-REP-1, INV-REP-2, ... | replay-semantics.md |
| Capability Invariants | INV-CP-* | INV-CP-1, INV-CP-2, ... | interfaces.md |
| Policy Invariants | INV-POL-* | INV-POL-1, INV-POL-2, ... | decision-policy.md |
| Theorems | THM- | THM-1, THM-2, ... (reserved up to THM-99) | formal-model.md |
| Definitions | DEF- | DEF-1, DEF-2, ... (reserved up to DEF-99) | formal-model.md |
| Axioms | AX- | AX-1, AX-2, ... (reserved up to AX-20) | formal-model.md |
| Lemmas | LEM- | LEM-1, LEM-2, ... (reserved up to LEM-99) | formal-model.md |
| Evaluation Metrics | MET-* | MET-DCI-1, MET-CCG-1, MET-BE-1, ... | evaluation-framework.md |
| Trace Extensions | TRC-* | Reserved for trace schema extensions | execution-trace-format.md |
| Adaptation Metrics | MET-* | MET-PS-1, MET-TD-1, ... | evaluation-framework.md |
| Extension | EXT-* | EXT-<vendor>-<feature> | conformance-model.md |

Cross-document citations MUST use the prefixed identifier (e.g., "per INV-4", "by THM-1", "see DEF-3"). No local synonyms or unnamed references to numbered objects are permitted.

---

## Section 3 — Document Dependency Graph

The DNC specification is organized into seven layers. Each layer may reference any lower layer; no layer may reference any higher layer. The document dependency graph SHALL remain a directed acyclic graph (DAG). Any proposed change that introduces a cycle is a Layering Violation and requires a new specification version that resolves the cycle before adoption.

```
Layer 0 (Governance)
  │
  ├── specification-foundation.md
  │
Layer 1 (Vocabulary)
  │
  └── core-terminology.md
  │
Layer 2 (Constitution)
  │
  └── runtime-invariants.md
  │
Layer 3 (Semantics)
  │
  ├── execution-model.md
  │
  └── formal-model.md
  │
Layer 4 (Mechanisms)
  │
  ├── planner-pipeline.md
  ├── scheduler.md
  ├── module-lifecycle.md
  │
  └── cost-semantics.md
  │
Layer 5 (Observability)
  │
  ├── provenance-model.md
  ├── failure-taxonomy.md
  │
  └── evaluation-suite.md
  │
Layer 6 (Evolution)
  │
  ├── continual-learning.md
  ├── mvp-roadmap.md
  ├── execution-semantics.md         (Architecture v1.0)
  ├── architecture.md                (Architecture v1.0)
  ├── interfaces.md                  (Architecture v1.0)
  ├── execution-trace-format.md      (Architecture v1.0)
  ├── replay-semantics.md            (Architecture v1.0)
  ├── conformance-model.md           (Architecture v1.0)
  ├── evaluation-framework.md         (Architecture v1.0)
  └── decision-policy.md             (Architecture v1.0)
```

This diagram is normative. Its acyclicity is a direct consequence of PR-4.

---

## Section 4 — Principles

The following ten principles govern every DNC specification document. Each principle appears with its stable identifier, statement in RFC 2119 normative language, rationale, requirements, verification mechanism, and interactions with other principles.

---

### PR-1 Single-Ownership Rule

**Statement**

Every specification concept SHALL have exactly one owning document. No concept SHALL be defined, redefined, or ambiguously described across multiple documents.

**Rationale**

When two documents govern the meaning of a single term, they inevitably drift out of synchronization. Reviewers spend cycles resolving conflicts rather than evaluating substance. Single ownership eliminates this class of specification entropy.

**Requirements**

- Every capitalized or otherwise significant term appearing in any document MUST appear in exactly one document's glossary or definition section.
- Cross-references to a concept MUST point to its owning document rather than redefining the concept locally.
- When a new concept is required, the authoring document MUST either adopt an existing term from `../layer-1-terminology/core-terminology.md` or introduce the term through a glossary amendment targeting `../layer-1-terminology/core-terminology.md`.

**Verification**

Static analysis: a linter that detects duplicate definitions of the same term across specification documents. Manual review: each document's reviewer checks that no locally introduced term already exists in an earlier layer.

**Interactions**

Governs PR-2 (vocabulary discipline), PR-3 (notation), PR-5 (verification). Constrains all Layer 1 through Layer 6 documents.

---

### PR-2 Single-Vocabulary Rule

**Statement**

Every term used in a DNC specification document MUST appear in `../layer-1-terminology/core-terminology.md` before its first use in any other document.

**Rationale**

A specification that introduces vocabulary ad hoc accumulates synonym families. "Planner", "policy", "execution controller", "graph synthesiser" quietly refer to the same object or subtly different ones depending on document mood. Vocabulary-first ordering prevents this.

**Requirements**

- `../layer-1-terminology/core-terminology.md` MUST be fully drafted and frozen before any Layer 3 or later document introduces terms not already defined.
- New terms introduced mid-specification MUST be processed through a Glossary Amendment targeting `../layer-1-terminology/core-terminology.md` before use in any other document.
- No document MAY redefine a term that already appears in `../layer-1-terminology/core-terminology.md`.

**Verification**

Review of amendment log. Linter check: any capitalized term in a non-terminology document must resolve to a `../layer-1-terminology/core-terminology.md` entry.

**Interactions**

Implements PR-1 (ownership). Supported by PR-3 (notation consistency). Constrains all specification documents.

---

### PR-3 Single-Notation Rule

**Statement**

Mathematical notation SHALL be introduced once, in `../layer-3-execution/formal-model.md`, and reused without variation in all other specification documents.

**Rationale**

Notational drift — using "G" for a graph in one section and "(V, E)" in another, or redefining a symbol across documents — makes formal reasoning fragile and cross-document references error-prone. One canonical introduction site prevents this.

**Requirements**

- `../layer-3-execution/formal-model.md` MUST contain a Notation Conventions section that defines every symbol used in any DNC specification document.
- No document MAY introduce notation not defined in `../layer-3-execution/formal-model.md` without first extending the Notation Conventions section via formal amendment.
- Symbol reuse across documents MUST match the definition in `../layer-3-execution/formal-model.md` exactly.

**Verification**

Manual cross-reference check. A linter can verify that every mathematical symbol in any document appears in `../layer-3-execution/formal-model.md` with the same type signature.

**Interactions**

Constrains `../layer-3-execution/execution-model.md` (no math), `../layer-3-execution/formal-model.md` (canonical notation site), all downstream documents.

---

### PR-4 Lower-Layers-Only Rule

**Statement**

Specification documents MAY reference any lower-numbered layer. Specification documents MUST NOT reference any higher-numbered layer. The full document dependency graph SHALL remain a DAG.

**Rationale**

Cross-layer references that go "upward" create implicit circular dependencies. The specification would describe concepts in terms of things that are not yet defined. Lower-layers-only enforces a consistent level of abstraction at each layer.

**Requirements**

- Layer 0 documents MAY NOT reference any other layer.
- Layer 1 documents MAY reference Layer 0 only.
- Layer 2 documents MAY reference Layers 0 and 1.
- Layer 3 documents MAY reference Layers 0, 1, and 2.
- Layer 4 documents MAY reference Layers 0 through 3.
- Layer 5 documents MAY reference Layers 0 through 4.
- Layer 6 documents MAY reference all lower layers.
- Any proposed change that creates a reference from a lower layer to a higher layer, or that creates a cycle in the document dependency graph, is a Layering Violation and is forbidden.

**Verification**

Directed acyclicity check on the document dependency graph. Every cross-document reference is verified to point to a lower-or-equal layer number.

**Interactions**

Defines the document layer structure (Section 3). Constrains all specification documents. Related to PR-1 (no circular ownership).

---

### PR-5 Verification-Mechanism Rule

**Statement**

Every normative statement in any DNC specification document SHALL specify its verification mechanism, whether by formal proof, runtime assertion, static analysis, model checking, deterministic replay, benchmark evaluation, or explicit human review.

**Rationale**

A specification that asserts requirements without identifying how those requirements are confirmed is incomplete. Verification-mechanism specification enables: (a) implementers to know what correctness means, (b) reviewers to evaluate whether the verification is adequate, and (c) future tooling to automate compliance checking.

**Requirements**

- Every Principle's Verification section (this document) MUST name at least one verification mechanism.
- Every Invariant's verification specification in `../layer-2-invariants/runtime-invariants.md` MUST name at least one mechanism from the set: formal proof, runtime assertion, static analysis, model checking, deterministic replay, benchmark evaluation, human review.
- Any normative statement introduced in a Layer 3 or later document MUST carry an explicit verification clause identifying the compliance mechanism.
- Normative statements lacking an identified verification mechanism are specification defects and MUST be resolved before the containing document advances to Frozen state.

**Verification**

Review of every document's verification clauses. Linter: every normative statement must cite a verification mechanism.

**Interactions**

Governs verification obligations across all layers. Supports PR-6 (defined behavior), PR-7 (normative wording).

---

### PR-6 No-Undefined-Behavior Rule

**Statement**

Every behavior described in any DNC specification document SHALL be either explicitly defined, explicitly permitted, or explicitly forbidden. No behavior SHALL be left undefined, unspecified, or described as "implementation-defined" without an explicit rationale.

**Rationale**

Undefined behavior in a specification is an ownership gap. It delegates decisions to implementers in ways that are not audited, comparable, or reproducible. A runtime for neural execution especially needs well-defined behavior boundaries because stochastic components already introduce non-determinism; specification-level undefined behavior compounds this unpredictably.

**Requirements**

- For any behavior described in a DNC specification document, the document MUST classify it as: Defined (normative description provided), Permitted (allowed but not mandated), Forbidden (explicitly prohibited), or Undefined (with a documented rationale for why it is intentionally left open).
- Ambiguity discovered during review MUST be resolved before the document freezes.
- Any behavior classified as Undefined MUST be revisited in a subsequent specification revision.

**Verification**

Review: each document's reviewer checks that no normative statement leaves a behavioral class unmarked. Linter: checks for the four-class classification on all behavioral descriptions.

**Interactions**

Supports PR-5 (verification mechanisms must have defined behavior to verify), PR-7 (normative wording must be precise). Constrains all specification documents.

---

### PR-7 Normative-Wording Rule

**Statement**

Normative statements in DNC specification documents SHALL use RFC 2119 keyword forms (MUST, SHALL, MUST NOT, SHOULD, MAY) to express requirement levels. Explanatory text MAY use lower-case forms without normative implication.

**Rationale**

RFC 2119 provides an unambiguous, machine-testable vocabulary for requirement levels. Consistent use eliminates the ambiguity of "should", "ought to", "is expected to", and similar informal强度 markers. Reviewers can check compliance mechanically; implementers can verify conformance with precision.

**Requirements**

- Every normative statement in any DNC specification document MUST use at least one RFC 2119 keyword (MUST, SHALL, MUST NOT, SHOULD, MAY) to express its requirement level.
- Explanatory text that does not carry a requirement MUST use lower-case forms without capitalization. Lower-case forms carry no normative implication.
- Any document violating this requirement is a Normative-Wording Violation and MUST be corrected before advancing to Frozen state.

**Verification**

Linter: every normative statement contains at least one RFC 2119 keyword in all-caps. Manual review spot-checks for semantic accuracy of the selected keyword.

**Interactions**

Normative reference: RFC 2119 and RFC 8174. Governs all specification documents. Related to PR-6 (undefined behavior prohibition).

---

### PR-8 Preservation-under-Extension Rule

**Statement**

Any change to a DNC specification document at Layer 2 or higher that modifies an existing Invariant or introduces a new Invariant MUST either preserve all previously established Invariants or explicitly revise the specification version, declare the breaking change, and provide a migration rationale.

**Rationale**

Invariants are the constitutional layer of the runtime. If extensions can silently weaken them, the runtime has no stable foundation. This principle ensures that evolution happens through explicit amendment rather than gradual erosion.

**Requirements**

- A proposed change to any Invariant in `../layer-2-invariants/runtime-invariants.md` MUST either:
  (a) preserve all existing INV-* statements unchanged, or
  (b) declare the change as a Breaking Revision, update the specification version, record a migration rationale, and require acceptance by explicit review ballot.
- No Breaking Revision is permitted without declaring itself as such.
- Layer 4, Layer 5, or Layer 6 changes that affect Layer 2 Invariants are subject to the same constraint.

**Verification**

Amendment log review. Any amendment that modifies an INV-* statement must include a Breaking Revision declaration or a compatibility confirmation.

**Interactions**

Governs `../layer-2-invariants/runtime-invariants.md` (Layer 2). Constrains all mechanism, observability, and evolution documents. Related to PR-10 (version consistency).

---

### PR-9 Evidence Principle

**Statement**

Any claim about runtime behavior in any DNC specification document MUST be backed by evidence that is provenance-able, reproducible, or formally derivable. Appeals to authority or intuition without supporting evidence are not sufficient to establish runtime behavior claims.

**Rationale**

Specifications that assert runtime properties without evidence are hypotheses, not specifications. This principle ensures that every behavioral claim — not just those in Invariants — is grounded in something verifiable. Provenance (via the provenance model), formal derivation (via the formal model), or reproducible evaluation (via the evaluation suite) are the three primary evidence classes.

**Requirements**

- Every claim about actual runtime behavior appearing in any DNC specification document MUST cite at least one of:
  (a) A provenance chain traceable through `../layer-5-observability/provenance-model.md`;
  (b) A formal proof derivable from `../layer-3-execution/formal-model.md`;
  (c) An evaluation result from `../layer-5-observability/evaluation-suite.md`.
- Claims without one of these three evidence classes are Informative Claims and MUST be explicitly labeled as such. Informative Claims MUST NOT appear as normative requirements.
- Future evidence classes (e.g., symbolic proofs, verifier certificates) are admissible by explicit amendment to this principle.

**Verification**

Review of each document's claims against the evidence classification. Linter: unclassified claims flagged as violations.

**Interactions**

Governs all specification documents. Supported by `../layer-5-observability/provenance-model.md` (Layer 5), `../layer-3-execution/formal-model.md` (Layer 3), `../layer-5-observability/evaluation-suite.md` (Layer 5). Related to PR-5 (verification mechanisms are one form of evidence).

---

### PR-10 Version Consistency Rule

**Statement**

Every execution of the DNC runtime SHALL be governed by exactly one immutable tuple of specification version, runtime version, registry version, and planner version. Mixed-version semantics within a single execution are forbidden. The runtime MUST refuse to initiate an execution when any component of this tuple cannot be resolved.

**Rationale**

Reproducible execution requires version-fixed dependencies. If a planner executes with one set of module definitions while the specification references another, the provenance chain is compromised. Version consistency closes this gap and makes deterministic replay feasible.

**Requirements**

- Every execution MUST be prefixed with the eight-field execution header: ExecutionID, Specification Version, Runtime Version, Planner Version, Registry Version, Configuration Hash, Random Seed, Timestamp.
- No execution MAY proceed if any field of this header cannot be resolved.
- The version tuple is immutable for the lifetime of the execution. Module updates MUST NOT be visible to any in-flight execution.
- The configuration hash MUST cover all runtime configuration parameters that affect execution behavior.

**Verification**

Runtime assertion: execution header fields MUST be non-null and resolvable before execution begins. Static analysis: module update operations MUST verify no in-flight executions are affected.

**Interactions**

Governs `../layer-2-invariants/runtime-invariants.md` (INV-10), `../layer-4-mechanisms/planner-pipeline.md` (planner version tracking), `../layer-4-mechanisms/module-lifecycle.md` (registry version), `../layer-5-observability/evaluation-suite.md` (baseline locking). Related to PR-8 (breaking revision handling), PR-6 (defined behavior).

---

## Section 5 — Glossary of Principles

This section maps each principle to the class of questions it answers, enabling reviewers and authors to locate the governing principle for any concern efficiently.

| Principle | Owner Question |
|---|---|
| PR-1 Single-Ownership Rule | Which document owns this concept? |
| PR-2 Single-Vocabulary Rule | Has this term been introduced in the glossary before use? |
| PR-3 Single-Notation Rule | Is this mathematical symbol defined once and reused consistently? |
| PR-4 Lower-Layers-Only Rule | Does this cross-reference go upward or create a cycle? |
| PR-5 Verification-Mechanism Rule | How is this claim verified or confirmed? |
| PR-6 No-Undefined-Behavior Rule | Is this behavior defined, permitted, forbidden, or unspecified? |
| PR-7 Normative-Wording Rule | Does this normative statement use the correct RFC 2119 keyword? |
| PR-8 Preservation-under-Extension Rule | Does this change preserve existing Invariants? |
| PR-9 Evidence Principle | What evidence backs this claim about runtime behavior? |
| PR-10 Version Consistency Rule | Is every execution governed by a single, immutable version tuple? |
| PR-16 Principle Conflict Resolution | When PR-12 (safety bounds) conflicts with other principles, which takes precedence? |

---

## Section 6 — Governance for Regulated Deployment

This section augments the 10 principles with additional governance requirements for deployment in regulated industries (healthcare, finance, government, EU AI Act high-risk systems). These are mandatory constraints when the DNC runtime is deployed in contexts requiring external accountability.

### PR-11 — External Authority Structure

**Statement:**

The DNC specification is governed by an **External Authority** — an independent body with legal standing, composed of:
- One representative from each deploying organization
- One independent technical auditor (rotating 2-year term)
- One representative from the data subjects affected by automated decisions

The External Authority has final decision-making authority over Breaking Revisions (PR-8) and may mandate specification changes required by regulatory obligation.

**Breaking Revision Approval:** A Breaking Revision requires:
1. 60% supermajority vote of the External Authority
2. Public 30-day review period
3. Documented response to all submitted objections

**Verification:** External Authority charter and voting records are maintained as public documents.

### PR-12 — Minimum Safety Bounds

**Statement:**

Certain parameters MUST NOT be set below specified minimums in any regulated deployment:

| Parameter | Minimum | Applies To |
|---|---|---|
| `DRIFT_BOUND` | 15% | All deployments |
| `DEGRADATION_TOLERANCE` | 5% | All deployments |
| `RESP_BUDGET` | 50ms | Interactive deployments (< 1s latency requirement) |
| `LOOP_BUDGET` | 25ms | All deployments |

Changes to any of these parameters require documented review and explicit approval from the External Authority.

**Verification:** Configuration validation at runtime initialization (INV-CTRL-13 in `../layer-3-execution/control-loop.md` already enforces this). The minimum values are checked and any configuration violating them transitions the runtime to ERROR(INVALID_CONFIG).

### PR-13 — Namespace Extension Mechanism

**Statement:**

If the identifier namespace for any concept class is within 10 allocations of exhaustion (i.e., the next available identifier is within 10 of the reserved range maximum), the External Authority MUST initiate a namespace extension process:

1. Publish a namespace extension proposal for 30-day public comment
2. Allocate a new extended range (e.g., PR-100 to PR-999)
3. Archive the near-exhausted namespace range with a DEPRECATED marker
4. All existing identifiers remain valid indefinitely

**Verification:** Registry maintenance check. The registry MUST emit a NAMESPACE_WARNING event when any namespace reaches 80% capacity.

### PR-14 — Algorithmic Transparency

**Statement:**

For every execution that produces an outcome affecting a data subject (automated decision, recommendation, classification), the runtime MUST produce a **decision record** containing:
1. The execution graph G that was used
2. The KB version at execution initiation
3. The assessment outcome A(i) for each control loop iteration
4. The causal chain from observation to decision
5. Any replan events and their rationale

The decision record MUST be retained for a minimum of **3 years** and MUST be provided to the affected data subject upon request.

**Verification:** Provenance log retention assertion. The log retention policy (INV-PROV-5) is extended to require 3-year minimum retention for decision-relevant execution records.

### PR-15 — Bias and Fairness Evaluation

**Statement:**

Before deployment and after any KB update affecting module selection or output quality, the runtime MUST undergo **bias evaluation** against the following fairness metrics:

| Fairness Metric | Threshold |
|---|---|
| Demographic parity difference | ≤ 0.05 |
| Equalized odds difference | ≤ 0.05 |
| Disparate impact ratio | ≥ 0.8 and ≤ 1.25 |
| Individual fairness consistency score | ≥ 0.85 |

If any threshold is violated, the deployment or KB update is blocked until the bias is mitigated.

**Verification:** Bias evaluation is part of the FULL evaluation stage (DEF-EVAL-9 in `../layer-5-observability/evaluation-suite.md`). Class 5 (Fairness) metrics are evaluated alongside Class 1-4.

### PR-16 — Principle Conflict Resolution

**Statement:**

When two principles in this specification produce contradictory constraints at runtime, the following resolution hierarchy applies:

1. **Safety dominates**: If PR-12 (Minimum Safety Bounds) conflicts with any other principle's runtime constraints (including PR-10's version immutability), the higher safety bound takes precedence. The version tuple is amended with a configuration override notation (`CONFIG_OVERRIDE`) rather than a breaking revision.

2. **Immutability within bounds**: PR-10 (Version Consistency) remains in force for all parameters not overridden by PR-12's minimum safety bounds. The CONFIG_OVERRIDE is a lightweight annotation on the version tuple, not a modification of the core specification.

3. **Explicit declaration**: Any runtime configuration that applies a PR-12 override MUST be declared in the execution header as `CONFIG_OVERRIDE: [parameter_name, overriding_value, justification]`. The override is recorded in the provenance log.

4. **Temporal scope**: A PR-12 override applies only to the execution(s) active at the time of the override declaration. It does not modify the persistent specification or the module registry.

**Examples of PR-10 vs PR-12 conflicts and their resolution:**

| Conflict | Resolution |
|---|---|
| PR-12 mandates DRIFT_BOUND ≥ 15% but current execution uses 10% | CONFIG_OVERRIDE raises DRIFT_BOUND to 15% for this execution |
| PR-12 mandates RESP_BUDGET ≥ 50ms but current LOOP_BUDGET would exceed this with DECIDE_BUDGET=10ms | CTRL-AMEND-001 resolved this by adding INV-CTRL-9b (async exclusion), avoiding a budget conflict |
| External Authority mandates higher DEGRADATION_TOLERANCE mid-execution | CONFIG_OVERRIDE records new value; existing in-flight executions use their pre-existing values (PR-10); new executions use the override |

**Verification:** Configuration override log. Every CONFIG_OVERRIDE entry is audited at execution termination. The External Authority reviews all overrides at its quarterly review.

**Rationale:** The PR-10/PR-12 interaction was not theoretical — CTRL-AMEND-001 (renaming latency budgets and adding async exclusion) was exactly the kind of amendment required to resolve a live conflict. A formal conflict resolution mechanism prevents ad-hoc workarounds.

---

## Section 6B — Architecture v1.0 Governance

This section defines the governance policy for Architecture v1.0, which is the frozen baseline specification for Phase 5 (DNC runtime with LLM integration, execution provider abstraction, decision policies, and computation-aware evaluation).

### Architecture Version Policy

| Change Type | Version Action | Example |
|---|---|---|
| Editorial clarification | No version increment | Fixing ambiguous wording, adding examples |
| Backward-compatible addition | Architecture v1.x | Adding new OPTIONAL fields to trace schema, new capability flags, new Level 0/1 metrics |
| Breaking architectural change | Architecture v2.0 | Modifying execution semantics, changing invariant meanings, removing REQUIRED fields |

### Architecture v1.0

| Property | Value |
|---|---|
| Version | Architecture v1.0 |
| Status | Draft (target: Frozen) |
| Scope | Phase 5 specification: execution-semantics, architecture, interfaces, execution-trace-format, replay-semantics, conformance-model, evaluation-framework, decision-policy |
| Breaking Changes | Require Architecture v2.0 |
| Extension Namespace | EXT-* (vendor/experimental) |
| Extension Rules | Per conformance-model.md Section 3 |

### Permanent Rule: Normative Requirements

> **Normative requirements SHALL NOT appear in implementation documentation. All normative requirements originate in the specification and implementations may only reference them by identifier.**

This rule prevents specification drift between documentation and code. Normative requirements (statements using RFC 2119 keywords: MUST, SHALL, MUST NOT, SHOULD, MAY) are defined exclusively in specification documents. Implementation code and documentation may reference requirements by identifier (e.g., "per INV-EXEC-1") but may not redefine, narrow, or extend them.

This rule is enforced by:
- Static analysis: no RFC 2119 keywords in implementation documentation
- Conformance testing: requirements are verified against the specification, not implementation docs
- Architecture review: any doc claiming to describe DNC behavior is checked against the specification

### Architecture v1.0 Change Control

A breaking architectural change to Architecture v1.0 requires:

1. Formal proposal identifying the breaking change with impact analysis
2. Migration path for existing v1.0 implementations
3. External Authority vote (for regulated deployments)
4. 60-day public review period
5. Explicit Architecture v2.0 declaration

Non-breaking additions to Architecture v1.0 proceed via the amendment process (amendment log entry, no version increment).

---

## Section 7 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| FOUND-AMEND-001 | specification-foundation.md | 2026-07-09 | Draft DR-2: Added PR-11 (External Authority Structure), PR-12 (Minimum Safety Bounds with concrete parameter values), PR-13 (Namespace Extension Mechanism), PR-14 (Algorithmic Transparency / decision records), PR-15 (Bias and Fairness Evaluation with quantitative thresholds). Addresses GRC review gaps G-1, G-3, AC-1, AC-2, R-5, R-11. | No |
| FOUND-AMEND-002 | specification-foundation.md | 2026-07-10 | Added PR-16 (Principle Conflict Resolution). | No |
| FOUND-AMEND-003 | specification-foundation.md | 2026-07-11 | Architecture v1.0 Draft: Added Architecture v1.0 governance (version policy, breaking vs. backward-compatible changes, permanent normative requirements rule), updated identifier namespace table (INV-RT-*, INV-EV-*, INV-REP-*, INV-CP-*, INV-POL-*, MET-*, TRC-*, EXT-*), updated document dependency graph (Phase 5 documents). | No |