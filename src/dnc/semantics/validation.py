"""Semantic composition policy, capability, provenance, and isolation validation."""

from __future__ import annotations

from dataclasses import dataclass

from dnc.capabilities.registry import CapabilityRegistry
from dnc.cognition.contracts import CognitiveActionType, RiskClass
from dnc.ir.operations import OperationType
from dnc.semantics.contracts import SemanticGraphCandidate


_ISOLATION_ORDER = {
    "I0_NONE": 0,
    "I1_GRAPH_ONLY": 1,
    "I2_PROCESS_LOCAL": 2,
    "I3_RECORDED_EXTERNALS": 3,
    "I4_SANDBOXED_ENVIRONMENT": 4,
}


@dataclass(frozen=True)
class SemanticValidation:
    valid: bool
    reason_codes: tuple[str, ...]


def validate_semantic_candidate(
    candidate: SemanticGraphCandidate,
    registry: CapabilityRegistry,
    *,
    task_id: str,
    tenant_id: str,
    available_budget: float,
    granted_permissions: frozenset[str],
    available_isolation_grade: str,
) -> SemanticValidation:
    reasons: list[str] = []
    if candidate.task_id != task_id:
        reasons.append("TASK_MISMATCH")
    if candidate.estimated_cost > available_budget:
        reasons.append("COST_BUDGET")
    if not candidate.provenance_refs:
        reasons.append("PROVENANCE_REQUIRED")
    if _ISOLATION_ORDER.get(available_isolation_grade, -1) < _ISOLATION_ORDER.get(candidate.required_isolation_grade, 99):
        reasons.append("ISOLATION_GRADE")
    for capability_id in candidate.capability_ids:
        card = registry.get(capability_id)
        if card is None or card not in registry.available():
            reasons.append(f"CAPABILITY_UNAVAILABLE:{capability_id}")
        elif not card.permissions.issubset(granted_permissions):
            reasons.append(f"PERMISSION:{capability_id}")
    for unit in candidate.units:
        if unit.metadata.get("tenant_id") != tenant_id:
            reasons.append(f"TENANT_MISMATCH:{unit.unit_id.value}")
        if not unit.contract.input_schema or not unit.contract.output_schema:
            reasons.append(f"SCHEMA_REQUIRED:{unit.unit_id.value}")
        if not unit.metadata.get("semantic_justification"):
            reasons.append(f"JUSTIFICATION_REQUIRED:{unit.unit_id.value}")
        capability_id = unit.metadata.get("capability_id")
        if capability_id not in candidate.capability_ids:
            reasons.append(f"CAPABILITY_BINDING:{unit.unit_id.value}")
        card = registry.get(capability_id) if capability_id else None
        try:
            action = CognitiveActionType(unit.metadata.get("action_type"))
            risk = RiskClass(unit.metadata.get("risk_class"))
        except (TypeError, ValueError):
            reasons.append(f"SEMANTIC_METADATA:{unit.unit_id.value}")
        else:
            if card is not None and action not in card.supported_actions:
                reasons.append(f"ACTION_UNSUPPORTED:{unit.unit_id.value}")
            if card is not None and _risk_order(risk) > _risk_order(card.risk_limit):
                reasons.append(f"RISK_LIMIT:{unit.unit_id.value}")
        required = frozenset(unit.metadata.get("required_permissions", ()))
        if not required.issubset(granted_permissions):
            reasons.append(f"UNIT_PERMISSION:{unit.unit_id.value}")
    declared_units = {unit.unit_id.value for unit in candidate.units}
    added_units = set()
    for operation in candidate.operations:
        if not operation.rationale:
            reasons.append("OPERATION_RATIONALE_REQUIRED")
        if operation.op_type not in {OperationType.ADD_UNIT, OperationType.CONNECT_UNITS}:
            reasons.append(f"OPERATION_NOT_SEMANTIC:{operation.op_type.value}")
        if operation.op_type is OperationType.ADD_UNIT:
            unit = operation.parameters.get("unit")
            if unit is None or unit.unit_id.value not in declared_units:
                reasons.append("UNDECLARED_ADDED_UNIT")
            else:
                added_units.add(unit.unit_id.value)
    if added_units != declared_units:
        reasons.append("DECLARED_UNIT_OPERATION_MISMATCH")
    return SemanticValidation(not reasons, tuple(reasons))


def _risk_order(value: RiskClass) -> int:
    return {RiskClass.LOW: 1, RiskClass.MEDIUM: 2, RiskClass.HIGH: 3, RiskClass.CRITICAL: 4}[value]
