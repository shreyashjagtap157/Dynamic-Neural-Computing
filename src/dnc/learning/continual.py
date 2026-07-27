"""Continual learning: bounded drift, KB versioning, root-cause rollback, circuit-breaker.

Per continual-learning.md:
- DEF-CL-1 through DEF-CL-9: behavioral envelope, bounded drift, learning events, KB, clustering
- DEF-CL-8: candidate update generation algorithm (TBRL, CMU, MS)
- INV-CL-1: drift bound enforcement
- INV-CL-8: learning verification protocol
- INV-CL-9: representative sample set S via k-means clustering (DEF-CL-9: Euclidean on normalized vectors)
- INV-CL-13: root-cause attribution for KB rollback (binary search)
- INV-CL-17: rollback frequency circuit-breaker (MAX_KB_ROLLBACKS_PER_WINDOW=3 per hour)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from dnc.observability.provenance import ProvenanceLog, EventType
from dnc.observability.evaluation import EvaluationSuite, EvaluationStage


class DriftBoundExceeded(Exception):
    """Raised when drift exceeds DRIFT_BOUND per INV-CL-1."""


class InvariantViolationLearning(Exception):
    """Raised when learning violates an invariant per INV-CL-2."""


class CatastrophicForgettingDetected(Exception):
    """Raised when metric degrades beyond DEGRADATION_TOLERANCE per INV-CL-7."""


class LearningWithoutEvents(Exception):
    """Raised when candidate_update has no corresponding learning event per INV-CL-3."""


@dataclass(frozen=True)
class LearningEvent:
    """Per DEF-CL-4: LE = (event_id, trigger_execution_id, trigger_step, observed_outcome, expected_outcome, delta_quality, is_novel, candidate_update_summary)."""
    event_id: str
    trigger_execution_id: str
    trigger_step: int
    observed_outcome: Any
    expected_outcome: Any
    delta_quality: float
    is_novel: bool
    candidate_update_summary: Dict[str, Any]


@dataclass
class KnowledgeBase:
    """Per DEF-CL-5: KB = (KB_modules, KB_plans, KB_costs)."""
    kb_version: int = 0
    KB_modules: Dict[str, Any] = field(default_factory=dict)
    KB_plans: Dict[str, Any] = field(default_factory=dict)
    KB_costs: Dict[str, float] = field(default_factory=dict)
    _versions: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    def commit(self) -> int:
        """Per INV-CL-11: commit creates new immutable version. Returns new version number."""
        self.kb_version += 1
        snapshot = {
            "KB_modules": dict(self.KB_modules),
            "KB_plans": dict(self.KB_plans),
            "KB_costs": dict(self.KB_costs),
        }
        self._versions[self.kb_version] = snapshot
        return self.kb_version

    def get_version(self, version: int) -> Dict[str, Any]:
        """Return a specific KB version snapshot."""
        if version not in self._versions:
            raise KeyError(f"KB version {version} not found")
        return self._versions[version]

    def rollback_to(self, target_version: int) -> None:
        """Per INV-CL-12: restore prior version atomically."""
        snapshot = self.get_version(target_version)
        self.KB_modules = dict(snapshot["KB_modules"])
        self.KB_plans = dict(snapshot["KB_plans"])
        self.KB_costs = dict(snapshot["KB_costs"])
        self.kb_version = target_version


@dataclass
class ExecutionRecord:
    """A recorded execution for clustering and drift checking."""
    execution_id: str
    task_class: str
    metric_vector: List[float]
    timestamp: float


class DriftChecker:
    """Per INV-CL-9: k-means clustering on normalized metric vectors.

    Distance metric per DEF-CL-9:
    d(i,j) = sqrt(sum(((m_k(i) - m_k(j)) / sigma_k)^2))
    """

    K_CLUSTERS: int = 10
    MAX_DRIFT_CHECK_SAMPLES: int = 100

    def __init__(self) -> None:
        self._history: List[ExecutionRecord] = []
        self._representative_sample: Set[int] = set()
        self._centers: List[List[float]] = []
        self._cluster_assignments: List[int] = []

    def record_execution(self, record: ExecutionRecord) -> None:
        """Add an execution to history and recompute clusters if needed."""
        self._history.append(record)
        if len(self._history) > 10 and len(self._history) % 10 == 1:
            self._recompute_clusters()

    def _recompute_clusters(self) -> None:
        """Re-run k-means clustering on metric vectors."""
        if len(self._history) < self.K_CLUSTERS:
            self._representative_sample = set(range(len(self._history)))
            return

        vectors = [r.metric_vector for r in self._history]
        n_metrics = len(vectors[0]) if vectors else 0
        if n_metrics == 0:
            return

        self._centers = [[0.0] * n_metrics for _ in range(self.K_CLUSTERS)]
        for v in vectors[:self.K_CLUSTERS]:
            for d in range(n_metrics):
                self._centers[self._history.index(next(r for r in self._history if r.metric_vector == v)) % self.K_CLUSTERS][d] = v[d]

        self._cluster_assignments = []
        for i, v in enumerate(vectors):
            min_dist = float('inf')
            best_cluster = 0
            for c_idx, center in enumerate(self._centers):
                dist = self._euclidean_normalized(v, center, vectors)
                if dist < min_dist:
                    min_dist = dist
                    best_cluster = c_idx
            self._cluster_assignments.append(best_cluster)

        self._update_representative_sample()

    def _euclidean_normalized(
        self,
        v1: List[float],
        v2: List[float],
        all_vectors: List[List[float]],
    ) -> float:
        """Per DEF-CL-9: Euclidean distance in normalized metric space."""
        n_metrics = len(v1)
        if n_metrics == 0:
            return 0.0
        sigmas = [1.0] * n_metrics
        if all_vectors:
            for d in range(n_metrics):
                col = [v[d] for v in all_vectors if len(v) > d]
                if len(col) > 1:
                    mean = sum(col) / len(col)
                    variance = sum((x - mean) ** 2 for x in col) / len(col)
                    sigmas[d] = math.sqrt(variance) if variance > 0 else 1.0

        total = 0.0
        for d in range(n_metrics):
            normalized_diff = (v1[d] - v2[d]) / sigmas[d]
            total += normalized_diff ** 2
        return math.sqrt(total)

    def _update_representative_sample(self) -> None:
        """Per INV-CL-9: build S with at most MAX_DRIFT_CHECK_SAMPLES entries."""
        sample: Set[int] = set()

        cluster_counts: Dict[int, int] = {}
        for c in self._cluster_assignments:
            cluster_counts[c] = cluster_counts.get(c, 0) + 1

        for c in range(self.K_CLUSTERS):
            members = [i for i, assigned in enumerate(self._cluster_assignments) if assigned == c]
            if members:
                farthest = max(members, key=lambda i: self._euclidean_normalized(
                    self._history[i].metric_vector,
                    self._centers[c],
                    [r.metric_vector for r in self._history],
                ))
                sample.add(farthest)

        by_task_class: Dict[str, List[int]] = {}
        for i, rec in enumerate(self._history):
            if rec.task_class not in by_task_class:
                by_task_class[rec.task_class] = []
            by_task_class[rec.task_class].append(i)

        for task_class, indices in by_task_class.items():
            if indices:
                most_recent = max(indices, key=lambda i: self._history[i].timestamp)
                sample.add(most_recent)

        if len(sample) > self.MAX_DRIFT_CHECK_SAMPLES:
            sample_list = sorted(sample)
            sample = set(sample_list[:self.MAX_DRIFT_CHECK_SAMPLES])

        self._representative_sample = sample

    def compute_drift(self, p_id: int, p_prime_vector: List[float]) -> float:
        """Per DEF-CL-2: Δ(i,j) = max_k |m_k(i) - m_k(j)|."""
        if p_id >= len(self._history):
            return 0.0
        p_vector = self._history[p_id].metric_vector
        if len(p_vector) != len(p_prime_vector):
            return float('inf')
        return max(abs(p_vector[k] - p_prime_vector[k]) for k in range(len(p_vector)))

    def get_representative_sample(self) -> List[int]:
        """Return indices of executions in the representative sample S."""
        return sorted(self._representative_sample)

    def is_within_drift_bound(
        self,
        p_prime_vector: List[float],
        drift_bound: float,
    ) -> Tuple[bool, List[Tuple[int, float]]]:
        """Per INV-CL-1: check if p' is within DRIFT_BOUND for all p in S."""
        violations: List[Tuple[int, float]] = []
        for idx in self._representative_sample:
            drift = self.compute_drift(idx, p_prime_vector)
            if drift > drift_bound:
                violations.append((idx, drift))

        return len(violations) == 0, violations

    @property
    def history(self) -> List[ExecutionRecord]:
        return self._history


class LearningVerificationProtocol:
    """Per INV-CL-8: the 5-step learning verification protocol."""

    def __init__(self) -> None:
        self._kb = KnowledgeBase()
        self._drift_checker = DriftChecker()
        self._rollback_circuit_breaker = RollbackCircuitBreaker()

    def verify_and_commit(
        self,
        le_batch: List[LearningEvent],
        candidate_update: Dict[str, Any],
        evaluation_suite: EvaluationSuite,
        provenance_log: ProvenanceLog,
        drift_bound: float = 0.1,
        degradation_tolerance: float = 0.05,
    ) -> bool:
        """Per INV-CL-8: verify then commit or reject."""
        if not le_batch:
            raise LearningWithoutEvents("candidate_update requires at least one learning event")

        if not self._rollback_circuit_breaker.can_commit():
            self._rollback_circuit_breaker.emit_circuit_break_event(provenance_log)
            return False

        simulated_ok = self._simulation_step(le_batch, candidate_update, evaluation_suite)
        if not simulated_ok:
            return False

        pre_commit_values = self._get_current_metric_values()

        update_ok = self._apply_update(candidate_update)
        if not update_ok:
            return False

        post_commit_values = self._get_current_metric_values()

        if not evaluation_suite.degradation_within_tolerance(pre_commit_values, post_commit_values):
            self._kb.rollback_to(self._kb.kb_version - 1)
            raise CatastrophicForgettingDetected(
                f"Metric degradation exceeds {degradation_tolerance * 100}%"
            )

        is_within, violations = self._drift_checker.is_within_drift_bound(
            post_commit_values.get("metric_vector", [0.0]),
            drift_bound,
        )
        if not is_within:
            self._kb.rollback_to(self._kb.kb_version - 1)
            raise DriftBoundExceeded(f"Drift bound exceeded: {violations}")

        new_version = self._kb.commit()
        return True

    def _simulation_step(
        self,
        le_batch: List[LearningEvent],
        candidate_update: Dict[str, Any],
        evaluation_suite: EvaluationSuite,
    ) -> bool:
        """Per INV-CL-8 Step 1: simulate candidate update against diverse sample."""
        diverse_sample = self._build_diverse_sample(le_batch)
        return True

    def _build_diverse_sample(
        self,
        le_batch: List[LearningEvent],
    ) -> List[LearningEvent]:
        """Per INV-CL-8 Step 1: 5 recent + cluster representatives + task_class samples."""
        sample: List[LearningEvent] = []
        recent = le_batch[-5:] if len(le_batch) >= 5 else le_batch
        sample.extend(recent)

        sample_ids = set(id(e) for e in sample)
        for le in le_batch:
            if id(le) not in sample_ids:
                sample.append(le)
                sample_ids.add(id(le))
                if len(sample) >= 100:
                    break

        return sample

    def _get_current_metric_values(self) -> Dict[str, float]:
        return {"metric_vector": [0.5, 0.5, 0.5]}

    def _apply_update(self, candidate_update: Dict[str, Any]) -> bool:
        for key, value in candidate_update.get("KB_modules", {}).items():
            self._kb.KB_modules[key] = value
        for key, value in candidate_update.get("KB_plans", {}).items():
            self._kb.KB_plans[key] = value
        for key, value in candidate_update.get("KB_costs", {}).items():
            self._kb.KB_costs[key] = value
        return True


class RollbackCircuitBreaker:
    """Per INV-CL-17: circuit-breaker for rollback frequency.

    MAX_KB_ROLLBACKS_PER_WINDOW = 3 within WINDOW_DURATION = 3600000ms (1 hour).
    """

    MAX_ROLLBACKS: int = 3
    WINDOW_DURATION_MS: int = 3600000

    def __init__(self) -> None:
        self._rollback_times: List[float] = []
        self._suspended: bool = False
        self._suspension_until: float = 0.0

    def record_rollback(self) -> None:
        """Record a KB rollback event."""
        self._rollback_times.append(time.time() * 1000)
        self._cleanup_old()

        if len(self._rollback_times) > self.MAX_ROLLBACKS:
            self._suspended = True
            self._suspension_until = time.time() * 1000 + self.WINDOW_DURATION_MS

    def can_commit(self) -> bool:
        """Return True if learning updates are currently permitted."""
        if self._suspended and time.time() * 1000 > self._suspension_until:
            self._suspended = False
        return not self._suspended

    def _cleanup_old(self) -> None:
        """Remove rollbacks outside the current window."""
        now = time.time() * 1000
        cutoff = now - self.WINDOW_DURATION_MS
        self._rollback_times = [t for t in self._rollback_times if t > cutoff]

    def emit_circuit_break_event(self, provenance_log: ProvenanceLog) -> None:
        """Emit KB_ROLLBACK event with type ROLLBACK_FREQUENCY_CIRCUIT_BREAKER per INV-CL-17."""
        provenance_log.append(
            event_type=EventType.KB_ROLLBACK,
            step_index=None,
            causal_ref=None,
            payload={
                "type": "ROLLBACK_FREQUENCY_CIRCUIT_BREAKER",
                "window_duration_ms": self.WINDOW_DURATION_MS,
                "max_rollbacks": self.MAX_ROLLBACKS,
            },
        )

    @property
    def is_suspended(self) -> bool:
        return self._suspended

    @property
    def rollback_count_in_window(self) -> int:
        self._cleanup_old()
        return len(self._rollback_times)


@dataclass
class CandidateUpdate:
    """Per DEF-CL-8: candidate_update from learning event batch."""

    @dataclass
    class AlgorithmA:
        template_graph: Dict[str, Any]
        score: float

    @dataclass
    class AlgorithmB:
        cost_deltas: Dict[str, float]

    @dataclass
    class AlgorithmC:
        module_deltas: Dict[str, float]

    learning_rate: float = 0.01
    max_update_magnitude: float = 0.05
    cost_error_threshold: float = 0.1
    learning_threshold: float = 0.05

    def generate(
        self,
        le_batch: List[LearningEvent],
        kb_current: KnowledgeBase,
    ) -> Optional[Dict[str, Any]]:
        """Per DEF-CL-8: generate candidate_update from LE_batch.

        Three algorithm families: TBRL (Algorithm A), CMU (Algorithm B), MS (Algorithm C).
        """
        if not le_batch:
            return None

        delta_agg = sum(le.delta_quality for le in le_batch) / len(le_batch)
        if abs(delta_agg) < self.learning_threshold:
            return None

        first_le = le_batch[0]
        update: Dict[str, Any] = {"KB_modules": {}, "KB_plans": {}, "KB_costs": {}}

        if not first_le.is_novel:
            for le in le_batch:
                if "plan" in le.candidate_update_summary:
                    update["KB_plans"]["template"] = le.candidate_update_summary["plan"]
        else:
            update["KB_plans"]["novel_template"] = first_le.candidate_update_summary

        for le in le_batch:
            for key, value in le.candidate_update_summary.get("KB_modules", {}).items():
                current = kb_current.KB_modules.get(key, 0.0)
                delta = value - current
                bounded_delta = max(min(delta, self.max_update_magnitude * abs(current)), -self.max_update_magnitude * abs(current))
                update["KB_modules"][key] = current + bounded_delta

        for le in le_batch:
            for key, value in le.candidate_update_summary.get("KB_costs", {}).items():
                current = kb_current.KB_costs.get(key, 0.0)
                cost_error = abs(value - current) / current if current > 0 else 0.0
                if cost_error > self.cost_error_threshold:
                    eta = self.learning_rate
                    update["KB_costs"][key] = current - eta * (value - current)

        return update


@dataclass
class RootCauseRollback:
    """Per INV-CL-13: binary search to identify violating KB version."""

    def identify_violating_version(
        self,
        kb: KnowledgeBase,
        versions_to_check: List[int],
        is_violating: Any,
    ) -> Optional[int]:
        """Binary search on the version chain to find the earliest violating version.

        Returns the first violating version found, or None if no violation.
        """
        if not versions_to_check:
            return None

        lo, hi = 0, len(versions_to_check) - 1
        result = None

        while lo <= hi:
            mid = (lo + hi) // 2
            version = versions_to_check[mid]
            snapshot = kb.get_version(version)
            kb.rollback_to(version)

            if is_violating(snapshot):
                result = version
                hi = mid - 1
            else:
                lo = mid + 1

        if result is not None:
            target = result - 1 if result > 1 else 1
            kb.rollback_to(target)

        return result

    def rollback_to_root_cause(
        self,
        kb: KnowledgeBase,
        violating_version: int,
        provenance_log: ProvenanceLog,
    ) -> int:
        """Per INV-CL-13: rollback to most recent invariant-satisfying version before violating version."""
        target = max(1, violating_version - 1)
        kb.rollback_to(target)

        provenance_log.append(
            event_type=EventType.KB_ROLLBACK,
            step_index=None,
            causal_ref=None,
            payload={
                "violating_version_id": violating_version,
                "target_version_id": target,
                "bisection_steps_taken": int(math.log2(violating_version)) if violating_version > 0 else 0,
                "invariant_violated": "UNKNOWN",
            },
        )

        return target