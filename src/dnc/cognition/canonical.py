"""Canonical serialization, schemas, and hashing for cognitive contracts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


COGNITIVE_SCHEMA_VERSION = "2026-07-31.phase3.v1"
COGNITIVE_SCHEMA_ID = "dnc.cognition.canonical.v1"


def normalize_text(value: str) -> str:
    """Normalize free text without pretending to interpret hidden reasoning."""

    return re.sub(r"\s+", " ", value.strip()).casefold()


def canonical_data(value: Any) -> Any:
    """Return JSON-compatible, deterministically ordered data."""

    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return canonical_data(asdict(value))
    if isinstance(value, dict):
        return {
            str(key): canonical_data(value[key])
            for key in sorted(value, key=lambda item: str(item))
            if value[key] is not None
        }
    if isinstance(value, (set, frozenset)):
        normalized = [canonical_data(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    if isinstance(value, (list, tuple)):
        return [canonical_data(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    """Serialize cognitive state canonically for persistence and hashing."""

    return json.dumps(
        canonical_data(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def canonical_hash(value: Any, *, namespace: str = COGNITIVE_SCHEMA_ID) -> str:
    """Hash cognitive data in a namespace separate from DNC-IR identity hashes."""

    payload = f"{namespace}\n{canonical_json(value)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def task_fingerprint(
    *,
    objective: str,
    tenant_id: str,
    actor_id: str,
    session_id: str,
    parent_task_id: str | None = None,
) -> str:
    """Create a deterministic fingerprint for normalized task identity inputs."""

    return canonical_hash(
        {
            "objective": normalize_text(objective),
            "tenant_id": tenant_id,
            "actor_id": actor_id,
            "session_id": session_id,
            "parent_task_id": parent_task_id,
        },
        namespace=f"{COGNITIVE_SCHEMA_ID}.task",
    )


def ambiguous_task_fields(task: Any) -> tuple[str, ...]:
    """Return fields that require clarification before high-risk work."""

    missing: list[str] = []
    if not getattr(task, "expected_output_contract", {}):
        missing.append("expected_output_contract")
    if not getattr(task, "required_evidence", ()):
        missing.append("required_evidence")
    if getattr(task, "acceptable_uncertainty", None) is None:
        missing.append("acceptable_uncertainty")
    return tuple(missing)


TASK_SPEC_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://dnc.local/schemas/cognition/task-spec.v1.json",
    "title": "TaskSpec",
    "type": "object",
    "required": ["schema_version", "task_id", "tenant_id", "actor_id", "session_id", "description"],
    "properties": {
        "schema_version": {"const": COGNITIVE_SCHEMA_VERSION},
        "task_id": {"type": "string", "minLength": 1},
        "parent_task_id": {"type": ["string", "null"]},
        "tenant_id": {"type": "string", "minLength": 1},
        "actor_id": {"type": "string", "minLength": 1},
        "session_id": {"type": "string", "minLength": 1},
        "description": {"type": "string", "minLength": 1},
        "normalized_objective": {"type": "string"},
        "expected_output_contract": {"type": "object"},
        "risk_class": {"enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
        "security_labels": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": True,
}


EPISTEMIC_ITEM_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://dnc.local/schemas/cognition/epistemic-item.v1.json",
    "title": "EpistemicItem",
    "type": "object",
    "required": ["schema_version", "item_id", "status", "content", "tenant_id", "security_labels"],
    "properties": {
        "schema_version": {"const": COGNITIVE_SCHEMA_VERSION},
        "item_id": {"type": "string", "minLength": 1},
        "status": {
            "enum": [
                "VERIFIED_FACT",
                "DIRECT_OBSERVATION",
                "RETRIEVED_CLAIM",
                "MODEL_INFERENCE",
                "ASSUMPTION",
                "PREDICTION",
                "CONFLICT",
                "UNKNOWN",
                "CAPABILITY_LIMIT",
                "UNVERIFIABLE",
                "RETRACTED",
                "FACT",
                "OBSERVATION",
            ]
        },
        "content": {"type": "string", "minLength": 1},
        "tenant_id": {"type": "string", "minLength": 1},
        "security_labels": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": True,
}


COGNITIVE_STATE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://dnc.local/schemas/cognition/state.v1.json",
    "title": "CognitiveState",
    "type": "object",
    "required": ["schema_version", "task", "epistemic_items", "evidence", "event_log"],
    "properties": {
        "schema_version": {"const": COGNITIVE_SCHEMA_VERSION},
        "task": TASK_SPEC_SCHEMA,
        "epistemic_items": {"type": "array", "items": EPISTEMIC_ITEM_SCHEMA},
        "epistemic_history": {"type": "array", "items": EPISTEMIC_ITEM_SCHEMA},
        "evidence": {"type": "array"},
        "event_log": {"type": "array"},
    },
    "additionalProperties": True,
}


EVIDENCE_REF_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://dnc.local/schemas/cognition/evidence-ref.v1.json",
    "type": "object",
    "required": [
        "schema_version", "evidence_id", "artifact_hash", "source_type",
        "source_identity", "acquired_at", "tenant_id", "security_labels",
    ],
    "properties": {
        "schema_version": {"const": COGNITIVE_SCHEMA_VERSION},
        "evidence_id": {"type": "string", "minLength": 1},
        "artifact_hash": {"type": "string", "minLength": 1},
        "source_type": {"type": "string"},
        "source_identity": {"type": "string", "minLength": 1},
        "acquired_at": {"type": "string", "minLength": 1},
        "tenant_id": {"type": "string", "minLength": 1},
        "security_labels": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": True,
}


EPISTEMIC_RELATION_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://dnc.local/schemas/cognition/epistemic-relation.v1.json",
    "type": "object",
    "required": ["schema_version", "relation_id", "relation_type", "source_id", "target_id", "tenant_id"],
    "properties": {
        "schema_version": {"const": COGNITIVE_SCHEMA_VERSION},
        "relation_id": {"type": "string", "minLength": 1},
        "relation_type": {"enum": ["SUPPORTS", "CONTRADICTS", "DEPENDS_ON", "INVALIDATES"]},
        "source_id": {"type": "string", "minLength": 1},
        "target_id": {"type": "string", "minLength": 1},
        "tenant_id": {"type": "string", "minLength": 1},
    },
    "additionalProperties": True,
}


HYPOTHESIS_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://dnc.local/schemas/cognition/hypothesis.v1.json",
    "type": "object",
    "required": ["schema_version", "hypothesis_id", "proposition", "status", "tenant_id"],
    "properties": {
        "schema_version": {"const": COGNITIVE_SCHEMA_VERSION},
        "hypothesis_id": {"type": "string", "minLength": 1},
        "proposition": {"type": "string", "minLength": 1},
        "status": {"type": "string"},
        "tenant_id": {"type": "string", "minLength": 1},
    },
    "additionalProperties": True,
}


ACTION_OUTCOME_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://dnc.local/schemas/cognition/action-outcome.v1.json",
    "type": "object",
    "required": [
        "schema_version", "outcome_id", "action_id", "attempt_id", "trace_id",
        "lifecycle_state", "execution_status",
    ],
    "properties": {
        "schema_version": {"const": COGNITIVE_SCHEMA_VERSION},
        "outcome_id": {"type": "string", "minLength": 1},
        "action_id": {"type": "string", "minLength": 1},
        "attempt_id": {"type": "string", "minLength": 1},
        "trace_id": {"type": "string", "minLength": 1},
        "lifecycle_state": {"type": "string"},
        "execution_status": {"type": "string"},
    },
    "additionalProperties": True,
}


CONFIDENCE_ESTIMATE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://dnc.local/schemas/cognition/confidence-estimate.v1.json",
    "type": "object",
    "required": ["schema_version", "estimate_id", "target_id", "target_type"],
    "properties": {
        "schema_version": {"const": COGNITIVE_SCHEMA_VERSION},
        "estimate_id": {"type": "string", "minLength": 1},
        "target_id": {"type": "string", "minLength": 1},
        "target_type": {"type": "string", "minLength": 1},
        "p_correct": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
    },
    "additionalProperties": True,
}


RATIONALE_CODE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://dnc.local/schemas/cognition/rationale-code.v1.json",
    "type": "object",
    "required": ["schema_version", "code", "label"],
    "properties": {
        "schema_version": {"const": COGNITIVE_SCHEMA_VERSION},
        "code": {"type": "string", "minLength": 1},
        "label": {"type": "string", "minLength": 1},
    },
    "additionalProperties": True,
}
