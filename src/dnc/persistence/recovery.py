"""Declared recovery objectives and deterministic fault-campaign evidence."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryObjectives:
    maximum_lost_events: int
    maximum_recovery_ticks: int
    minimum_availability: float


@dataclass(frozen=True)
class FaultCampaignResult:
    faults: tuple[str, ...]
    lost_events: int
    recovery_ticks: int
    availability: float
    duplicate_irreversible_effects: int
    semantic_match: bool
    tenant_isolation_violations: int

    def meets(self, objectives: RecoveryObjectives) -> bool:
        return (
            self.lost_events <= objectives.maximum_lost_events
            and self.recovery_ticks <= objectives.maximum_recovery_ticks
            and self.availability >= objectives.minimum_availability
            and self.duplicate_irreversible_effects == 0
            and self.semantic_match
            and self.tenant_isolation_violations == 0
        )
