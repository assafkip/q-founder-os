from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

import httpx
import feedparser
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

from kipi_mcp.executors import ExecutorResult

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0


def _get_ga4_client():
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    return BetaAnalyticsDataClient()


def _extract_records(data: dict | list, records_path: list[str]) -> list[dict]:
    if not records_path:
        return data if isinstance(data, list) else [data]
    node = data
    for key in records_path:
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return []
    return node if isinstance(node, list) else [node]


def _inject_cursor_param(url: str, param: str, value: str) -> str:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs[param] = [value]
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


class _TransientHTTPError(Exception):
    def __init__(self, response: httpx.Response):
        self.response = response
        super().__init__(f"HTTP {response.status_code}")


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, _TransientHTTPError)


@retry(
    retry=retry_if_exception(_is_transient),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _http_request(
    client: httpx.AsyncClient,
    url: str,
    verb: str,
    headers: dict[str, str],
    body: dict | None,
) -> httpx.Response:
    if verb.upper() == "GET":
        resp = await client.get(url, headers=headers)
    elif verb.upper() == "POST":
        resp = await client.post(url, headers=headers, json=body)
    elif verb.upper() == "PUT":
        resp = await client.put(url, headers=headers, json=body)
    else:
        resp = await client.request(verb.upper(), url, headers=headers, json=body)

    if resp.status_code == 429 or resp.status_code >= 500:
        raise _TransientHTTPError(resp)
    return resp


async def _execute_ga4(config: dict) -> ExecutorResult:
    try:
        client = _get_ga4_client()
        body = config.get("body_template") or {}
        property_id = config["url"]

        from google.analytics.data_v1beta.types import (
            RunReportRequest, Dimension, Metric, DateRange,
        )

        request = RunReportRequest(
            property=property_id,
            dimensions=[Dimension(**d) for d in body.get("dimensions", [])],
            metrics=[Metric(**m) for m in body.get("metrics", [])],
            date_ranges=[DateRange(**dr) for dr in body.get("date_ranges", [])],
        )

        response = await asyncio.to_thread(client.run_report, request)

        dim_names = [h.name for h in response.dimension_headers]
        met_names = [h.name for h in response.metric_headers]

        records = []
        for row in response.rows:
            rec = {}
            for name, val in zip(dim_names, row.dimension_values):
                rec[name] = val.value
            for name, val in zip(met_names, row.metric_values):
                rec[name] = val.value
            records.append(rec)

        return ExecutorResult(records=records)
    except Exception as exc:
        logger.error("GA4 execute failed: %s", exc)
        return ExecutorResult(error=str(exc))


async def _execute_rss(config: dict) -> ExecutorResult:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(config["url"], headers=config.get("headers", {}))
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        records = [dict(entry) for entry in feed.entries]
        return ExecutorResult(records=records)
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        return ExecutorResult(error=str(exc))
    except Exception as exc:
        logger.error("RSS execute failed: %s", exc)
        return ExecutorResult(error=str(exc))


async def _execute_http(config: dict, cursor: str | None = None) -> ExecutorResult:
    url = config["url"]
    verb = config.get("verb", "GET")
    headers = config.get("headers", {})
    body = config.get("body_template")
    records_path = config.get("records_path", [])
    pagination = config.get("pagination")

    all_records: list[dict] = []
    last_cursor: str | None = None
    current_cursor = cursor

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            while True:
                req_url = url
                if current_cursor and pagination:
                    param = pagination.get("cursor_param", "cursor")
                    req_url = _inject_cursor_param(req_url, param, current_cursor)

                resp = await _http_request(client, req_url, verb, headers, body)
                resp.raise_for_status()

                data = resp.json()
                page_records = _extract_records(data, records_path)
                all_records.extend(page_records)

                if not pagination or pagination.get("type") != "cursor":
                    break

                cursor_field = pagination.get("cursor_field", "next_cursor")
                has_more_field = pagination.get("has_more_field", "has_more")

                next_cursor = data.get(cursor_field) if isinstance(data, dict) else None
                has_more = data.get(has_more_field, False) if isinstance(data, dict) else False

                if not next_cursor or not has_more:
                    last_cursor = next_cursor
                    break

                current_cursor = next_cursor
                last_cursor = next_cursor

    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        return ExecutorResult(records=all_records, error=str(exc))
    except _TransientHTTPError as exc:
        return ExecutorResult(records=all_records, error=f"HTTP {exc.response.status_code} after retries")
    except Exception as exc:
        logger.error("HTTP execute failed: %s", exc)
        return ExecutorResult(records=all_records, error=str(exc))

    return ExecutorResult(records=all_records, cursor_after=last_cursor)


async def execute(config: dict, cursor: str | None = None) -> ExecutorResult:
    """Execute an HTTP-based data source fetch.

    config keys (from HttpConfig):
        url, verb, headers, body_template, records_path, pagination, is_rss, is_ga4
    """
    if config.get("is_ga4"):
        return await _execute_ga4(config)
    if config.get("is_rss"):
        return await _execute_rss(config)
    return await _execute_http(config, cursor)
