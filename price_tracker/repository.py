from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .category_importer import read_input_records
from .db import connect, init_db
from .models import PriceResult, UrlRecord, utc_now_iso
from .quantity import extract_quantity, unit_price_per_kg
from .url_cleaner import domain_from_url


def ensure_database(db_path: Path | None = None) -> None:
    init_db(db_path)


def upsert_category(conn: sqlite3.Connection, name: str, source_file: str | None = None) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO categories(name, source_file) VALUES(?, ?)",
        (name, source_file),
    )
    if source_file:
        conn.execute(
            "UPDATE categories SET source_file = COALESCE(source_file, ?) WHERE name = ?",
            (source_file, name),
        )
    row = conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
    return int(row["id"])


def add_url(conn: sqlite3.Connection, category_id: int, url: str) -> int:
    domain = domain_from_url(url)
    conn.execute(
        """
        INSERT OR IGNORE INTO urls(category_id, url, domain, active)
        VALUES(?, ?, ?, 1)
        """,
        (category_id, url, domain),
    )
    row = conn.execute("SELECT id FROM urls WHERE url = ?", (url,)).fetchone()
    return int(row["id"])


def import_records(records: list[UrlRecord], db_path: Path | None = None) -> int:
    ensure_database(db_path)
    inserted = 0
    with connect(db_path) as conn:
        before = conn.execute("SELECT COUNT(*) AS count FROM urls").fetchone()["count"]
        for record in records:
            category_id = upsert_category(conn, record.category, record.source_file)
            add_url(conn, category_id, record.url)
        after = conn.execute("SELECT COUNT(*) AS count FROM urls").fetchone()["count"]
        inserted = int(after) - int(before)
    return inserted


def import_input(input_path: Path, db_path: Path | None = None) -> int:
    return import_records(read_input_records(input_path), db_path)


def list_categories(db_path: Path | None = None) -> list[sqlite3.Row]:
    ensure_database(db_path)
    with connect(db_path) as conn:
        return list(
            conn.execute(
                """
                SELECT c.*, COUNT(u.id) AS url_count
                FROM categories c
                LEFT JOIN urls u ON u.category_id = c.id AND u.active = 1
                GROUP BY c.id
                ORDER BY c.name
                """
            )
        )


def get_category(db_path: Path | None, category_id: int) -> sqlite3.Row | None:
    ensure_database(db_path)
    with connect(db_path) as conn:
        return conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()


def list_urls(
    db_path: Path | None = None,
    *,
    category_id: int | None = None,
    domain: str | None = None,
    limit: int | None = None,
    only_failed: bool = False,
) -> list[sqlite3.Row]:
    ensure_database(db_path)
    clauses = ["u.active = 1"]
    params: list[Any] = []
    if category_id is not None:
        clauses.append("u.category_id = ?")
        params.append(category_id)
    if domain:
        clauses.append("u.domain = ?")
        params.append(domain)
    if only_failed:
        clauses.append(
            """
            NOT EXISTS (
                SELECT 1
                FROM price_results latest_result
                WHERE latest_result.url_id = u.id
                  AND latest_result.id = (
                      SELECT MAX(previous.id)
                      FROM price_results previous
                      WHERE previous.url_id = u.id
                  )
                  AND latest_result.status IN ('success', 'low_confidence')
            )
            """
        )
    sql = (
        "SELECT u.*, c.name AS category, c.source_file "
        "FROM urls u JOIN categories c ON c.id = u.category_id "
        f"WHERE {' AND '.join(clauses)} ORDER BY c.name, u.id"
    )
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    with connect(db_path) as conn:
        return list(conn.execute(sql, params))


def create_job(
    db_path: Path | None,
    *,
    scope: str,
    total: int,
    category_id: int | None = None,
) -> int:
    ensure_database(db_path)
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO scrape_jobs(status, scope, category_id, total, started_at)
            VALUES('running', ?, ?, ?, ?)
            """,
            (scope, category_id, total, utc_now_iso()),
        )
        return int(cursor.lastrowid)


def update_job_progress(
    conn: sqlite3.Connection,
    job_id: int,
    *,
    processed_delta: int = 0,
    success_delta: int = 0,
    failed_delta: int = 0,
) -> None:
    conn.execute(
        """
        UPDATE scrape_jobs
        SET processed = processed + ?,
            success_count = success_count + ?,
            failed_count = failed_count + ?
        WHERE id = ?
        """,
        (processed_delta, success_delta, failed_delta, job_id),
    )


def finish_job(db_path: Path | None, job_id: int, status: str = "finished", error: str | None = None) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE scrape_jobs SET status = ?, finished_at = ?, error = ? WHERE id = ?",
            (status, utc_now_iso(), error, job_id),
        )


def get_job(db_path: Path | None, job_id: int) -> sqlite3.Row | None:
    ensure_database(db_path)
    with connect(db_path) as conn:
        return conn.execute("SELECT * FROM scrape_jobs WHERE id = ?", (job_id,)).fetchone()


def latest_job(db_path: Path | None = None) -> sqlite3.Row | None:
    ensure_database(db_path)
    with connect(db_path) as conn:
        return conn.execute("SELECT * FROM scrape_jobs ORDER BY id DESC LIMIT 1").fetchone()


def mark_running_jobs_interrupted(db_path: Path | None = None) -> None:
    ensure_database(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE scrape_jobs
            SET status = 'error',
                finished_at = ?,
                error = COALESCE(error, 'Server restarted before this job finished')
            WHERE status = 'running'
            """,
            (utc_now_iso(),),
        )


def clear_results(db_path: Path | None = None, *, category_id: int | None = None) -> None:
    ensure_database(db_path)
    with connect(db_path) as conn:
        if category_id is None:
            conn.execute("DELETE FROM price_results")
            conn.execute("DELETE FROM scrape_jobs")
            return

        conn.execute(
            """
            DELETE FROM price_results
            WHERE url_id IN (
                SELECT id FROM urls WHERE category_id = ?
            )
            """,
            (category_id,),
        )
        conn.execute(
            "DELETE FROM scrape_jobs WHERE category_id = ?",
            (category_id,),
        )


def backfill_unit_prices(db_path: Path | None = None) -> int:
    ensure_database(db_path)
    updated = 0
    with connect(db_path) as conn:
        rows = list(
            conn.execute(
                """
                SELECT id, product_name, url, category, price
                FROM price_results
                WHERE price IS NOT NULL
                """
            )
        )
        for row in rows:
            quantity = extract_quantity(
                product_name=row["product_name"],
                url=row["url"],
                category=row["category"],
            )
            if quantity is None:
                conn.execute(
                    """
                    UPDATE price_results
                    SET quantity_grams = NULL,
                        unit_price_per_kg = NULL,
                        quantity_source = NULL,
                        quantity_confidence = 0
                    WHERE id = ?
                    """,
                    (row["id"],),
                )
                continue
            conn.execute(
                """
                UPDATE price_results
                SET quantity_grams = ?,
                    unit_price_per_kg = ?,
                    quantity_source = ?,
                    quantity_confidence = ?
                WHERE id = ?
                """,
                (
                    quantity.grams,
                    unit_price_per_kg(row["price"], quantity.grams),
                    quantity.source,
                    quantity.confidence,
                    row["id"],
                ),
            )
            updated += 1
    return updated


def save_result(
    conn: sqlite3.Connection,
    result: PriceResult,
    *,
    url_id: int | None = None,
    job_id: int | None = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO price_results(
            url_id, job_id, source_file, category, url, domain, product_name,
            price, currency, raw_price, quantity_grams, unit_price_per_kg,
            quantity_source, quantity_confidence, method, confidence, status, error,
            fetched_at, http_status, final_url
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            url_id,
            job_id,
            result.source_file,
            result.category,
            result.url,
            result.domain,
            result.product_name,
            result.price,
            result.currency,
            result.raw_price,
            result.quantity_grams,
            result.unit_price_per_kg,
            result.quantity_source,
            result.quantity_confidence,
            result.method,
            result.confidence,
            result.status,
            result.error,
            result.fetched_at,
            result.http_status,
            result.final_url,
        ),
    )
    return int(cursor.lastrowid)


def latest_results(
    db_path: Path | None = None,
    *,
    category_id: int | None = None,
    status: str | None = None,
    domain: str | None = None,
    limit: int = 1000,
) -> list[sqlite3.Row]:
    ensure_database(db_path)
    clauses = ["1 = 1"]
    params: list[Any] = []
    if category_id is not None:
        clauses.append("u.category_id = ?")
        params.append(category_id)
    if status:
        clauses.append("r.status = ?")
        params.append(status)
    if domain:
        clauses.append("r.domain = ?")
        params.append(domain)

    sql = f"""
        SELECT r.*, u.category_id
        FROM price_results r
        JOIN (
            SELECT url_id, MAX(id) AS latest_id
            FROM price_results
            WHERE url_id IS NOT NULL
            GROUP BY url_id
        ) latest ON latest.latest_id = r.id
        LEFT JOIN urls u ON u.id = r.url_id
        WHERE {' AND '.join(clauses)}
        ORDER BY r.category, r.domain, r.id DESC
        LIMIT ?
    """
    params.append(limit)
    with connect(db_path) as conn:
        return list(conn.execute(sql, params))


def distinct_domains(db_path: Path | None = None) -> list[str]:
    ensure_database(db_path)
    with connect(db_path) as conn:
        return [row["domain"] for row in conn.execute("SELECT DISTINCT domain FROM urls ORDER BY domain")]
