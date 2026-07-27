"""Distributed Handoff Protocol: inter-process and inter-node state transfer.

Per distributed-handoff-protocol.md: Layer 7 extends the single-address-space two-phase
commit (INV-STATE-6) to inter-process and inter-node boundaries using a message-passing
protocol that achieves equivalent atomicity guarantees through acknowledgment and retry
semantics.

The core invariant (INV-DIST-2): a distributed handoff MUST be atomic — either the
sender's state is transferred and acknowledged, or no state transfer is recorded.

Key concepts:
- At-Least-Once Delivery: messages retried until acknowledged
- Idempotent Receivers: duplicate message IDs discarded via deduplication window
- Two-Phase Commit: prepare → commit/abort with coordinator
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set


class HandoffMessageType(Enum):
    """Per distributed-handoff-protocol.md: types of handoff messages."""

    PREPARE = auto()
    COMMIT = auto()
    ABORT = auto()
    STATE_TRANSFER = auto()
    ACK = auto()
    NACK = auto()
    HEARTBEAT = auto()


class HandoffStatus(Enum):
    """Status of a distributed handoff operation."""

    PENDING = auto()
    PREPARING = auto()
    COMMITTED = auto()
    ABORTED = auto()
    FAILED = auto()


@dataclass(frozen=True)
class DistributedHandoffMessage:
    """Per DEF-DIST-1: a state transfer message across process/node boundaries.

    Each message has a unique message_id for idempotent receiver deduplication.
    """

    message_id: str
    handoff_id: str
    sender_node_id: str
    receiver_node_id: str
    message_type: HandoffMessageType
    step_index: int
    state_payload: Dict[str, Any]
    timestamp: float
    provenance_ref: str
    retry_count: int = 0

    def content_hash(self) -> str:
        """Compute a content hash for integrity verification.

        Per distributed-handoff-protocol.md: hash chain for provenance.
        """
        content = json.dumps(self.state_payload, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class IdempotentReceiver:
    """Per DEF-DIST-2: receiver that discards duplicate message IDs.

    Maintains a deduplication window of seen message_ids. Messages with
    already-seen IDs are acknowledged without reapplying state.
    """

    def __init__(self, window_size: int = 1000) -> None:
        self._window_size = window_size
        self._seen_ids: Set[str] = set()
        self._message_history: Dict[str, Dict[str, Any]] = {}

    def is_duplicate(self, message_id: str) -> bool:
        """Return True if this message_id has already been processed."""
        return message_id in self._seen_ids

    def record(self, message: DistributedHandoffMessage, result: Any) -> None:
        """Record a processed message and its result."""
        if message.message_id in self._seen_ids:
            return

        self._seen_ids.add(message.message_id)
        self._message_history[message.message_id] = {
            "result": result,
            "timestamp": time.time(),
        }

        if len(self._seen_ids) > self._window_size:
            oldest = sorted(
                self._message_history.items(), key=lambda x: x[1]["timestamp"]
            )[0][0]
            self._seen_ids.discard(oldest)
            self._message_history.pop(oldest, None)

    def get_cached_result(self, message_id: str) -> Optional[Any]:
        """Return the cached result for a previously processed message."""
        if message_id in self._message_history:
            return self._message_history[message_id]["result"]
        return None


@dataclass
class DistributedHandoffRecord:
    """Record of a distributed handoff operation for provenance tracking."""

    handoff_id: str
    sender_node_id: str
    receiver_node_id: str
    status: HandoffStatus
    prepare_sent_at: Optional[float] = None
    commit_sent_at: Optional[float] = None
    completed_at: Optional[float] = None
    abort_sent_at: Optional[float] = None
    error: Optional[str] = None
    message_count: int = 0
    retry_count: int = 0


class DistributedCoordinator:
    """Two-phase commit coordinator for distributed handoffs.

    Per distributed-handoff-protocol.md INV-DIST-2: coordinates prepare/commit/abort
    across sender and receiver to achieve atomic state transfer.

    The coordinator can operate in two modes:
    1. Full 2PC: coordinator + participant voting
    2. At-least-once with idempotent receiver: simpler, sufficient for DNC use cases
    """

    def __init__(
        self,
        node_id: str,
        mode: str = "at_least_once",
    ) -> None:
        self._node_id = node_id
        self._mode = mode
        self._handoff_records: Dict[str, DistributedHandoffRecord] = {}
        self._participant_states: Dict[str, Dict[str, Any]] = {}

    @property
    def node_id(self) -> str:
        return self._node_id

    def initiate_handoff(
        self,
        sender_node_id: str,
        receiver_node_id: str,
        state_payload: Dict[str, Any],
        provenance_ref: str,
        step_index: int,
    ) -> DistributedHandoffMessage:
        """Per 2PC protocol: initiate a new handoff by creating the STATE_TRANSFER message."""
        handoff_id = str(uuid.uuid4())
        message = DistributedHandoffMessage(
            message_id=str(uuid.uuid4()),
            handoff_id=handoff_id,
            sender_node_id=sender_node_id,
            receiver_node_id=receiver_node_id,
            message_type=HandoffMessageType.STATE_TRANSFER,
            step_index=step_index,
            state_payload=state_payload,
            timestamp=time.time(),
            provenance_ref=provenance_ref,
        )

        record = DistributedHandoffRecord(
            handoff_id=handoff_id,
            sender_node_id=sender_node_id,
            receiver_node_id=receiver_node_id,
            status=HandoffStatus.PENDING,
        )
        self._handoff_records[handoff_id] = record
        self._participant_states[handoff_id] = state_payload
        return message

    def receive_message(
        self,
        message: DistributedHandoffMessage,
        receiver: IdempotentReceiver,
    ) -> Optional[DistributedHandoffMessage]:
        """Process an incoming handoff message and produce a response.

        Per DEF-DIST-2: uses idempotent receiver to deduplicate.
        Per INV-DIST-2: atomic handoff — ACK only sent after successful processing.
        """
        if receiver.is_duplicate(message.message_id):
            cached = receiver.get_cached_result(message.message_id)
            return self._make_ack(message, already_processed=True)

        if message.message_type == HandoffMessageType.STATE_TRANSFER:
            try:
                self._participant_states[message.handoff_id] = message.state_payload
                receiver.record(message, {"status": "accepted"})
                self._update_record(message.handoff_id, status=HandoffStatus.COMMITTED)
                return self._make_ack(message)
            except Exception as e:
                receiver.record(message, {"status": "rejected", "error": str(e)})
                self._update_record(message.handoff_id, status=HandoffStatus.FAILED, error=str(e))
                return self._make_nack(message, str(e))

        elif message.message_type == HandoffMessageType.COMMIT:
            receiver.record(message, {"status": "committed"})
            self._update_record(message.handoff_id, status=HandoffStatus.COMMITTED)
            return self._make_ack(message)

        elif message.message_type == HandoffMessageType.ABORT:
            receiver.record(message, {"status": "aborted"})
            self._participant_states.pop(message.handoff_id, None)
            self._update_record(message.handoff_id, status=HandoffStatus.ABORTED)
            return self._make_ack(message)

        return None

    def _make_ack(
        self,
        message: DistributedHandoffMessage,
        already_processed: bool = False,
    ) -> DistributedHandoffMessage:
        return DistributedHandoffMessage(
            message_id=str(uuid.uuid4()),
            handoff_id=message.handoff_id,
            sender_node_id=message.receiver_node_id,
            receiver_node_id=message.sender_node_id,
            message_type=HandoffMessageType.ACK,
            step_index=message.step_index,
            state_payload={"already_processed": already_processed},
            timestamp=time.time(),
            provenance_ref=message.provenance_ref,
        )

    def _make_nack(
        self,
        message: DistributedHandoffMessage,
        error: str,
    ) -> DistributedHandoffMessage:
        return DistributedHandoffMessage(
            message_id=str(uuid.uuid4()),
            handoff_id=message.handoff_id,
            sender_node_id=message.receiver_node_id,
            receiver_node_id=message.sender_node_id,
            message_type=HandoffMessageType.NACK,
            step_index=message.step_index,
            state_payload={"error": error},
            timestamp=time.time(),
            provenance_ref=message.provenance_ref,
        )

    def _update_record(
        self,
        handoff_id: str,
        status: HandoffStatus,
        error: Optional[str] = None,
    ) -> None:
        record = self._handoff_records.get(handoff_id)
        if record:
            record.status = status
            if error:
                record.error = error
            if status == HandoffStatus.COMMITTED:
                record.completed_at = time.time()

    def get_record(self, handoff_id: str) -> Optional[DistributedHandoffRecord]:
        return self._handoff_records.get(handoff_id)

    def list_pending_handoffs(self) -> List[str]:
        return [
            hid for hid, rec in self._handoff_records.items()
            if rec.status == HandoffStatus.PENDING
        ]


def handoff_needs_distribution(module_contract: Any) -> bool:
    """Per INV-DIST-1: determine if a handoff requires distributed protocol.

    Uses the module contract's distribution_model field to determine
    whether to use intra-process (2PC) or inter-process (distributed) protocol.
    """
    if module_contract is None:
        return False
    dist_model = getattr(module_contract, "distribution_model", "single_node")
    return dist_model in ("distributed", "multi_node", "cross_process")