"""
w_lionscliapp.py — lionscliapp + tkintertester unified execution example
"""

import tkinter
from tkinter import ttk

import lionscliapp as app
from tkintertester import harness


# ─────────────────────────────────────────────────────────────
# Application state
# ─────────────────────────────────────────────────────────────

app_state = {
    "count": 0,
    "toplevel": None,
}

widgets = {}


def app_entry():
    """Create application UI."""
    app_state["count"] = 0

    win = tkinter.Toplevel(harness.g["root"])
    win.title("Counter")

    widgets["label"] = ttk.Label(win, text="0")
    widgets["label"].grid(row=0, column=0, padx=20, pady=10)

    widgets["button"] = ttk.Button(
        win,
        text="Increment",
        command=handle_increment
    )
    widgets["button"].grid(row=1, column=0, padx=20, pady=10)

    app_state["toplevel"] = win

    app_state["toplevel"].protocol(
        "WM_DELETE_WINDOW",
        handle_when_user_closes_window
    )


def handle_when_user_closes_window():
    app_state["toplevel"].destroy()
    harness.g["root"].quit()


def app_reset():
    """Reset application between tests."""
    if app_state["toplevel"]:
        app_state["toplevel"].destroy()
        app_state["toplevel"] = None
    widgets.clear()


def handle_increment():
    app_state["count"] += 1
    widgets["label"].config(text=str(app_state["count"]))


# ─────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────

def test_initial_state():
    def check():
        if widgets["label"].cget("text") == "0":
            return ("success", None)
        return ("fail", "Initial value should be 0")
    return [check]


def test_increment_once():
    def click():
        widgets["button"].invoke()
        return ("next", None)

    def verify():
        if widgets["label"].cget("text") == "1":
            return ("success", None)
        return ("fail", "Expected count = 1")

    return [click, verify]


# ─────────────────────────────────────────────────────────────
# Unified execution command
# ─────────────────────────────────────────────────────────────

def cmd_run():
    """
    Unified run command.

    Flags:
      x → exit after tests
      s → show results window after tests
    """

    flags = ""

    if app.ctx["runtime.tests.show"]:
        flags += "s"

    if app.ctx["runtime.tests.exit"]:
        flags += "x"

    if app.ctx["runtime.tests.enabled"]:
        harness.set_resetfn(app_reset)
        harness.add_test("Initial state", test_initial_state())
        harness.add_test("Increment once", test_increment_once())

    harness.run_host(app_entry, flags)


# ─────────────────────────────────────────────────────────────
# lionscliapp declarations
# ─────────────────────────────────────────────────────────────

app.declare_app("counter", "0.1")
app.describe_app("Counter demo with tkintertester")

app.declare_projectdir(".counter")

app.declare_key("runtime.tests.enabled", False)
app.declare_key("runtime.tests.show", False)
app.declare_key("runtime.tests.exit", False)

app.describe_key("runtime.tests.enabled", "Enable GUI tests")
app.describe_key("runtime.tests.show", "Show test results window")
app.describe_key("runtime.tests.exit", "Exit after tests complete")

app.declare_cmd("run", cmd_run)
app.describe_cmd("run", "Run application (optionally with tests)")

app.main()
