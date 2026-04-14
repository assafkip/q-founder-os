from __future__ import annotations

import json


def generate_chrome_prompt(
    sources: list[dict],
    run_id: str,
) -> str | None:
    """Generate a prompt for a Chrome extraction agent handling all Chrome sources."""
    if not sources:
        return None

    max_throttle = max(s["chrome"].get("throttle_ms", 3000) for s in sources)

    parts: list[str] = [
        "You are a data extraction agent. Your ONLY job is to navigate a real Chrome browser, extract structured data, and store it.",
        "",
        "SAFETY RULES:",
        "- NEVER post, comment, like, follow, send messages, click submit, or modify anything. Read-only.",
        f"- Wait {max_throttle}ms between page navigations.",
        "",
    ]

    for s in sources:
        chrome = s["chrome"]
        schema = s.get("output", {}).get("schema", {})
        urls = chrome.get("urls", [])
        throttle = chrome.get("throttle_ms", 3000)
        parts.append(f"## Source: {s['name']}")
        if urls:
            parts.append(f"URLs: {', '.join(urls)}")
        if throttle != max_throttle:
            parts.append(f"Throttle: {throttle}ms between navigations")
        parts.append(f"Instructions:\n{s['chrome_instructions']}")
        parts.append(f"Output schema per record: {json.dumps(schema)}")
        parts.append("")

    parts.append(
        f"For each source, call kipi_store_harvest(source_name='<name>', records_json='[...]', run_id='{run_id}') to persist results."
    )
    parts.append(
        "If extraction fails for a source, call kipi_store_harvest with records_json='[]' and move to the next source."
    )

    return "\n".join(parts)


def generate_mcp_prompt(
    sources: list[dict],
    run_id: str,
) -> str | None:
    """Generate a prompt for an MCP-tool extraction agent handling all MCP sources."""
    if not sources:
        return None

    parts: list[str] = [
        "You are a data extraction agent. Your ONLY job is to call MCP tools, extract data, and store it.",
        "",
    ]

    for s in sources:
        mcp = s["mcp"]
        schema = s.get("output", {}).get("schema", {})
        parts.append(f"## Source: {s['name']}")
        parts.append(f"Server: {mcp['server']}")
        parts.append(f"Tool: {mcp['tool']}")
        if mcp.get("calls"):
            parts.append(f"Call arguments: {json.dumps(mcp['calls'])}")
        parts.append(f"Output schema per record: {json.dumps(schema)}")
        parts.append("")

    parts.append(
        f"For each source, call kipi_store_harvest(source_name='<name>', records_json='[...]', run_id='{run_id}') to persist results."
    )
    parts.append(
        "If extraction fails for a source, call kipi_store_harvest with records_json='[]' and move to the next source."
    )

    return "\n".join(parts)
