from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedPrice:
    raw_price: str
    price: float
    currency: str
    method: str
    confidence: int
    product_name: str | None = None
