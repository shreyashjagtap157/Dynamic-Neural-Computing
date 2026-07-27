"""
Mutation Undo Log and Inverse Compensation (Mutation Semantics Section 6)
Implements inverse operations for structural rollback support.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from dnc.ir.identity import UnitID
from dnc.ir.graph import Edge, EdgeType

@dataclass
class InverseOperation:
    op_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)

class UndoLog:
    """
    Records inverse operations during mutation application to enable exact rollback.
    """
    def __init__(self):
        self._log: List[InverseOperation] = []

    def push(self, inverse: InverseOperation) -> None:
        self._log.append(inverse)

    def pop_all(self) -> List[InverseOperation]:
        items = list(self._log)
        self._log.clear()
        return list(reversed(items))

    def __len__(self) -> int:
        return len(self._log)
