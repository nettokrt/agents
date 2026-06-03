"""QA pipeline orchestrator.

Runs the four agents in sequence, validating each JSON payload against its
contract before handing it to the next agent, and pausing at the manual gates.

    story.txt → Agent 0 → schema_a
                Agent 1 → schema_b → GATE 1
                Agent 2 → *.spec.ts → GATE 2
                (stubbed CI)
                Agent 3 → triage   → GATE 3

Core rule: only the validated JSON output of agent N is passed to agent N+1 —
never raw LLM responses or conversation history.

Usage:
    python orchestrator.py --input story.txt
"""

from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()  # pull ANTHROPIC_API_KEY + MCP config from .env before importing agents

from pipeline import agent0_story_refiner as agent0  # noqa: E402
from pipeline import agent1_modeler as agent1  # noqa: E402
from pipeline import agent2_automator as agent2  # noqa: E402
from pipeline import agent3_triager as agent3  # noqa: E402
from pipeline import ci_stub, gates, schemas  # noqa: E402


def _banner(text: str) -> None:
    print(f"\n>>> {text}")


def run(story_path: str) -> int:
    story_text = open(story_path, encoding="utf-8").read()

    # --- Agent 0: Story Refiner (interactive) -----------------------------
    _banner("Agent 0 — Story Refiner")
    schema_a = agent0.refine(story_text)
    schemas.validate_schema_a(schema_a)
    print(f"    schema_a OK — {schema_a['historia_id']}: {schema_a['titulo']}")

    # --- Agent 1: Modeler --------------------------------------------------
    _banner("Agent 1 — Modeler")
    schema_b = agent1.model(schema_a)
    schemas.validate_schema_b(schema_b)
    print(f"    schema_b OK — {len(schema_b['cenarios'])} cenário(s)")

    gates.gate(
        1,
        "Revisar cenários (saída do Agent 1)",
        [f"{c['id']} [{c['prioridade']}/{c['tipo']}] {c['titulo']}" for c in schema_b["cenarios"]],
    )

    # --- Agent 2: Automator ------------------------------------------------
    _banner("Agent 2 — Automator")
    specs = agent2.automate(schema_b)

    gates.gate(
        2,
        "Revisar código gerado (saída do Agent 2)",
        [
            f"{s['scenario_id']} → {s['filename']} "
            f"(healed {s['healed']}x, {'pass' if s['passed'] else 'FAIL'})"
            for s in specs
        ],
    )

    # --- Stubbed CI + Agent 3: Bug Triager ---------------------------------
    _banner("CI (stubbed) → Agent 3 — Bug Triager")
    ci_results = ci_stub.simulate_ci(schema_b["suite"], specs)
    failed = [r for r in ci_results["results"] if r["status"] == "failed"]
    print(f"    CI: {len(ci_results['results'])} testes, {len(failed)} falha(s)")

    triage = agent3.triage(ci_results, schema_b)

    gates.gate(
        3,
        "Revisar triagem de bugs (saída do Agent 3)",
        [
            f"{t['scenario_id']} → {t['category']} ({t.get('route', '?')}): "
            f"{t.get('action_taken', '-')}"
            for t in triage.get("triage", [])
        ],
    )

    _banner("Pipeline concluído")
    print(json.dumps(triage, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the QA pipeline.")
    parser.add_argument("--input", required=True, help="Path to the user story (.txt)")
    args = parser.parse_args()

    try:
        return run(args.input)
    except gates.GateAborted as exc:
        print(f"\n[abortado] {exc}")
        return 1
    except schemas.SchemaValidationError as exc:
        print(f"\n[falha de validação] {exc}")
        return 2
    except FileNotFoundError:
        print(f"\n[erro] Arquivo de história não encontrado: {args.input}")
        return 2
    except KeyboardInterrupt:
        print("\n[interrompido]")
        return 130


if __name__ == "__main__":
    sys.exit(main())
