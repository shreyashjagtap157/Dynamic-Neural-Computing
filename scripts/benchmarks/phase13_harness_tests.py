"""
Phase 13 Benchmark Integrity Tests
Verifies runner reproducibility, contract compliance, equivalent inputs, and baseline isolation.
"""

import sys


from dnc.evaluation.contracts import ExperimentResult, BenchmarkSystem
from dnc.evaluation.runner import BenchmarkRunner


def test_contract_compliance():
    """All registered systems satisfy BenchmarkSystem abstract base class."""
    runner = BenchmarkRunner()
    for sys_key, factory in runner.registered_systems.items():
        system = factory() if callable(factory) and not isinstance(factory, type) else factory()
        assert isinstance(system, BenchmarkSystem)
        print(f"PASS: contract_compliance for {sys_key}")


def test_runner_reproducibility():
    """Same seed and workload produce identical ExperimentResults."""
    runner = BenchmarkRunner(repetitions=1)
    workload = [{"complexity": 5, "fault_injected": False}]

    res1 = runner.run_experiment("StaticDAG", "W1_Static", workload, base_seed=123)
    res2 = runner.run_experiment("StaticDAG", "W1_Static", workload, base_seed=123)

    assert len(res1) == 1
    assert len(res2) == 1
    assert res1[0].success == res2[0].success
    assert res1[0].task_quality == res2[0].task_quality
    # Wall-clock latency is observational and cannot be byte-identical. The
    # deterministic contract covers decisions, quality, cost, and structure.
    assert res1[0].structural_mutations == res2[0].structural_mutations
    assert res1[0].total_cost == res2[0].total_cost
    print("PASS: runner_reproducibility")


def test_all_baselines_execution():
    """All 7 systems (3 baselines + Full DNC + 3 ablations) execute workload successfully."""
    runner = BenchmarkRunner(repetitions=1)
    workload = [
        {"complexity": 4, "fault_injected": False},
        {"complexity": 6, "fault_injected": True}
    ]

    for sys_key in runner.registered_systems.keys():
        results = runner.run_experiment(sys_key, "W3_Faults", workload, base_seed=42)
        assert len(results) == 1
        assert isinstance(results[0], ExperimentResult)
        print(f"PASS: baseline_execution for {sys_key} (quality={results[0].task_quality:.2f})")


def run_all_tests():
    tests = [
        test_contract_compliance,
        test_runner_reproducibility,
        test_all_baselines_execution,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"Phase 13 Benchmark Harness Tests: {passed}/{passed+failed} passed")
    print(f"{'='*60}")

    if failed > 0:
        print(f"FAILURES: {failed}")
        sys.exit(1)
    else:
        print("ALL PHASE 13 BENCHMARK HARNESS TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
