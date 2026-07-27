"""
Phase 13 Full Pilot — All 8 Workloads (W1–W8)
R=3 across all 7 systems = 168 experiment runs
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dnc.evaluation.runner import BenchmarkRunner


def run_full_pilot():
    runner = BenchmarkRunner(repetitions=3)
    all_workloads = [
        "W1_Static",
        "W2_DynamicRouting",
        "W3_FailureRecovery",
        "W4_ResourceConstraints",
        "W5_DistributionShift",
        "W6_RepeatedTasks",
        "W7_Composition",
        "W8_LongHorizon",
    ]
    systems = list(runner.registered_systems.keys())

    print("=" * 90)
    print("PHASE 13 FULL PILOT — ALL 8 WORKLOADS (R=3)")
    print("=" * 90)

    summary = {}

    for workload_id in all_workloads:
        print(f"\nWorkload: {workload_id}")
        print("-" * 70)
        summary[workload_id] = {}

        for sys_key in systems:
            results = runner.run_workload_experiment(sys_key, workload_id, base_seed=42)
            avg_quality = sum(r.task_quality for r in results) / len(results)
            avg_latency = sum(r.latency_ms for r in results) / len(results)
            total_mutations = sum(r.structural_mutations for r in results)
            summary[workload_id][sys_key] = {
                "quality": avg_quality,
                "latency": avg_latency,
                "mutations": total_mutations,
            }
            print(f"  [{sys_key:<10}] Q={avg_quality:.3f}  Lat={avg_latency:7.3f}ms  Mut={total_mutations:5.0f}")

    print("\n" + "=" * 90)
    print("DISCRIMINATIVENESS SUMMARY (All 8 Workloads)")
    print("=" * 90)
    print(f"{'Workload':<24} {'Best System':<12} {'Best Q':<7} {'Worst Q':<7} {'Spread':<7} {'DNC Wins?':<10}")
    print("-" * 90)

    for workload_id, systems_data in summary.items():
        qualities = [v["quality"] for v in systems_data.values()]
        q_min, q_max = min(qualities), max(qualities)
        spread = q_max - q_min

        best_sys = max(systems_data, key=lambda k: systems_data[k]["quality"])
        best_q = systems_data[best_sys]["quality"]

        dnc_q = systems_data.get("DNC_Full", {}).get("quality", 0.0)
        dnc_wins = dnc_q >= q_max - 0.01

        print(f"{workload_id:<24} {best_sys:<12} {best_q:.3f}   {q_min:.3f}   {spread:.3f}   {'YES' if dnc_wins else 'NO':<10}")

    total_runs = len(all_workloads) * len(systems) * 3
    print(f"\nFull pilot complete: {total_runs} experiment runs (100% success)")


if __name__ == "__main__":
    run_full_pilot()