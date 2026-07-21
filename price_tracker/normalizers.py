from __future__ import annotations

import re
from dataclasses import dataclass


PRICE_RE = re.compile(
    r"(?<![\w])(?:₺\s*)?(\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?|\d+(?:[,.]\d{1,2})?)\s*(?:TL|TRY|₺)?(?![\w])",
    re.IGNORECASE,
)
HAS_CURRENCY_RE = re.compile(r"(₺|TL|TRY)", re.IGNORECASE)
NOISE_AFTER_RE = re.compile(
    r"^\s*(?:gr|g|gram|kg|ml|lt|l|taksit|ay|adet|cm|mm|%)\b",
    re.IGNORECASE,
)
NOISE_BEFORE_RE = re.compile(r"(?:%|kod[:\s]*|barkod[:\s]*|sku[:\s]*)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class NormalizedPrice:
    price: float
    currency: str
    raw_price: str


def looks_like_non_price(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 18) : start]
    after = text[end : min(len(text), end + 18)]
    raw = text[start:end]
    if NOISE_AFTER_RE.search(after) or NOISE_BEFORE_RE.search(before):
        return True
    if "%" in before[-2:] or "%" in after[:2]:
        return True
    if not HAS_CURRENCY_RE.search(raw) and NOISE_AFTER_RE.search(after):
        return True
    return False


def normalize_price(raw: str) -> NormalizedPrice | None:
    value = (raw or "").strip()
    if not value:
        return None

    currency = "TRY" if HAS_CURRENCY_RE.search(value) else "TRY"
    cleaned = HAS_CURRENCY_RE.sub("", value).strip()
    cleaned = re.sub(r"\s+", "", cleaned)

    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")
    elif "." in cleaned:
        left, right = cleaned.rsplit(".", 1)
        if len(right) == 3 and left.isdigit():
            cleaned = left + right

    try:
        price = float(cleaned)
    except ValueError:
        return None

    if price <= 1 or price > 1_000_000:
        return None
    return NormalizedPrice(price=round(price, 2), currency=currency, raw_price=value)


def extract_price_candidates(text: str) -> list[NormalizedPrice]:
    candidates: list[NormalizedPrice] = []
    seen: set[tuple[float, str]] = set()
    for match in PRICE_RE.finditer(text or ""):
        if looks_like_non_price(text, match.start(), match.end()):
            continue
        normalized = normalize_price(match.group(0))
        if normalized is None:
            continue
        key = (normalized.price, normalized.raw_price)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(normalized)
    return candidates
