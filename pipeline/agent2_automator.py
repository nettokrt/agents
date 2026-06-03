"""Agent 2 — Automator.

Turns each scenario (schema_b) into a Playwright spec (.spec.ts), self-heals
selector errors with a ReAct loop (up to 3 iterations), writes the file under
generated_tests/, and commits it to the GitLab repo via the GitLab MCP.

Test execution during healing is stubbed (ci_stub.run_playwright) — no
homologation environment yet.
"""

from __future__ import annotations

import json
import os
import pathlib
import re

from . import anthropic_client as ac
from . import ci_stub
from . import mcp

OUTPUT_DIR = pathlib.Path(__file__).resolve().parent.parent / "generated_tests"
MAX_HEAL_ITERATIONS = 3

GEN_SYSTEM = """\
Você é o Agent 2 (Automatizador) de um pipeline de QA, especialista em Playwright
com TypeScript.

Gere UM arquivo de teste Playwright (.spec.ts) para o cenário fornecido.

Regras:
- Use @playwright/test (import { test, expect }).
- Prefira seletores resilientes: getByRole, getByTestId, getByLabel, getByText.
  Evite page.locator() com CSS frágil.
- Um test() por cenário, com título igual ao do cenário.
- Implemente pré-condições, passos e a asserção do resultado esperado.
- Responda APENAS com o código TypeScript dentro de um bloco ```ts ... ```.
"""

HEAL_SYSTEM = """\
Você é o Agent 2 (Automatizador) em modo self-healing. Um teste Playwright falhou.
Corrija o código para resolver o erro de seletor relatado, mantendo a intenção do
cenário e usando seletores resilientes (getByRole/getByTestId/getByLabel/getByText).
Responda APENAS com o código TypeScript corrigido dentro de um bloco ```ts ... ```.
"""

_CODE_FENCE = re.compile(r"```(?:ts|typescript)?\s*(.*?)\s*```", re.DOTALL)


def _extract_code(text: str) -> str:
    match = _CODE_FENCE.search(text)
    return (match.group(1) if match else text).strip()


def _generate(scenario: dict) -> str:
    user = (
        "# Cenário (schema_b)\n"
        f"```json\n{json.dumps(scenario, ensure_ascii=False, indent=2)}\n```\n\n"
        "Gere o arquivo .spec.ts."
    )
    return _extract_code(ac.run_agent(GEN_SYSTEM, user, effort="high"))


def _heal(scenario: dict, code: str, failure: dict) -> str:
    user = (
        "# Cenário\n"
        f"```json\n{json.dumps(scenario, ensure_ascii=False, indent=2)}\n```\n\n"
        "# Código atual\n"
        f"```ts\n{code}\n```\n\n"
        "# Erro reportado\n"
        f"{failure.get('message', failure)}\n\n"
        "Corrija o código."
    )
    return _extract_code(ac.run_agent(HEAL_SYSTEM, user, effort="high"))


def _commit_to_gitlab(filename: str, code: str, scenario: dict) -> None:
    """Best-effort commit of the generated spec via the GitLab MCP."""
    servers = mcp.servers("gitlab")
    if not servers:
        return
    project = os.environ.get("GITLAB_PROJECT", "")
    user = (
        "Faça commit do arquivo de teste Playwright abaixo no repositório GitLab "
        f"projeto '{project}', no caminho 'generated_tests/{filename}', usando as "
        "ferramentas do GitLab. Crie um commit (ou merge request) com mensagem "
        f"'test: add {scenario['id']} {scenario['titulo']}'.\n\n"
        f"```ts\n{code}\n```"
    )
    commit_system = (
        "Você é o Agent 2. Use as ferramentas do GitLab para versionar o arquivo "
        "de teste. Responda com um resumo curto do que fez."
    )
    summary = ac.run_agent(commit_system, user, mcp_servers=servers)
    print(f"    [gitlab] {summary.splitlines()[0] if summary else 'commit attempted'}")


def automate(schema_b: dict) -> list[dict]:
    """Generate, heal, persist, and commit a spec per scenario.

    Returns a list of spec records used downstream by the CI stub and Agent 3.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    specs: list[dict] = []

    for scenario in schema_b["cenarios"]:
        scenario_id = scenario["id"]
        print(f"  [Agent 2] Gerando {scenario_id} — {scenario['titulo']}")
        code = _generate(scenario)

        healed = 0
        for _ in range(MAX_HEAL_ITERATIONS):
            result = ci_stub.run_playwright(code, scenario_id=scenario_id)
            if result["passed"]:
                break
            healed += 1
            print(f"    [self-heal {healed}/{MAX_HEAL_ITERATIONS}] {result['message']}")
            code = _heal(scenario, code, result)
        else:
            print(f"    [self-heal] limite atingido para {scenario_id}; mantendo última versão")

        passed = ci_stub.run_playwright(code, scenario_id=scenario_id)["passed"]

        filename = f"{scenario_id}.spec.ts"
        (OUTPUT_DIR / filename).write_text(code, encoding="utf-8")

        _commit_to_gitlab(filename, code, scenario)

        specs.append(
            {
                "scenario_id": scenario_id,
                "titulo": scenario["titulo"],
                "filename": filename,
                "code": code,
                "healed": healed,
                "passed": passed,
            }
        )

    return specs
