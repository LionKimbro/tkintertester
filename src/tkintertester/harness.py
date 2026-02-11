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
    "app_reset": None,                # Application reset function (for next test)
    "timeout_ms": 5000,               # Default timeout per test (ms)
    "exit_after_tests_executed": None,
    "show_results_in_tk_after_tests_executed": None
}


def set_timeout(timeout_ms):
    g["timeout_ms"] = timeout_ms

def set_resetfn(app_reset):
    g["app_reset"] = app_reset

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


def run_host(app_entry, flags=""):
    """Harness owns lifecycle and hosts application tests.

    Runs all tests, if any.
    Calls resetfn (declared with set_resetfn) between test executions.

    If "x" in flags, (e"x"it), it exits after running all tests.
    If "s" in flags, ("s"how), show results in a Toplevel after running all tests.
      (DO NOT USE "s" with "x".)
    """
    g["app_entry"] = app_entry
    g["exit_after_tests_executed"] = "x" in flags
    g["show_results_in_tk_after_tests_executed"] = "s" in flags

    root = tkinter.Tk()
    root.withdraw()

    _attach_harness(root)

    root.mainloop()


def attach_harness(root, flags=""):
    """Attach harness to an already-running application."""

    g["app_entry"] = None
    g["app_reset"] = None
    g["exit_after_tests_executed"] = False

    if "x" in flags:
        raise RuntimeError("may not use flag 'x' with attach_harness")

    g["show_results_in_tk_after_tests_executed"] = "s" in flags
    
    # attach mode does NOT set entry/exit
    _attach_harness(root)


def _attach_harness(root):
    """Attach harness scheduling onto an existing Tk root."""

    g["root"] = root
    g["test_index"] = 0

    def _report_callback_exception(exc, val, tb):
        if g.get("current_test") and not g.get("test_done"):
            message = f"Tk callback exception: {val}"
            _mark_fail(message, "".join(traceback.format_exception(exc, val, tb)))
        else:
            traceback.print_exception(exc, val, tb)

    root.report_callback_exception = _report_callback_exception
    root.after_idle(_advance_to_next_test)


def _advance_to_next_test():
    """Set up and begin the next test in the queue."""
    if g["test_index"] >= len(tests):

        if g["show_results_in_tk_after_tests_executed"]:
            show_results()
        
        # All tests finished
        if g["exit_after_tests_executed"]:
            g["root"].quit()
        
        # Transition into normal runtime
        if g["app_entry"]:
            g["app_entry"]()
        
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
        delay = 0 if value is None else value
        g["root"].after(delay, _execute_current_step)

    elif action == "wait":
        g["root"].after(value, _execute_current_step)

    elif action == "goto":
        g["current_step_index"] = value
        g["root"].after(0, _execute_current_step)

    else:
        _mark_fail(f"Unknown action: {action}")


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

    if g["app_reset"]:
        g["app_reset"]()

    g["test_index"] += 1
    g["root"].after(0, _advance_to_next_test)


def get_results():
    """Return a formatted string summarizing test results."""
    lines = []
    counts = {}

    lines.append("Results:")
    for test in tests:
        status = test.get("status") or "unknown"
        status_u = status.upper()
        counts[status] = counts.get(status, 0) + 1

        lines.append(f"  [{status_u}] {test['title']}")
        if test.get("fail_message"):
            lines.append(f"         {test['fail_message']}")

    if tests:
        lines.append("")
        summary = ", ".join(
            f"{counts.get(k, 0)} {k}"
            for k in sorted(counts)
        )
        lines.append(f"Summary: {summary}")

    return "\n".join(lines)


def print_results():
    """Print test results to stdout."""
    print(get_results())


def write_results(filepath):
    """Write test results to a file."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(get_results())


def show_results():
    """Display test results in a Tk window."""
    if g["root"] is None:
        raise RuntimeError("No Tk root available for show_results()")

    win = tkinter.Toplevel(g["root"])
    win.title("tkintertester results")

    text = tkinter.Text(
        win,
        width=80,
        height=24,
        wrap="word"
    )
    text.pack(fill="both", expand=True, padx=10, pady=10)

    text.insert("end", get_results())
    text.config(state="disabled")
