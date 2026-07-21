from pathlib import Path

from price_tracker.extractors.common import ExtractedPrice
from price_tracker.fetchers.static_fetcher import FetchResponse
from price_tracker.db import connect, init_db
from price_tracker.models import PriceResult, UrlRecord, utc_now_iso
from price_tracker.repository import create_job, import_records
from price_tracker.scraper import run_scrape_job, scrape_url


def test_scrape_url_preserves_original_variant_query(monkeypatch):
    requested: list[str] = []

    def fake_fetch(url: str) -> FetchResponse:
        requested.append(url)
        return FetchResponse("<html></html>", 200, url)

    monkeypatch.setattr("price_tracker.scraper.fetch_static", fake_fetch)
    monkeypatch.setattr(
        "price_tracker.scraper.extract_price",
        lambda html: ExtractedPrice(
            raw_price="500 TL",
            price=500.0,
            currency="TRY",
            method="test",
            confidence=90,
            product_name="Urun 500 g",
        ),
    )

    result = scrape_url(
        source_file="test.xlsx",
        category="1000_gr_urun",
        url="https://example.com/urun?Gram=500-g",
        use_browser_fallback=False,
    )

    assert requested == ["https://example.com/urun?Gram=500-g"]
    assert result.url == requested[0]


def test_scrape_job_continues_after_unhandled_url_error(monkeypatch, tmp_path: Path):
    db_path = tmp_path / "job.sqlite3"
    init_db(db_path)
    import_records(
        [
            UrlRecord("test.xlsx", "test", "https://example.com/a"),
            UrlRecord("test.xlsx", "test", "https://example.com/b"),
        ],
        db_path,
    )
    job_id = create_job(db_path, scope="test", total=2)
    calls = 0

    def fake_scrape_url(*, source_file: str, category: str, url: str, use_browser_fallback: bool = True):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("fixture failure")
        return PriceResult(
            source_file=source_file,
            category=category,
            url=url,
            domain="example.com",
            product_name="Test",
            price=10.0,
            currency="TRY",
            raw_price="10 TL",
            quantity_grams=None,
            unit_price_per_kg=None,
            quantity_source=None,
            quantity_confidence=0,
            method="test",
            confidence=90,
            status="success",
            error=None,
            fetched_at=utc_now_iso(),
            http_status=200,
            final_url=url,
        )

    monkeypatch.setattr("price_tracker.scraper.scrape_url", fake_scrape_url)
    run_scrape_job(db_path=db_path, job_id=job_id, delay_seconds=0)

    with connect(db_path) as conn:
        job = conn.execute("SELECT * FROM scrape_jobs WHERE id = ?", (job_id,)).fetchone()
        statuses = [row["status"] for row in conn.execute("SELECT status FROM price_results ORDER BY id")]
    assert job["status"] == "finished"
    assert job["processed"] == 2
    assert statuses == ["error", "success"]
