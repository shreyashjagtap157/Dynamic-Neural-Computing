"""
Phase 13C.2 — Mutation Lifecycle Audit (v2)

Precisely diagnoses WHERE in the DNC pipeline the over-mutation failure occurs.
For every cycle, records proposals generated, authorized, and operations per authorized proposal.
"""

import random


from dnc.dcc.computation_generator import GenerationObjective
from dnc.evaluation.workloads.taxonomy import WorkloadTaxonomy


def run_lifecycle_for_system(system_key, workload_id, base_seed=42):
    """Run one system through one workload with full lifecycle tracing."""
    from dnc.evaluation.baselines.dnc_variants import DNCVariantSystem
    from dnc.evaluation.baselines.static_dag import StaticDAGSystem
    from dnc.evaluation.baselines.replanner import ReplannerSystem
    from dnc.evaluation.baselines.agentic_loop import AgenticLoopSystem

    FACTORY = {
        "StaticDAG": StaticDAGSystem,
        "Replanner": ReplannerSystem,
        "AgenticLoop": AgenticLoopSystem,
        "DNC_Full": lambda: DNCVariantSystem("DNC_Full", True, True, True),
        "DNC_L": lambda: DNCVariantSystem("DNC_L", False, True, True),
        "DNC_M": lambda: DNCVariantSystem("DNC_M", True, False, True),
        "DNC_P": lambda: DNCVariantSystem("DNC_P", True, True, False),
    }

    factory = FACTORY[system_key]
    system = factory() if callable(factory) and not isinstance(factory, type) else factory()

    workload_def = WorkloadTaxonomy.get_workload(workload_id)
    seed = base_seed
    random.seed(seed)
    task_inputs = workload_def.task_generator(seed)

    system.initialize(workload_id=workload_id, seed=seed, config={})

    cycle_log = []

    # Special handling for DNC variants (they have .system attribute)
    is_dnc = isinstance(system, DNCVariantSystem)

    for task_input in task_inputs:
        complexity = task_input.get("complexity", 5)
        objective = GenerationObjective(
            task_description=task_input.get("description", "Benchmark task"),
            max_units=complexity * 2,
            max_edges=complexity * 3,
            cost_budget=100.0
        )

        if is_dnc:
            prior = system.last_assessment if system.enable_learning else None
            graph_units_before = len(system.system.graph.units)
            graph_edges_before = len(system.system.graph.edges)
            proposals_before = system.system._proposals_generated

            success, assessment, authorized_proposal = system.system.run_cycle(objective, prior)

            graph_units_after = len(system.system.graph.units)
            graph_edges_after = len(system.system.graph.edges)
            proposals_after = system.system._proposals_generated
            auth_ops = len(authorized_proposal.candidate_operations) if authorized_proposal else 0
            ops_delta = graph_units_after - graph_units_before  # actual unit change

            if success and assessment:
                system.last_assessment = assessment
                if authorized_proposal and system.enable_mutation:
                    system.mutations_count += len(authorized_proposal.candidate_operations)
            else:
                system.recovery_count += 1

            utility = system.last_assessment.post_execution_utility_measured if system.last_assessment else 0.75

            cycle_log.append({
                "cycle": len(cycle_log) + 1,
                "graph_before": (graph_units_before, graph_edges_before),
                "graph_after": (graph_units_after, graph_edges_after),
                "proposals_generated_this_cycle": proposals_after - proposals_before,
                "proposals_cumulative": proposals_after,
                "authorized": success,
                "auth_ops": auth_ops,
                "ops_actually_applied": ops_delta,
                "proposal_id": authorized_proposal.proposal_id if authorized_proposal else None,
                "utility": utility,
            })
        else:
            system.execute(task_input)
            cycle_log.append({
                "cycle": len(cycle_log) + 1,
                "authorized": True,
                "auth_ops": 0,
                "proposal_id": None,
            })

    final_result = system.get_result()
    system.shutdown()

    return cycle_log, final_result


def print_lifecycle_table(cycle_log, workload_id, system_key, result):
    print(f"\n{'='*80}")
    print(f"  {workload_id}  |  {system_key}")
    print(f"{'='*80}")
    print(f"  {'Cyc':>3}  {'Units(->)':>12} {'Edges(->)':>12} {'Props/cum':>12}  {'Auth':>5}  {'Ops':>4}  {'Utility':>7}")
    print(f"  {'-'*80}")

    for c in cycle_log:
        before = str(c["graph_before"])
        after = str(c["graph_after"])
        auth = "YES" if c["authorized"] else "no "
        ops = c.get("auth_ops", 0)
        utility = c.get("utility", 0.0)
        props = c.get("proposals_generated_this_cycle", 0)
        cum = c.get("proposals_cumulative", 0)

        print(f"  {c['cycle']:>3}  {before:>12} {after:>12}  {props:>2}/{cum:>3}    {auth:>5}  {ops:>4}  {utility:.3f}")

    # Summary
    dnc_cycles = [c for c in cycle_log if "proposals_cumulative" in c]
    if dnc_cycles:
        total_props = dnc_cycles[-1]["proposals_cumulative"]
        auth_cycles = [c for c in cycle_log if c["authorized"]]
        total_ops = sum(c["auth_ops"] for c in cycle_log)
        avg_ops_per_auth = total_ops / max(len(auth_cycles), 1)

        print("\n  SUMMARY:")
        print(f"    Total proposals generated:  {total_props}")
        print(f"    Authorized cycles:           {len(auth_cycles)} / {len(cycle_log)}")
        print(f"    Total ops in authorized:     {total_ops}")
        print(f"    Avg ops per authorized cycle: {avg_ops_per_auth:.1f}")
        print(f"    Final mutations_count:        {result.structural_mutations}")
        print(f"    Final task_quality:          {result.task_quality:.3f}")

        # Diagnosis
        if len(auth_cycles) == len(cycle_log):
            print("  -> DIAG: ALL cycles authorized (controller NOT filtering)")
        elif len(auth_cycles) < len(cycle_log) * 0.3:
            print(f"  -> DIAG: Controller very selective ({len(auth_cycles)}/{len(cycle_log)} authorized)")
        else:
            print(f"  -> DIAG: Controller moderately selective ({len(auth_cycles)}/{len(cycle_log)} authorized)")

        if avg_ops_per_auth > 5:
            print(f"  -> DIAG: GENERATOR produces bloated proposals ({avg_ops_per_auth:.1f} ops/proposal)")
        elif avg_ops_per_auth > 2:
            print(f"  -> DIAG: Generator moderately large proposals ({avg_ops_per_auth:.1f} ops/proposal)")
        else:
            print(f"  -> DIAG: Generator proposal size normal ({avg_ops_per_auth:.1f} ops/proposal)")


def run_audit():
    workloads = ["W1_Static", "W3_FailureRecovery", "W6_RepeatedTasks", "W8_LongHorizon"]

    print("=" * 80)
    print("PHASE 13C.2 — MUTATION LIFECYCLE AUDIT")
    print("=" * 80)

    for workload_id in workloads:
        for system_key in ["DNC_Full", "DNC_M", "DNC_L"]:
            try:
                cycle_log, result = run_lifecycle_for_system(system_key, workload_id, base_seed=42)
                print_lifecycle_table(cycle_log, workload_id, system_key, result)
            except Exception as e:
                print(f"  ERROR on {workload_id}/{system_key}: {e}")

        print()


if __name__ == "__main__":
    run_audit()
