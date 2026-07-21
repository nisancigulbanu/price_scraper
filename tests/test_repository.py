from pathlib import Path

from price_tracker.db import init_db
from price_tracker.models import PriceResult, UrlRecord, utc_now_iso
from price_tracker.repository import (
    clear_results,
    create_job,
    finish_job,
    import_records,
    list_categories,
    list_urls,
    latest_results,
    save_result,
)
from price_tracker.db import connect


def test_import_records_deduplicates_urls(tmp_path: Path):
    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)
    records = [
        UrlRecord(source_file="a.xlsx", category="bal", url="https://example.com/a"),
        UrlRecord(source_file="a.xlsx", category="bal", url="https://example.com/a"),
    ]
    assert import_records(records, db_path) == 1
    assert len(list_categories(db_path)) == 1
    assert len(list_urls(db_path)) == 1


def test_clear_results_can_clear_one_category(tmp_path: Path):
    db_path = tmp_path / "test.sqlite3"
    init_db(db_path)
    import_records(
        [
            UrlRecord(source_file="a.xlsx", category="bal", url="https://example.com/a"),
            UrlRecord(source_file="b.xlsx", category="cay", url="https://example.com/b"),
        ],
        db_path,
    )
    urls = list_urls(db_path)
    job_id = create_job(db_path, scope="test", total=2)
    with connect(db_path) as conn:
        for row in urls:
            save_result(
                conn,
                PriceResult(
                    source_file=row["source_file"],
                    category=row["category"],
                    url=row["url"],
                    domain=row["domain"],
                    product_name=None,
                    price=10.0,
                    currency="TRY",
                    raw_price="10 TL",
                    quantity_grams=1000,
                    unit_price_per_kg=10,
                    quantity_source="test",
                    quantity_confidence=100,
                    method="test",
                    confidence=90,
                    status="success",
                    error=None,
                    fetched_at=utc_now_iso(),
                    http_status=200,
                    final_url=row["url"],
                ),
                url_id=row["id"],
                job_id=job_id,
            )
    finish_job(db_path, job_id)

    clear_results(db_path, category_id=urls[0]["category_id"])

    rows = latest_results(db_path)
    assert len(rows) == 1
    assert rows[0]["category"] == "cay"


def test_list_urls_only_failed_returns_urls_without_successful_latest_result(tmp_path: Path):
    db_path = tmp_path / "failed.sqlite3"
    init_db(db_path)
    import_records(
        [
            UrlRecord(source_file="a.xlsx", category="bal", url="https://example.com/a"),
            UrlRecord(source_file="a.xlsx", category="bal", url="https://example.com/b"),
        ],
        db_path,
    )
    urls = list_urls(db_path)
    with connect(db_path) as conn:
        for row, status in zip(urls, ("success", "not_found")):
            save_result(
                conn,
                PriceResult(
                    source_file=row["source_file"],
                    category=row["category"],
                    url=row["url"],
                    domain=row["domain"],
                    product_name=None,
                    price=10.0 if status == "success" else None,
                    currency="TRY" if status == "success" else None,
                    raw_price="10 TL" if status == "success" else None,
                    quantity_grams=None,
                    unit_price_per_kg=None,
                    quantity_source=None,
                    quantity_confidence=0,
                    method="test",
                    confidence=90 if status == "success" else 0,
                    status=status,
                    error=None if status == "success" else "missing",
                    fetched_at=utc_now_iso(),
                    http_status=200,
                    final_url=row["url"],
                ),
                url_id=row["id"],
            )

    failed = list_urls(db_path, only_failed=True)
    assert [row["url"] for row in failed] == ["https://example.com/b"]
