# Pipeline de Agentes QA — Movida

Sistema multi-agente de QA construído por Marcos Freitas Netto (SDET, Movida).

## Visão geral

Pipeline de 4 agentes especializados que transforma uma história de usuário bruta em testes Cypress automatizados, com triagem automática de falhas de CI.

```
Input bruto (story, print, parágrafo)
        ↓
  [Agent 0 — Story Refiner]
  analisa lacunas → pergunta para Marcos → entrega JSON estruturado
        ↓ Schema A (contrato de entrada)
  [Agente 1 — Modelador]
        ↓ Schema B (contrato entre agentes)
  *** GATE 1: Marcos aprova cenários ***
        ↓
  [Agente 2 — Automatizador]
  gera .cy.ts → self-healing via loop ReAct (até 3x)
        ↓ arquivos Cypress salvos
  *** GATE 2: Marcos revisa código (some após ~1 mês) ***
        ↓
  [Pipeline CI — futuro]
        ↓ logs
  [Agente 3 — Bug Triager]
  classifica: locator quebrado → Agente 2 | cenário errado → Agente 1 | bug real → Jira | flaky → marca
        ↓
  *** GATE 3: Marcos revisa bugs reais ***
```

**Regra de ouro do orquestrador:** passa APENAS o JSON estruturado de um agente para o próximo. Nunca o histórico de conversa. Controla consumo de contexto.

## Restrições

- Sem MCP (norma interna Movida) — integrações via REST direto
- Sem ambiente de homologação ainda — testes não rodam em pipeline ainda
- Jira: REST API com token de serviço
- Linguagem: Python com SDK da Anthropic

## Interface de execução

- MVP: CLI — `python orchestrator.py --input "story.txt"`
- Gates: orquestrador pausa e aguarda `y/n` no terminal
- Evolução futura: Streamlit ou integração Slack/Teams

## Schemas (contratos entre agentes)

Os arquivos JSON de contrato ficam em `schemas/`:
- `schema_a.json` — contrato de entrada: output do Agent 0 → input do Agente 1
- `schema_b.json` — contrato entre agentes: output do Agente 1 → input do Agente 2

## Roadmap

| Semana | Foco | Status |
|---|---|---|
| 2026-05-09 | Schemas JSON definidos | Concluído |
| 2026-05-16 | Agent 0 (Story Refiner) | Em andamento |
| 2026-05-23 | Self-healing com loop ReAct no Agente 2 | Pendente |
| 2026-05-30 | Tool use para o Agente 3 | Pendente |
| Quando CI pronto | Agente 3 conectado com feedback loop | Pendente |

## Estrutura do código

```
agents/
├── agent0_refiner.py      # Story Refiner
├── agent1_modeler.py      # Modelador de cenários
├── agent2_automator.py    # Automatizador Cypress
└── agent3_triager.py      # Bug Triager
orchestrator.py            # Orquestrador principal com gates
schemas/
├── schema_a.json          # Contrato entrada (história estruturada)
└── schema_b.json          # Contrato entre agentes (cenários)
```
