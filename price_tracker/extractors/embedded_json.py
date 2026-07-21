from __future__ import annotations

import json
import re
from collections.abc import Iterable

from bs4 import BeautifulSoup

from ..normalizers import normalize_price
from .common import ExtractedPrice

PREFERRED_KEYS = ("salePrice", "discountedPrice", "currentPrice", "finalPrice", "sellingPrice", "price")
AVOID_KEYS = {"oldPrice", "listPrice", "marketPrice", "compareAtPrice"}


def _walk(value: object) -> Iterable[tuple[str, object, dict | None]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child, value
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def extract_embedded_json(html: str) -> ExtractedPrice | None:
    soup = BeautifulSoup(html, "html.parser")
    payloads: list[object] = []
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data:
        try:
            payloads.append(json.loads(next_data.get_text(strip=True)))
        except json.JSONDecodeError:
            pass

    for script in soup.find_all("script"):
        text = script.string or script.get_text(" ", strip=True)
        if not text or not any(key in text for key in PREFERRED_KEYS):
            continue
        for match in re.finditer(r"\{[^{}]*(?:salePrice|discountedPrice|currentPrice|finalPrice|sellingPrice|price)[^{}]*\}", text):
            try:
                payloads.append(json.loads(match.group(0)))
            except json.JSONDecodeError:
                continue

    for payload in payloads:
        for key, value, parent in _walk(payload):
            if key in AVOID_KEYS or key not in PREFERRED_KEYS:
                continue
            normalized = normalize_price(str(value))
            if normalized:
                product_name = None
                if parent:
                    product_name = parent.get("name") or parent.get("title") or parent.get("productName")
                return ExtractedPrice(
                    raw_price=normalized.raw_price,
                    price=normalized.price,
                    currency=normalized.currency,
                    method="embedded_json",
                    confidence=85,
                    product_name=str(product_name) if product_name else None,
                )
    return None
