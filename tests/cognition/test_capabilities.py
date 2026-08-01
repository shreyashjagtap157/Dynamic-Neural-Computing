from dnc.cognition import (
    CapabilityBroker,
    CapabilityCard,
    CapabilityRequirement,
    CapabilityRegistry,
    CognitiveActionType,
    RiskClass,
)
from dnc.capabilities import HealthStatus


def _card(capability_id: str, *, cost: float = 0.0, competence: float = 0.8) -> CapabilityCard:
    return CapabilityCard(
        capability_id=capability_id,
        name=capability_id,
        provider_id="test",
        provider_version="1",
        model_id=capability_id,
        supported_actions=frozenset({CognitiveActionType.VERIFY}),
        risk_limit=RiskClass.HIGH,
        permissions=frozenset({"read"}),
        competence=competence,
        cost_per_call=cost,
        health=HealthStatus.HEALTHY,
        fingerprint=capability_id,
    )


def test_cognition_facade_uses_phase4_registry_and_broker() -> None:
    registry = CapabilityRegistry()
    registry.register(_card("expensive", cost=3.0))
    registry.register(_card("cheap", cost=1.0))

    match = CapabilityBroker(registry).match(
        CapabilityRequirement(CognitiveActionType.VERIFY, RiskClass.MEDIUM)
    )

    assert match.satisfied
    assert match.selected.capability_id == "cheap"


def test_cognition_facade_broker_enforces_permissions_and_competence() -> None:
    registry = CapabilityRegistry()
    registry.register(_card("limited", competence=0.4))

    match = CapabilityBroker(registry).match(
        CapabilityRequirement(
            CognitiveActionType.VERIFY,
            RiskClass.HIGH,
            required_permissions=frozenset({"read", "network"}),
            minimum_competence=0.9,
        )
    )

    assert not match.satisfied
    assert set(match.rejections[0].reason_codes) >= {"PERMISSIONS_MISSING", "COMPETENCE_LOW"}
