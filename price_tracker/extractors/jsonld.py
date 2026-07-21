from __future__ import annotations

import json
from collections.abc import Iterable

from bs4 import BeautifulSoup

from ..normalizers import normalize_price
from .common import ExtractedPrice


def _walk(value: object) -> Iterable[dict]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _type_matches(value: object, name: str) -> bool:
    if isinstance(value, str):
        return value.lower() == name.lower()
    if isinstance(value, list):
        return any(_type_matches(item, name) for item in value)
    return False


def extract_jsonld(html: str) -> ExtractedPrice | None:
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = script.string or script.get_text(" ", strip=True)
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        for node in _walk(data):
            offers = node.get("offers")
            if not offers:
                continue
            product_name = node.get("name") if _type_matches(node.get("@type"), "Product") else None
            offer_list = offers if isinstance(offers, list) else [offers]
            for offer in offer_list:
                if not isinstance(offer, dict):
                    continue
                raw = offer.get("price") or offer.get("lowPrice") or offer.get("highPrice")
                if raw is None:
                    continue
                currency = offer.get("priceCurrency") or "TRY"
                normalized = normalize_price(f"{raw} {currency}")
                if normalized:
                    return ExtractedPrice(
                        raw_price=normalized.raw_price,
                        price=normalized.price,
                        currency=normalized.currency,
                        method="json_ld",
                        confidence=95,
                        product_name=str(product_name) if product_name else None,
                    )
    return None
