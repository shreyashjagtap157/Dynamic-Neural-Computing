"""Observability package: provenance, failure taxonomy, and evaluation."""

from dnc.observability.provenance import (
    ProvenanceLog,
    ProvenanceEvent,
    EventType,
    ProvenanceTamperingViolation,
    CausalChainBroken,
)
from dnc.observability.failure import (
    FailureClassifier,
    FailureHandler,
    AlertManager,
    FailureClassification,
    FailureSignal,
    FailureRecord,
    AlertSeverity,
    SIGNAL_TO_CLASSIFICATION,
)
from dnc.observability.evaluation import (
    EvaluationSuite,
    EvaluationScenario,
    EvaluationRun,
    EvaluationStage,
    StagedEvaluationResult,
    MetricResult,
    MetricClass,
    ResultClassification,
    NovelTaskBenchmark,
    get_canonical_novel_benchmarks,
)

__all__ = [
    "ProvenanceLog",
    "ProvenanceEvent",
    "EventType",
    "ProvenanceTamperingViolation",
    "CausalChainBroken",
    "FailureClassifier",
    "FailureHandler",
    "AlertManager",
    "FailureClassification",
    "FailureSignal",
    "FailureRecord",
    "AlertSeverity",
    "SIGNAL_TO_CLASSIFICATION",
    "EvaluationSuite",
    "EvaluationScenario",
    "EvaluationRun",
    "EvaluationStage",
    "StagedEvaluationResult",
    "MetricResult",
    "MetricClass",
    "ResultClassification",
    "NovelTaskBenchmark",
    "get_canonical_novel_benchmarks",
]