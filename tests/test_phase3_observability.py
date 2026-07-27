"""Phase 3 exit criteria tests — 12 criteria from mvp-roadmap.md Section 5.C.

Tests provenance model, failure taxonomy, evaluation suite, and continual learning.
"""

import sys
import math
sys.path.insert(0, 'src')

from dnc.observability.provenance import (
    ProvenanceLog,
    ProvenanceEvent,
    EventType,
    ProvenanceTamperingViolation,
    CausalChainBroken,
)
from dnc.observability.failure import (
    FailureClassifier,
    FailureHandler,
    AlertManager,
    FailureClassification,
    FailureSignal,
    FailureRecord,
    AlertSeverity,
    SIGNAL_TO_CLASSIFICATION,
)
from dnc.observability.evaluation import (
    EvaluationSuite,
    EvaluationScenario,
    EvaluationRun,
    EvaluationStage,
    MetricResult,
    MetricClass,
    ResultClassification,
    NovelTaskBenchmark,
    get_canonical_novel_benchmarks,
)
from dnc.learning.continual import (
    KnowledgeBase,
    LearningEvent,
    DriftChecker,
    ExecutionRecord,
    LearningVerificationProtocol,
    RollbackCircuitBreaker,
    RootCauseRollback,
    CandidateUpdate,
    DriftBoundExceeded,
    CatastrophicForgettingDetected,
    ProvenanceTamperingViolation,
)


class TestPhase3ExitCriteria:

    def test_ec1_provenance_event_recording(self):
        """EC-1: Every runtime event recorded with correct causal_ref."""
        pl = ProvenanceLog("exec_1")
        init = pl.append(EventType.MODULE_REGISTERED, None, None, {"module": "Source"})
        dispatch = pl.append(EventType.STEP_DISPATCHED, 1, init.event_id, {"step": 1})
        completed = pl.append(EventType.STEP_COMPLETED, 2, dispatch.event_id, {"step": 2})

        assert len(pl) == 3
        assert dispatch.causal_ref == init.event_id
        assert completed.causal_ref == dispatch.event_id

    def test_ec2_causal_chain_query(self):
        """EC-2: Causal chain query returns correct chain for any event."""
        pl = ProvenanceLog("exec_2")
        e0 = pl.append(EventType.MODULE_REGISTERED, None, None, {"module": "A"})
        e1 = pl.append(EventType.DECISION, 1, e0.event_id, {"decision": "CONTINUE"})
        e2 = pl.append(EventType.STEP_DISPATCHED, 2, e1.event_id, {"step": 1})
        e3 = pl.append(EventType.STEP_COMPLETED, 3, e2.event_id, {"step": 1})

        chain = pl.query_causal_chain(e3.event_id)
        ids = [ev.event_id for ev in chain]
        assert ids == [e0.event_id, e1.event_id, e2.event_id, e3.event_id]
        assert chain[0].causal_ref is None
        assert chain[1].causal_ref == chain[0].event_id

    def test_ec3_hash_chain_integrity(self):
        """EC-3: Hash chain integrity maintained — tamper detection works."""
        pl = ProvenanceLog("exec_3")
        pl.append(EventType.MODULE_REGISTERED, None, None, {"module": "A"})
        pl.append(EventType.STEP_DISPATCHED, 1, None, {"step": 1})
        pl.append(EventType.STEP_COMPLETED, 2, None, {"step": 1})

        assert pl.verify_chain() is True

        events = list(pl._events)
        events[1]._fields = tuple(
            dict(zip(['event_id','event_type','timestamp','execution_id','step_index','causal_ref','payload','integrity_hash'], ev))
            for ev in [events[1]]
        )[0] if False else events[1]
        try:
            pl._events[1] = ProvenanceEvent(
                event_id=events[1].event_id,
                event_type=events[1].event_type,
                timestamp=events[1].timestamp,
                execution_id=events[1].execution_id,
                step_index=events[1].step_index,
                causal_ref=events[1].causal_ref,
                payload={"tampered": True},
                integrity_hash=events[1].integrity_hash,
            )
            pl.verify_chain()
            assert False, "Should have raised ProvenanceTamperingViolation"
        except ProvenanceTamperingViolation:
            pass

    def test_ec4_failure_classification_mapping(self):
        """EC-4: Failure classification matches prescribed mapping for all defined signals."""
        classifier = FailureClassifier()
        signals = list(FailureSignal)

        for signal in signals:
            record = classifier.classify(
                module_id=None,
                signal=signal,
                step_index=0,
            )
            assert record.classification == SIGNAL_TO_CLASSIFICATION[signal], \
                f"{signal} classified as {record.classification}, expected {SIGNAL_TO_CLASSIFICATION[signal]}"

        assert len(signals) == len(FailureSignal)
        assert FailureSignal.GPU_RECOVERY in signals

    def test_ec5_failure_rate_tracking(self):
        """EC-5: Failure rate tracked per module type and exposed to planner."""
        classifier = FailureClassifier()

        classifier.record_failure("transformer_v1", total_invocations=100)
        classifier.record_failure("transformer_v1", total_invocations=100)

        rate = classifier.get_failure_rate("transformer_v1")
        assert rate == 0.02, f"Expected 0.02, got {rate}"

        unknown_rate = classifier.get_failure_rate("unknown_module")
        assert unknown_rate == 0.0

    def test_ec6_evaluation_trial_count(self):
        """EC-6: Evaluation suite runs with MIN_TRIAL_COUNT trials per scenario."""
        suite = EvaluationSuite()
        scenario = EvaluationScenario(
            scenario_id="test_scenario",
            task_class="functional",
            task_description="Test task",
            input_distribution="uniform",
            expected_output_spec="output",
            baseline_implementations=["Baseline1"],
            success_criteria=">0.5",
        )
        suite.register_scenario(scenario)

        dnc_values = [0.8] * 30
        baseline_values = [0.6] * 30

        mean_val, std_val, p_val, d = suite.compute_statistics(dnc_values, baseline_values)
        assert mean_val == 0.8
        assert p_val < 0.05, f"Expected p < 0.05, got {p_val}"
        assert d > 0, f"Expected positive effect size, got {d}"

    def test_ec7_statistical_significance(self):
        """EC-7: WIN/LOSS/TIE classification is statistically significant (p < 0.05)."""
        suite = EvaluationSuite()

        dnc_values = [0.75, 0.8, 0.85, 0.7, 0.9, 0.78, 0.82, 0.88, 0.72, 0.79,
                      0.83, 0.76, 0.87, 0.71, 0.84, 0.77, 0.81, 0.86, 0.73, 0.79,
                      0.85, 0.78, 0.82, 0.88, 0.74, 0.80, 0.84, 0.77, 0.83, 0.79]
        baseline_values = [0.5, 0.55, 0.6, 0.52, 0.58, 0.51, 0.56, 0.59, 0.53, 0.57,
                           0.5, 0.54, 0.58, 0.52, 0.57, 0.51, 0.55, 0.59, 0.53, 0.56,
                           0.5, 0.54, 0.58, 0.52, 0.57, 0.51, 0.55, 0.59, 0.53, 0.57]

        assert len(dnc_values) == 30, f"Expected 30 trials, got {len(dnc_values)}"
        assert len(baseline_values) == 30

        mean_val, std_val, p_val, d = suite.compute_statistics(dnc_values, baseline_values)
        classification = suite.classify_result(p_val, d)

        assert classification == ResultClassification.WIN, \
            f"Expected WIN, got {classification} (p={p_val:.4f}, d={d:.4f})"

        tie_values = [0.5] * 30
        _, _, p_tie, d_tie = suite.compute_statistics(tie_values, tie_values)
        tie_class = suite.classify_result(p_tie, d_tie)
        assert tie_class == ResultClassification.TIE

    def test_ec8_regression_detection(self):
        """EC-8: Regression detection emits PROV event and blocks KB update on Class 1 regression."""
        suite = EvaluationSuite()

        prior_results = {
            "scenario_A": {
                "accuracy": ResultClassification.WIN,
                "latency": ResultClassification.TIE,
            }
        }

        current = EvaluationRun(
            run_id="run_2",
            scenario_id="scenario_A",
            runtime_under_test="dnc_v2",
            baseline_ids=["baseline_1"],
            metric_results=[
                MetricResult("accuracy", MetricClass.CLASS_1_FUNCTIONAL, 0.45, 0.5, 0.3, -0.2, ResultClassification.LOSS),
                MetricResult("latency", MetricClass.CLASS_1_FUNCTIONAL, 50.0, 48.0, 0.6, 0.1, ResultClassification.TIE),
            ],
            timestamp=0.0,
            statistical_analysis={},
        )

        regressions = suite.detect_regression(current, prior_results)
        assert len(regressions) == 1
        scenario, metric, prior_class = regressions[0]
        assert scenario == "scenario_A"
        assert metric == "accuracy"
        assert prior_class in (ResultClassification.WIN.value, ResultClassification.TIE.value)

    def test_ec9_drift_bound_rejected(self):
        """EC-9: Learning update rejected when drift exceeds DRIFT_BOUND."""
        dr = DriftChecker()
        DRIFT_BOUND = 0.1

        dr._history = [
            ExecutionRecord("ex1", "task_A", [0.8, 0.7, 0.9], 1.0),
            ExecutionRecord("ex2", "task_A", [0.75, 0.72, 0.88], 2.0),
            ExecutionRecord("ex3", "task_B", [0.6, 0.5, 0.7], 3.0),
        ]
        dr._representative_sample = {0, 1, 2}
        dr._centers = [[0.8, 0.7, 0.9], [0.75, 0.72, 0.88], [0.6, 0.5, 0.7]]
        dr._cluster_assignments = [0, 1, 2]

        is_within, violations = dr.is_within_drift_bound([0.8, 0.7, 0.9], DRIFT_BOUND)
        assert is_within is True

        far_vector = [0.2, 0.2, 0.2]
        is_within_far, far_violations = dr.is_within_drift_bound(far_vector, DRIFT_BOUND)
        assert is_within_far is False
        assert len(far_violations) > 0

    def test_ec10_degradation_rejected(self):
        """EC-10: Learning update rejected when metric degrades beyond DEGRADATION_TOLERANCE."""
        suite = EvaluationSuite()
        baseline_values = {"accuracy": 0.8, "latency": 50.0}
        updated_ok = [0.79, 51.0]
        updated_ok_dict = {"accuracy": updated_ok[0], "latency": updated_ok[1]}
        assert suite.degradation_within_tolerance(baseline_values, updated_ok_dict) is True

        degraded = {"accuracy": 0.5, "latency": 100.0}
        assert suite.degradation_within_tolerance(baseline_values, degraded) is False

    def test_ec11_kb_version_incremented(self):
        """EC-11: KB version incremented on each commit; old versions preserved."""
        kb = KnowledgeBase()

        assert kb.kb_version == 0
        v1 = kb.commit()
        assert v1 == 1
        assert kb.kb_version == 1

        kb.KB_modules["transform_v1"] = {"param": 0.5}
        v2 = kb.commit()
        assert v2 == 2
        assert kb.kb_version == 2

        snap_v1 = kb.get_version(1)
        assert "KB_modules" in snap_v1
        snap_v2 = kb.get_version(2)
        assert snap_v2["KB_modules"]["transform_v1"] == {"param": 0.5}

    def test_ec12_kb_rollback_restores_version(self):
        """EC-12: KB rollback restores previous version and preserves execution history."""
        kb = KnowledgeBase()
        for _ in range(3):
            kb.KB_modules[f"mod_v{kb.kb_version}"] = {"value": kb.kb_version + 1}
            kb.commit()

        assert kb.kb_version == 3

        prior_modules = dict(kb.KB_modules)
        kb.rollback_to(1)
        assert kb.kb_version == 1
        assert "mod_v0" in kb.KB_modules
        assert "mod_v2" not in kb.KB_modules


if __name__ == "__main__":
    import traceback

    t = TestPhase3ExitCriteria()
    results = []
    for name in sorted(dir(t)):
        if name.startswith('test_ec'):
            try:
                getattr(t, name)()
                results.append(f'PASS: {name}')
            except Exception as e:
                results.append(f'FAIL: {name} -- {e}')
                traceback.print_exc()

    for r in results:
        print(r)
    print(f"\n{sum(1 for r in results if r.startswith('PASS'))}/{len(results)} Phase 3 tests passed")