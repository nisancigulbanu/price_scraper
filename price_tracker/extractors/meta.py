from __future__ import annotations

from bs4 import BeautifulSoup

from ..normalizers import normalize_price
from .common import ExtractedPrice


PRICE_KEYS = {
    "product:price:amount",
    "product:price",
    "og:price:amount",
    "twitter:data1",
}
CURRENCY_KEYS = {"product:price:currency", "og:price:currency"}


def extract_meta(html: str) -> ExtractedPrice | None:
    soup = BeautifulSoup(html, "html.parser")
    meta_values: dict[str, str] = {}
    for tag in soup.find_all("meta"):
        key = (tag.get("property") or tag.get("name") or "").strip().lower()
        content = (tag.get("content") or "").strip()
        if key and content:
            meta_values[key] = content

    title = None
    title_tag = soup.find("meta", attrs={"property": "og:title"}) or soup.find("title")
    if title_tag:
        title = title_tag.get("content") if title_tag.name == "meta" else title_tag.get_text(" ", strip=True)

    currency = next((meta_values[key] for key in CURRENCY_KEYS if key in meta_values), "TRY")
    for key in PRICE_KEYS:
        if key not in meta_values:
            continue
        normalized = normalize_price(f"{meta_values[key]} {currency}")
        if normalized:
            return ExtractedPrice(
                raw_price=normalized.raw_price,
                price=normalized.price,
                currency=normalized.currency,
                method="meta_tag",
                confidence=90,
                product_name=title,
            )
    return None
