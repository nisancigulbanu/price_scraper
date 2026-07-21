from __future__ import annotations

import re
import json
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from ..extractors.common import ExtractedPrice
from ..normalizers import normalize_price
from ..quantity import extract_url_query_quantity
from .base import BaseAdapter


VARIANT_PRICE_RE = re.compile(
    r'"prices"\s*:\s*\[\s*\{.*?"sellPrice"\s*:\s*(?P<price>\d+(?:\.\d+)?).*?\}\s*\]'
    r'.*?"variantValues"\s*:\s*\[\s*\{.*?"name"\s*:\s*"(?P<name>[^"]+)"',
    re.IGNORECASE | re.DOTALL,
)


def _grams_from_name(name: str) -> float | None:
    quantity = extract_url_query_quantity(f"https://example.test/?Gram={name.replace(' ', '-')}")
    return quantity.grams if quantity else None


def _variant_id_from_offer(offer: dict) -> str | None:
    raw_url = offer.get("url")
    if not raw_url:
        return None
    values = parse_qs(urlparse(str(raw_url)).query).get("vid")
    return values[0] if values else None


def _variant_name_by_id(html: str, variant_id: str) -> str | None:
    escaped_id = re.escape(variant_id)
    patterns = [
        rf'"id"\s*:\s*"{escaped_id}".{{0,12000}}?"variantValues"\s*:\s*\[\s*\{{.*?"name"\s*:\s*"(?P<name>[^"]+)"',
        rf'"variantValues"\s*:\s*\[\s*\{{.*?"name"\s*:\s*"(?P<name>[^"]+)".{{0,12000}}?"id"\s*:\s*"{escaped_id}"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group("name")
    return None


def _iter_jsonld_products(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = script.string or script.get_text(" ", strip=True)
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "Product":
                yield item


def _extract_offer_by_quantity(html: str, target_grams: float) -> ExtractedPrice | None:
    for product in _iter_jsonld_products(html):
        offers = product.get("offers")
        if not offers:
            continue
        offer_list = offers if isinstance(offers, list) else [offers]
        if not offer_list:
            continue

        for offer in offer_list:
            if not isinstance(offer, dict):
                continue
            variant_id = _variant_id_from_offer(offer)
            variant_name = _variant_name_by_id(html, variant_id) if variant_id else None
            variant_grams = _grams_from_name(variant_name) if variant_name else None
            if variant_grams is None or abs(variant_grams - target_grams) > 0.01:
                continue
            normalized = normalize_price(f"{offer.get('price')} {offer.get('priceCurrency') or 'TRY'}")
            if normalized is None:
                continue
            return ExtractedPrice(
                raw_price=normalized.raw_price,
                price=normalized.price,
                currency=normalized.currency,
                method="ikas_jsonld_variant",
                confidence=96,
                product_name=f"{product.get('name') or ''} - {variant_name}".strip(" -"),
            )

        # Fallback for simple two-variant pages where vid metadata is not present.
        index = int(round(target_grams / 500)) - 1 if target_grams % 500 == 0 else 0
        if index < 0 or index >= len(offer_list):
            index = len(offer_list) - 1
        offer = offer_list[index]
        if not isinstance(offer, dict) or offer.get("price") is None:
            continue
        normalized = normalize_price(f"{offer.get('price')} {offer.get('priceCurrency') or 'TRY'}")
        if normalized is None:
            continue
        return ExtractedPrice(
            raw_price=normalized.raw_price,
            price=normalized.price,
            currency=normalized.currency,
            method="ikas_jsonld_variant",
            confidence=95,
            product_name=str(product.get("name")) if product.get("name") else None,
        )
    return None


class IkasVariantAdapter(BaseAdapter):
    confidence = 94

    def matches(self, url: str, domain: str) -> bool:
        return "?" in url and extract_url_query_quantity(url) is not None

    def extract(self, html: str, url: str, category: str | None = None) -> ExtractedPrice | None:
        target_quantity = extract_url_query_quantity(url)
        if target_quantity is None:
            return None

        from_jsonld = _extract_offer_by_quantity(html, target_quantity.grams)
        if from_jsonld:
            return from_jsonld

        for match in VARIANT_PRICE_RE.finditer(html):
            variant_name = match.group("name")
            variant_grams = _grams_from_name(variant_name)
            if variant_grams is None or abs(variant_grams - target_quantity.grams) > 0.01:
                continue

            normalized = normalize_price(f"{match.group('price')} TRY")
            if normalized is None:
                return None
            return ExtractedPrice(
                raw_price=normalized.raw_price,
                price=normalized.price,
                currency=normalized.currency,
                method="ikas_variant",
                confidence=self.confidence,
                product_name=variant_name,
            )
        return None
