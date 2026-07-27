"""Provenance model: append-only event graph with causal chains and hash chain integrity.

Per provenance-model.md DEF-PROV-1 through DEF-PROV-5, INV-PROV-1 through INV-PROV-5:
- Append-only event log with cryptographic integrity hashes
- Causal chains via causal_ref linking
- Hash chain for tamper detection
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Set

from dnc.runtime.types import ModuleInstanceID


class ProvenanceTamperingViolation(Exception):
    """Raised when integrity hash mismatch detected per INV-PROV-4."""


class CausalChainBroken(Exception):
    """Raised when causal_ref does not resolve per INV-PROV-2."""


class EventType:
    STEP_DISPATCHED = "STEP_DISPATCHED"
    STEP_COMPLETED = "STEP_COMPLETED"
    STEP_FAILED = "STEP_FAILED"
    CHECKPOINT_CREATED = "CHECKPOINT_CREATED"
    REPLAN_TRIGGERED = "REPLAN_TRIGGERED"
    GRAPH_DIFF_COMPUTED = "GRAPH_DIFF_COMPUTED"
    DECISION = "DECISION"
    MODULE_REGISTERED = "MODULE_REGISTERED"
    MODULE_DEREGISTERED = "MODULE_DEREGISTERED"
    MODULE_RETIRED = "MODULE_RETIRED"
    LEARNING_EVENT = "LEARNING_EVENT"
    KB_UPDATE_COMMITTED = "KB_UPDATE_COMMITTED"
    KB_ROLLBACK = "KB_ROLLBACK"
    EXECUTION_TERMINATED = "EXECUTION_TERMINATED"
    REGRESSION_DETECTED = "REGRESSION_DETECTED"
    STRUCTURAL_TRANSACTION_BEGIN = "STRUCTURAL_TRANSACTION_BEGIN"
    STRUCTURAL_TRANSACTION_ROLLED_BACK = "STRUCTURAL_TRANSACTION_ROLLED_BACK"
    STRUCTURAL_MUTATION_APPLIED = "STRUCTURAL_MUTATION_APPLIED"
    STRUCTURAL_TRANSACTION_COMMITTED = "STRUCTURAL_TRANSACTION_COMMITTED"
    STRUCTURAL_GRAPH_VERSION_CREATED = "STRUCTURAL_GRAPH_VERSION_CREATED"


@dataclass(frozen=True)
class ProvenanceEvent:
    """Per DEF-PROV-1: e = (event_id, event_type, timestamp, execution_id, step_index, causal_ref, payload, integrity_hash)."""
    event_id: str
    event_type: str
    timestamp: float
    execution_id: str
    step_index: Optional[int]
    causal_ref: Optional[str]
    payload: Dict[str, Any]
    integrity_hash: str


class ProvenanceLog:
    """Append-only event log per INV-PROV-1.

    Per DEF-PROV-2: G_prov = (V_prov, E_prov) where E_prov = {(e_causal, e_effect) | e_effect.causal_ref = e_causal.event_id}.
    Per INV-PROV-4: hash chain integrity — each event's integrity_hash incorporates the previous event's hash.
    """

    def __init__(self, execution_id: str) -> None:
        self._execution_id = execution_id
        self._events: List[ProvenanceEvent] = []
        self._prev_hash: str = "0" * 64
        self._event_index: Dict[str, ProvenanceEvent] = {}
        self._causal_index: Dict[str, List[ProvenanceEvent]] = {}

    def append(
        self,
        event_type: str,
        step_index: Optional[int],
        causal_ref: Optional[str],
        payload: Dict[str, Any],
    ) -> ProvenanceEvent:
        """Append a new event. Per INV-PROV-1: append-only, no delete/modify/reorder."""
        event_id = str(uuid.uuid4())

        prev_hash_for_chain = self._prev_hash
        event_data = {
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": time.time(),
            "execution_id": self._execution_id,
            "step_index": step_index,
            "causal_ref": causal_ref,
            "payload": payload,
            "prev_integrity_hash": prev_hash_for_chain,
        }
        integrity_hash = self._compute_hash(event_data)

        event = ProvenanceEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=event_data["timestamp"],
            execution_id=self._execution_id,
            step_index=step_index,
            causal_ref=causal_ref,
            payload=payload,
            integrity_hash=integrity_hash,
        )

        self._events.append(event)
        self._event_index[event_id] = event

        if causal_ref:
            if causal_ref not in self._causal_index:
                self._causal_index[causal_ref] = []
            self._causal_index[causal_ref].append(event)

        self._prev_hash = integrity_hash
        return event

    def _compute_hash(self, event_data: dict) -> str:
        """Compute SHA-256 integrity hash including previous event's hash (hash chain per INV-PROV-4)."""
        data_str = "|".join(
            f"{k}={event_data.get(k)}"
            for k in sorted(event_data.keys())
        )
        return hashlib.sha256(data_str.encode()).hexdigest()

    def verify_chain(self) -> bool:
        """Per INV-PROV-4: verify entire hash chain. Raises ProvenanceTamperingViolation on mismatch."""
        if not self._events:
            return True

        prev_expected = "0" * 64
        for event in self._events:
            event_data = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "execution_id": event.execution_id,
                "step_index": event.step_index,
                "causal_ref": event.causal_ref,
                "payload": event.payload,
                "prev_integrity_hash": prev_expected,
            }
            expected_hash = self._compute_hash(event_data)
            if expected_hash != event.integrity_hash:
                raise ProvenanceTamperingViolation(
                    f"Integrity hash mismatch at event {event.event_id}. "
                    f"Expected {expected_hash}, got {event.integrity_hash}. "
                    f"Chain broken at step_index={event.step_index}."
                )
            prev_expected = event.integrity_hash
        return True

    def query_causal_chain(self, event_id: str) -> List[ProvenanceEvent]:
        """Per DEF-PROV-3: return [e_0, ..., e_n] where e_n = event, e_i.causal_ref = e_{i-1}.event_id."""
        chain: List[ProvenanceEvent] = []
        current_id: Optional[str] = event_id

        while current_id is not None:
            event = self._event_index.get(current_id)
            if event is None:
                raise CausalChainBroken(
                    f"Causal chain broken: event {current_id} not found in provenance log"
                )
            chain.append(event)
            current_id = event.causal_ref

        return list(reversed(chain))

    def query_effects(self, event_id: str) -> List[ProvenanceEvent]:
        """Per DEF-PROV-4: return all events reachable from e in G_prov."""
        visited: Set[str] = set()
        queue = [event_id]
        effects: List[ProvenanceEvent] = []

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for effect in self._causal_index.get(current, []):
                effects.append(effect)
                queue.append(effect.event_id)

        return effects

    def __len__(self) -> int:
        return len(self._events)

    def __getitem__(self, event_id: str) -> ProvenanceEvent:
        return self._event_index[event_id]

    def __iter__(self) -> Iterator[ProvenanceEvent]:
        return iter(self._events)

    def latest(self) -> Optional[ProvenanceEvent]:
        if not self._events:
            return None
        return self._events[-1]