"""
DNC-IR Abstract Operations Vocabulary (SPEC-IR Section 12)
Implements abstract mutation operation definitions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any

class OperationType(str, Enum):
    ADD_UNIT = "ADD_UNIT"
    REMOVE_UNIT = "REMOVE_UNIT"
    CONNECT_UNITS = "CONNECT_UNITS"
    DISCONNECT_UNITS = "DISCONNECT_UNITS"
    REWIRE_EDGE = "REWIRE_EDGE"
    SPECIALIZE_UNIT = "SPECIALIZE_UNIT"
    DESPECIALIZE_UNIT = "DESPECIALIZE_UNIT"
    COMPOSE_UNITS = "COMPOSE_UNITS"
    DECOMPOSE_UNIT = "DECOMPOSE_UNIT"
    UPDATE_CONTRACT = "UPDATE_CONTRACT"

@dataclass
class IROperation:
    op_type: OperationType
    parameters: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""

    def validate(self) -> bool:
        if self.op_type == OperationType.ADD_UNIT:
            return "unit" in self.parameters
        elif self.op_type == OperationType.REMOVE_UNIT:
            return "unit_id" in self.parameters
        elif self.op_type == OperationType.CONNECT_UNITS:
            return "source" in self.parameters and "target" in self.parameters and "edge_type" in self.parameters
        elif self.op_type == OperationType.DISCONNECT_UNITS:
            return "source" in self.parameters and "target" in self.parameters
        elif self.op_type == OperationType.REWIRE_EDGE:
            return "old_source" in self.parameters and "old_target" in self.parameters and "new_source" in self.parameters and "new_target" in self.parameters
        return True
