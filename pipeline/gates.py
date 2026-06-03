"""Manual approval gates.

Gates are blocking: they print a summary of the stage's output and read a y/n
from the terminal. Anything other than 'y' aborts the run (raises GateAborted,
which the orchestrator catches for a clean exit).

Gate 1 — after Agent 1 (review scenarios)
Gate 2 — after Agent 2 (review generated code)
Gate 3 — after Agent 3 (review triaged bugs)
"""

from __future__ import annotations


class GateAborted(Exception):
    """Raised when the operator declines a gate."""


def gate(number: int, title: str, summary_lines: list[str]) -> None:
    bar = "=" * 64
    print(f"\n{bar}")
    print(f" GATE {number}: {title}")
    print(bar)
    for line in summary_lines:
        print(f"  {line}")
    print(bar)

    answer = input(f"Approve gate {number} and continue? [y/N] ").strip().lower()
    if answer != "y":
        raise GateAborted(f"Gate {number} ({title}) was not approved.")
