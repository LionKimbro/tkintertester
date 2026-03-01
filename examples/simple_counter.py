"""Simple example: test a counter app."""

import tkinter
from tkinter import ttk

from tkintertester import harness


# Application state
app = {
    "count": 0,
    "toplevel": None,
}

widgets = {}


def entry():
    """Set up the counter app."""
    app["count"] = 0

    app["toplevel"] = tkinter.Toplevel(harness.g["root"])
    app["toplevel"].title("Counter")

    app["toplevel"].protocol(
        "WM_DELETE_WINDOW",
        handle_when_user_closes_window
    )
    
    widgets["label"] = ttk.Label(app["toplevel"], text="0")
    widgets["label"].grid(row=0, column=0, padx=20, pady=10)

    widgets["button"] = ttk.Button(
        app["toplevel"],
        text="Increment",
        command=handle_when_user_clicks_increment
    )
    widgets["button"].grid(row=1, column=0, padx=20, pady=10)

def handle_when_user_closes_window():
    app["toplevel"].destroy()
    harness.quit()


def reset():
    """Reset app between tests."""
    if app["toplevel"] is not None:
        app["toplevel"].destroy()
        app["toplevel"] = None

    widgets.clear()


def handle_when_user_clicks_increment():
    app["count"] += 1
    widgets["label"].config(text=str(app["count"]))


# Tests

def test_initial_state():
    def step_check_initial_value():
        if widgets["label"].cget("text") == "0":
            return ("success", None)
        return ("fail", "Initial value should be 0")

    return [step_check_initial_value]


def test_increment_once():
    def step_click_button():
        widgets["button"].invoke()
        return ("next", None)

    def step_verify_count():
        if widgets["label"].cget("text") == "1":
            return ("success", None)
        return ("fail", f"Expected '1', got '{widgets['label'].cget('text')}'")

    return [step_click_button, step_verify_count]


def test_increment_three_times():
    def step_click_three_times():
        widgets["button"].invoke()
        widgets["button"].invoke()
        widgets["button"].invoke()
        return ("next", None)

    def step_verify_count():
        if widgets["label"].cget("text") == "3":
            return ("success", None)
        return ("fail", f"Expected '3', got '{widgets['label'].cget('text')}'")

    return [step_click_three_times, step_verify_count]


def test_visual_slow_increment():
    def step_show_window():
        return ("next", 500)

    def step_click_and_wait_1():
        widgets["button"].invoke()
        return ("next", 400)

    def step_click_and_wait_2():
        widgets["button"].invoke()
        return ("next", 400)

    def step_click_and_wait_3():
        widgets["button"].invoke()
        return ("next", 400)

    def step_verify_and_pause():
        if widgets["label"].cget("text") == "3":
            return ("success", 500)
        return ("fail", f"Expected '3', got '{widgets['label'].cget('text')}'")

    return [
        step_show_window,
        step_click_and_wait_1,
        step_click_and_wait_2,
        step_click_and_wait_3,
        step_verify_and_pause,
    ]


if __name__ == "__main__":
    harness.set_resetfn(reset)
    harness.set_timeout(5000)

    harness.add_test("Initial state is zero", test_initial_state())
    harness.add_test("Increment once", test_increment_once())
    harness.add_test("Increment three times", test_increment_three_times())
    harness.add_test("Visual: slow increment", test_visual_slow_increment())

    harness.run_host(entry, "x")  # You can take out "x" too, to just leave it running.

    # Print results
    print("\nResults:")
    for test in harness.tests:
        status = test["status"].upper()
        print(f"  [{status}] {test['title']}")
        if test["fail_message"]:
            print(f"         {test['fail_message']}")
