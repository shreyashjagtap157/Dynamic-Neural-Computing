"""Stable, dependency-light Python SDK facade for Generic DNC-IR workflows."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from dnc.ir.contracts import ExecutionContext
from dnc.ir.graph import StructuralGraph
from dnc.ir.serialization import DNWIRSerializer
from dnc.ir.validator import DNCIRValidator
from dnc.kernel.contracts import IsolationGrade
from dnc.kernel.errors import DNCValidationError
from dnc.kernel.versioning import DNC_IR_SCHEMA_ID, DNC_IR_SCHEMA_VERSION
from dnc.projection.executable_graph import ExecutableDAG
from dnc.projection.projector import StructuralProjector
from dnc.registry import ArtifactRecord, ArtifactRegistry, GraphRecord, GraphRegistry

SDK_API_VERSION = "1.0.0"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    target_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.target_id is not None:
            result["target_id"] = self.target_id
        return result


@dataclass(frozen=True)
class GraphValidationReport:
    graph_id: str
    graph_version: str
    structurally_valid: bool
    context_required: bool
    execution_admissible: bool | None
    valid: bool
    errors: tuple[ValidationIssue, ...] = ()
    warnings: tuple[ValidationIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": DNC_IR_SCHEMA_ID,
            "schema_version": DNC_IR_SCHEMA_VERSION,
            "graph_id": self.graph_id,
            "graph_version": self.graph_version,
            "structurally_valid": self.structurally_valid,
            "context_required": self.context_required,
            "execution_admissible": self.execution_admissible,
            "valid": self.valid,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


@dataclass(frozen=True)
class ProjectionResult:
    executable: ExecutableDAG
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return executable_dag_to_dict(self.executable, self.warnings)


class DNCSDK:
    """One maintained facade for parsing, validating, storing, and projecting graphs."""

    api_version = SDK_API_VERSION

    def __init__(
        self,
        *,
        validator: DNCIRValidator | None = None,
        artifact_registry: ArtifactRegistry | None = None,
        graph_registry: GraphRegistry | None = None,
    ) -> None:
        if validator is None and graph_registry is not None:
            validator = graph_registry.validator
        self.validator = validator or DNCIRValidator()
        if graph_registry is not None and graph_registry.validator is not self.validator:
            raise DNCValidationError(
                "SDK and supplied graph registry MUST share one validator authority"
            )
        self.artifacts = artifact_registry or ArtifactRegistry()
        self.graphs = graph_registry or GraphRegistry(validator=self.validator)
        self.projector = StructuralProjector(self.validator)

    def parse_graph(self, source: StructuralGraph | Mapping[str, Any] | str | bytes) -> StructuralGraph:
        if isinstance(source, StructuralGraph):
            return source
        if isinstance(source, Mapping):
            return DNWIRSerializer.from_dict(dict(source))
        if isinstance(source, bytes):
            try:
                source = source.decode("utf-8")
            except UnicodeDecodeError as error:
                raise DNCValidationError("graph document MUST be UTF-8 JSON") from error
        if isinstance(source, str):
            try:
                return DNWIRSerializer.from_json(source)
            except json.JSONDecodeError as error:
                raise DNCValidationError("graph document MUST be valid JSON") from error
        raise DNCValidationError(
            "graph source MUST be a StructuralGraph, mapping, JSON string, or UTF-8 bytes"
        )

    def validate_graph(
        self,
        source: StructuralGraph | Mapping[str, Any] | str | bytes,
        *,
        context: ExecutionContext | None = None,
        require_execution_context: bool = True,
    ) -> GraphValidationReport:
        graph = self.parse_graph(source)
        structural = self.validator.validate_graph(graph)
        errors = tuple(_validation_issue(issue) for issue in structural.errors)
        warnings = tuple(_validation_issue(issue) for issue in structural.warnings)
        context_required = any(
            unit.contract.requires_execution_context() for unit in graph.units.values()
        )
        execution_admissible: bool | None
        if context is not None:
            context_result = self.validator.validate_execution_context(graph, context)
            execution_admissible = context_result.is_valid
            errors += tuple(_validation_issue(issue) for issue in context_result.errors)
            warnings += tuple(_validation_issue(issue) for issue in context_result.warnings)
        elif context_required:
            execution_admissible = None
            if require_execution_context:
                errors += (
                    ValidationIssue(
                        code="CTX_REQUIRED",
                        message="governed graph validation requires an ExecutionContext",
                    ),
                )
        else:
            execution_admissible = True
        if context is not None:
            admission_valid = execution_admissible is True
        elif context_required:
            admission_valid = not require_execution_context
        else:
            admission_valid = True
        valid = structural.is_valid and admission_valid
        return GraphValidationReport(
            graph_id=graph.graph_id.value,
            graph_version=str(graph.version),
            structurally_valid=structural.is_valid,
            context_required=context_required,
            execution_admissible=execution_admissible,
            valid=valid,
            errors=errors,
            warnings=warnings,
        )

    def inspect_graph(
        self,
        source: StructuralGraph | Mapping[str, Any] | str | bytes,
        *,
        context: ExecutionContext | None = None,
    ) -> dict[str, Any]:
        graph = self.parse_graph(source)
        report = self.validate_graph(
            graph,
            context=context,
            require_execution_context=False,
        )
        edge_counts: dict[str, int] = {}
        for edge in graph.edges:
            edge_counts[edge.edge_type.value] = edge_counts.get(edge.edge_type.value, 0) + 1
        governed_units = sum(
            unit.contract.requires_execution_context() for unit in graph.units.values()
        )
        return {
            "schema_id": DNC_IR_SCHEMA_ID,
            "schema_version": DNC_IR_SCHEMA_VERSION,
            "graph_id": graph.graph_id.value,
            "graph_version": str(graph.version),
            "unit_count": len(graph.units),
            "edge_count": len(graph.edges),
            "edge_counts": dict(sorted(edge_counts.items())),
            "governed_unit_count": governed_units,
            "metadata_keys": sorted(graph.metadata),
            "validation": report.to_dict(),
        }

    def project_graph(
        self,
        source: StructuralGraph | Mapping[str, Any] | str | bytes,
        *,
        context: ExecutionContext | None = None,
    ) -> ProjectionResult:
        graph = self.parse_graph(source)
        report = self.validate_graph(graph, context=context)
        if not report.valid:
            details = "; ".join(f"{issue.code}: {issue.message}" for issue in report.errors)
            raise DNCValidationError(f"graph is not admissible for projection: {details}")
        executable, warnings = self.projector.project(graph, context=context)
        return ProjectionResult(executable=executable, warnings=tuple(warnings))

    def register_artifact(
        self,
        data: bytes,
        *,
        tenant_id: str,
        media_type: str = "application/octet-stream",
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        return self.artifacts.register(
            data,
            tenant_id=tenant_id,
            media_type=media_type,
            metadata=metadata,
        )

    def register_graph(
        self,
        source: StructuralGraph | Mapping[str, Any] | str | bytes,
        *,
        tenant_id: str,
        context: ExecutionContext | None = None,
    ) -> GraphRecord:
        return self.graphs.register(
            self.parse_graph(source),
            tenant_id=tenant_id,
            context=context,
        )

    def load_graph(
        self,
        content_ref: str,
        *,
        tenant_id: str,
        context: ExecutionContext | None = None,
    ) -> StructuralGraph:
        return self.graphs.load(content_ref, tenant_id=tenant_id, context=context)


def execution_context_from_dict(document: object) -> ExecutionContext:
    """Strictly parse the JSON representation accepted by the SDK and CLI."""

    if not isinstance(document, dict):
        raise DNCValidationError("execution context MUST be an object")
    required = frozenset({"tenant_id", "permissions", "isolation_grade"})
    optional = frozenset(
        {
            "region",
            "device",
            "runtime",
            "capabilities",
            "trust_zone",
            "confidential_compute",
        }
    )
    present = frozenset(document)
    missing = required - present
    unknown = present - required - optional
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing {sorted(missing)}")
        if unknown:
            details.append(f"unknown {sorted(unknown)}")
        raise DNCValidationError("execution context fields are invalid: " + "; ".join(details))
    for name in ("permissions", "capabilities"):
        values = document.get(name, [])
        if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
            raise DNCValidationError(f"execution context {name} MUST be an array of strings")
        if len(values) != len(set(values)):
            raise DNCValidationError(f"execution context {name} MUST contain unique values")
    for name in ("tenant_id", "region", "device", "runtime", "trust_zone"):
        if name in document and not isinstance(document[name], str):
            raise DNCValidationError(f"execution context {name} MUST be a string")
    confidential = document.get("confidential_compute", False)
    if not isinstance(confidential, bool):
        raise DNCValidationError("execution context confidential_compute MUST be boolean")
    try:
        isolation = IsolationGrade(document["isolation_grade"])
    except (TypeError, ValueError) as error:
        raise DNCValidationError("execution context isolation_grade is unsupported") from error
    return ExecutionContext(
        tenant_id=document["tenant_id"],
        permissions=frozenset(document["permissions"]),
        isolation_grade=isolation,
        region=document.get("region", ""),
        device=document.get("device", ""),
        runtime=document.get("runtime", ""),
        capabilities=frozenset(document.get("capabilities", [])),
        trust_zone=document.get("trust_zone", ""),
        confidential_compute=confidential,
    )


def executable_dag_to_dict(
    executable: ExecutableDAG,
    warnings: tuple[str, ...] = (),
) -> dict[str, Any]:
    nodes: dict[str, Any] = {}
    for unit_id, node in sorted(executable.nodes.items()):
        nodes[unit_id] = {
            "unit_id": node.unit_id.value,
            "name": node.name,
            "metadata": node.metadata,
            "idempotency": {
                "mode": node.idempotency.mode.value,
                "scope": node.idempotency.scope.value,
                "key_field": node.idempotency.key_field,
                "payload_hash_required": node.idempotency.payload_hash_required,
            },
            "side_effects": {
                "classification": node.side_effects.classification.value,
                "effect_types": sorted(item.value for item in node.side_effects.effect_types),
                "compensation_action": node.side_effects.compensation_action,
                "minimum_isolation": node.side_effects.minimum_isolation.value,
            },
            "placement": {
                "allowed_regions": sorted(node.placement.allowed_regions),
                "allowed_devices": sorted(node.placement.allowed_devices),
                "allowed_runtimes": sorted(node.placement.allowed_runtimes),
                "required_capabilities": sorted(node.placement.required_capabilities),
                "preferred_regions": list(node.placement.preferred_regions),
                "preferred_devices": list(node.placement.preferred_devices),
                "requires_local_inputs": node.placement.requires_local_inputs,
            },
            "security": {
                "tenant_id": node.security.tenant_id,
                "required_permissions": sorted(node.security.required_permissions),
                "security_labels": sorted(node.security.security_labels),
                "output_classification": node.security.output_classification.value,
                "maximum_input_classification": (
                    node.security.maximum_input_classification.value
                ),
                "allowed_residencies": sorted(node.security.allowed_residencies),
                "trust_zone": node.security.trust_zone,
                "accepted_trust_zones": sorted(node.security.accepted_trust_zones),
                "confidential_compute_required": (
                    node.security.confidential_compute_required
                ),
            },
        }
    edges = [
        {
            "source": edge.source.value,
            "target": edge.target.value,
            "edge_type": edge.edge_type,
            "source_port": edge.source_port,
            "target_port": edge.target_port,
            "metadata": edge.metadata,
        }
        for edge in sorted(
            executable.edges,
            key=lambda item: (
                item.source.value,
                item.target.value,
                item.edge_type,
                item.source_port or "",
                item.target_port or "",
            ),
        )
    ]
    return {
        "schema_id": "dnc.execution.executable_dag",
        "schema_version": SDK_API_VERSION,
        "graph_id": executable.graph_id.value,
        "source_version": str(executable.source_version),
        "nodes": nodes,
        "edges": edges,
        "topological_order": [unit_id.value for unit_id in executable.topological_order],
        "metadata": executable.metadata,
        "warnings": list(warnings),
    }


def _validation_issue(issue: object) -> ValidationIssue:
    return ValidationIssue(
        code=str(getattr(issue, "code")),
        message=str(getattr(issue, "message")),
        target_id=getattr(issue, "target_id", None),
    )


__all__ = [
    "DNCSDK",
    "GraphValidationReport",
    "ProjectionResult",
    "SDK_API_VERSION",
    "ValidationIssue",
    "executable_dag_to_dict",
    "execution_context_from_dict",
]
