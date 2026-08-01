"""Capability registry lifecycle, health, expiry, and kill switches."""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Any, Callable

from dnc.capabilities.contracts import (
    CapabilityCard,
    CapabilityFeature,
    CapabilityLifecycle,
    HealthStatus,
    ModelChangeEvent,
)
from dnc.cognition.canonical import canonical_data
from dnc.cognition.contracts import CognitiveActionType, RiskClass


@dataclass
class CapabilityRegistry:
    _cards: dict[str, CapabilityCard] = field(default_factory=dict)
    _disabled: set[str] = field(default_factory=set)
    _change_listeners: list[Callable[[ModelChangeEvent], None]] = field(default_factory=list)

    def register(self, card: CapabilityCard) -> None:
        previous = self._cards.get(card.capability_id)
        self._cards[card.capability_id] = card
        if previous and previous.fingerprint != card.fingerprint:
            event = ModelChangeEvent(card.capability_id, previous.fingerprint, card.fingerprint)
            for listener in tuple(self._change_listeners):
                listener(event)

    def get(self, capability_id: str) -> CapabilityCard | None:
        return self._cards.get(capability_id)

    def all(self) -> tuple[CapabilityCard, ...]:
        return tuple(self._cards[key] for key in sorted(self._cards))

    def available(self, now_ns: int | None = None) -> tuple[CapabilityCard, ...]:
        current = time.time_ns() if now_ns is None else now_ns
        return tuple(
            card for card in self.all()
            if card.capability_id not in self._disabled
            and card.lifecycle is CapabilityLifecycle.ACTIVE
            and card.health in {HealthStatus.HEALTHY, HealthStatus.UNKNOWN}
            and not card.is_expired(current)
        )

    def set_health(self, capability_id: str, health: HealthStatus) -> None:
        self._cards[capability_id] = replace(self._require(capability_id), health=health)

    def set_lifecycle(self, capability_id: str, lifecycle: CapabilityLifecycle) -> None:
        self._cards[capability_id] = replace(self._require(capability_id), lifecycle=lifecycle)

    def disable(self, capability_id: str) -> None:
        self._require(capability_id)
        self._disabled.add(capability_id)

    def enable(self, capability_id: str) -> None:
        self._require(capability_id)
        self._disabled.discard(capability_id)

    def is_disabled(self, capability_id: str) -> bool:
        return capability_id in self._disabled

    def add_change_listener(self, listener: Callable[[ModelChangeEvent], None]) -> None:
        self._change_listeners.append(listener)

    def snapshot_state(self) -> dict[str, Any]:
        """Return a deterministic, JSON-compatible registry image."""

        cards = []
        for card in self.all():
            cards.append(
                {
                    "capability_id": card.capability_id,
                    "name": card.name,
                    "provider_id": card.provider_id,
                    "provider_version": card.provider_version,
                    "model_id": card.model_id,
                    "supported_actions": sorted(value.value for value in card.supported_actions),
                    "risk_limit": card.risk_limit.value,
                    "features": sorted(value.value for value in card.features),
                    "permissions": sorted(card.permissions),
                    "calibration_domains": sorted(card.calibration_domains),
                    "locality": card.locality,
                    "competence": card.competence,
                    "cost_per_call": card.cost_per_call,
                    "latency_ms": card.latency_ms,
                    "max_tokens": card.max_tokens,
                    "max_parallelism": card.max_parallelism,
                    "lifecycle": card.lifecycle.value,
                    "health": card.health.value,
                    "expires_at_ns": card.expires_at_ns,
                    "fingerprint": card.fingerprint,
                    "failure_modes": list(card.failure_modes),
                    "metadata": canonical_data(card.metadata),
                }
            )
        return {"cards": cards, "disabled": sorted(self._disabled)}

    def restore_state(self, state: dict[str, Any]) -> None:
        """Atomically restore cards and kill switches while preserving listeners."""

        if not isinstance(state, dict) or not isinstance(state.get("cards"), list):
            raise ValueError("capability registry snapshot MUST contain a cards list")
        disabled = state.get("disabled", [])
        if not isinstance(disabled, list) or not all(isinstance(value, str) for value in disabled):
            raise ValueError("capability registry disabled IDs MUST be a list of strings")

        cards: dict[str, CapabilityCard] = {}
        for raw in state["cards"]:
            if not isinstance(raw, dict):
                raise ValueError("capability registry card MUST be an object")
            card = CapabilityCard(
                capability_id=raw["capability_id"],
                name=raw["name"],
                provider_id=raw["provider_id"],
                provider_version=raw["provider_version"],
                model_id=raw["model_id"],
                supported_actions=frozenset(
                    CognitiveActionType(value) for value in raw["supported_actions"]
                ),
                risk_limit=RiskClass(raw["risk_limit"]),
                features=frozenset(CapabilityFeature(value) for value in raw.get("features", [])),
                permissions=frozenset(raw.get("permissions", [])),
                calibration_domains=frozenset(raw.get("calibration_domains", [])),
                locality=raw.get("locality", "remote"),
                competence=raw.get("competence", 0.0),
                cost_per_call=raw.get("cost_per_call", 0.0),
                latency_ms=raw.get("latency_ms", 0),
                max_tokens=raw.get("max_tokens"),
                max_parallelism=raw.get("max_parallelism", 1),
                lifecycle=CapabilityLifecycle(raw.get("lifecycle", "ACTIVE")),
                health=HealthStatus(raw.get("health", "UNKNOWN")),
                expires_at_ns=raw.get("expires_at_ns"),
                fingerprint=raw.get("fingerprint", ""),
                failure_modes=tuple(raw.get("failure_modes", [])),
                metadata=raw.get("metadata", {}),
            )
            if card.capability_id in cards:
                raise ValueError(f"duplicate capability in registry snapshot: {card.capability_id}")
            cards[card.capability_id] = card
        unknown_disabled = set(disabled) - set(cards)
        if unknown_disabled:
            raise ValueError(f"disabled capabilities are unknown: {sorted(unknown_disabled)}")
        self._cards = cards
        self._disabled = set(disabled)

    def _require(self, capability_id: str) -> CapabilityCard:
        card = self.get(capability_id)
        if card is None:
            raise KeyError(f"unknown capability: {capability_id}")
        return card
