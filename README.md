# agents — QA pipeline

A 4-agent pipeline that turns a user story into automated **Playwright** tests, with
manual review gates and real Jira triage. Built on the Anthropic Python SDK; external
systems are reached through the **Anthropic MCP connector** (Atlassian + GitLab).

```
story.txt → Agent 0 (Story Refiner)  → schema_a
            Agent 1 (Modeler)        → schema_b           ── GATE 1
            Agent 2 (Automator)      → *.spec.ts          ── GATE 2
            (CI, stubbed)
            Agent 3 (Bug Triager)    → Jira / GitLab / re-run ── GATE 3
```

Each agent receives only the validated JSON output of the previous stage — never the
conversation history. See [CLAUDE.md](CLAUDE.md) for the full architecture and rules.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required. |
| `PIPELINE_MODEL` | Optional model override (default `claude-opus-4-8`). |
| `ATLASSIAN_MCP_URL`, `ATLASSIAN_MCP_TOKEN`, `JIRA_PROJECT_KEY` | Real Jira via the Atlassian MCP (Agent 3). |
| `GITLAB_MCP_URL`, `GITLAB_TOKEN`, `GITLAB_PROJECT` | GitLab MCP: repo context, commits/MRs, issues, pipeline reads. |

MCP integrations are optional to *run* — if a token is missing, that agent simply
runs without those tools (and prints a warning). `ANTHROPIC_API_KEY` is required.

## Run

```bash
python orchestrator.py --input story.txt
```

Agent 0 asks clarifying questions in the terminal; the three gates prompt `y/n`
between stages. Generated specs land in `generated_tests/`.

## What's real vs stubbed

- **Real:** all four agents, schema validation, gates, the Atlassian/GitLab MCP wiring.
- **Stubbed (no homologation env yet):** Playwright execution during self-healing and
  the CI feedback that drives Agent 3 — both live in `pipeline/ci_stub.py` with `TODO`s
  marking where to wire `npx playwright test` and a real GitLab pipeline read.

## Layout

See [CLAUDE.md](CLAUDE.md#repository-layout). The `*.md` files at the repo root
(`playwright-architect.md`, `sdet-agent-mentor.md`, `pt-en-translator.md`) are
standalone Claude Code subagent definitions, unrelated to this pipeline.
