"""Capability self-model and deterministic broker for cognitive actions."""

from __future__ import annotations

from dataclasses import dataclass, field

from dnc.cognition.contracts import CognitiveActionType, RiskClass


@dataclass(frozen=True)
class CapabilityCard:
    """Declared competence, cost, policy, and failure-mode record."""

    capability_id: str
    name: str
    supported_actions: frozenset[CognitiveActionType]
    risk_limit: RiskClass
    permissions: frozenset[str] = frozenset()
    calibration_domains: frozenset[str] = frozenset()
    cost_per_call: float = 0.0
    latency_ms: int = 0
    failure_modes: tuple[str, ...] = ()
    degraded: bool = False
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.capability_id:
            raise ValueError("capability_id MUST be non-empty")
        if not self.name:
            raise ValueError("name MUST be non-empty")
        if not self.supported_actions:
            raise ValueError("supported_actions MUST be non-empty")
        if not isinstance(self.risk_limit, RiskClass):
            raise TypeError("risk_limit MUST be RiskClass")
        for action in self.supported_actions:
            if not isinstance(action, CognitiveActionType):
                raise TypeError("supported_actions MUST contain CognitiveActionType values")
        if self.cost_per_call < 0:
            raise ValueError("cost_per_call MUST be non-negative")
        if self.latency_ms < 0:
            raise ValueError("latency_ms MUST be non-negative")


@dataclass(frozen=True)
class CapabilityMatch:
    """Broker result for a capability lookup."""

    capability: CapabilityCard | None
    action_type: CognitiveActionType
    satisfied: bool
    reason: str


@dataclass
class CapabilityRegistry:
    """In-memory reference registry for capability cards."""

    _cards: dict[str, CapabilityCard] = field(default_factory=dict)

    def register(self, card: CapabilityCard) -> None:
        """Register or replace a capability card by stable ID."""

        self._cards[card.capability_id] = card

    def get(self, capability_id: str) -> CapabilityCard | None:
        """Return a card by ID if present."""

        return self._cards.get(capability_id)

    def all(self) -> tuple[CapabilityCard, ...]:
        """Return registered cards in deterministic ID order."""

        return tuple(self._cards[key] for key in sorted(self._cards))


@dataclass(frozen=True)
class CapabilityBroker:
    """Select the lowest-cost non-degraded card that satisfies an action."""

    registry: CapabilityRegistry

    def match(
        self,
        action_type: CognitiveActionType,
        risk_class: RiskClass,
        required_permissions: frozenset[str] = frozenset(),
    ) -> CapabilityMatch:
        """Find a capability that supports the requested action and policy."""

        candidates: list[CapabilityCard] = []
        for card in self.registry.all():
            if card.degraded:
                continue
            if action_type not in card.supported_actions:
                continue
            if _risk_order(card.risk_limit) < _risk_order(risk_class):
                continue
            if not required_permissions.issubset(card.permissions):
                continue
            candidates.append(card)

        if not candidates:
            return CapabilityMatch(
                capability=None,
                action_type=action_type,
                satisfied=False,
                reason="no registered capability satisfies action, risk, and permissions",
            )

        selected = min(candidates, key=lambda card: (card.cost_per_call, card.latency_ms, card.capability_id))
        return CapabilityMatch(
            capability=selected,
            action_type=action_type,
            satisfied=True,
            reason="capability matched",
        )


def _risk_order(risk_class: RiskClass) -> int:
    order = {
        RiskClass.LOW: 1,
        RiskClass.MEDIUM: 2,
        RiskClass.HIGH: 3,
        RiskClass.CRITICAL: 4,
    }
    return order[risk_class]
