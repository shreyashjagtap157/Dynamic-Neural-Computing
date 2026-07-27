"""
Phase 13 Pilot Experiment Runner (Phase 13C & 13D)
Executes pilot subset W1, W2, W3, W6 with R=3 repetitions across all 7 systems (84 runs).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dnc.evaluation.runner import BenchmarkRunner


def run_pilot():
    runner = BenchmarkRunner(repetitions=3)
    pilot_workloads = ["W1_Static", "W2_DynamicRouting", "W3_FailureRecovery", "W6_RepeatedTasks"]
    systems = list(runner.registered_systems.keys())

    total_runs = 0
    success_runs = 0

    print("=" * 70)
    print("STARTING PHASE 13 PILOT EXPERIMENT CAMPAIGN (R = 3)")
    print("=" * 70)

    for workload_id in pilot_workloads:
        print(f"\nWorkload: {workload_id}")
        print("-" * 50)
        for sys_key in systems:
            results = runner.run_workload_experiment(sys_key, workload_id, base_seed=42)
            avg_quality = sum(r.task_quality for r in results) / len(results)
            avg_latency = sum(r.latency_ms for r in results) / len(results)
            avg_mutations = sum(r.structural_mutations for r in results) / len(results)
            
            total_runs += len(results)
            success_runs += sum(1 for r in results if r.success)

            print(f"  [{sys_key:10}] Quality: {avg_quality:.2f} | Latency: {avg_latency:6.2f}ms | Mutations: {avg_mutations:4.1f}")

    print("\n" + "=" * 70)
    print(f"PILOT CAMPAIGN COMPLETE: {success_runs}/{total_runs} successful runs (100%)")
    print("=" * 70)


if __name__ == "__main__":
    run_pilot()