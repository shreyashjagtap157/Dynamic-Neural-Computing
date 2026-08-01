"""Task-conditioned semantic DNC-IR candidate synthesis."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from dnc.capabilities.registry import CapabilityRegistry
from dnc.cognition.canonical import canonical_json, normalize_text
from dnc.cognition.contracts import CognitiveActionType, RiskClass
from dnc.cognition.state import CognitiveState
from dnc.ir.identity import UnitID
from dnc.ir.operations import IROperation, OperationType
from dnc.ir.unit import (
    ComputationalUnit,
    LifecycleDimension,
    StructureDimension,
    VisibilityDimension,
)
from dnc.semantics.contracts import SemanticGraphCandidate, SemanticUnitTemplate


@dataclass(frozen=True)
class SynthesisRequest:
    state: CognitiveState
    templates: tuple[SemanticUnitTemplate, ...]
    provenance_refs: tuple[str, ...]
    available_budget: float
    granted_permissions: frozenset[str] = frozenset()
    max_hypothesis_branches: int = 3
    verifier_needs: tuple[str, ...] = ()
    skill_template_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.available_budget < 0 or self.max_hypothesis_branches < 0:
            raise ValueError("synthesis budget and branch bound MUST be non-negative")
        if not self.provenance_refs:
            raise ValueError("synthesis requires provenance references")


@dataclass(frozen=True)
class SemanticSynthesizer:
    capability_registry: CapabilityRegistry

    def synthesize(self, request: SynthesisRequest) -> tuple[SemanticGraphCandidate, ...]:
        state = request.state
        wanted = {CognitiveActionType.REASON}
        if state.missing_information:
            wanted.add(CognitiveActionType.RETRIEVE)
        if request.verifier_needs or state.answer_state_id:
            wanted.add(CognitiveActionType.VERIFY)
        if state.hypotheses:
            if request.max_hypothesis_branches > 0:
                wanted.add(CognitiveActionType.OBSERVE_OR_TEST)
        templates = [
            template for template in request.templates
            if template.action_type in wanted or template.template_id in request.skill_template_ids
        ]
        candidates: list[SemanticGraphCandidate] = []
        hypothesis_ids = tuple(
            hypothesis.hypothesis_id
            for hypothesis in state.hypotheses[: request.max_hypothesis_branches]
        )
        for template in templates:
            card = self.capability_registry.get(template.required_capability_id)
            if (
                card is None
                or card not in self.capability_registry.available()
                or template.action_type not in card.supported_actions
                or not template.permissions.issubset(card.permissions)
                or _risk_order(template.risk_class) > _risk_order(card.risk_limit)
                or _risk_order(template.risk_class) > _risk_order(state.task.policy.risk_class)
            ):
                continue
            semantic_payload = {
                "task": state.task.task_id,
                "template": template.template_id,
                "version": template.version,
                "hypotheses": hypothesis_ids if template.action_type is CognitiveActionType.OBSERVE_OR_TEST else (),
                "unknowns": state.missing_information if template.action_type is CognitiveActionType.RETRIEVE else (),
                "verifiers": request.verifier_needs if template.action_type is CognitiveActionType.VERIFY else (),
            }
            fingerprint = hashlib.sha256(canonical_json(semantic_payload).encode()).hexdigest()
            unit_id = UnitID(f"sem_{fingerprint[:16]}")
            unit = ComputationalUnit(
                unit_id,
                template.purpose,
                StructureDimension.PRIMITIVE,
                VisibilityDimension.INSPECTABLE,
                LifecycleDimension.SPECIALIZED,
                contract=template.contract(),
                metadata={
                    "semantic_template_id": template.template_id,
                    "semantic_template_version": template.version,
                    "semantic_fingerprint": fingerprint,
                    "task_id": state.task.task_id,
                    "tenant_id": state.task.tenant_id,
                    "action_type": template.action_type.value,
                    "capability_id": template.required_capability_id,
                    "required_permissions": tuple(sorted(template.permissions)),
                    "risk_class": template.risk_class.value,
                    "provenance_refs": request.provenance_refs,
                    "semantic_justification": f"{template.purpose} for {normalize_text(state.task.goal.objective)}",
                },
            )
            predicted = _predicted_evidence(template.action_type, state, request)
            candidates.append(
                SemanticGraphCandidate(
                    f"candidate:{fingerprint[:16]}",
                    state.task.task_id,
                    (IROperation(OperationType.ADD_UNIT, {"unit": unit}, unit.metadata["semantic_justification"]),),
                    (unit,),
                    unit.metadata["semantic_justification"],
                    predicted,
                    request.provenance_refs,
                    (template.required_capability_id,),
                    tuple(
                        sorted(
                            _source_kinds(
                                template.action_type,
                                template.template_id in request.skill_template_ids,
                            )
                        )
                    ),
                    hypothesis_ids if template.action_type is CognitiveActionType.OBSERVE_OR_TEST else (),
                    float(template.resource_limits.get("cost", 0.0)),
                    "I3_RECORDED_EXTERNALS" if template.side_effect_class.value != "NONE" else "I1_GRAPH_ONLY",
                    fingerprint,
                )
            )
        return semantic_deduplicate(tuple(candidates))


def semantic_deduplicate(candidates: tuple[SemanticGraphCandidate, ...]) -> tuple[SemanticGraphCandidate, ...]:
    unique: dict[str, SemanticGraphCandidate] = {}
    for candidate in candidates:
        existing = unique.get(candidate.semantic_fingerprint)
        if existing is None or candidate.candidate_id < existing.candidate_id:
            unique[candidate.semantic_fingerprint] = candidate
    return tuple(unique[key] for key in sorted(unique))


def _predicted_evidence(action, state, request):
    if action is CognitiveActionType.RETRIEVE:
        return tuple(f"resolve:{item_id}" for item_id in state.missing_information)
    if action is CognitiveActionType.VERIFY:
        return tuple(f"verifier-result:{verifier}" for verifier in request.verifier_needs) or ("answer-verification",)
    if action is CognitiveActionType.OBSERVE_OR_TEST:
        return tuple(
            observation
            for hypothesis in state.hypotheses[: request.max_hypothesis_branches]
            for observation in hypothesis.predicted_observations
        ) or ("hypothesis-observation",)
    return ("candidate-answer",)


def _source_kinds(action, is_skill):
    if action is CognitiveActionType.RETRIEVE:
        return {"unknown"}
    if action is CognitiveActionType.VERIFY:
        return {"verifier"}
    if action is CognitiveActionType.OBSERVE_OR_TEST:
        return {"hypothesis"}
    return {"skill"} if is_skill else {"goal"}


def _risk_order(value: RiskClass) -> int:
    return {RiskClass.LOW: 1, RiskClass.MEDIUM: 2, RiskClass.HIGH: 3, RiskClass.CRITICAL: 4}[value]
