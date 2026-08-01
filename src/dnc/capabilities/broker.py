"""Deterministic, auditable capability selection."""

from __future__ import annotations

from dataclasses import dataclass

from dnc.capabilities.contracts import (
    CapabilityCard,
    CapabilityRejection,
    CapabilityRequirement,
    CapabilitySelection,
)
from dnc.capabilities.registry import CapabilityRegistry
from dnc.cognition.contracts import RiskClass


@dataclass(frozen=True)
class CapabilityBroker:
    registry: CapabilityRegistry

    def match(self, requirement: CapabilityRequirement, *, now_ns: int | None = None) -> CapabilitySelection:
        available_ids = {card.capability_id for card in self.registry.available(now_ns)}
        candidates: list[CapabilityCard] = []
        rejections: list[CapabilityRejection] = []
        for card in self.registry.all():
            reasons = self._reasons(card, requirement, available_ids)
            if reasons:
                rejections.append(CapabilityRejection(card.capability_id, tuple(reasons)))
            else:
                candidates.append(card)
        if not candidates:
            return CapabilitySelection(
                None, requirement, False, "no capability satisfies all requirements",
                rejections=tuple(rejections),
            )
        selected = min(
            candidates,
            key=lambda card: (-card.competence, card.cost_per_call, card.latency_ms, card.capability_id),
        )
        return CapabilitySelection(
            selected, requirement, True, "capability matched",
            candidates=tuple(card.capability_id for card in candidates),
            rejections=tuple(rejections),
        )

    def _reasons(
        self,
        card: CapabilityCard,
        requirement: CapabilityRequirement,
        available_ids: set[str],
    ) -> list[str]:
        reasons: list[str] = []
        if card.capability_id not in available_ids:
            reasons.append("UNAVAILABLE")
        if requirement.action_type not in card.supported_actions:
            reasons.append("ACTION_UNSUPPORTED")
        if _risk_order(card.risk_limit) < _risk_order(requirement.risk_class):
            reasons.append("RISK_LIMIT")
        if not requirement.required_features.issubset(card.features):
            reasons.append("FEATURES_MISSING")
        if not requirement.required_permissions.issubset(card.permissions):
            reasons.append("PERMISSIONS_MISSING")
        if requirement.locality is not None and card.locality != requirement.locality:
            reasons.append("LOCALITY_MISMATCH")
        if requirement.domain and requirement.domain not in card.calibration_domains:
            reasons.append("DOMAIN_UNCALIBRATED")
        if card.competence < requirement.minimum_competence:
            reasons.append("COMPETENCE_LOW")
        if requirement.maximum_cost is not None and card.cost_per_call > requirement.maximum_cost:
            reasons.append("COST_BUDGET")
        if requirement.maximum_latency_ms is not None and card.latency_ms > requirement.maximum_latency_ms:
            reasons.append("LATENCY_BUDGET")
        if requirement.token_budget is not None and card.max_tokens is not None and requirement.token_budget > card.max_tokens:
            reasons.append("TOKEN_BUDGET")
        return reasons


def _risk_order(value: RiskClass) -> int:
    return {RiskClass.LOW: 1, RiskClass.MEDIUM: 2, RiskClass.HIGH: 3, RiskClass.CRITICAL: 4}[value]
