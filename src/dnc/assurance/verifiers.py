"""Deterministic and callback-backed verifier implementations."""

from __future__ import annotations

import ast
import json
import math
import operator
import re
from dataclasses import dataclass
from typing import Any, Callable

from dnc.assurance.contracts import (
    VerificationStatus,
    VerifierClaim,
    VerifierDescriptor,
    VerifierResult,
)


Check = Callable[[VerifierClaim], tuple[VerificationStatus, tuple[str, ...], dict[str, Any]]]


@dataclass(frozen=True)
class FunctionalVerifier:
    descriptor: VerifierDescriptor
    check: Check

    def verify(self, claim: VerifierClaim) -> VerifierResult:
        if not self.descriptor.supports(claim):
            return _result(self.descriptor, claim, VerificationStatus.INAPPLICABLE, ("INAPPLICABLE",))
        try:
            status, reasons, details = self.check(claim)
        except Exception as exc:
            return _result(
                self.descriptor,
                claim,
                VerificationStatus.ERROR,
                ("VERIFIER_ERROR",),
                {"error_type": type(exc).__name__, "error": str(exc)},
            )
        return _result(self.descriptor, claim, status, reasons, details)


@dataclass(frozen=True)
class CallbackVerifierAdapter(FunctionalVerifier):
    """External, model, or human verifier adapter with declared independence."""

    def __post_init__(self) -> None:
        if self.descriptor.kind.value not in {"EXTERNAL", "MODEL", "HUMAN"}:
            raise ValueError("callback verifier adapters MUST declare external, model, or human kind")


def format_check(*, pattern: str | None = None, non_empty: bool = True) -> Check:
    compiled = re.compile(pattern) if pattern else None

    def check(claim: VerifierClaim):
        value = claim.value
        if not isinstance(value, str):
            return VerificationStatus.FAIL, ("NOT_TEXT",), {}
        if non_empty and not value.strip():
            return VerificationStatus.FAIL, ("EMPTY",), {}
        if compiled and compiled.fullmatch(value) is None:
            return VerificationStatus.FAIL, ("PATTERN_MISMATCH",), {}
        return VerificationStatus.PASS, ("FORMAT_VALID",), {"pattern": pattern}

    return check


def schema_check(schema: dict[str, Any]) -> Check:
    def check(claim: VerifierClaim):
        value = claim.value
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return VerificationStatus.FAIL, ("INVALID_JSON",), {}
        errors = _schema_errors(value, schema)
        status = VerificationStatus.PASS if not errors else VerificationStatus.FAIL
        return status, (("SCHEMA_VALID",) if not errors else tuple(errors)), {"errors": errors}

    return check


def arithmetic_check(expected: float, *, tolerance: float = 1e-9) -> Check:
    def check(claim: VerifierClaim):
        actual = _safe_arithmetic(str(claim.value))
        passed = abs(actual - expected) <= tolerance
        return (
            VerificationStatus.PASS if passed else VerificationStatus.FAIL,
            ("ARITHMETIC_VALID" if passed else "ARITHMETIC_MISMATCH",),
            {"actual": actual, "expected": expected, "tolerance": tolerance},
        )

    return check


def callable_check(callback: Callable[[Any], bool], success_code: str) -> Check:
    def check(claim: VerifierClaim):
        passed = bool(callback(claim.value))
        return (
            VerificationStatus.PASS if passed else VerificationStatus.FAIL,
            (success_code if passed else f"{success_code}_FAILED",),
            {},
        )

    return check


def code_test_check(runner: Callable[[Any], bool]) -> Check:
    """Delegate code/test verification to an injected isolated runner."""

    return callable_check(runner, "CODE_TEST_VALID")


def policy_check(evaluator: Callable[[Any], bool]) -> Check:
    return callable_check(evaluator, "POLICY_VALID")


def provenance_check(claim: VerifierClaim):
    valid = bool(claim.evidence) and all(
        getattr(item, "artifact_hash", None)
        and getattr(item, "source_identity", None)
        and getattr(item, "chain_of_custody", ())
        for item in claim.evidence
    )
    return (
        VerificationStatus.PASS if valid else VerificationStatus.FAIL,
        ("PROVENANCE_VALID" if valid else "PROVENANCE_INCOMPLETE",),
        {"evidence_count": len(claim.evidence)},
    )


def _result(
    descriptor: VerifierDescriptor,
    claim: VerifierClaim,
    status: VerificationStatus,
    reasons: tuple[str, ...],
    details: dict[str, Any] | None = None,
) -> VerifierResult:
    return VerifierResult(
        result_id=f"{claim.claim_id}:{descriptor.verifier_id}",
        verifier_id=descriptor.verifier_id,
        verifier_version=descriptor.version,
        verifier_fingerprint=descriptor.fingerprint,
        claim_id=claim.claim_id,
        target_id=claim.target_id,
        scope=claim.scope,
        status=status,
        independence_group=descriptor.independence_group,
        tenant_id=claim.tenant_id,
        checks=reasons,
        reason_codes=reasons,
        details=details or {},
    )


def _schema_errors(value: Any, schema: dict[str, Any]) -> list[str]:
    expected_type = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "number": (int, float), "integer": int, "boolean": bool}
    if expected_type in {"number", "integer"} and isinstance(value, bool):
        return ["TYPE_MISMATCH"]
    if expected_type in types and not isinstance(value, types[expected_type]):
        return ["TYPE_MISMATCH"]
    errors: list[str] = []
    if isinstance(value, dict):
        errors.extend(f"MISSING:{key}" for key in schema.get("required", []) if key not in value)
        for key, child_schema in schema.get("properties", {}).items():
            if key in value:
                errors.extend(f"{key}:{error}" for error in _schema_errors(value[key], child_schema))
    return errors


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_arithmetic(expression: str) -> float:
    if len(expression) > 256:
        raise ValueError("arithmetic expression exceeds size limit")

    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 12:
                raise ValueError("arithmetic exponent exceeds limit")
            result = float(_OPS[type(node.op)](left, right))
            if not math.isfinite(result) or abs(result) > 1e100:
                raise ValueError("arithmetic result exceeds limit")
            return result
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
            return float(_UNARY[type(node.op)](evaluate(node.operand)))
        raise ValueError("unsupported arithmetic expression")

    return evaluate(ast.parse(expression, mode="eval"))
