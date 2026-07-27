"""
Phase 13 Diagnostic Pilot -- Native System Quality (No Ground-Truth Override)

Shows what each system ACTUALLY reports via get_result() without any
ground-truth evaluator override of task_quality.

This exposes:
- Whether DNC's native quality differs from baselines
- Whether structural mutations correlate with quality improvement
- Whether overhead causes measurable quality regression
"""



from dnc.evaluation.runner import BenchmarkRunner


def run_native_quality_pilot():
    runner = BenchmarkRunner(repetitions=3)
    pilot_workloads = ["W1_Static", "W2_DynamicRouting", "W3_FailureRecovery", "W6_RepeatedTasks"]
    systems = list(runner.registered_systems.keys())

    header = f"{'Workload':<22} {'System':<12} {'Succ':<5} {'Quality':<8} {'Latency':<10} {'Mutations':<10}"
    print("=" * 90)
    print("PHASE 13 DIAGNOSTIC -- NATIVE SYSTEM QUALITY (NO GROUND-TRUTH OVERRIDE)")
    print("=" * 90)
    print(header)
    print("-" * 90)

    workload_summary = {}

    for workload_id in pilot_workloads:
        workload_summary[workload_id] = {}

        for sys_key in systems:
            results = runner.run_workload_experiment_native(sys_key, workload_id, base_seed=42)
            avg_quality = sum(r.task_quality for r in results) / len(results)
            avg_latency = sum(r.latency_ms for r in results) / len(results)
            total_mutations = sum(r.structural_mutations for r in results)
            any_success = any(r.success for r in results)
            workload_summary[workload_id][sys_key] = {
                "quality": avg_quality,
                "latency": avg_latency,
                "mutations": total_mutations,
                "success": any_success
            }

            succ_str = "YES" if any_success else "NO"
            print(f"{workload_id:<22} {sys_key:<12} {succ_str:<5} {avg_quality:.3f}    {avg_latency:8.3f}ms {total_mutations:8.0f}")

    print()
    print("=" * 90)
    print("DISCRIMINATIVENESS ANALYSIS")
    print("=" * 90)

    for workload_id, systems_data in workload_summary.items():
        qualities = [v["quality"] for v in systems_data.values()]
        q_min, q_max = min(qualities), max(qualities)
        q_range = q_max - q_min

        dnc_quality = systems_data["DNC_Full"]["quality"]
        static_quality = systems_data["StaticDAG"]["quality"]
        dnc_mutations = systems_data["DNC_Full"]["mutations"]

        quality_diff = dnc_quality - static_quality

        print(f"\n{workload_id}:")
        print(f"  Quality range: {q_min:.3f} - {q_max:.3f}  (spread = {q_range:.3f})")
        print(f"  DNC_Full vs StaticDAG quality: {quality_diff:+.3f}")
        print(f"  DNC mutations: {dnc_mutations:.0f}")

        if q_range < 0.01:
            verdict = "NON-DISCRIMINATIVE: All systems identical quality"
        elif quality_diff > 0.02:
            verdict = f"DNC OUTPERFORMS: +{quality_diff:.3f} quality"
        elif quality_diff < -0.02:
            verdict = f"DNC UNDERPERFORMS: {quality_diff:.3f} (overhead > adaptation benefit)"
        else:
            verdict = "PARITY: DNC matches baseline quality"
        print(f"  -> {verdict}")


if __name__ == "__main__":
    run_native_quality_pilot()
