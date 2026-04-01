import json
import pytest
from pathlib import Path

from kipi_mcp.executors.local_executor import execute


@pytest.fixture
def tmp_json(tmp_path):
    fp = tmp_path / "data.json"
    fp.write_text(json.dumps([{"a": 1}, {"a": 2}]))
    return fp


@pytest.fixture
def tmp_jsonl(tmp_path):
    fp = tmp_path / "data.jsonl"
    fp.write_text('{"x":1}\n{"x":2}\n{"x":3}\n')
    return fp


def test_read_json(tmp_json):
    result = execute({"file_path": str(tmp_json), "format": "json"})
    assert result.error is None
    assert len(result.records) == 2
    assert result.records[0]["a"] == 1


def test_read_jsonl(tmp_jsonl):
    result = execute({"file_path": str(tmp_jsonl), "format": "jsonl"})
    assert result.error is None
    assert len(result.records) == 3
    assert result.records[2]["x"] == 3


def test_missing_file_graceful():
    result = execute({"file_path": "/nonexistent/path.json", "format": "json"})
    assert result.error is not None
    assert len(result.records) == 0


def test_empty_file(tmp_path):
    fp = tmp_path / "empty.json"
    fp.write_text("")
    result = execute({"file_path": str(fp), "format": "json"})
    assert result.error is None
    assert len(result.records) == 0
