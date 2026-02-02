"""harness.py - Test execution, scheduling, timeouts, and result recording."""

import tkinter
import time
import traceback


# Tests list - never rebound, contents updated with results
tests = []

# Glanceable state
g = {
    "root": None,                     # Hidden Tk root window
    "current_test": None,             # Currently executing test dict
    "current_step_index": 0,          # Index within current test's steps
    "test_done": False,               # Flag: current test completed
    "current_timeout_after_id": None, # Tk after() id for timeout
    "start_time": None,               # Timestamp when current test started
    "test_index": 0,                  # Index into tests list
    "app_entry": None,                # Application entry function
    "app_exit": None,                 # Application exit function
    "timeout_ms": 5000,               # Default timeout per test (ms)
}


def add_test(title, steps):
    """Register a test by appending to the global tests list."""
    test = {
        "title": title,
        "steps": list(steps),  # defensive copy
        "status": None,
        "fail_message": None,
        "exception": None,
    }
    tests.append(test)


def run(app_entry, app_exit, timeout_ms=5000):
    """Initialize harness and run all tests."""
    g["app_entry"] = app_entry
    g["app_exit"] = app_exit
    g["timeout_ms"] = timeout_ms
    g["test_index"] = 0

    g["root"] = tkinter.Tk()
    g["root"].withdraw()

    if tests:
        _advance_to_next_test()

    g["root"].mainloop()


def _advance_to_next_test():
    """Set up and begin the next test in the queue."""
    if g["test_index"] >= len(tests):
        g["root"].quit()
        return

    g["current_test"] = tests[g["test_index"]]
    g["current_step_index"] = 0
    g["test_done"] = False
    g["start_time"] = time.time()

    g["current_timeout_after_id"] = g["root"].after(
        g["timeout_ms"],
        _handle_when_current_test_times_out
    )

    if g["app_entry"]:
        g["app_entry"]()

    g["root"].after(0, _execute_current_step)


def _execute_current_step():
    """Execute the current step and handle its return value."""
    if g["test_done"]:
        return

    test = g["current_test"]
    steps = test["steps"]

    if g["current_step_index"] >= len(steps):
        _mark_success()
        return

    step_fn = steps[g["current_step_index"]]

    try:
        action, value = step_fn()
    except Exception:
        _mark_fail("Exception in step", traceback.format_exc())
        return

    if action == "fail":
        _mark_fail(value)
    elif action == "success":
        if value is None:
            _mark_success()
        else:
            g["root"].after(value, _mark_success)
    elif action == "next":
        g["current_step_index"] += 1
        if value is None:
            g["root"].after(0, _execute_current_step)
        else:
            g["root"].after(value, _execute_current_step)
    elif action == "wait":
        g["root"].after(value, _execute_current_step)


def _mark_success():
    """Mark current test as successful and proceed."""
    if g["test_done"]:
        return
    g["test_done"] = True
    g["current_test"]["status"] = "success"
    _finish_current_test()


def _mark_fail(message, exception=None):
    """Mark current test as failed and proceed."""
    if g["test_done"]:
        return
    g["test_done"] = True
    g["current_test"]["status"] = "fail"
    g["current_test"]["fail_message"] = message
    g["current_test"]["exception"] = exception
    _finish_current_test()


def _handle_when_current_test_times_out():
    """Handle test timeout."""
    g["current_timeout_after_id"] = None  # already fired
    if g["test_done"]:
        return
    g["test_done"] = True
    g["current_test"]["status"] = "timeout"
    g["current_test"]["fail_message"] = "Test timed out"
    _finish_current_test()


def _finish_current_test():
    """Clean up current test and advance to next."""
    if g["current_timeout_after_id"]:
        g["root"].after_cancel(g["current_timeout_after_id"])
        g["current_timeout_after_id"] = None

    if g["app_exit"]:
        g["app_exit"]()

    g["test_index"] += 1
    g["root"].after(0, _advance_to_next_test)
