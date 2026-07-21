from __future__ import annotations

import html as html_lib
import json
import re

from bs4 import BeautifulSoup

from ..extractors.html_price import extract_html_price
from ..extractors.common import ExtractedPrice
from ..normalizers import normalize_price
from ..quantity import extract_category_quantity, extract_quantity
from .base import BaseAdapter
from .ikas import IkasVariantAdapter
from .shopify import ShopifyAdapter


class KeywordAdapter(BaseAdapter):
    def __init__(self, domains: set[str], confidence: int = 92) -> None:
        self.domains = domains
        self.confidence = confidence

    def matches(self, url: str, domain: str) -> bool:
        return domain in self.domains

    def extract(self, html: str, url: str, category: str | None = None):
        result = extract_html_price(html)
        if result is None:
            return None
        return result.__class__(
            raw_price=result.raw_price,
            price=result.price,
            currency=result.currency,
            method="domain_adapter",
            confidence=self.confidence,
            product_name=result.product_name,
        )


class WooCommerceVariationAdapter(BaseAdapter):
    confidence = 96

    def matches(self, url: str, domain: str) -> bool:
        return domain in {"ozerciftlik.com"}

    def extract(self, html: str, url: str, category: str | None = None) -> ExtractedPrice | None:
        target_quantity = extract_category_quantity(category or "")
        if target_quantity is None:
            return None

        match = re.search(r'data-product_variations="(?P<data>.*?)"', html, flags=re.DOTALL)
        if not match:
            return None
        try:
            variations = json.loads(html_lib.unescape(match.group("data")))
        except json.JSONDecodeError:
            return None

        for variation in variations:
            attrs = variation.get("attributes") if isinstance(variation, dict) else None
            if not isinstance(attrs, dict):
                continue
            attr_text = " ".join(str(value) for value in attrs.values() if value)
            quantity = extract_quantity(product_name=attr_text, url="", category="")
            if quantity is None or abs(quantity.grams - target_quantity.grams) > 0.01:
                continue
            raw_price = variation.get("display_price")
            normalized = normalize_price(f"{raw_price} TRY")
            if normalized is None:
                continue
            product_name = _page_title(html)
            return ExtractedPrice(
                raw_price=normalized.raw_price,
                price=normalized.price,
                currency=normalized.currency,
                method="woocommerce_variant",
                confidence=self.confidence,
                product_name=f"{product_name} - {attr_text}".strip(" -") if product_name else attr_text,
            )
        return None


class GumushanePestilAdapter(BaseAdapter):
    confidence = 96

    def matches(self, url: str, domain: str) -> bool:
        return domain == "gumushanepestil.com"

    def extract(self, html: str, url: str, category: str | None = None) -> ExtractedPrice | None:
        soup = BeautifulSoup(html, "html.parser")
        visible = _first_price_from_selectors(
            soup,
            (
                ".product-price-container .product-price",
                ".product-price-container",
                ".product-price-old",
                ".product-price-new",
            ),
        )
        microdata = _microdata_price(soup)

        if visible and microdata and visible.price == microdata.price:
            normalized = visible
            method = "verified_product_price"
            confidence = self.confidence
        elif visible:
            normalized = visible
            method = "visible_product_price"
            confidence = 82 if microdata is None else 68
        elif microdata:
            normalized = microdata
            method = "microdata_price_unverified"
            confidence = 68
        else:
            return None

        return ExtractedPrice(
            raw_price=normalized.raw_price,
            price=normalized.price,
            currency=normalized.currency,
            method=method,
            confidence=confidence,
            product_name=_page_title(html),
        )


class PestilMarketimAdapter(BaseAdapter):
    confidence = 94

    def matches(self, url: str, domain: str) -> bool:
        return domain == "pestilmarketim.com"

    def extract(self, html: str, url: str, category: str | None = None) -> ExtractedPrice | None:
        soup = BeautifulSoup(html, "html.parser")
        main_price = soup.select_one(".h2.font-weight-bold.text-accent")
        if main_price is None:
            script_match = re.search(r"var\s+paket_fiyati_on\s*=\s*'(?P<price>[^']+)'", html)
            raw_text = script_match.group("price") if script_match else None
        else:
            raw_text = main_price.get_text(" ", strip=True)
        normalized = normalize_price(raw_text or "")
        if normalized is None:
            return None
        return ExtractedPrice(
            raw_price=normalized.raw_price,
            price=normalized.price,
            currency=normalized.currency,
            method="main_product_price",
            confidence=self.confidence,
            product_name=_page_title(html),
        )


def _page_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("h1") or soup.find("meta", attrs={"property": "og:title"}) or soup.find("title")
    if title_tag is None:
        return None
    title = title_tag.get("content") if title_tag.name == "meta" else title_tag.get_text(" ", strip=True)
    return str(title).strip() if title else None


def _first_price_from_selectors(soup: BeautifulSoup, selectors: tuple[str, ...]):
    for selector in selectors:
        tag = soup.select_one(selector)
        if tag is None:
            continue
        normalized = normalize_price(tag.get_text(" ", strip=True))
        if normalized:
            return normalized
    return None


def _microdata_price(soup: BeautifulSoup):
    price_meta = soup.find("meta", attrs={"itemprop": "price"})
    raw_price = price_meta.get("content") if price_meta else None
    return normalize_price(f"{raw_price} TRY") if raw_price else None


ADAPTERS: list[BaseAdapter] = [
    ShopifyAdapter(),
    IkasVariantAdapter(),
    WooCommerceVariationAdapter(),
    GumushanePestilAdapter(),
    PestilMarketimAdapter(),
    KeywordAdapter(
        {
            "peynircibaba.com",
            "migros.com.tr",
            "karadenizciftlik.com",
            "yayukyoresel.com",
            "tarladanmutfaga.com.tr",
            "neslidogal.com",
        },
        confidence=92,
    )
]


def get_adapter(url: str, domain: str) -> BaseAdapter | None:
    for adapter in ADAPTERS:
        if adapter.matches(url, domain):
            return adapter
    return None
