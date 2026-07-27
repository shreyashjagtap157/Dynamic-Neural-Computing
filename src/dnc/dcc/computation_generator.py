"""
DNC Computation Generator (Phase 7 + Phase 13C.3 Generator Necessity Gate)
Synthesizes DNC-IR structural changes from objectives with necessity-aware gating.

Phase 7: Core generation of expansion, wiring, specialization, and composition proposals.
Phase 13C.3: Necessity gate — only generates candidates when there is evidence that
structural change is warranted. The Generator proposes; the Controller authorizes.
The Generator does NOT authorize. But the Generator should not propose candidates
that are trivially unnecessary given the current graph state and observed history.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from dnc.ir.graph import StructuralGraph, EdgeType
from dnc.ir.operations import IROperation, OperationType
from dnc.ir.identity import UnitID, GraphID
from dnc.ir.unit import ComputationalUnit, StructureDimension, VisibilityDimension, LifecycleDimension
from dnc.dcc.dcc_contracts import MutationProposal


@dataclass
class GenerationObjective:
    task_description: str = ""
    target_outcome: str = ""
    constraints: List[str] = field(default_factory=list)
    cost_budget: float = 100.0
    max_units: int = 10
    max_edges: int = 20
    require_specialization: bool = False
    allow_composition: bool = True


class NecessitySignal(str, Enum):
    """Explicit evidence that may justify structural adaptation."""

    OBJECTIVE_VIOLATION = "objective_violation"
    CONSTRAINT_VIOLATION = "constraint_violation"
    CAPACITY_INSUFFICIENCY = "capacity_insufficiency"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    FAULT_RECOVERY_REQUIREMENT = "fault_recovery_requirement"
    ENVIRONMENT_SHIFT = "environment_shift"
    COMPOSITION_REQUIREMENT = "composition_requirement"


@dataclass
class GenerationContext:
    """
    Extended in Phase 13C.3 with hysteresis and historical evidence fields.
    These allow the Generator to make evidence-based necessity decisions.
    """
    objective: GenerationObjective
    available_unit_templates: List[ComputationalUnit] = field(default_factory=list)
    graph_id: GraphID = None
    current_unit_count: int = 0
    current_edge_count: int = 0
    last_observed_utility: float = 0.75
    recent_mutation_count: int = 0
    cycles_since_mutation: int = 999
    prior_mutation_harmed: bool = False
    necessity_signals: frozenset[NecessitySignal] = field(default_factory=frozenset)


class ComputationGenerator:
    """
    Phase 7 Computation Generator: Synthesizes DNC-IR structural changes from objectives.

    Consumes:
    - Current Structural Graph
    - GenerationObjective (task, constraints, cost, limits)
    - Available computational unit templates
    - GenerationContext (extended with Phase 13C.3 evidence fields)

    Produces:
    - MutationProposal with candidate_operations

    Maintains strict separation: Generator PROPOSES only. No authorization or execution.

    Phase 13C.3 Necessity Gate:
    Proposals are only generated when there is evidence that structural change is warranted.
    This prevents the generator from producing candidates that the Controller would correctly
    reject on marginal-value grounds.
    """

    def __init__(self):
        self._proposal_counter = 0

    def generate_proposals(self, graph: StructuralGraph, context: GenerationContext) -> List[MutationProposal]:
        """
        Generate candidate structural modifications from objective and graph state.

        NECESSITY GATE (Phase 13C.3):
        Each strategy only fires when there is evidence that structural change is needed.
        The Controller evaluates and authorizes; the Generator proposes when warranted.
        """
        proposals = []
        self._proposal_counter += 1

        graph_has_capacity = context.current_unit_count < context.objective.max_units
        edges_have_capacity = context.current_edge_count < context.objective.max_edges
        graph_is_near_empty = context.current_unit_count == 0

        # ------------------------------------------------------------------
        # STRATEGY 1: Expand computation (add units)
        # Propose ONLY when one of the following holds:
        #   (a) Graph is empty (bootstrap case — structural foundation needed)
        #   (b) Capacity is genuinely insufficient AND prior utility suggests
        #       the graph is not adequately serving the task
        #   (c) Prior mutation harmed — retry with different structure warranted
        # DO NOT propose when: graph already has adequate capacity AND prior
        # utility is acceptable
        # ------------------------------------------------------------------
        signals = context.necessity_signals
        explicit_capacity_shortfall = NecessitySignal.CAPACITY_INSUFFICIENCY in signals
        capacity_insufficient = context.current_unit_count < context.objective.max_units // 2
        prior_utility_poor = context.last_observed_utility < 0.70
        prior_mutation_failed = context.prior_mutation_harmed
        needs_bootstrap = graph_is_near_empty
        urgent_restructure = bool(
            signals
            & {
                NecessitySignal.OBJECTIVE_VIOLATION,
                NecessitySignal.CONSTRAINT_VIOLATION,
                NecessitySignal.PERFORMANCE_DEGRADATION,
                NecessitySignal.FAULT_RECOVERY_REQUIREMENT,
                NecessitySignal.ENVIRONMENT_SHIFT,
            }
        )
        needs_composition_capacity = (
            NecessitySignal.COMPOSITION_REQUIREMENT in signals
            and context.current_unit_count < 2
        )
        needs_capacity = (
            explicit_capacity_shortfall
            or needs_composition_capacity
            or urgent_restructure
            or (capacity_insufficient and (prior_utility_poor or prior_mutation_failed))
        )

        if graph_has_capacity and (needs_bootstrap or needs_capacity):
            expansion_proposal = self._create_expansion_proposal(graph, context)
            if expansion_proposal:
                proposals.append(expansion_proposal)

        # ------------------------------------------------------------------
        # STRATEGY 2: Connect disconnected subgraphs (wiring)
        # Propose ONLY when:
        #   (a) Graph has multiple units AND they are not yet connected
        #   (b) Prior utility suggests routing/connectivity is a bottleneck
        # DO NOT propose when: graph is a single unit or already well-connected
        # ------------------------------------------------------------------
        if edges_have_capacity and len(graph.units) >= 2:
            graph_has_no_edges = context.current_edge_count == 0
            prior_utility_degraded = (
                context.last_observed_utility < 0.65
                or NecessitySignal.FAULT_RECOVERY_REQUIREMENT in signals
                or NecessitySignal.ENVIRONMENT_SHIFT in signals
            )

            if graph_has_no_edges or (prior_utility_degraded and not context.prior_mutation_harmed):
                wiring_proposal = self._create_wiring_proposal(graph, context)
                if wiring_proposal:
                    proposals.append(wiring_proposal)

        # ------------------------------------------------------------------
        # STRATEGY 3: Optimize existing structure (specialization)
        # Propose when: objective explicitly requires specialization (necessity signal).
        # The controller will evaluate marginal-value; the generator just proposes
        # when the objective requests it.
        # ------------------------------------------------------------------
        if (
            context.objective.require_specialization
            or NecessitySignal.OBJECTIVE_VIOLATION in signals
        ) and len(graph.units) > 0:
            specialization_proposal = self._create_specialization_proposal(graph, context)
            if specialization_proposal:
                proposals.append(specialization_proposal)

        # ------------------------------------------------------------------
        # STRATEGY 4: Composition (structural consolidation)
        # Propose when: allow_composition AND composable patterns AND
        #   (prior utility is poor OR prior mutation harmed) AND not in churn
        # ------------------------------------------------------------------
        composition_required = NecessitySignal.COMPOSITION_REQUIREMENT in signals
        if context.objective.allow_composition and self._detect_composable_patterns(graph):
            prior_utility_low = context.last_observed_utility < 0.62
            should_compose = prior_utility_low or context.prior_mutation_harmed or composition_required
            if should_compose and context.cycles_since_mutation > 3:
                composition_proposal = self._create_composition_proposal(graph, context)
                if composition_proposal:
                    proposals.append(composition_proposal)

        return proposals

    def _create_expansion_proposal(self, graph: StructuralGraph, context: GenerationContext) -> Optional[MutationProposal]:
        """Propose adding new computational units to handle objective task."""
        if not context.available_unit_templates:
            unit_id = UnitID(f"gen_unit_{self._proposal_counter}_{len(graph.units)}")
            new_unit = ComputationalUnit(
                unit_id=unit_id,
                name=f"GeneratedUnit_{len(graph.units)}",
                structure=StructureDimension.PRIMITIVE,
                visibility=VisibilityDimension.INSPECTABLE,
                lifecycle=LifecycleDimension.BASE
            )
        else:
            template = context.available_unit_templates[0]
            new_unit = self._clone_unit_template(template, f"gen_{len(graph.units)}")

        ops = [IROperation(OperationType.ADD_UNIT, {"unit": new_unit})]

        if len(graph.units) > 0 and context.current_edge_count < context.objective.max_edges:
            existing_unit_id = list(graph.units.keys())[0]
            ops.append(IROperation(OperationType.CONNECT_UNITS, {
                "source": UnitID(existing_unit_id),
                "target": new_unit.unit_id,
                "edge_type": EdgeType.DATA
            }))
        elif len(graph.units) == 0:
            pass

        if context.current_edge_count >= context.objective.max_edges and len(graph.units) > 0:
            return None

        return MutationProposal(
            proposal_id=f"gen_prop_{self._proposal_counter}_{len(graph.units)}",
            target_graph_id=str(graph.graph_id.value),
            candidate_operations=ops,
            rationale=f"Expand computation for: {context.objective.task_description}",
            expected_utility=0.8,
            estimated_cost=1.0,
            risk_assessment="LOW"
        )

    def _create_wiring_proposal(self, graph: StructuralGraph, context: GenerationContext) -> Optional[MutationProposal]:
        """Propose connecting disconnected subgraphs or isolated units."""
        if len(graph.units) < 2:
            return None

        unit_ids = list(graph.units.keys())
        source = unit_ids[-1]
        target = unit_ids[0]

        ops = [IROperation(OperationType.CONNECT_UNITS, {
            "source": UnitID(source),
            "target": UnitID(target),
            "edge_type": EdgeType.DATA
        })]

        return MutationProposal(
            proposal_id=f"gen_wire_{self._proposal_counter}_{len(graph.units)}",
            target_graph_id=str(graph.graph_id.value),
            candidate_operations=ops,
            rationale=f"Wire isolated computation for: {context.objective.task_description}",
            expected_utility=0.6,
            estimated_cost=0.3,
            risk_assessment="LOW"
        )

    def _create_specialization_proposal(self, graph: StructuralGraph, context: GenerationContext) -> Optional[MutationProposal]:
        """Propose specializing an existing base unit."""
        unit_ids = list(graph.units.keys())
        if not unit_ids:
            return None

        target_unit_id = UnitID(unit_ids[0])
        ops = [IROperation(OperationType.SPECIALIZE_UNIT, {
            "unit_id": target_unit_id,
            "specialization_context": context.objective.task_description
        })]

        return MutationProposal(
            proposal_id=f"gen_spec_{self._proposal_counter}_{len(graph.units)}",
            target_graph_id=str(graph.graph_id.value),
            candidate_operations=ops,
            rationale=f"Specialize unit for: {context.objective.task_description}",
            expected_utility=0.5,
            estimated_cost=0.5,
            risk_assessment="MEDIUM"
        )

    def _create_composition_proposal(self, graph: StructuralGraph, context: GenerationContext) -> Optional[MutationProposal]:
        """Propose composing multiple units into a composite."""
        if len(graph.units) < 2:
            return None

        if context.current_edge_count >= context.objective.max_edges:
            return None

        unit_ids = [UnitID(uid) for uid in list(graph.units.keys())[:2]]
        ops = [IROperation(OperationType.COMPOSE_UNITS, {
            "units": unit_ids,
            "composite_name": f"ComposedUnit_{len(graph.units)}"
        })]

        return MutationProposal(
            proposal_id=f"gen_comp_{self._proposal_counter}_{len(graph.units)}",
            target_graph_id=str(graph.graph_id.value),
            candidate_operations=ops,
            rationale=f"Compose units for: {context.objective.task_description}",
            expected_utility=0.7,
            estimated_cost=1.5,
            risk_assessment="MEDIUM"
        )

    def _detect_composable_patterns(self, graph: StructuralGraph) -> bool:
        """Detect if graph has patterns suitable for composition."""
        return len(graph.units) >= 2

    def _clone_unit_template(self, template: ComputationalUnit, suffix: str) -> ComputationalUnit:
        """Clone a unit template with a new ID."""
        new_id = UnitID(f"{template.unit_id.value}_{suffix}")
        return ComputationalUnit(
            unit_id=new_id,
            name=f"{template.name}_{suffix}",
            structure=template.structure,
            visibility=template.visibility,
            lifecycle=template.lifecycle,
            contract=template.contract,
            mutation_contract=template.mutation_contract,
            constraints=template.constraints,
            metadata=dict(template.metadata),
            sub_units=list(template.sub_units)
        )
