from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

from .adapters import get_adapter
from .config import settings
from .db import connect
from .extractors.pipeline import extract_price
from .fetchers.browser_fetcher import fetch_with_browser
from .fetchers.static_fetcher import FetchError, fetch_static
from .models import PriceResult, utc_now_iso
from .quantity import (
    extract_category_quantity,
    extract_quantity,
    unit_price_per_kg,
)
from .repository import finish_job, list_urls, save_result, update_job_progress
from .url_cleaner import domain_from_url


def _status_for_confidence(confidence: int) -> str:
    return "success" if confidence >= settings.low_confidence_threshold else "low_confidence"


def _redirected_away_from_product(requested_url: str, final_url: str | None) -> bool:
    if not final_url:
        return False
    requested = urlparse(requested_url)
    final = urlparse(final_url)
    requested_path = requested.path.strip("/")
    final_path = final.path.strip("/")
    if not requested_path or requested_path == final_path:
        return False
    product_markers = {"urun", "products", "product", "magaza"}
    requested_parts = [part for part in requested_path.split("/") if part]
    if final.netloc.lower().removeprefix("www.") != requested.netloc.lower().removeprefix("www."):
        return True
    if any(part in product_markers for part in requested_parts) and not final_path:
        return True
    requested_slug = requested_parts[-1] if requested_parts else ""
    return bool(requested_slug and final_path and requested_slug not in final_path)


def _error_result(
    *,
    source_file: str,
    category: str,
    url: str,
    method: str,
    status: str,
    error: str,
    http_status: int | None = None,
    final_url: str | None = None,
) -> PriceResult:
    return PriceResult(
        source_file=source_file,
        category=category,
        url=url,
        domain=domain_from_url(url),
        product_name=None,
        price=None,
        currency=None,
        raw_price=None,
        quantity_grams=None,
        unit_price_per_kg=None,
        quantity_source=None,
        quantity_confidence=0,
        method=method,
        confidence=0,
        status=status,  # type: ignore[arg-type]
        error=error,
        fetched_at=utc_now_iso(),
        http_status=http_status,
        final_url=final_url,
    )


def scrape_url(
    *,
    source_file: str,
    category: str,
    url: str,
    use_browser_fallback: bool = True,
) -> PriceResult:
    # Category quantity is a hint for variant selection and review only.
    # Never rewrite the user's URL: query parameters may identify the exact
    # product variant they supplied.
    effective_url = url
    domain = domain_from_url(effective_url)
    html = ""
    http_status: int | None = None
    final_url: str | None = None
    try:
        response = fetch_static(effective_url)
        html = response.html
        http_status = response.status_code
        final_url = response.final_url
        if _redirected_away_from_product(effective_url, final_url):
            return _error_result(
                source_file=source_file,
                category=category,
                url=effective_url,
                method="redirect_check",
                status="not_found",
                error="URL redirected away from the product page",
                http_status=http_status,
                final_url=final_url,
            )
    except FetchError as exc:
        status = "blocked" if exc.status_code in {403, 429} else "timeout" if "timed out" in str(exc).lower() else "error"
        if not use_browser_fallback:
            return _error_result(
                source_file=source_file,
                category=category,
                url=effective_url,
                method="static_fetch",
                status=status,
                error=str(exc),
                http_status=exc.status_code,
            )
        try:
            response = fetch_with_browser(effective_url)
            html = response.html
            http_status = response.status_code
            final_url = response.final_url
        except FetchError as browser_exc:
            return _error_result(
                source_file=source_file,
                category=category,
                url=effective_url,
                method="fetch",
                status=status,
                error=f"{exc}; browser fallback: {browser_exc}",
                http_status=exc.status_code,
            )

    adapter = get_adapter(effective_url, domain)
    extracted = adapter.extract(html, effective_url, category=category) if adapter else None
    if extracted is None:
        extracted = extract_price(html)
    if extracted is None and use_browser_fallback:
        try:
            response = fetch_with_browser(effective_url)
            http_status = response.status_code
            final_url = response.final_url
            extracted = extract_price(response.html)
            if extracted:
                extracted = extracted.__class__(
                    raw_price=extracted.raw_price,
                    price=extracted.price,
                    currency=extracted.currency,
                    method=f"playwright_{extracted.method}",
                    confidence=min(100, extracted.confidence + 5),
                    product_name=extracted.product_name,
                )
        except FetchError:
            pass

    if extracted is None:
        return _error_result(
            source_file=source_file,
            category=category,
            url=effective_url,
            method="pipeline",
            status="not_found",
            error="Price not found",
            http_status=http_status,
            final_url=final_url,
        )

    quantity = extract_quantity(product_name=extracted.product_name, url=effective_url, category=category)
    quantity_grams = quantity.grams if quantity else None
    status = _status_for_confidence(extracted.confidence)
    error = None
    category_quantity = extract_category_quantity(category)
    if category_quantity and quantity_grams and abs(category_quantity.grams - quantity_grams) > 0.01:
        status = "low_confidence"
        error = (
            f"Quantity differs from category target: "
            f"category={category_quantity.grams:g}g result={quantity_grams:g}g"
        )
    return PriceResult(
        source_file=source_file,
        category=category,
        url=effective_url,
        domain=domain,
        product_name=extracted.product_name,
        price=extracted.price,
        currency=extracted.currency,
        raw_price=extracted.raw_price,
        quantity_grams=quantity_grams,
        unit_price_per_kg=unit_price_per_kg(extracted.price, quantity_grams),
        quantity_source=quantity.source if quantity else None,
        quantity_confidence=quantity.confidence if quantity else 0,
        method=extracted.method,
        confidence=extracted.confidence,
        status=status,  # type: ignore[arg-type]
        error=error,
        fetched_at=utc_now_iso(),
        http_status=http_status,
        final_url=final_url,
    )


def run_scrape_job(
    *,
    db_path: Path | None,
    job_id: int,
    category_id: int | None = None,
    limit: int | None = None,
    domain: str | None = None,
    only_failed: bool = False,
    delay_seconds: float = 1.5,
) -> None:
    urls = list_urls(
        db_path,
        category_id=category_id,
        domain=domain,
        limit=limit,
        only_failed=only_failed,
    )
    last_domain_at: dict[str, float] = defaultdict(float)
    try:
        with connect(db_path) as conn:
            for row in urls:
                elapsed = time.monotonic() - last_domain_at[row["domain"]]
                if elapsed < delay_seconds:
                    time.sleep(delay_seconds - elapsed)
                try:
                    result = scrape_url(
                        source_file=row["source_file"] or "",
                        category=row["category"],
                        url=row["url"],
                    )
                except Exception as exc:
                    result = _error_result(
                        source_file=row["source_file"] or "",
                        category=row["category"],
                        url=row["url"],
                        method="scrape_url",
                        status="error",
                        error=f"Unhandled URL error: {exc}",
                    )
                save_result(conn, result, url_id=row["id"], job_id=job_id)
                update_job_progress(
                    conn,
                    job_id,
                    processed_delta=1,
                    success_delta=1 if result.status == "success" else 0,
                    failed_delta=1 if result.status not in {"success", "low_confidence"} else 0,
                )
                conn.commit()
                last_domain_at[row["domain"]] = time.monotonic()
        finish_job(db_path, job_id)
    except Exception as exc:
        finish_job(db_path, job_id, status="error", error=str(exc))
