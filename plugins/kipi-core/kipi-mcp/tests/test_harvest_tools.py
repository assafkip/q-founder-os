import json
import time

import pytest

from kipi_mcp.harvest_store import HarvestStore


def test_kipi_store_harvest_writes_to_db(tmp_harvest_store: HarvestStore):
    run = tmp_harvest_store.create_run(mode="incremental")
    run_id = run["run_id"]

    result = tmp_harvest_store.store_record(
        run_id=run_id,
        source_name="test-source",
        record_key="https://example.com/1",
        summary_json='{"title": "Post 1"}',
        body_text="Full body text here",
    )
    assert result is not None
    assert "id" in result
    assert "deduped" not in result

    records = tmp_harvest_store.get_records("test-source", days=1)
    assert len(records) == 1
    assert records[0]["record_key"] == "https://example.com/1"


def test_kipi_get_harvest_reads_from_db(tmp_harvest_store: HarvestStore):
    run = tmp_harvest_store.create_run(mode="full")
    run_id = run["run_id"]

    for i in range(3):
        tmp_harvest_store.store_record(
            run_id=run_id,
            source_name="linkedin-feed",
            record_key=f"post-{i}",
            summary_json=json.dumps({"title": f"Post {i}"}),
        )

    records = tmp_harvest_store.get_records("linkedin-feed", days=1)
    assert len(records) == 3
    keys = [r["record_key"] for r in records]
    assert "post-0" in keys
    assert "post-2" in keys


def test_kipi_get_harvest_with_body(tmp_harvest_store: HarvestStore):
    run = tmp_harvest_store.create_run(mode="full")
    run_id = run["run_id"]

    body = "This is a long article body with lots of content."
    tmp_harvest_store.store_record(
        run_id=run_id,
        source_name="blog-rss",
        record_key="article-1",
        summary_json='{"title": "Article"}',
        body_text=body,
    )

    # Without body
    records = tmp_harvest_store.get_records("blog-rss", days=1, include_body=False)
    assert len(records) == 1
    assert "body_text" not in records[0]

    # With body (decompressed)
    records = tmp_harvest_store.get_records("blog-rss", days=1, include_body=True)
    assert len(records) == 1
    assert records[0]["body_text"] == body


def test_kipi_get_harvest_pagination(tmp_harvest_store: HarvestStore):
    run = tmp_harvest_store.create_run(mode="full")
    run_id = run["run_id"]

    for i in range(10):
        tmp_harvest_store.store_record(
            run_id=run_id,
            source_name="paginated-src",
            record_key=f"rec-{i:02d}",
            summary_json=json.dumps({"idx": i}),
        )

    # First page
    page1 = tmp_harvest_store.get_records("paginated-src", days=1, limit=3, after_id=0)
    assert len(page1) == 3

    # Second page using last id from first page
    last_id = page1[-1]["id"]
    page2 = tmp_harvest_store.get_records("paginated-src", days=1, limit=3, after_id=last_id)
    assert len(page2) == 3
    # No overlap
    page1_ids = {r["id"] for r in page1}
    page2_ids = {r["id"] for r in page2}
    assert page1_ids.isdisjoint(page2_ids)


def test_kipi_harvest_status(tmp_harvest_store: HarvestStore):
    run = tmp_harvest_store.create_run(mode="incremental")
    run_id = run["run_id"]

    fetched = tmp_harvest_store.get_run(run_id)
    assert fetched is not None
    assert fetched["run_id"] == run_id
    assert fetched["status"] == "running"
    assert fetched["mode"] == "incremental"
    assert "started_at" in fetched

    latest = tmp_harvest_store.get_latest_run()
    assert latest is not None
    assert latest["run_id"] == run_id


def test_kipi_harvest_cleanup(tmp_harvest_store: HarvestStore):
    run = tmp_harvest_store.create_run(mode="full")
    run_id = run["run_id"]

    tmp_harvest_store.store_record(
        run_id=run_id,
        source_name="old-src",
        record_key="old-1",
        summary_json='{"old": true}',
        body_text="old body",
    )

    # Backdate the run to 10 days ago
    conn = tmp_harvest_store._connect()
    try:
        conn.execute(
            "UPDATE harvest_runs SET started_at = datetime('now', '-10 days') WHERE run_id = ?",
            (run_id,),
        )
        conn.commit()
    finally:
        conn.close()

    result = tmp_harvest_store.cleanup(days=7)
    assert result["deleted_runs"] >= 1

    # Records should be cascade-deleted
    records = tmp_harvest_store.get_records("old-src", days=30)
    assert len(records) == 0


def test_kipi_harvest_summary(tmp_harvest_store: HarvestStore):
    run = tmp_harvest_store.create_run(mode="full")
    run_id = run["run_id"]

    for i in range(3):
        tmp_harvest_store.store_record(
            run_id=run_id,
            source_name="source-a",
            record_key=f"a-{i}",
            summary_json=json.dumps({"src": "a"}),
        )
    for i in range(5):
        tmp_harvest_store.store_record(
            run_id=run_id,
            source_name="source-b",
            record_key=f"b-{i}",
            summary_json=json.dumps({"src": "b"}),
        )

    summary = tmp_harvest_store.harvest_summary(run_id)
    assert summary["source-a"] == 3
    assert summary["source-b"] == 5


def test_kipi_approve_apify_budget(tmp_harvest_store: HarvestStore):
    month = "2026-04"

    # Check default budget
    budget = tmp_harvest_store.check_budget(month)
    assert budget["ok"] is True
    assert budget["remaining"] == 5.0

    # Spend up to the limit
    tmp_harvest_store.record_spend(month, 5.0)
    budget = tmp_harvest_store.check_budget(month)
    assert budget["ok"] is False
    assert budget["remaining"] == 0.0

    # Approve extra
    tmp_harvest_store.approve_extra(month, 3.0)
    budget = tmp_harvest_store.check_budget(month)
    assert budget["ok"] is True
    assert budget["remaining"] == 3.0
    assert budget["approved_extra"] == 3.0
