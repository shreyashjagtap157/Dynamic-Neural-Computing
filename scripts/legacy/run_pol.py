import sys
sys.path.insert(0, "src")
from tests.conformance.test_decision_policy import TestDecisionPolicy
t = TestDecisionPolicy()
for name in sorted(dir(t)):
    if name.startswith("test_"):
        try:
            getattr(t, name)()
            print(f"PASS: {name}")
        except Exception as e:
            print(f"FAIL: {name}: {e}")
