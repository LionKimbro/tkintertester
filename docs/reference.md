# tkintertester Reference

A minimal, event-loop-native test harness for Tkinter GUI applications.
Tests run inside the real Tk event loop — no async, no threads, no separate process.

---

## Overview

tkintertester works by taking over (or attaching to) a Tk mainloop and running
your tests as a sequence of scheduled callbacks. Each test is a list of *step
functions*. The harness calls them one at a time, and each step returns a tuple
telling the harness what to do next.

The application under test is created fresh before each test and torn down
after, so tests are isolated from one another.

---

## Concepts

### Host mode vs. attach mode

**Host mode** (`run_host`) is the normal case. The harness creates a hidden Tk
root, runs all tests, and then either exits or hands control to the application
for normal runtime. Your `entry()` function is called before each test to
create a fresh application instance.

**Attach mode** (`attach_harness`) is for programs that already own their Tk
root. You hand the root to the harness, it runs tests against the already-live
application, and then steps aside. The harness never calls `entry()` or
`reset()` and never terminates the mainloop.

### Step functions

A step function is a nullary callable that returns `(action, value)`. It must
return without blocking — no `time.sleep`, no waiting loops. If you need to
wait, return `("wait", ms)` and the harness will call you again after the
delay.

| Return value | Meaning |
|---|---|
| `("next", None)` | Advance to the next step immediately |
| `("next", ms)` | Advance to the next step after `ms` milliseconds |
| `("wait", ms)` | Repeat this step after `ms` milliseconds |
| `("success", None)` | Mark the test successful immediately |
| `("success", ms)` | Mark the test successful after `ms` milliseconds |
| `("fail", reason)` | Fail the test immediately with the given reason string |
| `("goto", index)` | Jump to step at `index` and execute it immediately |

If all steps are exhausted without an explicit `"success"` or `"fail"`, the
test is considered successful.

If a step raises an exception, the test is failed with status `"fail"` and the
traceback is captured in the test's `exception` field.

### Test lifecycle

For each test (in host mode):

1. `entry()` is called — creates the application instance
2. A timeout timer is started (`timeout_ms` milliseconds)
3. Steps execute in order, driven by their return values
4. When the test concludes (success, fail, or timeout):
   - The timeout timer is cancelled
   - `reset()` is called (if set) — tears down the application instance
5. The harness moves on to the next test

### Application exit

The application must never call `root.quit()` directly. All exit requests must
go through `harness.quit()`, which lets the harness intercept the signal during
tests and handle it appropriately.

---

## Setup

Import the harness:

```python
from tkintertester import harness
```

Or import individual names:

```python
from tkintertester import harness, add_test, run_host
```

---

## API Reference

### `run_host(app_entry, flags="")`

Start the harness in host mode. Creates a hidden Tk root, runs all registered
tests, then either exits or transitions into normal runtime.

Blocks until the Tk mainloop exits. Call this last, after all tests are
registered.

**`app_entry`** — nullary callable. Called before each test to create a fresh
application instance (typically a `Toplevel` rooted under `harness.g["root"]`).
Also called once after all tests complete if not exiting.

**flags:**

| Flag | Meaning |
|---|---|
| `"x"` | Exit after tests complete. The mainloop quits and `run_host` returns. |
| `"s"` | Show a results window after tests complete. The program does not transition into normal runtime. The mainloop exits when the results window is closed. |

```python
harness.run_host(entry)          # run tests, then continue as normal app
harness.run_host(entry, "x")     # run tests, then exit
harness.run_host(entry, "s")     # run tests, show results window, then continue
```

---

### `attach_harness(root, flags="")`

Attach the harness to an already-running Tk application. The harness schedules
tests onto the existing event loop and runs them against the live application
instance. Does not call `entry()` or `reset()`. Does not terminate the
mainloop.

**`root`** — the application's existing `tk.Tk` instance (or any object
supporting `.after()`).

**flags:**

| Flag | Meaning |
|---|---|
| `"s"` | Show a results window after tests complete. |
| `"x"` | **Disallowed.** Raises `RuntimeError`. |

```python
root = tkinter.Tk()
# ... build your app ...
harness.attach_harness(root)
root.mainloop()
```

---

### `add_test(title, steps, flags="")`

Register a test. Tests run in the order they are registered.

**`title`** — human-readable name shown in results.

**`steps`** — list of step functions (nullary callables). The list is copied
defensively.

**flags:**

| Flag | Meaning |
|---|---|
| `"q"` | This test expects the app to call `harness.quit()`. The harness will not auto-fail the test if `quit()` is called during execution. |

```python
harness.add_test("Button increments counter", [
    step_click_button,
    step_verify_count,
])

harness.add_test("Close button quits app", [
    step_click_close,
    step_verify_quit,
], "q")
```

---

### `set_timeout(timeout_ms)`

Set the per-test timeout in milliseconds. Default is `5000` (5 seconds).
If a test does not conclude within this time, it is marked `"timeout"`.

Must be called before `run_host` or `attach_harness`.

```python
harness.set_timeout(2000)   # 2 second timeout for all tests
```

---

### `set_resetfn(app_reset)`

Register a reset function to be called after each test in host mode.
The reset function should tear down the application instance created by
`entry()` (e.g., destroy the Toplevel, clear widget references).

```python
def reset():
    if app["toplevel"]:
        app["toplevel"].destroy()
        app["toplevel"] = None
    widgets.clear()

harness.set_resetfn(reset)
```

---

### `quit()`

Signal that the application wants to exit. Call this instead of
`get_root().quit()` or `root.quit()`.

Behavior depends on context:

| Context | Behavior |
|---|---|
| No test running (runtime) | Calls `root.quit()` immediately. |
| Test running, `"q"` flag set | Sets `g["exit_requested"] = True`. Test continues normally. |
| Test running, no `"q"` flag | Sets `g["exit_requested"] = True`, then immediately fails the test with `"app called quit() unexpectedly during test"`. |

`g["exit_requested"]` is reset to `False` at the start of every test. It does
not affect post-suite behavior; only `exit_after_tests_executed` (the `"x"`
flag on `run_host`) governs whether the harness exits after all tests.

```python
def handle_when_user_closes_window():
    app["toplevel"].destroy()
    harness.quit()              # not root.quit()
```

Testing that quit works:

```python
def test_close_button_quits():
    def step_click_close():
        widgets["close_button"].invoke()
        return ("next", None)

    def step_verify_quit():
        if harness.g["exit_requested"]:
            return ("success", None)
        return ("fail", "quit was not called")

    return [step_click_close, step_verify_quit]

harness.add_test("Close button quits", test_close_button_quits(), "q")
```

---

### `get_results(flags="")`

Return a string summarizing test outcomes.

**flags:**

| Flag | Meaning |
|---|---|
| (none) | Human-readable text summary. |
| `"J"` | JSON array of result objects. Steps are represented by function name strings. |

The JSON format per test:

```json
{
  "title": "My test",
  "steps": ["step_one", "step_two"],
  "allows_quit": false,
  "status": "success",
  "fail_message": null,
  "exception": null
}
```

`status` is one of `"success"`, `"fail"`, `"timeout"`, or `null` (not yet run).

---

### `print_results(flags="")`

Print `get_results()` to stdout. Accepts the same flags as `get_results()`.

```python
harness.print_results()       # human-readable
harness.print_results("J")    # JSON
```

---

### `write_results(filepath, flags="")`

Write `get_results()` to a file (utf-8). Accepts the same flags as
`get_results()`.

```python
harness.write_results("results.txt")
harness.write_results("results.json", "J")
```

---

### `show_results(flags="")`

Display `get_results()` in a Tk `Toplevel` window. Requires the harness to be
running (i.e., `g["root"]` must be set). Accepts the same flags as
`get_results()`.

Also called automatically after tests if the `"s"` flag was passed to
`run_host` or `attach_harness`. Returns the `Toplevel` window it creates.

```python
harness.show_results()        # human-readable window
harness.show_results("J")     # JSON window
```

---

### `get_root()`

Return the Tk root owned by the harness. Useful when the application module
needs a parent for Toplevels but should not import the harness directly.

Raises `RuntimeError` if called before the harness has started.

```python
win = tkinter.Toplevel(harness.get_root())
```

Note: in host mode, application code can also access the root directly via
`harness.g["root"]`.

---

## Global state

The harness exposes two module-level globals for power users.

### `harness.g`

Dictionary of all scalar mutable harness state. Safe to read at any time;
mutate with care.

| Key | Type | Description |
|---|---|---|
| `"root"` | `tk.Tk` or None | The Tk scheduler surface. |
| `"current_test"` | dict or None | The currently executing test dict. |
| `"current_step_index"` | int | Index of the current step within the current test. |
| `"test_done"` | bool | True once the current test has concluded. |
| `"current_timeout_after_id"` | str or None | Tk `after()` ID for the active timeout. |
| `"start_time"` | float or None | `time.time()` when the current test started. |
| `"test_index"` | int | Index of the next test to run. |
| `"app_entry"` | callable or None | The application entry function (host mode). |
| `"app_reset"` | callable or None | The application reset function (host mode). |
| `"timeout_ms"` | int | Per-test timeout in milliseconds (default 5000). |
| `"exit_after_tests_executed"` | bool or None | If true, harness quits after all tests. |
| `"show_results_in_tk_after_tests_executed"` | bool or None | If true, shows results window after all tests. |
| `"exit_requested"` | bool | Set by `harness.quit()` during an allows-quit test. Reset at the start of every test. |

### `harness.tests`

Module-level list of test dictionaries. Never rebound; mutated in place as
tests run.

Each test dict:

| Key | Type | Description |
|---|---|---|
| `"title"` | str | Human-readable test name. |
| `"steps"` | list | List of step callables. |
| `"allows_quit"` | bool | True if the test declared the `"q"` flag. |
| `"status"` | str or None | `"success"`, `"fail"`, `"timeout"`, or None. |
| `"fail_message"` | str or None | Failure reason, if any. |
| `"exception"` | str or None | Captured traceback, if any. |

---

## Complete example

```python
"""counter.py — counter app with tkintertester tests."""

import tkinter
from tkinter import ttk
from tkintertester import harness


# ── Application state ─────────────────────────────────────────────────────────

app = {"count": 0, "toplevel": None}
widgets = {}


def entry():
    app["count"] = 0
    win = tkinter.Toplevel(harness.g["root"])
    win.title("Counter")
    win.protocol("WM_DELETE_WINDOW", handle_when_user_closes_window)
    app["toplevel"] = win

    widgets["label"] = ttk.Label(win, text="0")
    widgets["label"].grid(row=0, column=0, padx=20, pady=10)

    widgets["button"] = ttk.Button(win, text="Increment",
                                   command=handle_when_user_clicks_increment)
    widgets["button"].grid(row=1, column=0, padx=20, pady=10)


def reset():
    if app["toplevel"]:
        app["toplevel"].destroy()
        app["toplevel"] = None
    widgets.clear()


def handle_when_user_closes_window():
    app["toplevel"].destroy()
    harness.quit()


def handle_when_user_clicks_increment():
    app["count"] += 1
    widgets["label"].config(text=str(app["count"]))


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_initial_state():
    def step_check_label():
        if widgets["label"].cget("text") == "0":
            return ("success", None)
        return ("fail", "initial label should be 0")
    return [step_check_label]


def test_increment_once():
    def step_click():
        widgets["button"].invoke()
        return ("next", None)
    def step_verify():
        if widgets["label"].cget("text") == "1":
            return ("success", None)
        return ("fail", f"expected 1, got {widgets['label'].cget('text')}")
    return [step_click, step_verify]


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    harness.set_timeout(5000)
    harness.set_resetfn(reset)

    harness.add_test("Initial state is zero", test_initial_state())
    harness.add_test("Increment once",        test_increment_once())

    harness.run_host(entry, "x")

    harness.print_results()
```
