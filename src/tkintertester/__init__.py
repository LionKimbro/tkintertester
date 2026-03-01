"""
tkintertester

Minimal Tkinter test harness.

Public API intentionally small:
    - run_host
    - attach_harness
    - add_test
    - set_timeout
    - set_resetfn
    - print_results
    - write_results
    - show_results
    - get_root
"""

__version__ = "0.1.0"


from .harness import (
    run_host,
    attach_harness,
    add_test,
    set_timeout,
    set_resetfn,
    get_results,
    print_results,
    write_results,
    show_results,
    g as _g,
)

__all__ = [
    "run_host",
    "attach_harness",
    "add_test",
    "set_timeout",
    "set_resetfn",
    "get_results",
    "print_results",
    "write_results",
    "show_results",
    "get_root",
]


def get_root():
    """
    Return the Tk root owned by the harness.

    Raises:
        RuntimeError if the harness has not been started yet.
    """
    root = _g.get("root")
    if root is None:
        raise RuntimeError("Tk root not initialized (run_host not started)")
    return root
