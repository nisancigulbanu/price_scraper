from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal


Status = Literal[
    "success",
    "low_confidence",
    "not_found",
    "blocked",
    "timeout",
    "invalid_url",
    "error",
]


@dataclass(slots=True)
class UrlRecord:
    source_file: str
    category: str
    url: str


@dataclass(slots=True)
class PriceResult:
    source_file: str
    category: str
    url: str
    domain: str
    product_name: str | None
    price: float | None
    currency: str | None
    raw_price: str | None
    quantity_grams: float | None
    unit_price_per_kg: float | None
    quantity_source: str | None
    quantity_confidence: int
    method: str
    confidence: int
    status: Status
    error: str | None
    fetched_at: str
    http_status: int | None
    final_url: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
