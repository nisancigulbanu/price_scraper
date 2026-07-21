from __future__ import annotations

from bs4 import BeautifulSoup

from ..normalizers import extract_price_candidates
from .common import ExtractedPrice


def extract_regex_price(html: str) -> ExtractedPrice | None:
    soup = BeautifulSoup(html, "html.parser")
    for hidden in soup(["script", "style", "noscript"]):
        hidden.decompose()
    text = soup.get_text(" ", strip=True)
    candidates = extract_price_candidates(text)
    if not candidates:
        return None
    candidate = candidates[0]
    confidence = 65 if any(word in text.lower() for word in ("fiyat", "sepette", "indirimli")) else 50
    return ExtractedPrice(
        raw_price=candidate.raw_price,
        price=candidate.price,
        currency=candidate.currency,
        method="regex_price",
        confidence=confidence,
    )
