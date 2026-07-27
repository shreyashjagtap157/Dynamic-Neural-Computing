"""
Phase 13C.5 / 13D.2 — R=30 Sensitivity Campaign Runner with Counterfactual Telemetry & Oracle Labeling.
Executes 1,680 runs (8 workloads x 7 configurations x 30 repetitions) and computes
Adaptation Precision, Recall, F1, ΔV Calibration Error, Decision Regret, and Convergence Metrics (T_stable).
"""

import argparse
import json
import random
import time
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Dict, Any


from dnc.evaluation.contracts import ExperimentResult
from dnc.evaluation.baselines.static_dag import StaticDAGSystem
from dnc.evaluation.baselines.replanner import ReplannerSystem
from dnc.evaluation.baselines.agentic_loop import AgenticLoopSystem
from dnc.evaluation.baselines.dnc_variants import DNCVariantSystem
from dnc.evaluation.workloads.taxonomy import WorkloadTaxonomy, CompositeEvaluator
from dnc.evaluation.counterfactual import EvidenceValueEstimator, features_from_tasks


@dataclass
class CounterfactualTelemetryRecord:
    run_id: str
    workload_id: str
    configuration: str
    replication_id: int
    cycle: int
    unit_count_before: int
    unit_count_after: int
    v_current: float
    v_no_op: float
    v_mutation: float
    predicted_delta_v: float
    realized_delta_v: float
    prediction_error: float
    decision: str
    oracle_necessary: bool
    regret: float
    estimator_id: str
    measurement_method: str = "paired_run_mutation_ablation"


class CampaignOrchestrator:
    """Orchestrates the 1,680-run R=30 sensitivity campaign with telemetry collection."""

    def __init__(self, repetitions: int = 30):
        self.repetitions = repetitions
        self.systems = [
            "StaticDAG", "Replanner", "AgenticLoop",
            "DNC_Full", "DNC_L", "DNC_M", "DNC_P"
        ]
        self.workloads = [
            "W1_Static", "W2_DynamicRouting", "W3_FailureRecovery",
            "W4_ResourceConstraints", "W5_DistributionShift",
            "W6_RepeatedTasks", "W7_Composition", "W8_LongHorizon"
        ]
        self.telemetry_records: List[CounterfactualTelemetryRecord] = []
        self.value_estimator = EvidenceValueEstimator()

    def _factory(self, sys_key: str):
        if sys_key == "StaticDAG":
            return StaticDAGSystem()
        elif sys_key == "Replanner":
            return ReplannerSystem()
        elif sys_key == "AgenticLoop":
            return AgenticLoopSystem()
        elif sys_key == "DNC_Full":
            return DNCVariantSystem("DNC_Full", enable_learning=True, enable_mutation=True, enable_provenance=True)
        elif sys_key == "DNC_L":
            return DNCVariantSystem("DNC_L", enable_learning=False, enable_mutation=True, enable_provenance=True)
        elif sys_key == "DNC_M":
            return DNCVariantSystem("DNC_M", enable_learning=True, enable_mutation=False, enable_provenance=True)
        elif sys_key == "DNC_P":
            return DNCVariantSystem("DNC_P", enable_learning=True, enable_mutation=True, enable_provenance=False)
        raise KeyError(f"Unknown system {sys_key}")

    def run_campaign(self) -> Dict[str, Any]:
        total_runs = len(self.workloads) * len(self.systems) * self.repetitions
        print("=" * 90)
        print(
            f"  STARTING R={self.repetitions} SENSITIVITY CAMPAIGN "
            f"({total_runs:,} EXPERIMENT RUNS)"
        )
        print("=" * 90)

        completed = 0
        start_time = time.time()

        campaign_results: Dict[str, Dict[str, List[ExperimentResult]]] = {
            w: {s: [] for s in self.systems} for w in self.workloads
        }

        for w_id in self.workloads:
            workload_def = WorkloadTaxonomy.get_workload(w_id)
            for sys_key in self.systems:
                for rep in range(self.repetitions):
                    seed = 42 + rep
                    random.seed(seed)
                    task_inputs = workload_def.task_generator(seed)

                    sys_inst = self._factory(sys_key)
                    sys_inst.initialize(w_id, seed, {})

                    for t_in in task_inputs:
                        sys_inst.execute(t_in)

                    result = sys_inst.get_result()
                    result.task_quality = workload_def.ground_truth_evaluator(task_inputs, result, seed)
                    campaign_results[w_id][sys_key].append(result)

                    sys_inst.shutdown()
                    completed += 1

                print(f"  [COMPLETED] Workload: {w_id:<25} | System: {sys_key:<12} | Progress: {completed}/{total_runs}")

        elapsed_sec = time.time() - start_time
        print("\n" + "=" * 90)
        print(f"  CAMPAIGN COMPLETE: {completed}/{total_runs} runs in {elapsed_sec:.1f}s")
        print("=" * 90)

        self._measure_counterfactuals(campaign_results)
        return self.analyze_results(campaign_results)

    def _measure_counterfactuals(
        self, results: Dict[str, Dict[str, List[ExperimentResult]]]
    ) -> None:
        """Measure DNC-Full against its mutation-disabled paired execution.

        DNC-Full and DNC-M use the same seed, tasks, evaluator, learning setting,
        and initial graph. Their only intended capability difference is structural
        mutation. This provides an observed run-level counterfactual; it is not
        presented as a per-candidate causal estimate.
        """
        self.telemetry_records.clear()
        for workload_id in self.workloads:
            workload = WorkloadTaxonomy.get_workload(workload_id)
            full_runs = results[workload_id]["DNC_Full"]
            no_op_runs = results[workload_id]["DNC_M"]
            for replication_id, (mutation_run, no_op_run) in enumerate(
                zip(full_runs, no_op_runs, strict=True)
            ):
                seed = 42 + replication_id
                tasks = workload.task_generator(seed)
                features = features_from_tasks(
                    workload_id,
                    tasks,
                    current_unit_count=int(mutation_run.metadata.get("initial_units", 0)),
                    expected_mutation_cost=0.002 * max(1, len(tasks)),
                )
                prediction = self.value_estimator.predict(features)
                realized_delta = mutation_run.task_quality - no_op_run.task_quality
                mutated = mutation_run.structural_mutations > 0
                chosen_value = mutation_run.task_quality if mutated else no_op_run.task_quality
                best_value = max(mutation_run.task_quality, no_op_run.task_quality)
                self.telemetry_records.append(
                    CounterfactualTelemetryRecord(
                        run_id=mutation_run.experiment_id,
                        workload_id=workload_id,
                        configuration="DNC_Full",
                        replication_id=replication_id,
                        cycle=mutation_run.execution_steps,
                        unit_count_before=int(mutation_run.metadata.get("initial_units", 0)),
                        unit_count_after=int(mutation_run.metadata.get("final_units", 0)),
                        v_current=no_op_run.task_quality,
                        v_no_op=no_op_run.task_quality,
                        v_mutation=mutation_run.task_quality,
                        predicted_delta_v=prediction.delta_v,
                        realized_delta_v=realized_delta,
                        prediction_error=abs(realized_delta - prediction.delta_v),
                        decision="AUTHORIZE" if mutated else "STABLE",
                        oracle_necessary=CompositeEvaluator.is_adaptation_necessary(
                            workload_id, tasks
                        ),
                        regret=best_value - chosen_value,
                        estimator_id=self.value_estimator.estimator_id,
                    )
                )

    def analyze_results(self, results: Dict[str, Dict[str, List[ExperimentResult]]]) -> Dict[str, Any]:
        analysis = {}

        # Compute Adaptation Precision, Recall, F1 for DNC_Full across workloads
        tp = fp = fn = tn = 0
        for rec in self.telemetry_records:
            if rec.configuration == "DNC_Full":
                mutated = (rec.decision == "AUTHORIZE")
                if rec.oracle_necessary and mutated:
                    tp += 1
                elif not rec.oracle_necessary and mutated:
                    fp += 1
                elif rec.oracle_necessary and not mutated:
                    fn += 1
                else:
                    tn += 1

        precision = tp / max(1, (tp + fp))
        recall = tp / max(1, (tp + fn))
        f1 = (2 * precision * recall) / max(1e-6, (precision + recall))

        # Compute Calibration Error (MAE of Delta V)
        errors = [r.prediction_error for r in self.telemetry_records if r.configuration == "DNC_Full"]
        mae_dv = statistics.mean(errors) if errors else 0.0
        rmse_dv = (statistics.mean([e**2 for e in errors]) ** 0.5) if errors else 0.0

        # Compute Regret
        regrets = [r.regret for r in self.telemetry_records if r.configuration == "DNC_Full"]
        mean_regret = statistics.mean(regrets) if regrets else 0.0

        analysis["adaptivity"] = {
            "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "Precision": precision,
            "Recall": recall,
            "F1": f1
        }
        analysis["calibration"] = {
            "MAE_DeltaV": mae_dv,
            "RMSE_DeltaV": rmse_dv,
            "MeanRegret": mean_regret
        }
        analysis["methodology"] = {
            "repetitions": self.repetitions,
            "seed_start": 42,
            "estimator_id": self.value_estimator.estimator_id,
            "realized_counterfactual": "paired DNC_Full minus DNC_M run-level quality",
            "adaptivity_metric_scope": (
                "metadata-label adherence; generator and oracle consume the same explicit signals"
            ),
            "causal_scope": (
                "paired trajectory ablation, not a per-candidate randomized causal estimate"
            ),
            "benchmark_scope": (
                "synthetic reference systems; results do not demonstrate external task utility"
            ),
        }

        # Workload-level summary
        workload_summary = {}
        for w_id, systems in results.items():
            workload_summary[w_id] = {}
            for sys_key, runs in systems.items():
                avg_q = statistics.mean([r.task_quality for r in runs])
                avg_lat = statistics.mean([r.latency_ms for r in runs])
                avg_mut = statistics.mean([r.structural_mutations for r in runs])
                workload_summary[w_id][sys_key] = {
                    "Quality": avg_q,
                    "Latency_ms": avg_lat,
                    "Mutations": avg_mut
                }
        analysis["workload_summary"] = workload_summary

        return analysis


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=30)
    parser.add_argument("--out", type=Path, help="Write summary and telemetry as JSON")
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")

    orchestrator = CampaignOrchestrator(repetitions=args.repetitions)
    report = orchestrator.run_campaign()

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(
                {
                    "report": report,
                    "telemetry": [asdict(record) for record in orchestrator.telemetry_records],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    print("\n" + "#" * 90)
    print(
        "  PHASE 13C.5 / 13D.2 SENSITIVITY CAMPAIGN RESULTS "
        f"(R={args.repetitions})"
    )
    print("#" * 90)

    print("\n[Layer 2] Adaptation Precision & Recall (DNC_Full):")
    adt = report["adaptivity"]
    print(f"  True Positives: {adt['TP']} | False Positives: {adt['FP']} | False Negatives: {adt['FN']} | True Negatives: {adt['TN']}")
    print(f"  Adaptation Precision: {adt['Precision']:.3f}")
    print(f"  Adaptation Recall:    {adt['Recall']:.3f}")
    print(f"  Adaptation F1 Score:  {adt['F1']:.3f}")

    print("\n[Layer 3] Counterfactual Calibration & Regret (DNC_Full):")
    cal = report["calibration"]
    print(f"  MAE (Delta V Predicted vs Realized): {cal['MAE_DeltaV']:.4f}")
    print(f"  RMSE (Delta V Predicted vs Realized): {cal['RMSE_DeltaV']:.4f}")
    print(f"  Mean Decision Regret:           {cal['MeanRegret']:.4f}")

    print("\n[Layer 4] Workload Summary (Quality / Mutations):")
    for wid, systems in report["workload_summary"].items():
        print(f"  - {wid}:")
        for sk, metrics in systems.items():
            print(f"      {sk:<12} -> Quality: {metrics['Quality']:.3f} | Mut: {metrics['Mutations']:.1f}")
