"""Compatibility facade for the canonical Phase 4 capability subsystem."""

from dnc.capabilities import (
    CapabilityBroker,
    CapabilityCard,
    CapabilityRegistry,
    CapabilityRequirement,
    CapabilitySelection,
)

CapabilityMatch = CapabilitySelection

__all__ = [
    "CapabilityBroker",
    "CapabilityCard",
    "CapabilityMatch",
    "CapabilityRegistry",
    "CapabilityRequirement",
    "CapabilitySelection",
]
