from dnc.cognition import (
    CapabilityBroker,
    CapabilityCard,
    CapabilityRegistry,
    CognitiveActionType,
    RiskClass,
)


def test_broker_selects_lowest_cost_matching_capability() -> None:
    registry = CapabilityRegistry()
    registry.register(
        CapabilityCard(
            capability_id="expensive-verifier",
            name="Expensive verifier",
            supported_actions=frozenset({CognitiveActionType.VERIFY}),
            risk_limit=RiskClass.HIGH,
            cost_per_call=3.0,
        )
    )
    registry.register(
        CapabilityCard(
            capability_id="cheap-verifier",
            name="Cheap verifier",
            supported_actions=frozenset({CognitiveActionType.VERIFY}),
            risk_limit=RiskClass.HIGH,
            cost_per_call=1.0,
        )
    )

    match = CapabilityBroker(registry).match(CognitiveActionType.VERIFY, RiskClass.MEDIUM)

    assert match.satisfied is True
    assert match.capability.capability_id == "cheap-verifier"


def test_broker_rejects_degraded_capabilities() -> None:
    registry = CapabilityRegistry()
    registry.register(
        CapabilityCard(
            capability_id="degraded-retriever",
            name="Retriever",
            supported_actions=frozenset({CognitiveActionType.RETRIEVE}),
            risk_limit=RiskClass.MEDIUM,
            degraded=True,
        )
    )

    match = CapabilityBroker(registry).match(CognitiveActionType.RETRIEVE, RiskClass.LOW)

    assert match.satisfied is False
    assert match.capability is None


def test_broker_requires_permissions() -> None:
    registry = CapabilityRegistry()
    registry.register(
        CapabilityCard(
            capability_id="read-only-retriever",
            name="Read-only retriever",
            supported_actions=frozenset({CognitiveActionType.RETRIEVE}),
            risk_limit=RiskClass.MEDIUM,
            permissions=frozenset({"read"}),
        )
    )

    match = CapabilityBroker(registry).match(
        CognitiveActionType.RETRIEVE,
        RiskClass.LOW,
        required_permissions=frozenset({"read", "network"}),
    )

    assert match.satisfied is False


def test_broker_requires_risk_limit_to_cover_task_risk() -> None:
    registry = CapabilityRegistry()
    registry.register(
        CapabilityCard(
            capability_id="low-risk-asker",
            name="Low risk asker",
            supported_actions=frozenset({CognitiveActionType.ASK}),
            risk_limit=RiskClass.LOW,
        )
    )

    match = CapabilityBroker(registry).match(CognitiveActionType.ASK, RiskClass.HIGH)

    assert match.satisfied is False
