"""Run all conformance tests and report results."""
import sys
import traceback
import time

sys.path.insert(0, "src")

# Test modules to run
test_modules = [
    ("INV-POL (Decision Policy)", "tests.conformance.test_decision_policy", "TestDecisionPolicy"),
    ("INV-REP (Replay Semantics)", "tests.conformance.test_replay_semantics", "TestReplaySemantics"),
    ("INV-EVAL (Evaluation)", "tests.conformance.test_evaluation", "TestEvaluationInvariant"),
    ("INV-EXEC (Execution)", "tests.conformance.test_execution_invariants", "TestExecutionInvariant"),
    ("INV-SCHED (Scheduler)", "tests.conformance.scheduler.test_scheduler_invariants", "TestINV_SCHED_Extended"),
]

all_results = []
for suite_name, module_path, class_name in test_modules:
    print(f"\n{'='*60}")
    print(f"  {suite_name}")
    print(f"{'='*60}")
    try:
        mod = __import__(module_path, fromlist=[class_name])
        cls = getattr(mod, class_name)
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method_name in sorted(methods):
            try:
                start = time.time()
                getattr(instance, method_name)()
                elapsed = (time.time() - start) * 1000
                all_results.append(("PASS", method_name, suite_name, f"{elapsed:.1f}ms"))
                print(f"  PASS: {method_name} ({elapsed:.1f}ms)")
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                all_results.append(("FAIL", method_name, suite_name, str(e)[:200]))
                print(f"  FAIL: {method_name} ({elapsed:.1f}ms) -- {e}")
                traceback.print_exc()
    except Exception as e:
        all_results.append(("ERROR", module_path, suite_name, str(e)[:200]))
        print(f"  ERROR importing {module_path}: {e}")
        traceback.print_exc()

# Summary
print(f"\n{'='*60}")
print(f"  SUMMARY")
print(f"{'='*60}")

passed = sum(1 for r in all_results if r[0] == "PASS")
failed = sum(1 for r in all_results if r[0] == "FAIL")
errors = sum(1 for r in all_results if r[0] == "ERROR")
total = len(all_results)

print(f"\n  Total: {total}  Passed: {passed}  Failed: {failed}  Errors: {errors}")
print(f"  Pass rate: {passed/total*100:.1f}%" if total > 0 else "  No tests run")

if failed > 0 or errors > 0:
    print(f"\n  FAILURES:")
    for r in all_results:
        if r[0] != "PASS":
            print(f"    [{r[0]}] {r[1]} ({r[2]}): {r[3]}")
