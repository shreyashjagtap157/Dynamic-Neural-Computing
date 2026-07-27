"""Tests for G-12.3 INV-8 BootstrapVerifier.

Per formal-model.md G-12.3: INV-8 (All Invariants Verified Before Execution)
cannot be formally verified within the formal model itself. Resolution: implement
a verified verifier that checks all invariants at bootstrap time.
"""

from __future__ import annotations

import sys
sys.path.insert(0, "src")

from dnc.invariants.verifier import (
    BootstrapVerifier,
    BootstrapVerificationReport,
    VerificationResult,
    VerificationStatus,
    VerificationResult,
)
from dnc.state.execution_state import ExecutionState


def test_ec1_bootstrap_verifier_passes_clean_state():
    """EC-1: BootstrapVerifier passes for clean ExecutionState (no violations)."""
    es = ExecutionState()
    verifier = BootstrapVerifier()
    report = verifier.verify(es)

    assert report.all_passed, f"Expected all passed, got: {[r.invariant_id for r in report.results if not r.passed]}"
    print("PASS: ec1_bootstrap_verifier_passes_clean_state")


def test_ec2_bootstrap_verifier_reports_failed_invariants():
    """EC-2: BootstrapVerifier reports failed invariants in failed_invariants list."""
    es = ExecutionState()
    es.W = None
    verifier = BootstrapVerifier()
    report = verifier.verify(es)

    assert not report.all_passed
    assert "INV-1" in report.failed_invariants
    print("PASS: ec2_bootstrap_verifier_reports_failed_invariants")


def test_ec3_bootstrap_verifier_null_M_detected():
    """EC-3: BootstrapVerifier detects null module registry M(t)."""
    es = ExecutionState()
    es.M = None
    verifier = BootstrapVerifier()
    report = verifier.verify(es)

    assert not report.all_passed
    assert "INV-1" in report.failed_invariants
    print("PASS: ec3_bootstrap_verifier_null_M_detected")


def test_ec4_bootstrap_verifier_null_C_detected():
    """EC-4: BootstrapVerifier detects null checkpoint record C(t)."""
    es = ExecutionState()
    es.C = None
    verifier = BootstrapVerifier()
    report = verifier.verify(es)

    assert not report.all_passed
    assert "INV-1" in report.failed_invariants
    print("PASS: ec4_bootstrap_verifier_null_C_detected")


def test_ec5_bootstrap_verifier_null_H_detected():
    """EC-5: BootstrapVerifier detects null history log H(t)."""
    es = ExecutionState()
    es.H = None
    verifier = BootstrapVerifier()
    report = verifier.verify(es)

    assert not report.all_passed
    assert "INV-1" in report.failed_invariants
    print("PASS: ec5_bootstrap_verifier_null_H_detected")


def test_ec6_bootstrap_verifier_negative_step_index():
    """EC-6: BootstrapVerifier detects negative step_index."""
    es = ExecutionState()
    es._step_index = -1
    verifier = BootstrapVerifier()
    report = verifier.verify(es)

    assert not report.all_passed
    assert "INV-7" in report.failed_invariants
    print("PASS: ec6_bootstrap_verifier_negative_step_index")


def test_ec7_bootstrap_verifier_zero_step_index_ok():
    """EC-7: BootstrapVerifier accepts step_index == 0 (initial state)."""
    es = ExecutionState()
    assert es._step_index == 0
    verifier = BootstrapVerifier()
    report = verifier.verify(es)

    inv7 = next((r for r in report.results if r.invariant_id == "INV-7"), None)
    assert inv7 is not None
    assert inv7.status == VerificationStatus.PASS
    print("PASS: ec7_bootstrap_verifier_zero_step_index_ok")


def test_ec8_bootstrap_verifier_all_results_tracked():
    """EC-8: All individual verification results are recorded in report.results."""
    es = ExecutionState()
    verifier = BootstrapVerifier()
    report = verifier.verify(es)

    invariant_ids = {r.invariant_id for r in report.results}
    expected = {"INV-1", "INV-2", "INV-4", "INV-5", "INV-6", "INV-7", "INV-STATE-3"}
    assert expected.issubset(invariant_ids), f"Missing: {expected - invariant_ids}"
    print("PASS: ec8_bootstrap_verifier_all_results_tracked")


def test_ec9_bootstrap_verifier_has_timestamp():
    """EC-9: BootstrapVerificationReport includes verified_at timestamp."""
    es = ExecutionState()
    verifier = BootstrapVerifier()
    report = verifier.verify(es)

    assert report.verified_at is not None
    assert isinstance(report.verified_at, float)
    print("PASS: ec9_bootstrap_verifier_has_timestamp")


def test_ec10_bootstrap_verifier_result_has_passed_property():
    """EC-10: VerificationResult.passed property returns True for PASS status."""
    r_pass = VerificationResult("INV-1", VerificationStatus.PASS, "ok")
    r_fail = VerificationResult("INV-1", VerificationStatus.FAIL, "not ok")
    r_skip = VerificationResult("INV-1", VerificationStatus.SKIP, "skipped")

    assert r_pass.passed is True
    assert r_fail.passed is False
    assert r_skip.passed is False
    print("PASS: ec10_bootstrap_verifier_result_has_passed_property")


if __name__ == "__main__":
    tests = [
        test_ec1_bootstrap_verifier_passes_clean_state,
        test_ec2_bootstrap_verifier_reports_failed_invariants,
        test_ec3_bootstrap_verifier_null_M_detected,
        test_ec4_bootstrap_verifier_null_C_detected,
        test_ec5_bootstrap_verifier_null_H_detected,
        test_ec6_bootstrap_verifier_negative_step_index,
        test_ec7_bootstrap_verifier_zero_step_index_ok,
        test_ec8_bootstrap_verifier_all_results_tracked,
        test_ec9_bootstrap_verifier_has_timestamp,
        test_ec10_bootstrap_verifier_result_has_passed_property,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/10 BootstrapVerifier tests passed")

    if failed > 0:
        print(f"FAIL: {failed}/10 BootstrapVerifier tests failed")
        exit(1)
    else:
        print("PASS: All BootstrapVerifier tests passed")
        exit(0)