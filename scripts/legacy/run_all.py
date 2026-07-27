"""Run all conformance tests and report PASS/FAIL.

Developed to work around a corrupted Python 3.12 toolchain that breaks the `ast`
import path used by `python -m pytest`. We import test classes directly, run
each `test_*` method in isolation, and capture stdout/stderr so the result file
contains only the summary lines.
"""
from __future__ import annotations

import io
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout

ROOT = "src"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Target test classes: (import path, class name)
TARGETS = [
    ("tests.conformance.test_decision_policy", "TestDecisionPolicy"),
    ("tests.conformance.test_replay_semantics", "TestReplaySemantics"),
    ("tests.conformance.test_evaluation", "TestEvaluationInvariant"),
    ("tests.conformance.test_execution_invariants", "TestExecutionInvariant"),
    ("tests.conformance.scheduler.test_scheduler_invariants", "TestINV_SCHED_Extended"),
    ("tests.conformance.runtime.test_replan_invariants", "TestINV_REPLAN_Extended"),
]

RESULT_FILE = "test_results.txt"


def _safe_instantiate(cls):
    """Try multiple instantiation signatures, returning an instance.

    Many conformance test classes are plain Python classes (not subclasses of
    `unittest.TestCase`), so they rely on no fixtures and a default ctor. Others
    subclass `TestCase` and accept either no args or `methodName=...`.
    """
    last_err: Exception | None = None
    candidates = [
        {},
        {"methodName": "test"},
    ]
    for kwargs in candidates:
        try:
            return cls(**kwargs)
        except Exception as exc:  # noqa: BLE001 - we want any error
            last_err = exc
            continue
    if last_err is not None:
        raise last_err
    return None


def main() -> int:
    import importlib

    results: list[tuple[str, str, str, float]] = []
    # [(file_label, test_name, status, duration)]

    for module_path, class_name in TARGETS:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)

        # Find all test methods by name pattern `test_`.
        test_names: list[str] = []
        for name in dir(cls):
            if not name.startswith("test_"):
                continue
            attr = getattr(cls, name)
            if not callable(attr):
                continue
            if isinstance(attr, type):  # skip nested classes
                continue
            test_names.append(name)

        try:
            instance = _safe_instantiate(cls)
        except Exception as exc:  # noqa: BLE001
            results.append((module_path, "<init>", f"FAIL_INIT: {exc}", 0.0))
            continue

        if instance is None:
            results.append((module_path, "<init>", "FAIL_INIT: cannot instantiate", 0.0))
            continue

        for test_name in sorted(test_names):
            method = getattr(instance, test_name, None)
            if method is None:
                results.append((module_path, test_name, "FAIL_NO_METHOD", 0.0))
                continue

            buf_out = io.StringIO()
            buf_err = io.StringIO()
            t0 = time.monotonic()
            try:
                with redirect_stdout(buf_out), redirect_stderr(buf_err):
                    method()
                elapsed = time.monotonic() - t0
                results.append((module_path, test_name, "PASS", elapsed))
            except AssertionError as exc:
                elapsed = time.monotonic() - t0
                err = f"{str(exc).splitlines()[0] if str(exc) else 'AssertionError'}"
                results.append((module_path, test_name, f"FAIL: {err[:160]}", elapsed))
            except Exception as exc:  # noqa: BLE001
                elapsed = time.monotonic() - t0
                tb_lines = traceback.format_exc().splitlines()
                tail = next(
                    (ln.strip() for ln in reversed(tb_lines) if ln.strip() and not ln.startswith("Traceback")),
                    "Exception",
                )
                results.append((module_path, test_name, f"ERROR: {tail[:160]}", elapsed))

    # Write summary file
    pass_count = sum(1 for _, _, status, _ in results if status == "PASS")
    fail_count = len(results) - pass_count
    per_file: dict[str, dict[str, int]] = {}
    for path, _, status, _ in results:
        per_file.setdefault(path, {"PASS": 0, "OTHER": 0})
        if status == "PASS":
            per_file[path]["PASS"] += 1
        else:
            per_file[path]["OTHER"] += 1

    with open(RESULT_FILE, "w", encoding="utf-8") as fh:
        fh.write(f"# Conformance test results\n\n")
        fh.write(f"Total: {len(results)} | PASS: {pass_count} | FAIL/ERR: {fail_count}\n\n")
        fh.write("Per file:\n")
        for path in sorted(per_file):
            counts = per_file[path]
            fh.write(
                f"  {counts['PASS']} pass / {counts['OTHER']} fail — {path}\n"
            )
        fh.write("\nAll test outcomes:\n")
        current_path: str | None = None
        for path, name, status, elapsed in results:
            if path != current_path:
                fh.write(f"\n--- {path} ---\n")
                current_path = path
            fh.write(f"  [{status[:4]:4s}] {name}  ({elapsed:.3f}s)\n")
        if fail_count:
            fh.write("\nFailure/Error details:\n")
            for path, name, status, _ in results:
                if status == "PASS":
                    continue
                fh.write(f"  {path}::{name} -> {status}\n")

    print(f"Wrote {RESULT_FILE}: pass={pass_count} fail/err={fail_count} total={len(results)}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
