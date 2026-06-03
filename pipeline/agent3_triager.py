"""Agent 3 — Bug Triager.

Receives CI results (stubbed) and classifies each failure into exactly one of four
categories, then routes it:

  locator_broken  → re-run Agent 2 (regenerate/heal the spec)
  scenario_wrong  → re-run Agent 1 (the scenario itself is wrong)
  real_bug        → open a Jira ticket (real, via the Atlassian MCP)
  flaky           → tag for monitoring

May read GitLab pipeline/MR status and open GitLab issues via the GitLab MCP, and
open Jira tickets via the Atlassian MCP.
"""

from __future__ import annotations

import json
import os

from . import anthropic_client as ac
from . import mcp

SYSTEM = """\
Você é o Agent 3 (Bug Triager) de um pipeline de QA.

Entrada: resultados de execução de testes (CI) e, para contexto, os cenários.
Para cada teste que FALHOU, classifique a causa em EXATAMENTE uma categoria:

- "locator_broken": seletor quebrado → deve voltar para o Agent 2
- "scenario_wrong": cenário/expectativa incorretos → deve voltar para o Agent 1
- "real_bug": defeito real na aplicação → abra um ticket no Jira
- "flaky": instabilidade intermitente → marque para monitoramento

Ferramentas disponíveis:
- Atlassian (Jira): para "real_bug", abra um ticket no projeto indicado.
- GitLab: pode ler status de pipeline/MR e abrir issues quando útil.

Use as ferramentas para executar a ação adequada (ex.: criar o ticket no Jira).

Responda com UM único objeto JSON (sem texto fora dele):
{
  "triage": [
    {
      "scenario_id": "TC-002",
      "category": "real_bug",
      "reasoning": "...",
      "route": "jira|agent2|agent1|monitor",
      "action_taken": "Ticket QA-123 criado"
    }
  ]
}
"""


def triage(ci_results: dict, schema_b: dict) -> dict:
    """Classify and route the failures in a CI results payload."""
    jira_project = os.environ.get("JIRA_PROJECT_KEY", "")
    user = (
        "# Resultados de CI\n"
        f"```json\n{json.dumps(ci_results, ensure_ascii=False, indent=2)}\n```\n\n"
        "# Cenários (contexto)\n"
        f"```json\n{json.dumps(schema_b, ensure_ascii=False, indent=2)}\n```\n\n"
        f"Projeto Jira para tickets de bug: {jira_project or '(não configurado)'}\n\n"
        "Faça a triagem das falhas e execute as ações apropriadas."
    )
    servers = mcp.servers("atlassian", "gitlab")
    return ac.extract_json(ac.run_agent(SYSTEM, user, mcp_servers=servers))
