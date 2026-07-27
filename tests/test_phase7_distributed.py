"""Phase 7 (Distributed Handoffs) tests.

Per distributed-handoff-protocol.md: Distributed handoff infrastructure for
inter-process and inter-node state transfer using at-least-once delivery
with idempotent receiver buffers.
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "src")

from dnc.distributed.protocol import (
    DistributedCoordinator,
    DistributedHandoffMessage,
    DistributedHandoffRecord,
    HandoffMessageType,
    HandoffStatus,
    IdempotentReceiver,
    handoff_needs_distribution,
)


def test_ec1_idempotent_receiver_deduplicates_duplicate_message():
    """EC-1: IdempotentReceiver correctly identifies duplicate message IDs."""
    receiver = IdempotentReceiver(window_size=10)
    msg1 = DistributedHandoffMessage(
        message_id="msg_001",
        handoff_id="handoff_001",
        sender_node_id="node_A",
        receiver_node_id="node_B",
        message_type=HandoffMessageType.STATE_TRANSFER,
        step_index=0,
        state_payload={"key": "value"},
        timestamp=time.time(),
        provenance_ref="prov_001",
    )

    assert not receiver.is_duplicate("msg_001")
    receiver.record(msg1, {"status": "accepted"})
    assert receiver.is_duplicate("msg_001")
    print("PASS: ec1_idempotent_receiver_deduplicates_duplicate_message")


def test_ec2_idempotent_receiver_returns_cached_result():
    """EC-2: IdempotentReceiver returns cached result for duplicate messages."""
    receiver = IdempotentReceiver()
    msg = DistributedHandoffMessage(
        message_id="msg_002",
        handoff_id="handoff_001",
        sender_node_id="node_A",
        receiver_node_id="node_B",
        message_type=HandoffMessageType.STATE_TRANSFER,
        step_index=0,
        state_payload={"key": "value"},
        timestamp=time.time(),
        provenance_ref="prov_001",
    )

    receiver.record(msg, {"status": "accepted", "output": 42})
    cached = receiver.get_cached_result("msg_002")
    assert cached == {"status": "accepted", "output": 42}
    print("PASS: ec2_idempotent_receiver_returns_cached_result")


def test_ec3_idempotent_receiver_evicts_oldest_when_window_full():
    """EC-3: IdempotentReceiver evicts oldest entries when window is exceeded."""
    receiver = IdempotentReceiver(window_size=3)
    for i in range(5):
        msg = DistributedHandoffMessage(
            message_id=f"msg_{i:03d}",
            handoff_id="handoff_001",
            sender_node_id="node_A",
            receiver_node_id="node_B",
            message_type=HandoffMessageType.STATE_TRANSFER,
            step_index=i,
            state_payload={"n": i},
            timestamp=time.time() + i,
            provenance_ref="prov_001",
        )
        receiver.record(msg, {"n": i})

    assert not receiver.is_duplicate("msg_000")
    assert not receiver.is_duplicate("msg_001")
    assert receiver.is_duplicate("msg_004")
    print("PASS: ec3_idempotent_receiver_evicts_oldest_when_window_full")


def test_ec4_distributed_coordinator_initiate_handoff():
    """EC-4: DistributedCoordinator.initiate_handoff() creates a valid handoff message."""
    coordinator = DistributedCoordinator(node_id="node_A")
    msg = coordinator.initiate_handoff(
        sender_node_id="node_A",
        receiver_node_id="node_B",
        state_payload={"W": {}, "M": {}},
        provenance_ref="prov_001",
        step_index=5,
    )

    assert isinstance(msg, DistributedHandoffMessage)
    assert msg.message_type == HandoffMessageType.STATE_TRANSFER
    assert msg.sender_node_id == "node_A"
    assert msg.receiver_node_id == "node_B"
    assert msg.step_index == 5
    assert msg.state_payload == {"W": {}, "M": {}}
    print("PASS: ec4_distributed_coordinator_initiate_handoff")


def test_ec5_distributed_coordinator_receive_state_transfer():
    """EC-5: Coordinator processes STATE_TRANSFER and returns ACK."""
    coordinator = DistributedCoordinator(node_id="node_B")
    receiver = IdempotentReceiver()

    sender_msg = coordinator.initiate_handoff(
        sender_node_id="node_A",
        receiver_node_id="node_B",
        state_payload={"W": {}, "M": {}},
        provenance_ref="prov_001",
        step_index=5,
    )

    response = coordinator.receive_message(sender_msg, receiver)
    assert response is not None
    assert response.message_type == HandoffMessageType.ACK
    assert response.receiver_node_id == "node_A"
    print("PASS: ec5_distributed_coordinator_receive_state_transfer")


def test_ec6_distributed_coordinator_handles_duplicate_message():
    """EC-6: Coordinator returns ACK for duplicate messages without reprocessing."""
    coordinator = DistributedCoordinator(node_id="node_B")
    receiver = IdempotentReceiver()

    msg = coordinator.initiate_handoff(
        sender_node_id="node_A",
        receiver_node_id="node_B",
        state_payload={"W": {}, "M": {}},
        provenance_ref="prov_001",
        step_index=5,
    )

    coordinator.receive_message(msg, receiver)
    response2 = coordinator.receive_message(msg, receiver)
    assert response2 is not None
    assert response2.message_type == HandoffMessageType.ACK
    print("PASS: ec6_distributed_coordinator_handles_duplicate_message")


def test_ec7_distributed_coordinator_record_tracking():
    """EC-7: Coordinator tracks handoff records with correct status."""
    coordinator = DistributedCoordinator(node_id="node_A")
    receiver = IdempotentReceiver()

    msg = coordinator.initiate_handoff(
        sender_node_id="node_A",
        receiver_node_id="node_B",
        state_payload={"W": {}},
        provenance_ref="prov_001",
        step_index=5,
    )

    record = coordinator.get_record(msg.handoff_id)
    assert record is not None
    assert record.status == HandoffStatus.PENDING

    coordinator.receive_message(msg, receiver)
    record_after = coordinator.get_record(msg.handoff_id)
    assert record_after.status == HandoffStatus.COMMITTED
    print("PASS: ec7_distributed_coordinator_record_tracking")


def test_ec8_handoff_message_type_enum():
    """EC-8: All handoff message types are defined per distributed-handoff-protocol.md."""
    types = list(HandoffMessageType)
    assert HandoffMessageType.PREPARE in types
    assert HandoffMessageType.COMMIT in types
    assert HandoffMessageType.ABORT in types
    assert HandoffMessageType.STATE_TRANSFER in types
    assert HandoffMessageType.ACK in types
    assert HandoffMessageType.NACK in types
    assert HandoffMessageType.HEARTBEAT in types
    print("PASS: ec8_handoff_message_type_enum")


def test_ec9_handoff_message_content_hash():
    """EC-9: DistributedHandoffMessage.content_hash() returns a hex string."""
    msg = DistributedHandoffMessage(
        message_id="msg_001",
        handoff_id="handoff_001",
        sender_node_id="node_A",
        receiver_node_id="node_B",
        message_type=HandoffMessageType.STATE_TRANSFER,
        step_index=0,
        state_payload={"key": "value"},
        timestamp=time.time(),
        provenance_ref="prov_001",
    )

    h = msg.content_hash()
    assert isinstance(h, str)
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)
    print("PASS: ec9_handoff_message_content_hash")


def test_ec10_handoff_needs_distribution():
    """EC-10: handoff_needs_distribution() returns True for distributed module contracts."""
    class DistributedContract:
        distribution_model = "distributed"

    class SingleNodeContract:
        distribution_model = "single_node"

    class CrossProcessContract:
        distribution_model = "cross_process"

    assert handoff_needs_distribution(DistributedContract())
    assert handoff_needs_distribution(CrossProcessContract())
    assert not handoff_needs_distribution(SingleNodeContract())
    assert not handoff_needs_distribution(None)
    print("PASS: ec10_handoff_needs_distribution")


def test_ec11_distributed_coordinator_abort():
    """EC-11: Coordinator processes ABORT and updates handoff status to ABORTED."""
    coordinator = DistributedCoordinator(node_id="node_B")
    receiver = IdempotentReceiver()

    msg = coordinator.initiate_handoff(
        sender_node_id="node_A",
        receiver_node_id="node_B",
        state_payload={"W": {}},
        provenance_ref="prov_001",
        step_index=5,
    )

    abort_msg = DistributedHandoffMessage(
        message_id=str(time.time()),
        handoff_id=msg.handoff_id,
        sender_node_id="node_A",
        receiver_node_id="node_B",
        message_type=HandoffMessageType.ABORT,
        step_index=5,
        state_payload={},
        timestamp=time.time(),
        provenance_ref="prov_001",
    )

    response = coordinator.receive_message(abort_msg, receiver)
    assert response is not None
    assert response.message_type == HandoffMessageType.ACK
    record = coordinator.get_record(msg.handoff_id)
    assert record.status == HandoffStatus.ABORTED
    print("PASS: ec11_distributed_coordinator_abort")


def test_ec12_distributed_handoff_record_dataclass():
    """EC-12: DistributedHandoffRecord captures all required fields."""
    record = DistributedHandoffRecord(
        handoff_id="handoff_001",
        sender_node_id="node_A",
        receiver_node_id="node_B",
        status=HandoffStatus.PENDING,
        prepare_sent_at=time.time(),
    )

    assert record.handoff_id == "handoff_001"
    assert record.sender_node_id == "node_A"
    assert record.status == HandoffStatus.PENDING
    print("PASS: ec12_distributed_handoff_record_dataclass")


if __name__ == "__main__":
    tests = [
        test_ec1_idempotent_receiver_deduplicates_duplicate_message,
        test_ec2_idempotent_receiver_returns_cached_result,
        test_ec3_idempotent_receiver_evicts_oldest_when_window_full,
        test_ec4_distributed_coordinator_initiate_handoff,
        test_ec5_distributed_coordinator_receive_state_transfer,
        test_ec6_distributed_coordinator_handles_duplicate_message,
        test_ec7_distributed_coordinator_record_tracking,
        test_ec8_handoff_message_type_enum,
        test_ec9_handoff_message_content_hash,
        test_ec10_handoff_needs_distribution,
        test_ec11_distributed_coordinator_abort,
        test_ec12_distributed_handoff_record_dataclass,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/12 Phase 7 tests passed")

    if failed > 0:
        print(f"FAIL: {failed}/12 Phase 7 tests failed")
        exit(1)
    else:
        print("PASS: All Phase 7 tests passed")
        exit(0)
