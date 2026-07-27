import sys
import traceback

sys.path.insert(0, "src")
results = []

try:
    from tests.conformance.test_execution_invariants import TestExecutionInvariant
    t = TestExecutionInvariant()
    for name in sorted(dir(t)):
        if name.startswith("test_"):
            try:
                getattr(t, name)()
                results.append(f"PASS: {name}")
            except Exception as e:
                tb = traceback.format_exc()
                results.append(f"FAIL: {name}: {e}\n{tb}")
except Exception as e:
    results.append(f"IMPORT ERROR: {e}\n{traceback.format_exc()}")

with open("exec_test_results.txt", "w") as f:
    f.write("\n\n".join(results))
