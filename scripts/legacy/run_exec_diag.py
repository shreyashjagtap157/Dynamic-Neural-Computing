import sys
sys.path.insert(0, "src")

output_lines = []

try:
    from tests.conformance.test_execution_invariants import TestExecutionInvariant
    output_lines.append("IMPORT_OK")
except Exception as e:
    output_lines.append(f"IMPORT_FAIL: {e}")
    with open("exec_diag.txt", "w") as f:
        f.write("\n".join(output_lines))
    sys.exit(0)

tests = [
    "test_inv_exec1_precondition_before_dispatch",
    "test_inv_exec2_no_concurrent_step_dispatch",
    "test_inv_exec3_mutual_exclusion",
    "test_inv_exec4_critical_section_blocks_replan",
    "test_inv_inv5_no_preemption_during_act",
    "test_inv_exec6_timer_race_safety",
    "test_inv_exec7_handoff_coordinator_authority",
]

for test_name in tests:
    try:
        t = TestExecutionInvariant()
        getattr(t, test_name)()
        output_lines.append(f"PASS: {test_name}")
    except Exception as e:
        output_lines.append(f"FAIL: {test_name} -- {type(e).__name__}: {e}")

with open("exec_diag.txt", "w") as f:
    f.write("\n".join(output_lines))
