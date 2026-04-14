import logging
from apify_client import ApifyClientAsync
from kipi_mcp.executors import ExecutorResult

logger = logging.getLogger(__name__)


def _extract_by_path(items: list[dict], records_path: list[str]) -> list[dict]:
    """Walk into nested structure using records_path keys."""
    if not records_path:
        return items
    results = []
    for item in items:
        obj = item
        for key in records_path:
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                obj = None
                break
        if isinstance(obj, list):
            results.extend(obj)
        elif isinstance(obj, dict):
            results.append(obj)
    return results


async def execute(
    config: dict,
    cursor: str | None = None,
    budget_check_fn=None,
    apify_token: str | None = None,
) -> ExecutorResult:
    """Execute an Apify actor and return results."""
    if budget_check_fn is not None:
        check = budget_check_fn()
        if not check.get("ok", True):
            return ExecutorResult(error="budget_exceeded")

    try:
        client = ApifyClientAsync(token=apify_token)
        actor_id = config.get("actor_id", "")
        run_input = config.get("input", {})

        run_info = await client.actor(actor_id).call(run_input=run_input)

        status = run_info.get("status", "UNKNOWN")
        if status != "SUCCEEDED":
            return ExecutorResult(error=f"Actor run {status}")

        dataset_id = run_info.get("defaultDatasetId")
        if not dataset_id:
            return ExecutorResult(error="No dataset returned from actor run")

        dataset_result = await client.dataset(dataset_id).list_items()
        items = dataset_result.items

        records_path = config.get("records_path", [])
        records = _extract_by_path(items, records_path) if records_path else items

        cost = 0.0
        stats = run_info.get("stats", {})
        if isinstance(stats, dict):
            cost = stats.get("computeUnits", 0.0) or 0.0

        return ExecutorResult(records=records, cost=cost)

    except Exception as exc:
        logger.error("Apify executor error: %s", exc, exc_info=True)
        return ExecutorResult(error=str(exc))
