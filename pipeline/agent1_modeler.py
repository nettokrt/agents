"""Agent 1 — Modeler.

Receives the structured story (schema_a) and produces structured test scenarios
(schema_b). May read existing tests / page objects from the GitLab repo (read-only)
through the GitLab MCP to stay consistent with what's already there.

Input is ONLY the validated schema_a dict — never Agent 0's conversation.
"""

from __future__ import annotations

import json
import os

from . import anthropic_client as ac
from . import mcp

SYSTEM = """\
Você é o Agent 1 (Modelador) de um pipeline de QA.

Entrada: uma história estruturada (schema_a). Saída: cenários de teste
estruturados (contrato schema_b), prontos para automação em Playwright.

Você PODE usar as ferramentas do GitLab (somente leitura) para inspecionar
testes e page objects já existentes no repositório e manter consistência de
nomenclatura e seletores. Não escreva nada no repositório nesta etapa.

Cubra critérios de aceite e fluxos alternativos. Para cada cenário gere casos
funcionais e negativos quando fizer sentido.

Responda com UM único objeto JSON (sem texto fora dele) no formato schema_b:
{
  "suite": "...",
  "historia_id": "US-XXX",
  "cenarios": [
    {
      "id": "TC-001",
      "titulo": "...",
      "tipo": "funcional|negativo|...",
      "prioridade": "alta|media|baixa",
      "pre_condicoes": ["..."],
      "dados": { },
      "passos": ["...", "..."],
      "resultado_esperado": "...",
      "contexto_tecnico": {
        "url": "/rota",
        "tipo_teste": "web",
        "seletores_conhecidos": { }
      }
    }
  ]
}
"""


def model(schema_a: dict) -> dict:
    """Turn a schema_a story into a schema_b scenario set."""
    project = os.environ.get("GITLAB_PROJECT", "")
    user = (
        "# História estruturada (schema_a)\n"
        f"```json\n{json.dumps(schema_a, ensure_ascii=False, indent=2)}\n```\n\n"
        f"Repositório GitLab de referência: {project or '(não configurado)'}\n\n"
        "Gere os cenários de teste no formato schema_b."
    )
    servers = mcp.servers("gitlab")
    return ac.extract_json(ac.run_agent(SYSTEM, user, mcp_servers=servers))
