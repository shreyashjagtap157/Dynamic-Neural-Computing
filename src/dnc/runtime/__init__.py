"""DNC runtime: types, exceptions, and core runtime types."""

from dnc.runtime.types import (
    UNBOUND,
    PENDING,
    Buffer,
    ModuleInstanceID,
    ModuleTypeID,
    ModuleContract,
    Metadata,
    Value,
    InvariantViolation,
    StateComponentViolation,
    InvalidCheckpoint,
    HandoffFailure,
    ModuleNotFound,
    DAGCycle,
)

__all__ = [
    "UNBOUND",
    "PENDING",
    "Buffer",
    "ModuleInstanceID",
    "ModuleTypeID",
    "ModuleContract",
    "Metadata",
    "Value",
    "InvariantViolation",
    "StateComponentViolation",
    "InvalidCheckpoint",
    "HandoffFailure",
    "ModuleNotFound",
    "DAGCycle",
    "Runtime",
    "Decision",
    "AssessmentKind",
    "ExecutionState2",
    "LatencyConfig",
    "Observation",
]


def __getattr__(name: str):
    if name in (
        "Runtime",
        "Decision",
        "AssessmentKind",
        "ExecutionState2",
        "LatencyConfig",
        "Observation",
    ):
        from dnc.runtime.runtime import (
            Runtime,
            Decision,
            AssessmentKind,
            ExecutionState2,
            LatencyConfig,
            Observation,
        )

        globals().update(
            Runtime=Runtime,
            Decision=Decision,
            AssessmentKind=AssessmentKind,
            ExecutionState2=ExecutionState2,
            LatencyConfig=LatencyConfig,
            Observation=Observation,
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")