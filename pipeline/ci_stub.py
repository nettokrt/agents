"""Stubbed test execution and CI feedback.

There is no homologation environment or live GitLab CI yet, so two things are
mocked here behind clean function boundaries:

1. ``run_playwright`` — used by Agent 2's self-healing ReAct loop. It does NOT
   run a browser; it inspects the generated spec for brittle selectors and
   returns a synthetic locator failure when it finds one, so the healing loop is
   exercised. Replace the body with a real ``npx playwright test`` invocation
   once an environment exists.

2. ``simulate_ci`` — produces a mock CI results payload for Agent 3 to triage.
   Replace with a real GitLab pipeline read (via the GitLab MCP) once CI runs.

Both are intentionally deterministic so the pipeline is demoable end-to-end
without external infrastructure.
"""

from __future__ import annotations

# Playwright's recommended, resilient locators. A spec that drives the page only
# through these is considered healthy by the stub runner.
_ROBUST_LOCATORS = (
    "getbyrole",
    "getbytestid",
    "getbylabel",
    "getbyplaceholder",
    "getbytext",
)


def run_playwright(spec_code: str, *, scenario_id: str = "") -> dict:
    """Stubbed Playwright run. Returns {passed, error_type?, message?}.

    TODO: replace with a real `npx playwright test <file>` call and parse its
    JSON reporter output once a runnable app URL is available.
    """
    low = spec_code.lower()
    uses_raw_locator = "page.locator(" in low
    uses_robust = any(token in low for token in _ROBUST_LOCATORS)

    if uses_raw_locator and not uses_robust:
        return {
            "passed": False,
            "error_type": "locator",
            "message": (
                "Selector error: spec relies on a brittle page.locator() CSS guess "
                "with no role/test-id based locator. Prefer getByRole/getByTestId."
            ),
            "scenario_id": scenario_id,
        }

    return {
        "passed": True,
        "scenario_id": scenario_id,
        "note": "stubbed run — no real Playwright execution performed",
    }


def simulate_ci(suite: str, specs: list[dict]) -> dict:
    """Produce a mock GitLab CI results payload for Agent 3.

    Passes every scenario except the second one, where it fabricates a timeout
    failure so the triager has something real to classify. ``specs`` is the list
    Agent 2 returns (each dict has ``scenario_id`` and ``titulo``).

    TODO: replace with a real GitLab pipeline/job read via the GitLab MCP.
    """
    results = []
    for index, spec in enumerate(specs):
        if index == 1:
            results.append(
                {
                    "scenario_id": spec["scenario_id"],
                    "titulo": spec["titulo"],
                    "status": "failed",
                    "error": (
                        "TimeoutError: locator.click: Timeout 30000ms exceeded.\n"
                        "Call log: waiting for getByRole('button', { name: 'Confirmar' })"
                    ),
                    "attempts": 2,
                }
            )
        else:
            results.append(
                {
                    "scenario_id": spec["scenario_id"],
                    "titulo": spec["titulo"],
                    "status": "passed",
                }
            )
    return {"suite": suite, "results": results, "source": "stubbed-ci"}
