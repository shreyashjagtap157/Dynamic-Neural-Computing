"""Canonical top-level DNC system composition.

This module owns the supported end-to-end lifecycle. Tests, benchmarks, and
applications must import it instead of importing executable phase scripts.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional, Protocol

from dnc.assurance.calibration import AssuranceCalibrationRegistry, CalibrationKey
from dnc.assurance.contracts import VerifierClaim
from dnc.assurance.outcomes import OutcomeLabel, OutcomeLabelStore
from dnc.assurance.policy import RiskPolicyRegistry, issue_confidence
from dnc.assurance.registry import CascadePolicy, CascadeResult, VerifierCascade, VerifierRegistry
from dnc.capabilities.broker import CapabilityBroker
from dnc.capabilities.contracts import CapabilityRequirement, CapabilitySelection
from dnc.capabilities.registry import CapabilityRegistry
from dnc.cognition.migration import export_cognitive_state, import_cognitive_state
from dnc.cognition.contracts import ConfidenceEstimate, RiskClass
from dnc.cognition.state import CognitiveState
from dnc.control.contracts import ControllerContext, ControllerDecision
from dnc.control.controller import SemanticCognitiveController
from dnc.dcc.assessment_engine import Assessment, AssessmentEngine, ExecutionResult
from dnc.dcc.computation_generator import (
    ComputationGenerator,
    GenerationContext,
    GenerationObjective,
    NecessitySignal,
)
from dnc.dcc.dcc_contracts import MutationProposal
from dnc.dcc.learning_engine import DeterministicLearningPolicy, PredictionTracker
from dnc.dcc.structural_controller import EvaluationContext, EvaluationCriteria, StructuralController
from dnc.execution.snapshot import ReferenceSnapshotManager, Snapshot
from dnc.ir.graph import StructuralGraph
from dnc.ir.identity import GraphID
from dnc.ir.validator import DNCIRValidator
from dnc.halting.contracts import HaltingContext, InferenceDecision
from dnc.halting.policy import AdaptiveHaltingPolicy
from dnc.memory import GovernedMemory, MemoryKind, SkillRegistry
from dnc.policy_learning import (
    LearnedPolicyRegistry, LearnedPolicyVersion, PolicyDecision,
    TabularShadowPredictor, select_action,
)
from dnc.semantics.contracts import SemanticGraphCandidate
from dnc.semantics.synthesis import SemanticSynthesizer, SynthesisRequest
from dnc.semantics.validation import SemanticValidation, validate_semantic_candidate
from dnc.repair.contracts import RepairOutcome
from dnc.repair.engine import execute_localized_repair
from dnc.mutation.engine import MutationEngine
from dnc.neural import AdaptiveDepthModel, AdaptiveDepthResult, NeuralExitEvidence, issue_exit_evidence
from dnc.observability.provenance import ProvenanceLog
from dnc.projection.projector import StructuralProjector
from dnc.transaction.manager import TransactionManager
from dnc.kernel.errors import DNCCalibrationError, DNCCapabilityError


class ExecutionCore(Protocol):
    """Backend contract consumed by the canonical DNC lifecycle."""

    def execute(self, executable_graph: object) -> ExecutionResult: ...


class ReferenceExecutionCore:
    """Deterministic in-process backend used until a real backend is injected."""

    def __init__(self, utility: float = 0.75) -> None:
        self.utility = utility
        self.execution_count = 0

    def execute(self, executable_graph: object) -> ExecutionResult:
        self.execution_count += 1
        dag = executable_graph[0] if isinstance(executable_graph, tuple) else executable_graph
        nodes = getattr(dag, "nodes", {})
        edges = getattr(dag, "edges", [])
        return ExecutionResult(
            graph_id=str(getattr(getattr(dag, "graph_id", None), "value", "dnc_system")),
            graph_version=str(getattr(dag, "source_version", "v1.0.0-0")),
            execution_time_ms=0.0,
            output=f"reference_result_{self.execution_count}",
            metrics={"utility": self.utility},
            units_executed=len(nodes),
            edges_traversed=len(edges),
            success=True,
        )


@dataclass(frozen=True)
class DNCSystemConfig:
    enable_learning: bool = True
    enable_mutation: bool = True
    enable_provenance: bool = True
    production_mode: bool = False
    allow_synthetic_execution: bool = False
    enable_adaptive_halting: bool = False


@dataclass(frozen=True)
class SystemStateSnapshot:
    cycle: int
    graph_id: str
    graph_version: str
    unit_count: int
    edge_count: int
    proposals_generated: int
    proposals_authorized: int
    learning_cycles: int
    adaptation_knowledge_cycles: int
    cumulative_improvement: float
    transaction_commits: int
    transaction_rollbacks: int


class DNCSystem:
    """Canonical, configurable DNC control and execution lifecycle."""

    def __init__(
        self,
        execution_id: str = "dnc-execution",
        *,
        config: Optional[DNCSystemConfig] = None,
        execution_core: Optional[ExecutionCore] = None,
        initial_graph: Optional[StructuralGraph] = None,
        cognitive_state: Optional[CognitiveState] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        verifier_registry: Optional[VerifierRegistry] = None,
        assurance_calibrations: Optional[AssuranceCalibrationRegistry] = None,
        outcome_labels: Optional[OutcomeLabelStore] = None,
        risk_policies: Optional[RiskPolicyRegistry] = None,
        inference_policy: Optional[AdaptiveHaltingPolicy] = None,
        semantic_controller: Optional[SemanticCognitiveController] = None,
        governed_memory: Optional[GovernedMemory] = None,
        skill_registry: Optional[SkillRegistry] = None,
        learned_policy_registry: Optional[LearnedPolicyRegistry] = None,
    ) -> None:
        self.execution_id = execution_id
        self.config = config or DNCSystemConfig()
        self.graph = copy.deepcopy(initial_graph) if initial_graph is not None else StructuralGraph(
            GraphID(f"dnc:{execution_id}")
        )
        validation = DNCIRValidator().validate_graph(self.graph)
        if not validation.is_valid:
            errors = ", ".join(error.code for error in validation.errors)
            raise ValueError(f"initial graph violates DNC-IR invariants: {errors}")
        self.provenance_log = (
            ProvenanceLog(execution_id=execution_id) if self.config.enable_provenance else None
        )
        self.mutation_engine = MutationEngine()
        self.transaction_manager = TransactionManager(
            mutation_engine=self.mutation_engine,
            provenance_log=self.provenance_log,
        )
        self.projector = StructuralProjector()
        self.snapshot_manager = ReferenceSnapshotManager()
        if self.config.production_mode and execution_core is None:
            raise ValueError("production mode requires an explicit non-synthetic execution core")
        selected_core = execution_core or ReferenceExecutionCore()
        if (
            self.config.production_mode
            and isinstance(selected_core, ReferenceExecutionCore)
            and not self.config.allow_synthetic_execution
        ):
            raise ValueError("synthetic reference execution is disabled in production mode")
        self.execution_core = selected_core
        self.cognitive_state = cognitive_state
        self.capability_registry = capability_registry or CapabilityRegistry()
        self.verifier_registry = verifier_registry or VerifierRegistry()
        self.assurance_calibrations = assurance_calibrations or AssuranceCalibrationRegistry()
        self.capability_registry.add_change_listener(self.assurance_calibrations.handle_model_change)
        self.outcome_labels = outcome_labels or OutcomeLabelStore()
        self.risk_policies = risk_policies or RiskPolicyRegistry()
        self.inference_policy = inference_policy
        self.semantic_controller = semantic_controller or SemanticCognitiveController()
        self.governed_memory = governed_memory or GovernedMemory()
        self.skill_registry = skill_registry or SkillRegistry()
        self.learned_policy_registry = learned_policy_registry or LearnedPolicyRegistry()
        self.assessment_engine = AssessmentEngine()
        self.generator = ComputationGenerator()
        self.controller = StructuralController()
        self.learning = DeterministicLearningPolicy()
        self.tracker = PredictionTracker()

        self._cycle_count = 0
        self._proposals_generated = 0
        self._proposals_authorized = 0
        self._transaction_commits = 0
        self._transaction_rollbacks = 0
        self._cycles_since_mutation = 999
        self._recent_mutation_count = 0
        self._prior_mutation_harmed = False
        self._last_observed_utility = 0.75

    def snapshot(self) -> SystemStateSnapshot:
        knowledge = self.learning.get_knowledge()
        return SystemStateSnapshot(
            cycle=self._cycle_count,
            graph_id=self.graph.graph_id.value,
            graph_version=str(self.graph.version),
            unit_count=len(self.graph.units),
            edge_count=len(self.graph.edges),
            proposals_generated=self._proposals_generated,
            proposals_authorized=self._proposals_authorized,
            learning_cycles=knowledge.cycle_count if self.config.enable_learning else 0,
            adaptation_knowledge_cycles=knowledge.cycle_count if self.config.enable_learning else 0,
            cumulative_improvement=(
                knowledge.cumulative_improvement if self.config.enable_learning else 0.0
            ),
            transaction_commits=self._transaction_commits,
            transaction_rollbacks=self._transaction_rollbacks,
        )

    def capture_execution_snapshot(self, snapshot_id: str) -> Snapshot:
        """Capture integrated graph, cognition, capabilities, and lifecycle state."""

        return self.snapshot_manager.capture_graph(
            self.graph,
            snapshot_id=snapshot_id,
            source_state_id=f"{self.execution_id}:{self.graph.version}",
            runtime_state={
                "cognitive_state_hash": (
                    self.cognitive_state.canonical_hash() if self.cognitive_state is not None else None
                ),
                "cognitive_state": (
                    export_cognitive_state(self.cognitive_state)
                    if self.cognitive_state is not None
                    else None
                ),
                "capability_registry": self.capability_registry.snapshot_state(),
                "governed_memory": self.governed_memory.snapshot(),
                "skill_registry": self.skill_registry.snapshot(),
                "learned_policy_registry": self.learned_policy_registry.snapshot(),
                "cycle_count": self._cycle_count,
                "proposals_generated": self._proposals_generated,
                "proposals_authorized": self._proposals_authorized,
                "transaction_commits": self._transaction_commits,
                "transaction_rollbacks": self._transaction_rollbacks,
                "cycles_since_mutation": self._cycles_since_mutation,
                "recent_mutation_count": self._recent_mutation_count,
                "prior_mutation_harmed": self._prior_mutation_harmed,
                "last_observed_utility": self._last_observed_utility,
            },
        )

    def set_cognitive_state(self, state: CognitiveState | None) -> None:
        """Attach additive Phase 3 cognitive state to the canonical system."""

        self.cognitive_state = state

    def update_cognitive_state(self, state: CognitiveState) -> None:
        """Replace the additive cognitive state without mutating the DNC-IR graph."""

        if self.cognitive_state is not None and state.task.task_id != self.cognitive_state.task.task_id:
            raise ValueError("updated cognitive state MUST belong to the active task")
        self.cognitive_state = state

    def select_capability(
        self, requirement: CapabilityRequirement, *, now_ns: int | None = None
    ) -> CapabilitySelection:
        """Select an available Phase 4 capability through the canonical system."""

        return CapabilityBroker(self.capability_registry).match(requirement, now_ns=now_ns)

    def verify_claim(
        self, claim: VerifierClaim, policy: CascadePolicy = CascadePolicy()
    ) -> CascadeResult:
        """Run a scoped Phase 5 verifier cascade through the canonical system."""

        return VerifierCascade(self.verifier_registry).run(claim, policy)

    def record_outcome_label(self, label: OutcomeLabel) -> None:
        """Append immediate or delayed Phase 5 outcome evidence."""

        self.outcome_labels.ingest(label)

    def issue_calibrated_confidence(
        self,
        estimate_id: str,
        target_id: str,
        target_type: str,
        probability: float,
        key: CalibrationKey,
        *,
        semantic_cluster_count: int = 0,
        correlation_groups: tuple[str, ...] = (),
    ) -> ConfidenceEstimate:
        """Issue confidence only through a matching promoted calibration artifact."""

        capability_fingerprints = {
            card.fingerprint for card in self.capability_registry.available() if card.fingerprint
        }
        if key.capability_fingerprint not in capability_fingerprints:
            raise DNCCalibrationError(
                "calibration capability fingerprint is not currently available"
            )
        active_verifier_fingerprints = {
            descriptor.fingerprint
            for descriptor in self.verifier_registry.active_descriptors()
            if descriptor.fingerprint
        }
        missing_verifiers = set(key.verifier_fingerprints) - active_verifier_fingerprints
        if missing_verifiers:
            raise DNCCalibrationError(
                f"calibration verifier fingerprints are unavailable: {sorted(missing_verifiers)}"
            )
        artifact = self.assurance_calibrations.require_applicable(key)
        return issue_confidence(
            estimate_id,
            target_id,
            target_type,
            probability,
            artifact,
            semantic_cluster_count=semantic_cluster_count,
            correlation_groups=correlation_groups,
        )

    def decide_inference(self, context: HaltingContext) -> InferenceDecision:
        """Run the Phase 6 policy, retaining fixed-attempt rollback by default."""

        if self.inference_policy is None:
            raise DNCCapabilityError("no inference halting policy is configured")
        if self.config.enable_adaptive_halting:
            return self.inference_policy.decide(context)
        return self.inference_policy.fallback.decide(context)

    def select_cognitive_action(
        self, context: ControllerContext, *, authorize_lifecycle: bool = True
    ) -> ControllerDecision:
        """Select and optionally lifecycle-authorize one Phase 7 cognitive action."""

        if self.cognitive_state is not None and context.task_id != self.cognitive_state.task.task_id:
            raise ValueError("controller context MUST belong to the active cognitive task")
        decision = self.semantic_controller.select(context)
        if authorize_lifecycle and decision.selected is not None:
            if self.cognitive_state is None:
                raise ValueError("lifecycle authorization requires active cognitive state")
            self.cognitive_state = self.semantic_controller.authorize_lifecycle(
                self.cognitive_state, decision
            )
        return decision

    def synthesize_semantic_graph(
        self, request: SynthesisRequest
    ) -> tuple[SemanticGraphCandidate, ...]:
        """Generate Phase 8 semantic DNC-IR candidates without mutating the graph."""

        if self.cognitive_state is None or request.state != self.cognitive_state:
            raise ValueError("synthesis request MUST use the active cognitive state")
        candidates = SemanticSynthesizer(self.capability_registry).synthesize(request)
        return tuple(
            candidate
            for candidate in candidates
            if all(unit.unit_id.value not in self.graph.units for unit in candidate.units)
        )

    def apply_semantic_candidate(
        self,
        candidate: SemanticGraphCandidate,
        *,
        available_budget: float,
        granted_permissions: frozenset[str],
        available_isolation_grade: str,
    ) -> tuple[bool, SemanticValidation]:
        """Validate and transactionally commit one semantic graph candidate."""

        if self.cognitive_state is None:
            raise ValueError("semantic candidate application requires cognitive state")
        existing_units = tuple(
            unit.unit_id.value
            for unit in candidate.units
            if unit.unit_id.value in self.graph.units
        )
        if existing_units:
            return False, SemanticValidation(
                False,
                tuple(f"SEMANTIC_TRANSPOSITION:{unit_id}" for unit_id in existing_units),
            )
        validation = validate_semantic_candidate(
            candidate,
            self.capability_registry,
            task_id=self.cognitive_state.task.task_id,
            tenant_id=self.cognitive_state.task.tenant_id,
            available_budget=available_budget,
            granted_permissions=granted_permissions,
            available_isolation_grade=available_isolation_grade,
        )
        if not validation.valid:
            return False, validation
        committed, _ = self.transaction_manager.execute_transaction(
            self.graph, list(candidate.operations), base_version=self.graph.version
        )
        if committed:
            self._transaction_commits += 1
        else:
            self._transaction_rollbacks += 1
        return committed, validation

    def repair_cognitive_state(self, root_item_id, recompute, verify) -> RepairOutcome:
        """Run Phase 9 localized repair within a snapshot rollback boundary."""

        return execute_localized_repair(self, root_item_id, recompute, verify)

    def retrieve_memory(self, kind: MemoryKind, **criteria):
        """Retrieve Phase 10 memory through tenant, freshness, and trust policy."""

        return self.governed_memory.store(kind).retrieve(**criteria)

    def select_learned_action(
        self,
        *,
        policy: LearnedPolicyVersion,
        predictor: TabularShadowPredictor,
        risk_class: RiskClass,
        context_key: str,
        candidate_ids: tuple[str, ...],
        deterministic_action_id: str,
        safe_action_ids: frozenset[str],
        exploration_index: int = 0,
    ) -> PolicyDecision:
        """Use Phase 11 policy only when its independent low-risk gate permits it."""

        return select_action(
            policy=policy,
            predictor=predictor,
            context_key=context_key,
            candidate_ids=candidate_ids,
            deterministic_action_id=deterministic_action_id,
            safe_action_ids=safe_action_ids,
            canary_allowed=self.learned_policy_registry.can_execute(
                policy.fingerprint, risk_class
            ),
            exploration_index=exploration_index,
        )

    def execute_adaptive_neural(
        self,
        *,
        capability_id: str,
        model: AdaptiveDepthModel,
        value,
        task_id: str,
        domain: str,
        risk_class: RiskClass,
        force_full_depth: bool = False,
    ) -> tuple[AdaptiveDepthResult, NeuralExitEvidence]:
        """Execute Phase 12 adaptive depth through an active model-matched capability."""

        available = {card.capability_id: card for card in self.capability_registry.available()}
        card = available.get(capability_id)
        if card is None:
            raise DNCCapabilityError("adaptive neural capability is unavailable")
        if card.model_id != model.model_fingerprint:
            raise DNCCapabilityError("adaptive neural capability model fingerprint mismatch")
        if not card.metadata.get("adaptive_neural", False):
            raise DNCCapabilityError("capability is not qualified for adaptive neural execution")
        risk_rank = {
            RiskClass.LOW: 0, RiskClass.MEDIUM: 1, RiskClass.HIGH: 2, RiskClass.CRITICAL: 3
        }
        if risk_rank[risk_class] > risk_rank[card.risk_limit]:
            raise DNCCapabilityError("adaptive neural capability risk limit exceeded")
        if domain not in card.calibration_domains:
            raise DNCCalibrationError("adaptive neural capability is not calibrated for domain")
        result = model.execute(
            value,
            domain=domain,
            risk_class=risk_class,
            force_full_depth=force_full_depth,
        )
        evidence = issue_exit_evidence(
            result,
            capability_id=capability_id,
            model_fingerprint=model.model_fingerprint,
            task_id=task_id,
        )
        return result, evidence

    def restore_execution_snapshot(self, snapshot: Snapshot) -> None:
        """Atomically restore integrated process-local state from a snapshot."""

        restored_graph = self.snapshot_manager.restore_graph(snapshot)
        runtime_state = snapshot.runtime_state or {}
        cognitive_payload = runtime_state.get("cognitive_state")
        restored_cognitive_state = (
            import_cognitive_state(cognitive_payload) if cognitive_payload is not None else None
        )
        expected_cognitive_hash = runtime_state.get("cognitive_state_hash")
        restored_cognitive_hash = (
            restored_cognitive_state.canonical_hash()
            if restored_cognitive_state is not None
            else None
        )
        if expected_cognitive_hash != restored_cognitive_hash:
            raise ValueError("snapshot cognitive state hash mismatch")

        restored_registry = CapabilityRegistry()
        registry_state = runtime_state.get("capability_registry")
        if registry_state is not None:
            restored_registry.restore_state(registry_state)
        restored_memory = GovernedMemory()
        memory_state = runtime_state.get("governed_memory")
        if memory_state is not None:
            restored_memory.restore(memory_state)
        restored_skills = SkillRegistry()
        skill_state = runtime_state.get("skill_registry")
        if skill_state is not None:
            restored_skills.restore(skill_state)
        restored_learned_policies = LearnedPolicyRegistry()
        learned_policy_state = runtime_state.get("learned_policy_registry")
        if learned_policy_state is not None:
            restored_learned_policies.restore(learned_policy_state)

        restored_counters = {
            "cycle_count": int(runtime_state.get("cycle_count", self._cycle_count)),
            "proposals_generated": int(
                runtime_state.get("proposals_generated", self._proposals_generated)
            ),
            "proposals_authorized": int(
                runtime_state.get("proposals_authorized", self._proposals_authorized)
            ),
            "transaction_commits": int(
                runtime_state.get("transaction_commits", self._transaction_commits)
            ),
            "transaction_rollbacks": int(
                runtime_state.get("transaction_rollbacks", self._transaction_rollbacks)
            ),
            "cycles_since_mutation": int(
                runtime_state.get("cycles_since_mutation", self._cycles_since_mutation)
            ),
            "recent_mutation_count": int(
                runtime_state.get("recent_mutation_count", self._recent_mutation_count)
            ),
            "prior_mutation_harmed": bool(
                runtime_state.get("prior_mutation_harmed", self._prior_mutation_harmed)
            ),
            "last_observed_utility": float(
                runtime_state.get("last_observed_utility", self._last_observed_utility)
            ),
        }

        self.graph = restored_graph
        self.cognitive_state = restored_cognitive_state
        if registry_state is not None:
            self.capability_registry.restore_state(restored_registry.snapshot_state())
        if memory_state is not None:
            self.governed_memory.restore(restored_memory.snapshot())
        if skill_state is not None:
            self.skill_registry.restore(restored_skills.snapshot())
        if learned_policy_state is not None:
            self.learned_policy_registry.restore(restored_learned_policies.snapshot())
        self._cycle_count = restored_counters["cycle_count"]
        self._proposals_generated = restored_counters["proposals_generated"]
        self._proposals_authorized = restored_counters["proposals_authorized"]
        self._transaction_commits = restored_counters["transaction_commits"]
        self._transaction_rollbacks = restored_counters["transaction_rollbacks"]
        self._cycles_since_mutation = restored_counters["cycles_since_mutation"]
        self._recent_mutation_count = restored_counters["recent_mutation_count"]
        self._prior_mutation_harmed = restored_counters["prior_mutation_harmed"]
        self._last_observed_utility = restored_counters["last_observed_utility"]

    def run_cycle(
        self,
        objective: GenerationObjective,
        prior_assessment: Optional[Assessment] = None,
        necessity_signals: frozenset[NecessitySignal] = frozenset(),
    ) -> tuple[bool, Optional[Assessment], Optional[MutationProposal]]:
        """Run GENERATE→AUTHORIZE→TRANSACT→EXECUTE→ASSESS→LEARN once."""
        self._cycle_count += 1
        graph_before_version = str(self.graph.version)
        last_utility = (
            prior_assessment.post_execution_utility_measured
            if prior_assessment is not None
            else self._last_observed_utility
        )
        proposals = self.generator.generate_proposals(
            self.graph,
            GenerationContext(
                objective=objective,
                graph_id=self.graph.graph_id,
                current_unit_count=len(self.graph.units),
                current_edge_count=len(self.graph.edges),
                last_observed_utility=last_utility,
                recent_mutation_count=self._recent_mutation_count,
                cycles_since_mutation=self._cycles_since_mutation,
                prior_mutation_harmed=self._prior_mutation_harmed,
                necessity_signals=necessity_signals,
            ),
        )
        self._proposals_generated += len(proposals)
        if not proposals:
            self._cycles_since_mutation += 1
            return False, None, None

        context = EvaluationContext(
            current_graph=self.graph,
            active_objectives=[objective.task_description],
            available_budget=objective.cost_budget,
            risk_tolerance="HIGH",
            criteria=EvaluationCriteria(
                min_utility=0.3,
                max_units=objective.max_units,
                max_edges=objective.max_edges,
            ),
            stability_baseline_utility=self._last_observed_utility,
            cycles_since_mutation=self._cycles_since_mutation,
            recent_mutation_count=self._recent_mutation_count,
        )
        evaluations = self.controller.evaluate_proposals(proposals, context)
        decision = self.controller.authorize_top_scoring(evaluations, context)
        if decision is None or not decision.authorized:
            self._cycles_since_mutation += 1
            return False, None, None

        self._proposals_authorized += 1
        proposal = next(
            (evaluation.proposal for evaluation in evaluations if evaluation.decision.value == "AUTHORIZE"),
            proposals[0],
        )
        prediction = self.tracker.record_prediction(proposal, decision)

        if self.config.enable_mutation:
            success, _ = self.transaction_manager.execute_transaction(
                self.graph, proposal.candidate_operations
            )
            if not success:
                self._transaction_rollbacks += 1
                self._cycles_since_mutation += 1
                return False, None, proposal
            self._transaction_commits += 1
            self._cycles_since_mutation = 0
            self._recent_mutation_count += 1
        else:
            # A true mutation ablation evaluates the existing graph without
            # changing graph structure, version, or transaction counters.
            self._cycles_since_mutation += 1

        execution = self.execution_core.execute(self.projector.project(self.graph))
        assessment = self.assessment_engine.assess_execution(
            execution,
            proposal,
            graph_before_version,
            str(self.graph.version),
            baseline_utility=last_utility,
        )
        if self.config.enable_learning and prior_assessment is not None:
            self.learning.process(prediction, assessment)

        self._prior_mutation_harmed = assessment.improvement_delta < -0.02
        self._last_observed_utility = assessment.post_execution_utility_measured
        return True, assessment, proposal


# One-release compatibility alias. New code should import DNCSystem.
DNCCanonicalSystem = DNCSystem
ConformantMockExecutionCore = ReferenceExecutionCore
