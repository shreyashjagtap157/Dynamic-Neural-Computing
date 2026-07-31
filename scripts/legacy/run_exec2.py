"""Legacy runner for execution invariant tests."""

import sys

sys.path.insert(0, "src")

from tests.conformance.test_execution_invariants import TestExecutionInvariants


def main() -> None:
    test_case = TestExecutionInvariants()
    for name in sorted(dir(test_case)):
        if not name.startswith("test_"):
            continue
        try:
            getattr(test_case, name)()
        except Exception as exc:
            print(f"FAIL: {name}: {exc}")
        else:
            print(f"PASS: {name}")


if __name__ == "__main__":
    main()
