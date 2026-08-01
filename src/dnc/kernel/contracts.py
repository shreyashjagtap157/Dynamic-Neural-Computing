"""Cross-layer governance contracts shared by IR, cognition, and execution."""

from enum import Enum


class SideEffectClass(str, Enum):
    NONE = "NONE"
    REVERSIBLE = "REVERSIBLE"
    COMPENSATABLE = "COMPENSATABLE"
    IRREVERSIBLE = "IRREVERSIBLE"


class EffectType(str, Enum):
    PROVIDER_CALL = "PROVIDER_CALL"
    FILE_WRITE = "FILE_WRITE"
    DATABASE_WRITE = "DATABASE_WRITE"
    NETWORK_CALL = "NETWORK_CALL"
    CACHE_WRITE = "CACHE_WRITE"
    PROCESS_SPAWN = "PROCESS_SPAWN"
    CLEANUP = "CLEANUP"


class IsolationGrade(str, Enum):
    """State-isolation strength available to an execution environment."""

    I0_NONE = "I0_NONE"
    I1_GRAPH_ONLY = "I1_GRAPH_ONLY"
    I2_PROCESS_LOCAL = "I2_PROCESS_LOCAL"
    I3_RECORDED_EXTERNALS = "I3_RECORDED_EXTERNALS"
    I4_SANDBOXED_ENVIRONMENT = "I4_SANDBOXED_ENVIRONMENT"

    @property
    def rank(self) -> int:
        return list(type(self)).index(self)
