# Transaction Semantics

## Metadata

| Field | Value |
|---|---|
| Document | transaction-semantics.md |
| Title | Transaction Semantics for DNC Structural Mutations |
| Document ID | SPEC-TRANSACTION |
| State | Active / Draft |
| Version | Baseline v1.1 |
| Owner | DNC Specification |
| Layer | 3 / 4 (Computation & Execution) |
| Owner Question | How do authorized structural mutations and state transitions become atomic, how does rollback work, how do checkpoints coordinate with graph mutations, and how are concurrent mutations resolved? |
| Depends on | Foundational Baseline (Axioms 3, 4, 5), DNC-IR Specification (`specs/dnc-ir.md`), Mutation Semantics (`specs/mutation-semantics.md`) |
| Depended on by | Dynamic Computation Control Layer, Implementation Core |

---

## 1. Purpose and Scope

### 1.1 Relationship to Mutation Semantics

Mutation Semantics (`specs/mutation-semantics.md`) defines **what** changes: the mutation taxonomy, algebraic properties, validation sequence, and structural boundaries ($M: G_t \to G_{t+1}$ and $T_M: \Sigma(t) \to \Sigma(t+1)$). 

Transaction Semantics defines **how** those changes become atomic, durable, and recoverable:
- How mutations execute within transaction boundaries.
- How partial failures trigger safe rollbacks.
- How checkpoints coordinate with graph mutations.
- How composite mutations decompose into transactional primitive sequences.
- How concurrent mutation proposals are ordered and resolved.

### 1.2 Scope

This specification applies to all **structural mutations** (and composite mutations derived from them) that pass through the 6-role authority pipeline (Generator → Controller → Engine → Execution → Assessment → Learning) and modify the unified system state $\Sigma(t)$. Non-structural parameter updates or routing adjustments managed entirely within unit execution bounds may use lightweight local transactions but must adhere to system consistency guarantees.

---

## 2. DNC Atomicity Model (ACID for Computation)

DNC system transitions $\Sigma(t) \to \Sigma(t+1)$ under mutation $M$ must satisfy modified ACID properties tailored for dynamic computation graphs:

### 2.1 Atomicity
Either all primitive operations comprising transaction $M$ apply successfully to unified state $\Sigma(t)$, producing unified state $\Sigma(t+1)$, or $\Sigma(t)$ remains entirely unchanged. No intermediate, partial, or half-applied structural modifications are ever visible to the Execution Core or inspection tools.

### 2.2 Consistency
Every state resulting from a committed transaction—as well as all intermediate states within the transaction sandbox—MUST satisfy all DNC-IR structural invariants, unit mutation contracts, edge constraints, and type requirements (per DNC-IR §11–13 and Mutation Semantics §5). A transaction that violates consistency at any point during validation or application MUST abort and roll back.

### 2.3 Isolation
Concurrent mutation proposals or execution steps are serialized or isolated such that Execution Cores never observe a graph in the middle of being mutated. The Mutation Engine acts as a single-writer serializable coordinator for all structural graph modifications.

### 2.4 Durability
Once a transaction commits, the resulting state $\Sigma(t+1)$, graph version $V_{t+1}$, and transaction provenance record are permanently recorded in the checkpointer and provenance logs, ensuring crash recovery, historical auditing, and execution replayability.

---

## 3. Transaction Lifecycle

Every structural mutation transaction progresses through four strict, ordered lifecycle phases:

```
[BEGIN] → [VALIDATE] → [APPLY] → [COMMIT / ROLLBACK]
```

### 3.1 Phase 1: BEGIN
- **Trigger**: An authorized mutation proposal $M$ (approved by the Controller) is submitted to the Mutation Engine.
- **Actions**:
  1. Allocate a transaction context $TxID$.
  2. Snapshot the current graph version $V_t$ and system state $\Sigma(t)$.
  3. Create an isolated staging sandbox for the Structural Graph ($G_{staging}$) and working memory staging buffers.
  4. Initialize an empty transaction undo log for rollback compensation.

### 3.2 Phase 2: VALIDATE
- **Trigger**: Transaction context initialized with $G_{staging}$.
- **Actions**: Execute the 7-step mechanical validation sequence (Mutation Semantics §5.1) against $G_{staging}$:
  1. Operation Validity (syntax and parameter correctness).
  2. Identity Validation (existence and validity of target units/edges).
  3. Contract Validation (MutationContract capability compliance).
  4. Invariant Validation (absolute DNC-IR structural invariants).
  5. Constraint Validation (negotiable edge/graph constraints).
  6. Resource Validation (cost budget and computational limits).
  7. Authorization Verification (Controller signature and policy compliance).
- **Outcome**: If any validation step fails, transition immediately to `ROLLBACK`. If all pass, proceed to `APPLY`.

### 3.3 Phase 3: APPLY
- **Trigger**: Successful validation in sandbox.
- **Actions**:
  1. Execute the primitive operation sequence (or decomposed composite operations) on $G_{staging}$.
  2. For each primitive operation applied, record its exact inverse operation in the undo log.
  3. Update working memory associations, scope mappings, and metadata references in the staging state.
  4. Run post-application structural consistency checks.

### 3.4 Phase 4: COMMIT or ROLLBACK
- **Commit Path**:
  1. If application succeeds without error and consistency holds:
  2. Atomically swap the active system graph $G_t$ with $G_{staging}$ and increment state version $V_t \to V_{t+1}$.
  3. Emit a post-mutation checkpoint ($Ck_{t+1}$).
  4. Record successful provenance transaction entry in history log $H(t)$.
  5. Close transaction $TxID$ with status `COMMITTED`.
- **Rollback Path**:
  1. If application throws an exception, invariant check fails, or explicit abort is signaled:
  2. Execute undo log operations in reverse order against $G_{staging}$ (or discard sandbox).
  3. Restore active system graph $G_t$ and state to pre-mutation snapshot.
  4. Record failure provenance entry in history log $H(t)$.
  5. Close transaction $TxID$ with status `ROLLED_BACK`.

---

## 4. Checkpoint Integration

Transactions coordinate tightly with the DNC Checkpointer (`specs/layer-3-execution/state-management.md` and DNC-IR Versioning §7):

1. **Pre-Mutation Checkpoint ($Ck_t$)**: Taken automatically upon entering `BEGIN`. Guarantees that a stable recovery snapshot exists before any mutation attempt.
2. **Post-Mutation Checkpoint ($Ck_{t+1}$)**: Taken upon successful `COMMIT`. Captures the new structural graph version $V_{t+1}$, updated working memory $W(t+1)$, and provenance reference.
3. **Rollback Restoration**: If a transaction rolls back, the system state is restored to $Ck_t$, ensuring zero state drift or partial corruption.

---

## 5. Composite Mutation Decomposition & Transactional Nesting

Composite mutations (`REPLACE`, `COMPOSE`, `DECOMPOSE`, `EXTRACT`, `INLINE`, `SPECIALIZE`) are non-atomic at the conceptual level but **must be atomic at the transaction level**.

### 5.1 Decomposition Rule
The Mutation Engine decomposes every composite mutation into an ordered sequence of primitive operations (`ADD`, `REMOVE`, `CONNECT`, `DISCONNECT`, `REWIRE`) during transaction initialization (`BEGIN`).

### 5.2 Transactional Nesting Semantics
- The entire decomposed primitive sequence executes within a single transaction boundary ($TxID$).
- If primitive operation $k$ in a sequence of $N$ operations fails, operations $1 \dots k-1$ must be undone via the undo log.
- Unit identities (`UnitID`) created or retired during composite mutation follow DNC-IR identity permanence rules (retired IDs are never reused).

---

## 6. Rollback Mechanics & Compensation

### 6.1 Inverse Generation Table

Every primitive structural operation has a deterministic inverse recorded during `APPLY`:

| Primitive Operation | Inverse Operation | Rollback Action |
|-------------------|-------------------|-----------------|
| `ADD(unit)` | `REMOVE(unit_id)` | Remove the added unit from graph and working memory |
| `REMOVE(unit_id)` | `ADD(unit_restored)` | Restore the removed unit, its contract, and metadata |
| `CONNECT(u₁, u₂, edge)` | `DISCONNECT(u₁, u₂)` | Remove the edge between u₁ and u₂ |
| `DISCONNECT(u₁, u₂)` | `CONNECT(u₁, u₂, edge)` | Re-establish the edge with original properties |
| `REWIRE(e_old, e_new)` | `REWIRE(e_new, e_old)` | Revert edge connection endpoints |
| `SPECIALIZE(unit_id)` | `DESPECIALIZE(unit_id)` | Revert specialized lifecycle state |

### 6.2 Restoration Guarantee
Executing the inverse sequence in reverse order restores the Structural Graph $G_t$, edge weights, contracts, and working memory bindings to bit-identical or semantically equivalent pre-transaction state.

---

## 7. Concurrent Mutation Resolution & Scheduling

### 7.1 Single-Writer Mutation Engine
To eliminate race conditions and complex distributed locking across execution cores, **all structural mutations are processed sequentially by a single-writer Mutation Engine**. 

### 7.2 Optimistic Concurrency Control (OCC) for Proposals
When multiple Generator/Controller components propose mutations asynchronously:
1. Proposals are tagged with the base graph version $V_{proposed}$ upon creation.
2. When a proposal reaches the Mutation Engine's validation queue, its $V_{proposed}$ is compared against the current active graph version $V_{current}$.
3. If $V_{proposed} == V_{current}$, the transaction proceeds normally.
4. If $V_{proposed} < V_{current}$, a **structural conflict** is detected (e.g., a target unit was deleted or modified by an intervening transaction).
5. **Conflict Resolution**:
   - The Mutation Engine submits the proposal back to the Controller/Generator for re-validation against $V_{current}$, OR
   - Automatically aborts the stale proposal, logging a concurrency conflict provenance event.

---

## 8. Failure Recovery & Error Propagation

### 8.1 Failure Classification
Transactions can fail due to:
- **Validation Errors**: Syntax, identity mismatch, or contract violation.
- **Invariant Violations**: Structural graph integrity broken (e.g., circular dependency in executable DAG projection).
- **Resource Exhaustion**: Cost budget exceeded during mutation evaluation.
- **Execution Exceptions**: Runtime failures during mutation application.

### 8.2 Recovery Protocol
1. Abort transaction immediately.
2. Invoke rollback compensation via undo log.
3. Restore system state to pre-mutation checkpoint $Ck_t$.
4. Log failure taxonomy record (`specs/layer-5-observability/failure-taxonomy.md`) with provenance reference.
5. Notify Controller and Learning domains of mutation failure without halting the core Execution Engine.

---

## 9. Conformance Requirements

### 9.1 Conformance Levels
An implementation of DNC Transaction Semantics conforms at one of four nested levels:
- **Level 1 (Basic Atomicity)**: Supports `BEGIN`, `VALIDATE`, `APPLY`, `COMMIT`/`ROLLBACK` for primitive mutations.
- **Level 2 (Checkpoint & Composite)**: Supports automatic checkpointing (`Ck_t`, `Ck_{t+1}`) and composite mutation decomposition.
- **Level 3 (Concurrency Control)**: Supports Optimistic Concurrency Control (OCC) version checking and conflict resolution.
- **Level 4 (Full Transactional Integrity)**: Supports complete failure recovery, provenance logging, undo log compensation, and multi-domain state synchronization ($\Sigma(t)$).

### 9.2 Traceability Matrix

| Transaction Semantics Concept | Q3 (State) | Q4 (Authority) | Axiom 3 | Axiom 4 | DNC-IR | Mutation Semantics | Status |
|-------------------------------|------------|----------------|---------|---------|--------|--------------------|--------|
| ACID Atomicity                | ✓          |                |         | ✓       | §3     | §1                 | PASS   |
| Four-Phase Lifecycle          |            | ✓              |         | ✓       | §12    | §3                 | PASS   |
| Checkpoint Integration        | ✓          |                | ✓       |         | §7     | §4                 | PASS   |
| Composite Decomposition       |            |                |         |         | §12    | §2                 | PASS   |
| Rollback & Inverse Logging    |            |                |         | ✓       | §6     | §6                 | PASS   |
| OCC Concurrency Control       |            | ✓              |         |         | §7     | §3                 | PASS   |
| Failure Recovery              | ✓          | ✓              | ✓       | ✓       | §11    | §7                 | PASS   |

---

## 10. Summary

Transaction Semantics bridges the gap between abstract mutation rules and concrete runtime execution. By enforcing ACID atomicity, four-phase transaction lifecycles, tight checkpoint coordination, deterministic inverse rollback, and OCC concurrency control, DNC v2.x guarantees that structural self-modification occurs with absolute safety, verifiability, and system stability.
