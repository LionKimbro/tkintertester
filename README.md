# tkintertester

A minimal, event-loop-native test harness for Tkinter GUI applications.

## The Problem

Tkinter doesn't play well with traditional testing approaches:

1. **Tk can't restart cleanly.** Once you destroy a Tk root and try to create another in the same process, things break. This makes pytest/unittest fixtures that create and tear down Tk windows unreliable or impossible.

2. **Tk runs a blocking event loop.** You can't just "call" your GUI from test code and inspect it—that blocks the mainloop or requires threading/async complexity.

3. **Tk silently swallows exceptions.** Exceptions in callbacks get printed to stderr but don't propagate—your test keeps running even though something failed.

## The Solution

Run tests *inside* the Tk event loop itself.

- One process, one thread, one `mainloop()`
- Tests execute as sequences of **step functions** scheduled via `root.after()`
- Step functions return control immediately—they never block
- The harness manages test progression, timeouts, and results
- Exceptions in callbacks are caught and fail the current test

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
    """Set up the app."""
    app["count"] = 0
    app["toplevel"] = tkinter.Toplevel(harness.g["root"])
    widgets["label"] = ttk.Label(app["toplevel"], text="0")
    widgets["label"].grid(row=0, column=0)
    widgets["button"] = ttk.Button(
        app["toplevel"], text="+1",
        command=lambda: increment()
    )
    widgets["button"].grid(row=1, column=0)

def reset():
    """Reset between tests."""
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
harness.set_resetfn(reset)
harness.set_timeout(5000)
harness.run_host(entry, flags="x")
harness.print_results()
```

## API Reference

### Test Registration

```python
harness.add_test(title, steps)
```
Register a test. `steps` is a list of nullary step functions.

### Configuration

```python
harness.set_timeout(timeout_ms)
```
Set the timeout for each test (default: 5000ms).

```python
harness.set_resetfn(app_reset)
```
Set a function to call between tests (to reset/clean up UI state).

### Running Tests

```python
harness.run_host(app_entry, flags="")
```
Harness creates a hidden Tk root and owns the lifecycle. Runs all registered tests, calling `app_entry()` before each test and `app_reset()` (if set) after each test. After all tests complete:
- If `"x"` in flags: exit mainloop
- Otherwise: call `app_entry()` one more time to transition into normal runtime

Flags:
- `"x"` — exit after tests complete
- `"s"` — show results in a Tk window after tests complete

```python
harness.attach_harness(root, flags="")
```
Attach the harness to an already-running application's root window. Tests run immediately. The `"x"` flag is not allowed (you can't exit an app you don't own).

### Results

```python
harness.get_results()      # Returns formatted string
harness.print_results()    # Prints to stdout
harness.write_results(filepath)  # Writes to file
harness.show_results()     # Displays in a Tk window
```

### Accessing State

```python
harness.tests    # List of test dictionaries (with results after execution)
harness.g        # Harness state dictionary (includes g["root"])
```

## Step Function Contract

Each step is a nullary function that returns `(action, value)`:

| Action | Value | Meaning |
|--------|-------|---------|
| `"next"` | `None` | Advance to next step immediately |
| `"next"` | `int` | Advance after N milliseconds |
| `"wait"` | `int` | Retry this step after N milliseconds |
| `"goto"` | `int` | Jump to step at index N |
| `"success"` | `None` | Test passed |
| `"success"` | `int` | Test passed, finalize after N ms |
| `"fail"` | `str` | Test failed with message |

If all steps complete without explicit `"success"` or `"fail"`, the test is considered successful.

## Exception Handling

The harness overrides `root.report_callback_exception` to catch exceptions in Tk callbacks. If an exception occurs during a test (in a button handler, `after()` callback, event binding, etc.), the test is immediately marked as failed with the exception traceback captured.

## Test Lifecycle

**With `run_host()`:**

1. Harness creates a hidden Tk root and enters `mainloop()`
2. For each test:
   - Call `app_entry()` (create windows, widgets)
   - Execute steps until success, failure, or timeout
   - Record result in the test object
   - Call `app_reset()` if set (clean up for next test)
3. After all tests:
   - If `"s"` flag: show results window
   - If `"x"` flag: exit mainloop
   - Otherwise: call `app_entry()` to transition into normal app runtime

**With `attach_harness()`:**

1. Attach to existing root window
2. Run tests immediately
3. After all tests: app continues running (no exit)

## Two-Track Testing Strategy

For larger applications (20+ files), split tests into two tracks:

- **Track 1: Logic tests** — Pure functions, data processing, validation. Use pytest normally; no Tk needed.
- **Track 2: GUI tests** — Widget behavior, user interactions. Use tkintertester.

This separation encourages keeping business logic out of GUI code.

## Structuring Your App for Testing

Design your app with `entry()` and `reset()` functions. The CLI or main script sets up the root and calls entry. Tests use the harness.

```python
# myapp/main.py
import tkinter as tk

g = {"count": 0}
widgets = {}
app = {"root": None, "toplevel": None}

def entry():
    """Create the UI. app['root'] must be set before calling."""
    g["count"] = 0
    app["toplevel"] = tk.Toplevel(app["root"])
    widgets["label"] = tk.Label(app["toplevel"], text="0")
    widgets["label"].grid(row=0, column=0)
    widgets["button"] = tk.Button(
        app["toplevel"], text="+1",
        command=handle_when_user_clicks_increment
    )
    widgets["button"].grid(row=1, column=0)

def reset():
    """Tear down the UI between tests."""
    app["toplevel"].destroy()
    widgets.clear()

def handle_when_user_clicks_increment():
    g["count"] += 1
    widgets["label"].config(text=str(g["count"]))
```

## Recommended Project Layout

Keep pytest tests and GUI tests in separate directories:

```
myproject/
  src/
    myapp/
      __init__.py
      main.py          # has entry(), reset()
      logic.py         # pure functions, no Tk dependency
  tests/               # pytest: logic tests (Track 1)
    test_logic.py
  guitests/            # tkintertester: GUI tests (Track 2)
    test_main_window.py
  pyproject.toml
```

Configure pytest to only discover tests in `tests/`:

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

A GUI test file imports the app and uses the harness:

```python
# guitests/test_main_window.py
from tkintertester import harness
from myapp import main as app

def test_increment():
    def step_click():
        app.widgets["button"].invoke()
        return ("next", None)

    def step_verify():
        if app.widgets["label"].cget("text") == "1":
            return ("success", None)
        return ("fail", "Counter should be 1")

    return [step_click, step_verify]

def app_entry():
    app.app["root"] = harness.g["root"]
    app.entry()

harness.add_test("Increment counter", test_increment())
harness.set_resetfn(app.reset)
harness.run_host(app_entry, flags="x")
harness.print_results()
```

Running tests:

```bash
python -m pytest                    # runs logic tests (Track 1)
python guitests/test_main_window.py # runs GUI tests (Track 2)
```

## Full Documentation

[docs/reference.md](docs/reference.md)

## License

CC0 1.0 Universal — Public Domain
