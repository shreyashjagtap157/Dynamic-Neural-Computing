"""Continual learning package: bounded drift, KB versioning, root-cause rollback."""

from dnc.learning.continual import (
    KnowledgeBase,
    LearningEvent,
    ExecutionRecord,
    DriftChecker,
    LearningVerificationProtocol,
    RollbackCircuitBreaker,
    RootCauseRollback,
    CandidateUpdate,
    DriftBoundExceeded,
    InvariantViolationLearning,
    CatastrophicForgettingDetected,
    LearningWithoutEvents,
)

__all__ = [
    "KnowledgeBase",
    "LearningEvent",
    "ExecutionRecord",
    "DriftChecker",
    "LearningVerificationProtocol",
    "RollbackCircuitBreaker",
    "RootCauseRollback",
    "CandidateUpdate",
    "DriftBoundExceeded",
    "InvariantViolationLearning",
    "CatastrophicForgettingDetected",
    "LearningWithoutEvents",
]