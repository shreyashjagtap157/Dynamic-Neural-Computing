"""Failure taxonomy: classification and handling policy per failure-taxonomy.md.

Per failure-taxonomy.md DEF-FAIL-1 through DEF-FAIL-7 and INV-FAIL-1 through INV-FAIL-8.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Any

from dnc.runtime.types import ModuleInstanceID


class FailureClassification(Enum):
    FAILURE_TRANSIENT = "FAILURE_TRANSIENT"
    FAILURE_RECOVERABLE = "FAILURE_RECOVERABLE"
    FAILURE_UNRECOVERABLE = "FAILURE_UNRECOVERABLE"
    FAILURE_FATAL = "FAILURE_FATAL"
    FAILURE_CATASTROPHIC = "FAILURE_CATASTROPHIC"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"


class FailureSignal(Enum):
    TIMEOUT = "TIMEOUT"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    INVALID_OUTPUT = "INVALID_OUTPUT"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    PANIC = "PANIC"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
    ERROR_CORRECTION_SUCCEEDED = "ERROR_CORRECTION_SUCCEEDED"
    ERROR_CORRECTION_FAILED = "ERROR_CORRECTION_FAILED"
    GPU_RECOVERY = "GPU_RECOVERY"


SIGNAL_TO_CLASSIFICATION: Dict[FailureSignal, FailureClassification] = {
    FailureSignal.TIMEOUT: FailureClassification.FAILURE_TRANSIENT,
    FailureSignal.RESOURCE_EXHAUSTED: FailureClassification.FAILURE_RECOVERABLE,
    FailureSignal.INVALID_OUTPUT: FailureClassification.INVALID_OUTPUT,
    FailureSignal.CONTRACT_VIOLATION: FailureClassification.FAILURE_FATAL,
    FailureSignal.PANIC: FailureClassification.FAILURE_FATAL,
    FailureSignal.RETRY_EXHAUSTED: FailureClassification.FAILURE_RECOVERABLE,
    FailureSignal.ERROR_CORRECTION_SUCCEEDED: FailureClassification.FAILURE_RECOVERABLE,
    FailureSignal.ERROR_CORRECTION_FAILED: FailureClassification.FAILURE_UNRECOVERABLE,
    FailureSignal.GPU_RECOVERY: FailureClassification.FAILURE_RECOVERABLE,
}


@dataclass
class FailureRecord:
    module_instance_id: ModuleInstanceID
    signal: FailureSignal
    classification: FailureClassification
    step_index: int
    payload: Dict[str, Any]


class FailureClassifier:
    """Per DEF-FAIL-1: failure detection and classification at the scheduler level."""

    MAX_TRANSIENT_RETRIES: int = 3

    def __init__(self) -> None:
        self._failure_counts: Dict[str, int] = {}
        self._module_failure_rates: Dict[str, float] = {}

    def classify(
        self,
        module_id: ModuleInstanceID,
        signal: FailureSignal,
        step_index: int,
        payload: Optional[Dict[str, Any]] = None,
    ) -> FailureRecord:
        """Per INV-FAIL-1: every failure must be classified before handling."""
        base_classification = SIGNAL_TO_CLASSIFICATION[signal]

        if signal == FailureSignal.TIMEOUT:
            count = self._increment_retry_count(module_id)
            if count >= self.MAX_TRANSIENT_RETRIES:
                classification = FailureClassification.FAILURE_UNRECOVERABLE
            else:
                classification = FailureClassification.FAILURE_TRANSIENT
        else:
            classification = base_classification

        return FailureRecord(
            module_instance_id=module_id,
            signal=signal,
            classification=classification,
            step_index=step_index,
            payload=payload or {},
        )

    def _increment_retry_count(self, module_id: ModuleInstanceID) -> int:
        key = str(module_id)
        count = self._failure_counts.get(key, 0) + 1
        self._failure_counts[key] = count
        return count

    def record_failure(
        self,
        module_type_name: str,
        total_invocations: int,
    ) -> None:
        """Per INV-FAIL-5: track failure rate per module type."""
        key = module_type_name
        failures = self._failure_counts.get(key, 0) + 1
        self._failure_counts[key] = failures
        if total_invocations > 0:
            self._module_failure_rates[key] = failures / total_invocations

    def get_failure_rate(self, module_type_name: str) -> float:
        return self._module_failure_rates.get(module_type_name, 0.0)


class FailureHandler:
    """Per failure-taxonomy.md Section 2: prescribed handling policy per classification."""

    def handle(
        self,
        record: FailureRecord,
        registry: Any,
    ) -> str:
        """Return handling action. Per INV-FAIL-2: must follow prescribed policy."""
        classification = record.classification

        if classification == FailureClassification.FAILURE_TRANSIENT:
            return "RETRY"
        elif classification == FailureClassification.FAILURE_RECOVERABLE:
            return "RECOVER"
        elif classification == FailureClassification.FAILURE_UNRECOVERABLE:
            return "TRIGGER_REPLAN"
        elif classification == FailureClassification.FAILURE_FATAL:
            return "TRIGGER_REPLAN_AUDIT"
        elif classification == FailureClassification.FAILURE_CATASTROPHIC:
            return "HALT_ALL"
        elif classification == FailureClassification.INVALID_OUTPUT:
            return "TRIGGER_REPLAN"
        elif classification == FailureClassification.PARTIAL_FAILURE:
            return "MAJORITY_VOTE"

        return "UNKNOWN"


class AlertSeverity(Enum):
    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_LOW = "P4_LOW"


class AlertManager:
    """Per failure-taxonomy.md DEF-FAIL-5: alert severity levels and runbook triggers."""

    def determine_severity(
        self,
        failure_record: FailureRecord,
        failure_rate_60min: float,
        retry_rate: float = 0.0,
    ) -> AlertSeverity:
        """Per DEF-FAIL-5: P1-P4 severity based on failure_rate and failure type."""
        classification = failure_record.classification

        if classification == FailureClassification.FAILURE_CATASTROPHIC:
            return AlertSeverity.P1_CRITICAL
        if failure_rate_60min > 0.05:
            return AlertSeverity.P1_CRITICAL
        if failure_rate_60min > 0.01:
            return AlertSeverity.P2_HIGH
        if retry_rate > 0.5 and classification == FailureClassification.FAILURE_TRANSIENT:
            return AlertSeverity.P2_HIGH
        if failure_rate_60min > 0.001:
            return AlertSeverity.P3_MEDIUM
        return AlertSeverity.P4_LOW

    def get_runbook_trigger(self, severity: AlertSeverity) -> str:
        """Per DEF-FAIL-6: runbook trigger per severity level."""
        triggers = {
            AlertSeverity.P1_CRITICAL: "CATASTROPHIC_RUNBOOK",
            AlertSeverity.P2_HIGH: "UNRECOVERABLE_RUNBOOK",
            AlertSeverity.P3_MEDIUM: "RECOVERABLE_RUNBOOK",
            AlertSeverity.P4_LOW: "LOG_ONLY",
        }
        return triggers.get(severity, "LOG_ONLY")
