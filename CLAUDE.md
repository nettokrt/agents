# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the pipeline

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY and the MCP tokens
python orchestrator.py --input "story.txt"
```

Gates pause execution and prompt `y/n` in the terminal. Gate 1 waits after Agent 1, Gate 2 after Agent 2 (planned to be removed after ~1 month of usage), Gate 3 after Agent 3 triages real bugs.

## Architecture

Four specialized agents connected by an orchestrator. Each agent receives only a structured JSON payload — never the conversation history from the previous agent. This is the core design constraint that keeps token consumption bounded.

```
story.txt → Agent 0 (Story Refiner) → schema_a.json shape
                                             ↓ GATE 1
                          Agent 1 (Modeler) → schema_b.json shape
                                             ↓ GATE 2
                     Agent 2 (Automator) → .spec.ts files (Playwright)
                                             ↓ (CI runs — stubbed for now)
                    Agent 3 (Bug Triager) → routes: Jira | back to Agent 2 | back to Agent 1 | flaky tag
                                             ↓ GATE 3
```

**Agent 0** is interactive: it detects gaps in the story, asks the QA (via `input()`), then emits `schema_a`.

**Agent 2** uses a ReAct self-healing loop (up to 3 iterations) to fix Playwright selector errors before giving up. Test execution during healing is currently stubbed (`pipeline/ci_stub.py`) — there is no homologation environment yet.

**Agent 3** classifies failures into exactly four categories: `locator_broken` (→ re-run Agent 2), `scenario_wrong` (→ re-run Agent 1), `real_bug` (→ open Jira ticket), `flaky` (→ tag for monitoring).

## Schemas as immutable contracts

`schemas/schema_a.json` and `schemas/schema_b.json` are the data contracts between agents. **Do not modify their structure** unless explicitly instructed — changing a field name breaks the agent boundary on both sides. Treat them like a published API.

- `schema_a.json`: output shape of Agent 0, input shape of Agent 1
- `schema_b.json`: output shape of Agent 1, input shape of Agent 2

`schemas/schema_a.schema.json` and `schemas/schema_b.schema.json` are the JSON-Schema versions used for runtime validation (`pipeline/schemas.py`). Keep them in sync with the example contracts above.

## Test framework

Generated tests are **Playwright** specs (`.spec.ts`, TypeScript), written to `generated_tests/`. Prefer resilient locators (`getByRole`, `getByTestId`, `getByLabel`, `getByText`) over brittle `page.locator()` CSS — the self-healing stub rejects the latter.

## SDK and integration constraints

- Use the **Anthropic Python SDK** (`anthropic` package) — not LangChain, CrewAI, or any other framework.
- **External integrations go through the Anthropic MCP connector**, not direct REST calls. Each agent attaches remote MCP servers to its Messages API call via the `mcp_servers` parameter plus the `mcp-client-2025-11-20` beta header; Anthropic runs the tool calls server-side. See `pipeline/mcp.py`.
  - **Atlassian (Jira)** — remote MCP at `ATLASSIAN_MCP_URL` (real Jira integration). Used by Agent 3 to open tickets.
  - **GitLab** — GitLab-hosted MCP at `GITLAB_MCP_URL`. Used to read repo context (Agent 1), commit generated specs / open MRs (Agent 2), and read pipeline/MR status + create issues (Agent 3).
- **CI is stubbed** for now (`pipeline/ci_stub.py`) — replace `run_playwright` (real `npx playwright test`) and `simulate_ci` (real GitLab pipeline read) once an environment exists.
- Secrets come from `.env` (gitignored); `.env.example` documents the keys. Never hardcode tokens.

## Orchestrator design rules

When working on `orchestrator.py`:
- Pass only the validated JSON output of agent N as the input to agent N+1.
- Never forward raw LLM responses or conversation turns across agent boundaries.
- Gates must be blocking: read `input()` from the terminal and abort on anything but `y`.
- Validate output JSON against the schema before passing it to the next agent — fail loudly, not silently.

## Repository layout

```
orchestrator.py            entrypoint
pipeline/
  anthropic_client.py      Messages API + MCP connector + caching + JSON extraction
  mcp.py                   Atlassian / GitLab remote MCP server definitions
  schemas.py               jsonschema validation of the contracts
  gates.py                 blocking y/n gates
  ci_stub.py               stubbed Playwright runner + CI results
  agent0_story_refiner.py  interactive → schema_a
  agent1_modeler.py        schema_a → schema_b (reads GitLab)
  agent2_automator.py      schema_b → .spec.ts + self-heal + GitLab commit
  agent3_triager.py        CI results → Jira / GitLab / re-run routing
schemas/                   contracts (*.json) + validators (*.schema.json)
generated_tests/           output Playwright specs
```

## Standalone Claude Code subagents (unrelated to the pipeline)

These `.md` files are Claude Code subagent definitions, **not** the pipeline agents above:

| Subagent | File | Purpose |
|---|---|---|
| `playwright-architect` | `playwright-architect.md` | Playwright expert — teaches every feature, documents into the JuiceShop vault |
| `sdet-agent-mentor` | `sdet-agent-mentor.md` | AI agents mentor for SDETs |
| `pt-en-translator` | `pt-en-translator.md` | Portuguese → English translator |
