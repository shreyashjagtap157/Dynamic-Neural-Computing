"""DNC Distributed Handoffs: inter-process and inter-node state transfer.

Per distributed-handoff-protocol.md: Layer 7 extends the single-address-space
two-phase commit to inter-process and inter-node boundaries using a message-passing
protocol with at-least-once delivery and idempotent receiver buffers.
"""

from __future__ import annotations

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

__all__ = [
    "DistributedCoordinator",
    "DistributedHandoffConfig",
    "DistributedHandoffMessage",
    "DistributedHandoffRecord",
    "HandoffMessageType",
    "HandoffStatus",
    "IdempotentReceiver",
    "handoff_needs_distribution",
]