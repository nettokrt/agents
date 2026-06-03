"""Remote MCP server definitions for the Anthropic MCP connector.

The agents reach external systems (Atlassian/Jira, GitLab) through Anthropic's
MCP connector rather than direct REST calls. Each call to the Messages API can
attach one or more remote MCP servers via the ``mcp_servers`` parameter plus the
``mcp-client-2025-11-20`` beta header; Anthropic's orchestration layer runs the
tool calls server-side and returns ``mcp_tool_use`` / ``mcp_tool_result`` blocks.

Configuration (URL + auth token) comes from the environment — see .env.example.
A server whose token is missing is treated as "not configured": the agent still
runs, but without that integration (and prints a warning).
"""

from __future__ import annotations

import os

# Beta header that enables the MCP connector on the Messages API.
MCP_BETA = "mcp-client-2025-11-20"


def _server(name: str, url_env: str, token_env: str, default_url: str) -> dict | None:
    url = os.environ.get(url_env, default_url)
    token = os.environ.get(token_env)
    if not url or not token:
        return None
    return {
        "type": "url",
        "name": name,
        "url": url,
        "authorization_token": token,
    }


def atlassian_server() -> dict | None:
    """Atlassian (Jira) remote MCP — real Jira integration."""
    return _server(
        "atlassian",
        "ATLASSIAN_MCP_URL",
        "ATLASSIAN_MCP_TOKEN",
        "https://mcp.atlassian.com/v1/sse",
    )


def gitlab_server() -> dict | None:
    """GitLab-hosted remote MCP — repo context, commits/MRs, issues, pipeline reads."""
    return _server(
        "gitlab",
        "GITLAB_MCP_URL",
        "GITLAB_TOKEN",
        "https://gitlab.com/api/v4/mcp",
    )


_MAKERS = {
    "atlassian": atlassian_server,
    "gitlab": gitlab_server,
}


def servers(*names: str, required: bool = False) -> list[dict] | None:
    """Build the ``mcp_servers`` list for the named integrations.

    Returns ``None`` (not an empty list) when nothing is configured, so callers
    can pass the result straight through to the client, which then makes a plain
    no-MCP request.
    """
    out: list[dict] = []
    for name in names:
        make = _MAKERS[name]
        srv = make()
        if srv is None:
            msg = (
                f"[mcp] '{name}' MCP server is not configured "
                f"(missing URL or token in .env) — its tools will be unavailable."
            )
            if required:
                raise RuntimeError(msg)
            print(msg)
            continue
        out.append(srv)
    return out or None
