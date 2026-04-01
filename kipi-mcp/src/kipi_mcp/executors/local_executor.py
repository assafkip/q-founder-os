import json
import logging
from pathlib import Path
from kipi_mcp.executors import ExecutorResult

logger = logging.getLogger(__name__)


def execute(config: dict) -> ExecutorResult:
    """Read records from a local file."""
    file_path = Path(config.get("file_path", ""))
    fmt = config.get("format", "json")

    try:
        if not file_path.exists():
            return ExecutorResult(error=f"File not found: {file_path}")

        text = file_path.read_text().strip()
        if not text:
            return ExecutorResult()

        if fmt == "jsonl":
            records = [json.loads(line) for line in text.splitlines() if line.strip()]
        else:
            data = json.loads(text)
            records = data if isinstance(data, list) else [data]

        return ExecutorResult(records=records)

    except Exception as exc:
        logger.error("Local executor error: %s", exc, exc_info=True)
        return ExecutorResult(error=str(exc))
