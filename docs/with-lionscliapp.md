
# Using tkintertester with lionscliapp

This document explains how to integrate **tkintertester** with **lionscliapp**, preserving:

* lionscliapp’s lifecycle model
* tkintertester’s single-mainloop execution model
* strict separation of declaration and runtime
* a unified execution path (no separate test command required)

---

# Core Principle

lionscliapp owns:

* CLI parsing
* application identity
* configuration
* command dispatch
* lifecycle phases

tkintertester owns:

* test scheduling
* step execution
* timeout handling
* result recording

They operate at different layers.

---

# Execution Model (Unified)

👉 tkintertester is invoked from inside the normal `run` command.

There is no separate “test mode”.

Instead:

* Tests are optionally registered.
* Harness behavior is controlled via flags.

---

# lionscliapp Lifecycle Reminder

```

declaring  →  running  →  shutdown

```

Tkinter and tkintertester must start during:

```

running phase only

```

---

# Recommended Command Layout

Single command:

```

myapp run

```

Configuration controls behavior:

```

runtime.tests.enabled
runtime.tests.show
runtime.tests.exit

````

---

# Minimal Integration Example

## 1. Declaration Phase

```python
import lionscliapp as app

app.declare_app("counter", "1.0")
app.describe_app("Example counter application")

app.declare_cmd("run", cmd_run)
````

No Tk or harness logic here.

---

## 2. Application Lifecycle Functions

```python
def app_entry():
    build_ui()

def app_reset():
    destroy_ui()
```

Register reset once:

```python
from tkintertester import harness

harness.set_resetfn(app_reset)
```

---

## 3. Unified Run Command

This is the canonical pattern.

```python
def cmd_run():

    flags = ""

    if app.ctx["runtime.tests.show"]:
        flags += "s"

    if app.ctx["runtime.tests.exit"]:
        flags += "x"

    if app.ctx["runtime.tests.enabled"]:
        register_tests()

    harness.run_host(app_entry, flags)
```

Behavior:

* If tests exist → they run first
* If no tests → app starts normally
* `"s"` → show results window after tests
* `"x"` → exit after tests

---

# Host Model

tkintertester owns the Tk lifecycle.

```
run_host():
    create hidden root
    enter mainloop
    schedule _advance_to_next_test()
```

Key rule:

👉 `_advance_to_next_test()` always runs once.

It decides:

* run tests
* start application
* exit

---

# Attach Mode (Optional)

Attach mode allows tests to run against an already-running application.

```python
harness.attach_harness(root, "s")
```

Attach mode:

* does NOT call `app_entry`
* does NOT call `app_reset`
* assumes app already running

Use cases:

* developer-triggered test runs
* debugging tools
* runtime automation scripts

---

# Why This Architecture Works

Because:

### lionscliapp controls:

* invocation semantics
* configuration
* command selection

### tkintertester controls:

* behavior inside the Tk event loop

No lifecycle conflict.

---

# Responsibilities Summary

## lionscliapp

* decides which command runs
* builds runtime context (`app.ctx`)
* registers tests when desired
* launches harness

## tkintertester

* executes tests
* schedules steps
* records results

---

# Important Rules

## Do NOT start Tk during declaration phase

Bad:

```python
root = tkinter.Tk()   # ❌
```

Correct:

```python
def cmd_run():
    harness.run_host(app_entry)
```

---

## Only ONE Tk mainloop per process

tkintertester assumes:

```
single-threaded
single-loop
real Tk environment
```

---

## Philosophy

This design avoids:

* async frameworks
* GUI mocking
* alternate test runners
* duplicate run/test command paths

Instead:

> lionscliapp decides *when execution begins*.
> tkintertester decides *what happens inside Tk*.

The harness does not infer intent.
Configuration defines behavior.

