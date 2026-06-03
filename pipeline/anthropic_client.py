"""Thin wrapper around the Anthropic Messages API.

Centralizes: the model id, adaptive thinking, the ``effort`` knob, prompt caching
of the (stable) system prompt, the MCP connector beta header, and a small loop to
resume server-side tool execution when the API returns ``stop_reason == "pause_turn"``.

Every agent calls :func:`run_agent`. The orchestrator never passes conversation
history between agents — each agent builds its own prompt from the validated JSON
payload of the previous stage, so nothing here is shared across agent boundaries.
"""

from __future__ import annotations

import json
import os
import re

import anthropic

from .mcp import MCP_BETA

DEFAULT_MODEL = os.environ.get("PIPELINE_MODEL", "claude-opus-4-8")

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        # Reads ANTHROPIC_API_KEY from the environment.
        _client = anthropic.Anthropic()
    return _client


def run_agent(
    system: str,
    user: str,
    *,
    mcp_servers: list[dict] | None = None,
    effort: str = "high",
    max_tokens: int = 16000,
) -> str:
    """Run one agent turn and return the assistant's final text.

    ``system`` is cached (it's the stable, per-agent instruction block); ``user``
    carries the volatile per-run payload. When ``mcp_servers`` is provided, the
    MCP connector beta is enabled and Anthropic runs the tool calls server-side.
    """
    messages: list[dict] = [{"role": "user", "content": user}]
    betas = [MCP_BETA] if mcp_servers else []

    final = None
    # Cap continuations so a misbehaving server-side tool loop can't run forever.
    for _ in range(10):
        kwargs: dict = dict(
            model=DEFAULT_MODEL,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": effort},
        )
        if mcp_servers:
            kwargs["mcp_servers"] = mcp_servers
            # The mcp-client-2025-11-20 beta requires exactly one mcp_toolset in
            # `tools` per server in `mcp_servers` (otherwise the request 400s).
            # No config => all of the server's tools are enabled.
            kwargs["tools"] = [
                {"type": "mcp_toolset", "mcp_server_name": srv["name"]}
                for srv in mcp_servers
            ]

        final = client().beta.messages.create(betas=betas, **kwargs)

        if final.stop_reason == "pause_turn":
            # Server-side tool loop hit its iteration cap — re-send to resume.
            messages.append({"role": "assistant", "content": final.content})
            continue
        break

    return "".join(b.text for b in final.content if b.type == "text").strip()


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json(text: str) -> dict:
    """Pull a single JSON object out of an LLM response.

    Tolerates fenced ```json blocks and surrounding prose. Raises ``ValueError``
    if no parseable object is found — the orchestrator turns that into a loud
    failure rather than passing junk to the next agent.
    """
    candidates: list[str] = []

    fenced = _FENCE_RE.search(text)
    if fenced:
        candidates.append(fenced.group(1))

    candidates.append(text)

    # Last resort: slice from the first '{' to the last '}'.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise ValueError(
        "Could not extract a JSON object from the agent response. "
        f"First 300 chars:\n{text[:300]}"
    )
