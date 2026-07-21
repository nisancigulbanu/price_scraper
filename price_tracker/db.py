from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import settings


SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    source_file TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    url TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scrape_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL,
    scope TEXT NOT NULL,
    category_id INTEGER,
    total INTEGER NOT NULL DEFAULT 0,
    processed INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    started_at TEXT,
    finished_at TEXT,
    error TEXT
);

CREATE TABLE IF NOT EXISTS price_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_id INTEGER REFERENCES urls(id) ON DELETE SET NULL,
    job_id INTEGER REFERENCES scrape_jobs(id) ON DELETE SET NULL,
    source_file TEXT NOT NULL,
    category TEXT NOT NULL,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    product_name TEXT,
    price REAL,
    currency TEXT,
    raw_price TEXT,
    quantity_grams REAL,
    unit_price_per_kg REAL,
    quantity_source TEXT,
    quantity_confidence INTEGER NOT NULL DEFAULT 0,
    method TEXT NOT NULL,
    confidence INTEGER NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    fetched_at TEXT NOT NULL,
    http_status INTEGER,
    final_url TEXT
);

CREATE INDEX IF NOT EXISTS idx_urls_category ON urls(category_id);
CREATE INDEX IF NOT EXISTS idx_results_url_id ON price_results(url_id);
CREATE INDEX IF NOT EXISTS idx_results_status ON price_results(status);
CREATE INDEX IF NOT EXISTS idx_results_category ON price_results(category);
"""

MIGRATIONS = {
    "quantity_grams": "ALTER TABLE price_results ADD COLUMN quantity_grams REAL",
    "unit_price_per_kg": "ALTER TABLE price_results ADD COLUMN unit_price_per_kg REAL",
    "quantity_source": "ALTER TABLE price_results ADD COLUMN quantity_source TEXT",
    "quantity_confidence": "ALTER TABLE price_results ADD COLUMN quantity_confidence INTEGER NOT NULL DEFAULT 0",
}


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or settings.database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        existing = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(price_results)")
        }
        for column, sql in MIGRATIONS.items():
            if column not in existing:
                conn.execute(sql)
