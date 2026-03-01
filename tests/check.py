"""check.py -- Verify tkintertester self-test results.

Loads results.json written by run.py and checks each test against
expected outcomes. Exits 0 if all pass, 1 if any fail.

Usage:
    python tests/check.py
"""

import json
import pathlib
import sys

kRESULTS_PATH = pathlib.Path(__file__).parent / "results.json"

expected = [
    {"title": "Explicit success",   "status": "success"},
    {"title": "Explicit fail",      "status": "fail",    "fail_message": "deliberate"},
    {"title": "Steps exhausted",    "status": "success"},
    {"title": "Exception in step",  "status": "fail",    "fail_message": "Exception in step"},
    {"title": "Timeout",            "status": "timeout"},
    {"title": "Wait then succeed",  "status": "success"},
    {"title": "Goto then succeed",  "status": "success"},
    {"title": "Unexpected quit",    "status": "fail",    "fail_message": "app called quit() unexpectedly during test"},
    {"title": "Expected quit",      "status": "success"},
]


def check():
    results = json.loads(kRESULTS_PATH.read_text(encoding="utf-8"))

    passed = 0
    failed = 0

    for result, exp in zip(results, expected):
        ok = True
        reasons = []

        if result["title"] != exp["title"]:
            ok = False
            reasons.append(f"title: expected {exp['title']!r}, got {result['title']!r}")

        if result["status"] != exp["status"]:
            ok = False
            reasons.append(f"status: expected {exp['status']!r}, got {result['status']!r}")

        if "fail_message" in exp and result["fail_message"] != exp["fail_message"]:
            ok = False
            reasons.append(f"fail_message: expected {exp['fail_message']!r}, got {result['fail_message']!r}")

        if ok:
            print(f"  [PASS] {exp['title']}")
            passed += 1
        else:
            print(f"  [FAIL] {exp['title']}")
            for r in reasons:
                print(f"         {r}")
            failed += 1

    if len(results) != len(expected):
        print(f"  [FAIL] test count: expected {len(expected)}, got {len(results)}")
        failed += 1

    print()
    print(f"Summary: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    if not kRESULTS_PATH.exists():
        print(f"No results file at {kRESULTS_PATH}")
        print("Run tests/run.py first.")
        sys.exit(1)

    sys.exit(0 if check() else 1)
