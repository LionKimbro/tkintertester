# tkintertester

A minimal, event-loop-native test harness for Tkinter GUI applications.

## The Problem

Tkinter doesn't play well with traditional testing approaches:

1. **Tk can't restart cleanly.** Once you destroy a Tk root and try to create another in the same process, things break. This makes pytest/unittest fixtures that create and tear down Tk windows unreliable or impossible.

2. **Tk runs a blocking event loop.** You can't just "call" your GUI from test code and inspect it—that blocks the mainloop or requires threading/async complexity.

## The Solution

Run tests *inside* the Tk event loop itself.

- One process, one thread, one `mainloop()`
- Tests execute as sequences of **step functions** scheduled via `root.after()`
- Step functions return control immediately—they never block
- The harness manages test progression, timeouts, and results

## Design Principles

- **No async/await** — step-based execution driven by return values
- **No classes** — global functions and dictionaries
- **No simulation** — tests run in the real Tk event loop
- **Lightweight harness** — doesn't own or track your widgets

## Installation

```bash
pip install -e .
```

## Quick Example

```python
import tkinter
from tkinter import ttk
from tkintertester import harness

# Application state
app = {"count": 0, "toplevel": None}
widgets = {}

def entry():
    """Set up the app for a test."""
    app["count"] = 0
    app["toplevel"] = tkinter.Toplevel(harness.g["root"])
    widgets["label"] = ttk.Label(app["toplevel"], text="0")
    widgets["label"].grid(row=0, column=0)
    widgets["button"] = ttk.Button(
        app["toplevel"], text="+1",
        command=lambda: increment()
    )
    widgets["button"].grid(row=1, column=0)

def exit():
    """Tear down after a test."""
    app["toplevel"].destroy()
    widgets.clear()

def increment():
    app["count"] += 1
    widgets["label"].config(text=str(app["count"]))

# Define a test
def test_increment():
    def step_click():
        widgets["button"].invoke()
        return ("next", None)

    def step_verify():
        if widgets["label"].cget("text") == "1":
            return ("success", None)
        return ("fail", "Counter should be 1")

    return [step_click, step_verify]

# Run
harness.add_test("Increment counter", test_increment())
harness.run(entry, exit, timeout_ms=5000)

for test in harness.tests:
    print(f"[{test['status'].upper()}] {test['title']}")
```

## Step Function Contract

Each step is a nullary function that returns `(action, value)`:

| Action | Value | Meaning |
|--------|-------|---------|
| `"next"` | `None` | Advance to next step immediately |
| `"next"` | `int` | Advance after N milliseconds |
| `"wait"` | `int` | Retry this step after N milliseconds |
| `"success"` | `None` | Test passed |
| `"success"` | `int` | Test passed, finalize after N ms |
| `"fail"` | `str` | Test failed with message |

If all steps complete without explicit `"success"` or `"fail"`, the test is considered successful.

## Test Lifecycle

1. Harness creates a hidden Tk root and enters `mainloop()`
2. For each test:
   - Call your `entry()` function (create windows, widgets)
   - Execute steps until success, failure, or timeout
   - Record result in the test object
   - Call your `exit()` function (destroy windows, clean up)
3. When all tests complete, exit `mainloop()`

## Two-Track Testing Strategy

For larger applications (20+ files), consider splitting tests:

- **Track 1: Logic tests** — Pure functions, data processing, validation. Use pytest normally; no Tk needed.
- **Track 2: GUI tests** — Widget behavior, user interactions. Use tkintertester.

This separation encourages keeping business logic out of GUI code.

## License

CC0 1.0 Universal — Public Domain
