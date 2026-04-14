import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from kipi_mcp.executors import ExecutorResult


RUN_OK = {
    "id": "run123",
    "status": "SUCCEEDED",
    "defaultDatasetId": "ds123",
    "stats": {"computeUnits": 0.05},
}

ITEMS_2 = [{"title": "A"}, {"title": "B"}]


def _build_mock_client(run_info, dataset_items):
    client = MagicMock()

    actor_client = MagicMock()
    actor_client.call = AsyncMock(return_value=run_info)
    client.actor.return_value = actor_client

    dataset_client = MagicMock()
    dataset_client.list_items = AsyncMock(return_value=MagicMock(items=dataset_items))
    client.dataset.return_value = dataset_client

    return client


def test_run_actor():
    async def _go():
        client = _build_mock_client(RUN_OK, ITEMS_2)
        with patch("kipi_mcp.executors.apify_executor.ApifyClientAsync", return_value=client):
            from kipi_mcp.executors.apify_executor import execute
            result = await execute(
                config={"input": {"url": "https://example.com"}, "actor_id": "actor/test"},
                apify_token="fake-token",
            )
        assert result.error is None
        assert len(result.records) == 2
        assert result.records[0]["title"] == "A"
        client.actor.return_value.call.assert_called_once_with(run_input={"url": "https://example.com"})
    asyncio.run(_go())


def test_poll_and_download():
    async def _go():
        client = _build_mock_client(RUN_OK, ITEMS_2)
        with patch("kipi_mcp.executors.apify_executor.ApifyClientAsync", return_value=client):
            from kipi_mcp.executors.apify_executor import execute
            result = await execute(
                config={"input": {"q": "test"}, "actor_id": "actor/test"},
                apify_token="fake-token",
            )
        assert result.error is None
        assert len(result.records) == 2
        client.dataset.assert_called_once_with("ds123")
    asyncio.run(_go())


def test_budget_check_before_run():
    async def _go():
        budget_fn = MagicMock(return_value={"ok": False, "reason": "over limit"})
        client = _build_mock_client({}, [])
        with patch("kipi_mcp.executors.apify_executor.ApifyClientAsync", return_value=client):
            from kipi_mcp.executors.apify_executor import execute
            result = await execute(
                config={"input": {}, "actor_id": "actor/test"},
                apify_token="fake-token",
                budget_check_fn=budget_fn,
            )
        assert result.error == "budget_exceeded"
        assert len(result.records) == 0
        client.actor.return_value.call.assert_not_called()
    asyncio.run(_go())


def test_cost_tracking():
    async def _go():
        client = _build_mock_client(RUN_OK, ITEMS_2)
        with patch("kipi_mcp.executors.apify_executor.ApifyClientAsync", return_value=client):
            from kipi_mcp.executors.apify_executor import execute
            result = await execute(
                config={"input": {}, "actor_id": "actor/test"},
                apify_token="fake-token",
            )
        assert result.cost == 0.05
    asyncio.run(_go())


def test_actor_failure():
    async def _go():
        failed_run = {
            "id": "run456",
            "status": "FAILED",
            "defaultDatasetId": None,
            "stats": {},
        }
        client = _build_mock_client(failed_run, [])
        with patch("kipi_mcp.executors.apify_executor.ApifyClientAsync", return_value=client):
            from kipi_mcp.executors.apify_executor import execute
            result = await execute(
                config={"input": {}, "actor_id": "actor/test"},
                apify_token="fake-token",
            )
        assert result.error is not None
        assert "FAILED" in result.error
    asyncio.run(_go())


def test_empty_dataset():
    async def _go():
        client = _build_mock_client(RUN_OK, [])
        with patch("kipi_mcp.executors.apify_executor.ApifyClientAsync", return_value=client):
            from kipi_mcp.executors.apify_executor import execute
            result = await execute(
                config={"input": {}, "actor_id": "actor/test"},
                apify_token="fake-token",
            )
        assert result.error is None
        assert len(result.records) == 0
    asyncio.run(_go())


def test_records_path_extraction():
    async def _go():
        nested_items = [{"data": {"results": [{"id": 1}, {"id": 2}]}}]
        run_info = {
            "id": "run789",
            "status": "SUCCEEDED",
            "defaultDatasetId": "ds789",
            "stats": {"computeUnits": 0.01},
        }
        client = _build_mock_client(run_info, nested_items)
        with patch("kipi_mcp.executors.apify_executor.ApifyClientAsync", return_value=client):
            from kipi_mcp.executors.apify_executor import execute
            result = await execute(
                config={
                    "input": {},
                    "actor_id": "actor/test",
                    "records_path": ["data", "results"],
                },
                apify_token="fake-token",
            )
        assert result.error is None
        assert len(result.records) == 2
        assert result.records[0]["id"] == 1
    asyncio.run(_go())
