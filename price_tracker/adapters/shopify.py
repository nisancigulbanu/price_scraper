from __future__ import annotations

from urllib.parse import parse_qsl, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from ..config import settings
from ..extractors.common import ExtractedPrice
from ..normalizers import normalize_price
from .base import BaseAdapter


def _product_js_url(url: str) -> str | None:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "products":
        return None
    path = f"/products/{parts[1]}.js"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def _selected_variant_id(url: str) -> int | None:
    query = dict(parse_qsl(urlparse(url).query))
    raw = query.get("variant")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _selected_option_values(url: str, html: str) -> list[str]:
    query = dict(parse_qsl(urlparse(url).query))
    option_value_ids = [item for item in query.get("option_values", "").split(",") if item]
    if not option_value_ids:
        return []

    soup = BeautifulSoup(html, "html.parser")
    selected: list[str] = []
    for option_id in option_value_ids:
        tag = soup.find(attrs={"data-option-value-id": option_id})
        value = tag.get("value") if tag else None
        if value:
            selected.append(str(value).strip())
    return selected


def _variant_matches_options(variant: dict, options: list[str]) -> bool:
    variant_options = [str(item).strip() for item in variant.get("options", []) if item is not None]
    if variant_options:
        return variant_options == options
    fallback = [
        str(variant.get(key)).strip()
        for key in ("option1", "option2", "option3")
        if variant.get(key) is not None
    ]
    return fallback == options


def _fetch_product_json(url: str) -> dict | None:
    product_url = _product_js_url(url)
    if product_url is None:
        return None
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "application/json,text/javascript,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    }
    response = httpx.get(product_url, headers=headers, follow_redirects=True, timeout=15)
    if response.status_code != 200:
        return None
    return response.json()


def _price_from_variant(variant: dict) -> float | None:
    raw = variant.get("price")
    if raw is None:
        return None
    try:
        cents = float(raw)
    except (TypeError, ValueError):
        return None
    return round(cents / 100, 2)


class ShopifyAdapter(BaseAdapter):
    confidence = 96

    def matches(self, url: str, domain: str) -> bool:
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query))
        return "/products/" in parsed.path and ("variant" in query or "option_values" in query)

    def extract(self, html: str, url: str, category: str | None = None) -> ExtractedPrice | None:
        product = _fetch_product_json(url)
        if not product:
            return None

        variant_id = _selected_variant_id(url)
        selected_options = _selected_option_values(url, html)
        variants = product.get("variants") or []
        selected = None
        for variant in variants:
            if variant_id is not None and variant.get("id") == variant_id:
                selected = variant
                break
            if selected_options and _variant_matches_options(variant, selected_options):
                selected = variant
                break
        if selected is None:
            return None

        price = _price_from_variant(selected)
        if price is None:
            return None

        title = selected.get("name") or " - ".join(
            item for item in [product.get("title"), selected.get("public_title") or selected.get("title")] if item
        )
        normalized = normalize_price(f"{price:.2f} TRY")
        if normalized is None:
            return None
        return ExtractedPrice(
            raw_price=normalized.raw_price,
            price=normalized.price,
            currency=normalized.currency,
            method="shopify_variant",
            confidence=self.confidence,
            product_name=str(title) if title else None,
        )
