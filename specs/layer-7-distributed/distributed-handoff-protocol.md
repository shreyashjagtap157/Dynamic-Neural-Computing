# Distributed Handoff Protocol

## Metadata

| Field | Value |
|---|---|
| Document | distributed-handoff-protocol.md |
| Title | Distributed Handoff Protocol |
| Document ID | SPEC-DIST |
| State | Frozen |
| Version | Baseline v1.0 |
| Owner | DNC Specification |
| Layer | 7 |
| Owner Question | How are inter-process and inter-node handoffs handled, and how does two-phase commit extend across distributed boundaries? |
| Last Updated | 2026-07-12 |

---

## Section 1 — Overview

Layer 7 (Distributed) extends the single-address-space handoff protocol (INV-STATE-6) to inter-process and inter-node boundaries using a message-passing protocol with at-least-once delivery and idempotent receiver buffers.

The key architectural insight is that distributed handoffs replace the single-address-space two-phase commit with a message-passing protocol that achieves equivalent atomicity guarantees through acknowledgment and retry semantics.

**Architecture decision:** This document specifies the at-least-once with idempotent receiver pattern (option (b) from the original stub). Full distributed 2PC with participant voting is out of scope for Baseline v1.0 but MAY be added in Architecture v1.1.

---

## Section 2 — Interface Contract (INV-DIST-1)

### INV-DIST-1 — Intra vs Inter-Process Handoff Boundary

**Statement:**

For intra-process handoffs (both sender and receiver in the same address space), the protocol MUST use two-phase commit per INV-STATE-6. For inter-process or inter-node handoffs, the protocol MUST use the distributed handoff interface defined in this document. The implementation MUST NOT mix the two protocols for the same handoff edge.

**Verification:** The scheduler determines the handoff boundary at graph construction time. The module contract's `distribution_model` field (per module-lifecycle.md) specifies whether a module supports single-node or distributed deployment.

---

## Section 3 — Core Definitions

### DEF-DIST-1 — Distributed Handoff

**Definition:** A distributed handoff is a state transfer across process or node boundaries using a message-passing protocol with at-least-once delivery and idempotent receiver buffers.

### DEF-DIST-2 — At-Least-Once Delivery with Idempotent Receivers

**Definition:** Messages are retried until acknowledged. The receiver discards duplicate messages using a message-id deduplication window. This provides exactly-once semantics at the application layer.

### DEF-DIST-3 — Handoff Timeout

**Definition:** The `handoff_timeout` is the maximum time a sender waits for an ACK before retrying. Default value: 30 seconds. Implementations MAY override via configuration.

### INV-DIST-2 — Handoff Atomicity Over Network

**Statement:** A distributed handoff MUST be atomic: either the sender's state is transferred and acknowledged, or no state transfer is recorded. The receiver MUST NOT apply state from a handoff that was not acknowledged by the sender.

**Note:** Full distributed two-phase commit (with coordinator, participant voting, and commit/abort) is the conservative approach. The interface contract allows either: (a) a full 2PC distributed coordinator, or (b) a more efficient at-least-once with idempotent receiver pattern that achieves the same outcome semantics.

---

## Section 4 — Network Partition Handling (INV-DIST-3)

### INV-DIST-3 — Partition Detection and Response

**Statement:** When a message times out (no ACK received within `handoff_timeout`), the sender MUST treat this as a potential network partition and enter the retry state. After `max_retries` consecutive failures, the sender MUST mark the handoff as FAILED and notify the control loop.

**Response levels:**

| Consecutive Failures | Action |
|---|---|
| 0-2 | Retry with exponential backoff (1s, 2s, 4s) |
| 3-5 | Retry with jitter, alert control loop |
| 6+ | Mark FAILED, halt handoff chain, notify control loop |

**Verification:** `DistributedCoordinator.retry_count` tracks consecutive failures. The control loop's Observe phase MUST check for FAILED handoff signals.

### DEF-DIST-4 — Partition State

**Definition:** A node is in partition state when it cannot reach its peer for `> handoff_timeout * max_retries` despite retries.

---

## Section 5 — Coordinator Election (INV-DIST-4)

### INV-DIST-4 — Coordinator Failover

**Statement:** When the initiating node fails before sending a COMMIT, any in-flight handoff is considered FAILED after `handoff_timeout * max_retries`. The receiver node MUST NOT apply any uncommitted state. No automatic coordinator failover is performed in Baseline v1.0 — the control loop is responsible for detecting failures and initiating recovery.

**Note:** Coordinator election (e.g., Raft-based leader election) is deferred to Architecture v1.1. Baseline v1.0 handles coordinator failure by failing fast and notifying the control loop.

**Verification:** `DistributedHandoffRecord.error` contains partition/failure reason. `HandoffStatus.FAILED` is the terminal state for unrecoverable handoffs.

---

## Section 6 — Multi-Hop Handoffs (INV-DIST-5)

### INV-DIST-5 — Multi-Hop Routing

**Statement:** Inter-node handoffs in Baseline v1.0 are direct sender→receiver only. Multi-hop routing (where state passes through intermediate nodes) is NOT supported. All handoffs MUST be point-to-point between the initiating node and the destination node.

**Rationale:** Multi-hop introduces causal ordering complexity (INV-PROV-4 chain breaks) that requires additional specification. It is deferred to Architecture v1.1.

**Verification:** `handoff_needs_distribution()` returns True for distributed contracts. The `DistributedCoordinator` verifies `receiver_node_id` is the final destination.

---

## Section 7 — Timeout Specification (DEF-DIST-3, INV-DIST-6)

### INV-DIST-6 — Timeout Values

**Statement:** The following timeout values are defined:

| Parameter | Default | Description |
|---|---|---|
| `handoff_timeout` | 30s | Time to wait for ACK before retry |
| `max_retries` | 6 | Maximum retry attempts before declaring FAILED |
| `heartbeat_interval` | 10s | Interval for heartbeat messages (if enabled) |

These values MAY be overridden per-handoff via `DistributedHandoffConfig`.

---

## Section 8 — Open Issues (Resolved in Baseline v1.0)

All previously open issues have been resolved:

1. ~~Network partition handling during handoff~~ — RESOLVED per INV-DIST-3
2. ~~Timeout values for inter-node round-trips~~ — RESOLVED per INV-DIST-6 and DEF-DIST-3
3. ~~Coordinator election if the 2PC coordinator fails mid-protocol~~ — RESOLVED per INV-DIST-4 (fail-fast, control loop recovery)
4. ~~Whether inter-node handoffs can span multiple hops or only direct sender→receiver~~ — RESOLVED per INV-DIST-5 (direct only, multi-hop deferred to v1.1)

---

## Section 9 — Glossary

| Term | Definition | Document |
|---|---|---|
| Distributed Handoff | State transfer across process/node boundaries | distributed-handoff-protocol.md |
| At-Least-Once Delivery | Message delivery with acknowledgment and retry | distributed-handoff-protocol.md |
| Idempotent Receiver | Receiver discards duplicate message IDs | distributed-handoff-protocol.md |
| Handoff Timeout | Maximum wait time for ACK before retry | distributed-handoff-protocol.md |
| Network Partition | Node unreachable for > timeout * max_retries | distributed-handoff-protocol.md |
| INV-DIST-1 | Handoff boundary classification | distributed-handoff-protocol.md |
| INV-DIST-2 | Atomicity over network | distributed-handoff-protocol.md |
| INV-DIST-3 | Partition detection and response | distributed-handoff-protocol.md |
| INV-DIST-4 | Coordinator failover | distributed-handoff-protocol.md |
| INV-DIST-5 | Multi-hop routing | distributed-handoff-protocol.md |
| INV-DIST-6 | Timeout values | distributed-handoff-protocol.md |

---

## Section 10 — Amendment Log

| Amendment ID | Target | Date | Description | Breaking? |
|---|---|---|---|---|
| FRZ-001 | distributed-handoff-protocol.md | 2026-07-12 | Frozen to Baseline v1.0. Resolved all 4 open issues: partition handling (INV-DIST-3), timeout values (INV-DIST-6), coordinator failover (INV-DIST-4), single-hop only (INV-DIST-5). | No |
| DIST-AMEND-001 | distributed-handoff-protocol.md | 2026-07-12 | Baseline v1.0: Initial implementation of distributed handoff with at-least-once delivery, idempotent receivers, coordinator, partition handling, timeout spec, and single-hop constraint. | No |