"""run.py -- tkintertester self-test suite.

Runs a battery of tests against tkintertester itself, using known-correct
and known-incorrect behaviors. Writes results to results.json.

Usage:
    python tests/run.py
"""

import pathlib
from tkintertester import harness

kRESULTS_PATH = pathlib.Path(__file__).parent / "results.json"
kTIMEOUT_MS   = 500


def entry():
    pass


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_explicit_success():
    def step():
        return ("success", None)
    return [step]


def test_explicit_fail():
    def step():
        return ("fail", "deliberate")
    return [step]


def test_steps_exhausted():
    def step_one():
        return ("next", None)
    def step_two():
        return ("next", None)
    return [step_one, step_two]


def test_exception_in_step():
    def step():
        raise RuntimeError("boom")
    return [step]


def test_timeout():
    def step():
        return ("wait", 50)
    return [step]


def test_wait_then_succeed():
    state = {"waited": False}
    def step():
        if not state["waited"]:
            state["waited"] = True
            return ("wait", 50)
        return ("success", None)
    return [step]


def test_goto_then_succeed():
    state = {"count": 0}
    def step():
        state["count"] += 1
        if state["count"] < 3:
            return ("goto", 0)
        return ("success", None)
    return [step]


def test_unexpected_quit():
    def step():
        harness.quit()
        return ("success", None)
    return [step]


def test_expected_quit():
    def step():
        harness.quit()
        if harness.g["exit_requested"]:
            return ("success", None)
        return ("fail", "exit_requested not set after harness.quit()")
    return [step]


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    harness.set_timeout(kTIMEOUT_MS)

    harness.add_test("Explicit success",   test_explicit_success())
    harness.add_test("Explicit fail",      test_explicit_fail())
    harness.add_test("Steps exhausted",    test_steps_exhausted())
    harness.add_test("Exception in step",  test_exception_in_step())
    harness.add_test("Timeout",            test_timeout())
    harness.add_test("Wait then succeed",  test_wait_then_succeed())
    harness.add_test("Goto then succeed",  test_goto_then_succeed())
    harness.add_test("Unexpected quit",    test_unexpected_quit())
    harness.add_test("Expected quit",      test_expected_quit(), "q")

    harness.run_host(entry, "x")

    harness.write_results(kRESULTS_PATH, "J")
    print(f"Results written to {kRESULTS_PATH}")
