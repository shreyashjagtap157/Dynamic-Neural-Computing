import sys
sys.path.insert(0, "src")
try:
    from tests.conformance.test_execution_invariants import TestExecutionInvariant
    t = TestExecutionInvariant()
    for name in sorted(dir(t)):
        if name.startswith("test_"):
            try:
                getattr(t, name)()
                print(f"PASS: {name}")
            except Exception as e:
                print(f"FAIL: {name}: {e}")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
    import traceback
    traceback.print_exc()
