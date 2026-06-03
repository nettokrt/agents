"""Agent 0 — Story Refiner.

Reads a raw user story, finds the gaps, and asks the operator (Marcos) about them
interactively (blocking on input()). Once the story is complete enough, it emits a
structured story matching contract A (schema_a).

No MCP — this stage is purely the model plus human clarification.
"""

from __future__ import annotations

from . import anthropic_client as ac

SYSTEM = """\
Você é o Agent 0 (Story Refiner) de um pipeline de QA.

Sua tarefa: transformar uma história de usuário em bruto num objeto estruturado
(contrato schema_a). Antes disso, identifique LACUNAS na história e pergunte ao
QA (Marcos) o que faltar. Faça perguntas objetivas e somente as necessárias.

Responda SEMPRE com um único objeto JSON, sem texto fora dele, em um destes formatos:

1) Quando ainda faltam informações:
{
  "status": "needs_input",
  "questions": ["pergunta 1", "pergunta 2", ...]
}

2) Quando a história está completa o suficiente:
{
  "status": "complete",
  "data": {
    "historia_id": "US-XXX",
    "titulo": "...",
    "ator": "...",
    "acao": "...",
    "objetivo_negocio": "...",
    "criterios_de_aceite": ["...", "..."],
    "fluxos_alternativos": ["..."],
    "dados_de_teste": { },
    "contexto_tecnico": {
      "url_base": "",
      "autenticacao_necessaria": true,
      "tipo": "web"
    },
    "fora_do_escopo": ["..."]
  }
}

Regras:
- Não invente regras de negócio críticas; pergunte.
- Use as respostas já fornecidas; não repita perguntas respondidas.
- Quando tiver o suficiente, emita "complete" — não pergunte por perguntar.
"""


def _build_user(story_text: str, qa_history: list[tuple[str, str]]) -> str:
    parts = ["# História em bruto\n", story_text.strip(), "\n"]
    if qa_history:
        parts.append("\n# Perguntas já respondidas pelo QA\n")
        for question, answer in qa_history:
            parts.append(f"- P: {question}\n  R: {answer}\n")
    parts.append(
        "\nAnalise as lacunas. Se faltar algo, devolva status=needs_input com as "
        "perguntas. Caso contrário, devolva status=complete com o schema_a preenchido."
    )
    return "".join(parts)


def refine(story_text: str) -> dict:
    """Run the interactive refinement loop and return a schema_a dict."""
    qa_history: list[tuple[str, str]] = []

    while True:
        user = _build_user(story_text, qa_history)
        result = ac.extract_json(ac.run_agent(SYSTEM, user))

        status = result.get("status")

        if status == "complete":
            return result["data"]

        if status == "needs_input":
            questions = result.get("questions", [])
            if not questions:
                # Nothing to ask but not complete — nudge once and retry.
                qa_history.append(
                    ("(sistema)", "Sem perguntas pendentes; finalize o schema_a.")
                )
                continue
            print("\n[Agent 0] Preciso de mais informações sobre a história:")
            for question in questions:
                answer = input(f"  • {question}\n    > ").strip()
                qa_history.append((question, answer))
            continue

        # The model returned a bare schema_a without the wrapper — accept it.
        if "historia_id" in result:
            return result

        raise ValueError(f"Agent 0 returned an unexpected shape: {result!r}")
