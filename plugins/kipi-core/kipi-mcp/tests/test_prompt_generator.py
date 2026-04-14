from __future__ import annotations

import json

import pytest

from kipi_mcp.executors.prompt_generator import generate_chrome_prompt, generate_mcp_prompt


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _chrome_source(
    name: str,
    urls: list[str] | None = None,
    throttle_ms: int = 3000,
    chrome_instructions: str = "Click the feed tab and scrape headlines.",
    output_schema: dict | None = None,
) -> dict:
    return {
        "name": name,
        "chrome": {
            "urls": urls or [f"https://{name}.example.com"],
            "throttle_ms": throttle_ms,
        },
        "output": {
            "schema": output_schema or {"title": "string", "url": "string"},
        },
        "chrome_instructions": chrome_instructions,
    }


def _mcp_source(
    name: str,
    server: str = "analytics-server",
    tool: str = "get_report",
    calls: list[dict] | None = None,
    output_schema: dict | None = None,
) -> dict:
    return {
        "name": name,
        "mcp": {
            "server": server,
            "tool": tool,
            "calls": calls or [{"date_range": "last_7_days"}],
        },
        "output": {
            "schema": output_schema or {"metric": "string", "value": "number"},
        },
    }


# ---------------------------------------------------------------------------
# Chrome prompt tests
# ---------------------------------------------------------------------------

class TestChromePrompt:
    def test_chrome_prompt_includes_all_sources(self):
        sources = [
            _chrome_source("twitter"),
            _chrome_source("linkedin"),
            _chrome_source("reddit"),
        ]
        prompt = generate_chrome_prompt(sources, run_id="run-001")
        assert prompt is not None
        for s in sources:
            assert s["name"] in prompt

    def test_chrome_prompt_embeds_md_instructions(self):
        instructions = "Navigate to the feed. Scroll down twice. Extract each post title and link."
        sources = [_chrome_source("twitter", chrome_instructions=instructions)]
        prompt = generate_chrome_prompt(sources, run_id="run-001")
        assert instructions in prompt

    def test_chrome_prompt_includes_run_id_and_store_tool(self):
        sources = [_chrome_source("twitter")]
        prompt = generate_chrome_prompt(sources, run_id="run-abc-123")
        assert "kipi_store_harvest" in prompt
        assert "run-abc-123" in prompt

    def test_chrome_prompt_includes_throttle(self):
        sources = [_chrome_source("twitter", throttle_ms=5000)]
        prompt = generate_chrome_prompt(sources, run_id="run-001")
        assert "5000" in prompt

    def test_chrome_prompt_output_schema(self):
        schema = {"headline": "string", "author": "string", "date": "string"}
        sources = [_chrome_source("news", output_schema=schema)]
        prompt = generate_chrome_prompt(sources, run_id="run-001")
        for key in schema:
            assert key in prompt

    def test_chrome_prompt_never_post(self):
        sources = [_chrome_source("twitter")]
        prompt = generate_chrome_prompt(sources, run_id="run-001")
        lower = prompt.lower()
        assert "never" in lower
        assert "read-only" in lower or "read only" in lower

    def test_chrome_prompt_error_handling(self):
        sources = [_chrome_source("twitter")]
        prompt = generate_chrome_prompt(sources, run_id="run-001")
        assert "records_json='[]'" in prompt or 'records_json="[]"' in prompt


# ---------------------------------------------------------------------------
# MCP prompt tests
# ---------------------------------------------------------------------------

class TestMcpPrompt:
    def test_mcp_prompt_includes_all_sources(self):
        sources = [_mcp_source("ga4"), _mcp_source("stripe")]
        prompt = generate_mcp_prompt(sources, run_id="run-002")
        assert prompt is not None
        assert "ga4" in prompt
        assert "stripe" in prompt

    def test_mcp_prompt_includes_tool_calls(self):
        sources = [_mcp_source(
            "ga4",
            server="analytics-server",
            tool="get_report",
            calls=[{"date_range": "last_7_days", "metrics": ["sessions"]}],
        )]
        prompt = generate_mcp_prompt(sources, run_id="run-002")
        assert "analytics-server" in prompt
        assert "get_report" in prompt
        assert "last_7_days" in prompt

    def test_mcp_prompt_includes_output_schema(self):
        schema = {"metric": "string", "value": "number", "delta": "number"}
        sources = [_mcp_source("ga4", output_schema=schema)]
        prompt = generate_mcp_prompt(sources, run_id="run-002")
        for key in schema:
            assert key in prompt

    def test_mcp_prompt_includes_run_id_and_store_tool(self):
        sources = [_mcp_source("ga4")]
        prompt = generate_mcp_prompt(sources, run_id="run-xyz-789")
        assert "kipi_store_harvest" in prompt
        assert "run-xyz-789" in prompt

    def test_mcp_prompt_error_handling(self):
        sources = [_mcp_source("ga4")]
        prompt = generate_mcp_prompt(sources, run_id="run-002")
        assert "records_json='[]'" in prompt or 'records_json="[]"' in prompt


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_sources_returns_none_chrome(self):
        assert generate_chrome_prompt([], run_id="run-001") is None

    def test_empty_sources_returns_none_mcp(self):
        assert generate_mcp_prompt([], run_id="run-001") is None
