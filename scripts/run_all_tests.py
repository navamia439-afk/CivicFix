"""
CivicFix Comprehensive Test Suite Runner & System Verification Reporter
Discovers and executes all 5 core unit and integration test suites:
- tests/test_workflow.py (Field Worker Operations & End-to-End Workflow)
- tests/test_database_integrity.py (PRAGMA Checks, Cascades & Optimization)
- tests/test_state_machine.py (12 Lifecycle States & Notification Triggers)
- tests/test_analytics_and_reporting.py (Analytics, Before/After & CSV Exports)
- tests/test_system_integration.py (Multi-Role Concurrency & Invariants)

Produces a clear, formatted summary of all assertions and pass/fail states.
"""

import os
import sys
import unittest
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def run_all_tests():
    print("=" * 78)
    print("      CIVICFIX MUNICIPAL APPLICATION — SYSTEM TEST SUITE RUNNER")
    print("=" * 78)
    print(f"Project Directory: {PROJECT_ROOT}")
    print(f"Python Platform:   {sys.version.split()[0]} ({sys.platform})")
    print("-" * 78)

    start_time = time.time()
    tests_dir = os.path.join(PROJECT_ROOT, "tests")

    # Defined test suite files
    test_suites = [
        ("test_workflow.py", "Field Worker Operations & Workflow"),
        ("test_database_integrity.py", "Database Health & Foreign Keys"),
        ("test_state_machine.py", "Lifecycle State Machine & Triggers"),
        ("test_analytics_and_reporting.py", "Analytics, Before/After & CSV Exports"),
        ("test_system_integration.py", "End-to-End System Integration & Invariants"),
    ]

    total_tests = 0
    total_failures = 0
    total_errors = 0
    suite_results = []

    loader = unittest.TestLoader()

    for filename, description in test_suites:
        filepath = os.path.join(tests_dir, filename)
        if not os.path.exists(filepath):
            print(f"[SKIP] Test suite file missing: {filename}")
            continue

        print(f"\n>>> Running: {description} ({filename})")
        suite = loader.loadTestsFromName(f"tests.{filename[:-3]}")
        runner = unittest.TextTestRunner(verbosity=1)
        res = runner.run(suite)

        run_count = res.testsRun
        fails = len(res.failures)
        errs = len(res.errors)

        total_tests += run_count
        total_failures += fails
        total_errors += errs

        status = "PASSED" if (fails == 0 and errs == 0) else "FAILED"
        suite_results.append((description, filename, run_count, fails, errs, status))

    elapsed = time.time() - start_time

    # Executive Summary Table
    print("\n" + "=" * 78)
    print("                          TEST EXECUTION SUMMARY")
    print("=" * 78)
    print(f"{'Test Suite':<44} {'Tests':<8} {'Fails':<8} {'Errors':<8} {'Status'}")
    print("-" * 78)
    for desc, fname, cnt, f, e, st in suite_results:
        print(f"{desc:<44} {cnt:<8} {f:<8} {e:<8} {st}")

    print("-" * 78)
    passed_total = total_tests - total_failures - total_errors
    print(f"Total Tests Executed: {total_tests}")
    print(f"Total Assertions Passed: {passed_total} / {total_tests}")
    print(f"Total Failures:          {total_failures}")
    print(f"Total Errors:            {total_errors}")
    print(f"Total Execution Time:    {elapsed:.2f} seconds")

    if total_failures == 0 and total_errors == 0:
        print("\n>>> ALL TESTS PASSED! ALL SYSTEM GUARDS & INVARIANTS ARE VERIFIED. <<<")
        print("=" * 78)
        return 0
    else:
        print("\n>>> WARNING: ONE OR MORE TEST SUITES ENCOUNTERED FAILURES. <<<")
        print("=" * 78)
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
