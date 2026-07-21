from __future__ import annotations

from statistics import mean, median
from typing import Iterable


def numeric_stats(rows: Iterable[object], field: str) -> dict[str, float | int | None]:
    prices: list[float] = []
    for row in rows:
        value = row[field] if hasattr(row, "keys") else getattr(row, field, None)
        if value is not None:
            prices.append(float(value))
    if not prices:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "count": len(prices),
        "mean": round(mean(prices), 2),
        "median": round(median(prices), 2),
        "min": round(min(prices), 2),
        "max": round(max(prices), 2),
    }


def price_stats(rows: Iterable[object]) -> dict[str, float | int | None]:
    return numeric_stats(rows, "price")


def unit_price_stats(rows: Iterable[object]) -> dict[str, float | int | None]:
    return numeric_stats(rows, "unit_price_per_kg")


def status_summary(rows: Iterable[object]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for row in rows:
        status = row["status"] if hasattr(row, "keys") else getattr(row, "status", "unknown")
        summary[status] = summary.get(status, 0) + 1
    return summary
