from __future__ import annotations

from bs4 import BeautifulSoup

from ..normalizers import extract_price_candidates
from .common import ExtractedPrice

SELECTOR_PARTS = (
    "price",
    "product-price",
    "current-price",
    "sale-price",
    "discounted-price",
    "final-price",
    "amount",
    "fiyat",
    "urun-fiyat",
    "indirimli",
)


def extract_html_price(html: str) -> ExtractedPrice | None:
    soup = BeautifulSoup(html, "html.parser")
    title = None
    title_tag = soup.find("h1") or soup.find("meta", attrs={"property": "og:title"}) or soup.find("title")
    if title_tag:
        title = title_tag.get("content") if title_tag.name == "meta" else title_tag.get_text(" ", strip=True)

    for tag in soup.find_all(True):
        attrs = " ".join(
            str(value)
            for key, value in tag.attrs.items()
            if key in {"class", "id", "itemprop", "data-price", "data-testid"}
        ).lower()
        if not any(part in attrs for part in SELECTOR_PARTS):
            continue
        text = tag.get_text(" ", strip=True)
        candidates = extract_price_candidates(text)
        if candidates:
            candidate = candidates[0]
            return ExtractedPrice(
                raw_price=candidate.raw_price,
                price=candidate.price,
                currency=candidate.currency,
                method="html_price_element",
                confidence=75,
                product_name=title,
            )
    return None
