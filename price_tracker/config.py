from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    root_dir: Path = ROOT_DIR
    categories_dir: Path = ROOT_DIR / "kategoriler"
    data_dir: Path = ROOT_DIR / "data"
    output_dir: Path = ROOT_DIR / "data" / "output"
    cache_dir: Path = ROOT_DIR / "data" / "cache"
    database_path: Path = ROOT_DIR / "data" / "price_tracker.sqlite3"
    request_timeout_seconds: float = 20.0
    low_confidence_threshold: int = 70
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36 PriceTracker/0.1"
    )


settings = Settings()
