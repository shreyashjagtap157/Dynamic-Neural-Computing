"""
Transaction Manager (Transaction Semantics Specification)
Orchestrates ACID transactions for DNC structural mutations with OCC, rollback, and provenance integration.
"""

import copy
from typing import List, Tuple, Optional
from dnc.ir.graph import StructuralGraph
from dnc.ir.operations import IROperation
from dnc.ir.validator import DNCIRValidator, ValidationResult
from dnc.mutation.engine import MutationEngine
from dnc.ir.identity import TransactionID, GraphVersion
from dnc.observability.provenance import ProvenanceLog, EventType
from .context import TransactionContext, TransactionState

class TransactionManager:
    """
    Manages transaction lifecycle, OCC validation, staging isolation, commit/rollback,
    and structural provenance logging.
    """
    def __init__(self, validator: Optional[DNCIRValidator] = None, mutation_engine: Optional[MutationEngine] = None, provenance_log: Optional[ProvenanceLog] = None):
        self.validator = validator or DNCIRValidator()
        self.mutation_engine = mutation_engine or MutationEngine()
        self.provenance_log = provenance_log

    def execute_transaction(self, graph: StructuralGraph, operations: List[IROperation], base_version: Optional[GraphVersion] = None) -> Tuple[bool, TransactionContext]:
        tx_id = TransactionID()
        expected_version = base_version or graph.version
        
        ctx = TransactionContext(
            tx_id=tx_id,
            base_version=expected_version,
            operations=operations
        )

        # Log transaction begin in provenance
        last_ref = None
        if self.provenance_log is not None:
            ev = self.provenance_log.append(
                event_type=EventType.STRUCTURAL_TRANSACTION_BEGIN,
                step_index=None,
                causal_ref=None,
                payload={"tx_id": str(tx_id), "base_version": str(expected_version), "graph_id": str(graph.graph_id)}
            )
            last_ref = ev.event_id

        # 1. BEGIN & OCC Check
        ctx.state = TransactionState.VALIDATING
        if graph.version != expected_version:
            ctx.state = TransactionState.FAILED
            ctx.error_message = f"OCC Conflict: Base version {expected_version} does not match current graph version {graph.version}."
            if self.provenance_log is not None:
                self.provenance_log.append(
                    event_type=EventType.STRUCTURAL_TRANSACTION_ROLLED_BACK,
                    step_index=None,
                    causal_ref=last_ref,
                    payload={"tx_id": str(tx_id), "reason": ctx.error_message}
                )
            return False, ctx

        # 2. Staging Sandbox Isolation (deep copy of graph for staging)
        staging_graph = copy.deepcopy(graph)

        # 3. VALIDATE and APPLY operations on staging graph
        ctx.state = TransactionState.APPLYING
        for op in operations:
            if not op.validate():
                ctx.state = TransactionState.ROLLING_BACK
                ctx.error_message = f"Operation validation failed for {op.op_type}"
                self._rollback_staging(graph, staging_graph, ctx)
                if self.provenance_log is not None:
                    self.provenance_log.append(
                        event_type=EventType.STRUCTURAL_TRANSACTION_ROLLED_BACK,
                        step_index=None,
                        causal_ref=last_ref,
                        payload={"tx_id": str(tx_id), "reason": ctx.error_message}
                    )
                return False, ctx

            success, warns, op_undo = self.mutation_engine.apply_operation(staging_graph, op)
            if not success:
                ctx.state = TransactionState.ROLLING_BACK
                ctx.error_message = f"Mutation application failed: {warns}"
                self.mutation_engine.rollback(staging_graph, ctx.undo_log)
                ctx.state = TransactionState.ROLLED_BACK
                if self.provenance_log is not None:
                    self.provenance_log.append(
                        event_type=EventType.STRUCTURAL_TRANSACTION_ROLLED_BACK,
                        step_index=None,
                        causal_ref=last_ref,
                        payload={"tx_id": str(tx_id), "reason": ctx.error_message}
                    )
                return False, ctx
            
            if self.provenance_log is not None:
                ev_mut = self.provenance_log.append(
                    event_type=EventType.STRUCTURAL_MUTATION_APPLIED,
                    step_index=None,
                    causal_ref=last_ref,
                    payload={"tx_id": str(tx_id), "op_type": op.op_type.value, "parameters": str(op.parameters)}
                )
                last_ref = ev_mut.event_id

            # Transfer undo operations
            for inv in op_undo.pop_all():
                ctx.undo_log.push(inv)

        # 4. Final validation of candidate state
        val_res = self.validator.validate_graph(staging_graph)
        ctx.validation_result = val_res
        if not val_res.is_valid:
            ctx.state = TransactionState.ROLLING_BACK
            ctx.error_message = f"Structural invariant violation after mutation: {val_res.errors}"
            self.mutation_engine.rollback(staging_graph, ctx.undo_log)
            ctx.state = TransactionState.ROLLED_BACK
            if self.provenance_log is not None:
                self.provenance_log.append(
                    event_type=EventType.STRUCTURAL_TRANSACTION_ROLLED_BACK,
                    step_index=None,
                    causal_ref=last_ref,
                    payload={"tx_id": str(tx_id), "reason": ctx.error_message}
                )
            return False, ctx

        # 5. COMMIT: atomically update active graph and advance version at transaction level
        ctx.state = TransactionState.COMMITTING
        graph.units = staging_graph.units
        graph.edges = staging_graph.edges
        graph.metadata = staging_graph.metadata
        graph.version = graph.version.next_sequence()

        ctx.state = TransactionState.COMMITTED
        if self.provenance_log is not None:
            ev_comm = self.provenance_log.append(
                event_type=EventType.STRUCTURAL_TRANSACTION_COMMITTED,
                step_index=None,
                causal_ref=last_ref,
                payload={"tx_id": str(tx_id), "new_version": str(graph.version)}
            )
            self.provenance_log.append(
                event_type=EventType.STRUCTURAL_GRAPH_VERSION_CREATED,
                step_index=None,
                causal_ref=ev_comm.event_id,
                payload={"graph_id": str(graph.graph_id), "version": str(graph.version)}
            )

        return True, ctx

    def _rollback_staging(self, active_graph: StructuralGraph, staging_graph: StructuralGraph, ctx: TransactionContext) -> None:
        self.mutation_engine.rollback(staging_graph, ctx.undo_log)
        ctx.state = TransactionState.ROLLED_BACK
