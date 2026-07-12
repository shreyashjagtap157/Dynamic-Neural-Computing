"""Phase 7 (Distributed Handoffs) tests.

Per distributed-handoff-protocol.md: Distributed handoff infrastructure for
inter-process and inter-node state transfer using at-least-once delivery
with idempotent receiver buffers.
"""

from __future__ import annotations

import sys
import time
import uuid

sys.path.insert(0, "src")

from dnc.distributed.protocol import (
    DistributedCoordinator,
    DistributedHandoffConfig,
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
    """EC-3: IdempotentReceiver evicts oldest entries when window is exceeded.

    After 5 items with window_size=3, the 2 oldest (msg_000, msg_001) are evicted,
    and only the 3 most recent (msg_002, msg_003, msg_004) remain.
    """
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

    assert receiver.is_duplicate("msg_000") is False, "msg_000 should be evicted (oldest)"
    assert receiver.is_duplicate("msg_001") is False, "msg_001 should be evicted"
    assert receiver.is_duplicate("msg_004") is True, "msg_004 should be retained (newest)"
    assert receiver.is_duplicate("msg_003") is True, "msg_003 should be retained"
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


def test_ec13_distributed_handoff_config_defaults():
    """EC-13: DistributedHandoffConfig has correct defaults per INV-DIST-6."""
    config = DistributedHandoffConfig()

    assert config.handoff_timeout == 30.0
    assert config.max_retries == 6
    assert config.heartbeat_interval == 10.0
    print("PASS: ec13_distributed_handoff_config_defaults")


def test_ec14_distributed_handoff_config_custom():
    """EC-14: DistributedHandoffConfig accepts custom values."""
    config = DistributedHandoffConfig(
        handoff_timeout=10.0,
        max_retries=3,
        heartbeat_interval=5.0,
    )

    assert config.handoff_timeout == 10.0
    assert config.max_retries == 3
    assert config.heartbeat_interval == 5.0
    print("PASS: ec14_distributed_handoff_config_custom")


def test_ec15_retry_with_backoff_exponential():
    """EC-15: retry_with_backoff returns exponential delays for failures 0-2 (INV-DIST-3)."""
    coordinator = DistributedCoordinator(node_id="node_A")

    delay_0 = coordinator.retry_with_backoff("handoff_001", consecutive_failures=0)
    delay_1 = coordinator.retry_with_backoff("handoff_001", consecutive_failures=1)
    delay_2 = coordinator.retry_with_backoff("handoff_001", consecutive_failures=2)

    assert delay_0 == 1.0, "failure=0: 1s base"
    assert delay_1 == 2.0, "failure=1: 2s base"
    assert delay_2 == 4.0, "failure=2: 4s base"
    print("PASS: ec15_retry_with_backoff_exponential")


def test_ec16_retry_with_backoff_jitter():
    """EC-16: retry_with_backoff adds jitter for failures 3-5 (INV-DIST-3)."""
    coordinator = DistributedCoordinator(node_id="node_A")

    delays = [coordinator.retry_with_backoff("handoff_001", consecutive_failures=4) for _ in range(10)]
    assert all(d > 16.0 for d in delays), "failure=4: base 16s + jitter"
    print("PASS: ec16_retry_with_backoff_jitter")


def test_ec17_retry_with_backoff_fail_fast():
    """EC-17: retry_with_backoff returns 0 for failures >= 6 (fail-fast INV-DIST-3)."""
    coordinator = DistributedCoordinator(node_id="node_A")

    delay = coordinator.retry_with_backoff("handoff_001", consecutive_failures=6)
    assert delay == 0.0, "failure>=6: fail-fast, control loop notified"
    print("PASS: ec17_retry_with_backoff_fail_fast")


def test_ec18_mark_failed_records_error():
    """EC-18: mark_failed sets FAILED status and error per INV-DIST-4."""
    coordinator = DistributedCoordinator(node_id="node_A")

    msg = coordinator.initiate_handoff(
        sender_node_id="node_A",
        receiver_node_id="node_B",
        state_payload={"W": {}},
        provenance_ref="prov_001",
        step_index=5,
    )

    coordinator.mark_failed(msg.handoff_id, "network_partition")
    record = coordinator.get_record(msg.handoff_id)

    assert record is not None
    assert record.status == HandoffStatus.FAILED
    assert record.error == "network_partition"
    print("PASS: ec18_mark_failed_records_error")


def test_ec19_single_hop_validation_rejects_same_node():
    """EC-19: initiate_handoff raises ValueError for same sender/receiver per INV-DIST-5."""
    coordinator = DistributedCoordinator(node_id="node_A")

    try:
        coordinator.initiate_handoff(
            sender_node_id="node_A",
            receiver_node_id="node_A",
            state_payload={"W": {}},
            provenance_ref="prov_001",
            step_index=5,
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "INV-DIST-5" in str(e)
        assert "multi-hop" in str(e).lower()
    print("PASS: ec19_single_hop_validation_rejects_same_node")


def test_ec20_coordinator_config_passed_through():
    """EC-20: Coordinator accepts and exposes DistributedHandoffConfig."""
    config = DistributedHandoffConfig(handoff_timeout=5.0, max_retries=10)
    coordinator = DistributedCoordinator(node_id="node_A", config=config)

    assert coordinator.config is config
    assert coordinator.config.handoff_timeout == 5.0
    assert coordinator.config.max_retries == 10
    print("PASS: ec20_coordinator_config_passed_through")


def test_ec21_partition_detection_via_retry_count():
    """EC-21: retry_count increments for partition detection per INV-DIST-3."""
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
    assert record.retry_count == 0

    coordinator._update_record(msg.handoff_id, HandoffStatus.PENDING, increment_retry=True)
    coordinator._update_record(msg.handoff_id, HandoffStatus.PENDING, increment_retry=True)
    record = coordinator.get_record(msg.handoff_id)
    assert record.retry_count == 2
    print("PASS: ec21_partition_detection_via_retry_count")


def test_ec22_abort_clears_participant_state():
    """EC-22: ABORT clears participant state per INV-DIST-2 atomicity."""
    coordinator = DistributedCoordinator(node_id="node_B")
    receiver = IdempotentReceiver()

    msg = coordinator.initiate_handoff(
        sender_node_id="node_A",
        receiver_node_id="node_B",
        state_payload={"W": {"key": "value"}},
        provenance_ref="prov_001",
        step_index=5,
    )

    assert msg.handoff_id in coordinator._participant_states

    abort_msg = DistributedHandoffMessage(
        message_id=str(uuid.uuid4()),
        handoff_id=msg.handoff_id,
        sender_node_id="node_A",
        receiver_node_id="node_B",
        message_type=HandoffMessageType.ABORT,
        step_index=5,
        state_payload={},
        timestamp=time.time(),
        provenance_ref="prov_001",
    )

    coordinator.receive_message(abort_msg, receiver)
    assert msg.handoff_id not in coordinator._participant_states
    print("PASS: ec22_abort_clears_participant_state")


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
        test_ec13_distributed_handoff_config_defaults,
        test_ec14_distributed_handoff_config_custom,
        test_ec15_retry_with_backoff_exponential,
        test_ec16_retry_with_backoff_jitter,
        test_ec17_retry_with_backoff_fail_fast,
        test_ec18_mark_failed_records_error,
        test_ec19_single_hop_validation_rejects_same_node,
        test_ec20_coordinator_config_passed_through,
        test_ec21_partition_detection_via_retry_count,
        test_ec22_abort_clears_participant_state,
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

    print(f"\n{passed}/22 Phase 7 tests passed")

    if failed > 0:
        print(f"FAIL: {failed}/22 Phase 7 tests failed")
        exit(1)
    else:
        print("PASS: All Phase 7 tests passed")
        exit(0)