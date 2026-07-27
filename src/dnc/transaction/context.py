"""
Transaction Context and Lifecycle States (Transaction Semantics Specification)
Implements TransactionID, TransactionState, and TransactionContext.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from dnc.ir.identity import TransactionID, GraphVersion
from dnc.ir.operations import IROperation
from dnc.mutation.undo import UndoLog
from dnc.ir.validator import ValidationResult

class TransactionState(str, Enum):
    BEGIN = "BEGIN"
    VALIDATING = "VALIDATING"
    APPLYING = "APPLYING"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"

@dataclass
class TransactionContext:
    tx_id: TransactionID
    base_version: GraphVersion
    operations: List[IROperation]
    state: TransactionState = TransactionState.BEGIN
    undo_log: UndoLog = field(default_factory=UndoLog)
    validation_result: Optional[ValidationResult] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
