from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, unquote, urlparse, urlunparse


QUANTITY_RE = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(kg|kilogram|kilo|gr|g|gram|ml|lt|l|litre|adet)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class QuantityResult:
    grams: float
    source: str
    confidence: int


def _to_grams(amount: float, unit: str) -> float | None:
    normalized = unit.lower()
    if normalized in {"kg", "kilogram", "kilo"}:
        return amount * 1000
    if normalized in {"gr", "g", "gram"}:
        return amount
    if normalized in {"lt", "l", "litre"}:
        return amount * 1000
    if normalized == "ml":
        return amount
    return None


def _parse_amount(raw: str) -> float | None:
    value = raw.strip()
    if not value:
        return None
    if "," in value:
        return float(value.replace(".", "").replace(",", "."))
    if "." in value:
        left, right = value.rsplit(".", 1)
        if len(right) == 3 and left.isdigit() and right.isdigit():
            return float(left + right)
    return float(value)


def _path_text_from_url(url: str) -> str:
    parsed = urlparse(url)
    return unquote(parsed.path.replace("-", " ").replace("_", " "))


def _query_text_from_url(url: str) -> str:
    parsed = urlparse(url)
    pairs = parse_qsl(parsed.query)
    values = [value.replace("-", " ").replace("_", " ") for _, value in pairs if value]
    if values:
        return " ".join(values)
    return " ".join(key.replace("-", " ").replace("_", " ") for key, _ in pairs)


def _extract_from_text(source_name: str, text: str, confidence: int) -> QuantityResult | None:
    for match in QUANTITY_RE.finditer(text):
        unit = match.group(2).lower()
        if unit == "adet":
            continue
        try:
            amount = _parse_amount(match.group(1))
        except ValueError:
            continue
        if amount is None:
            continue
        grams = _to_grams(amount, unit)
        if grams is None or grams <= 0:
            continue
        return QuantityResult(grams=round(grams, 2), source=source_name, confidence=confidence)
    return None


def extract_quantity(*, product_name: str | None, url: str, category: str) -> QuantityResult | None:
    sources = [
        ("url_query", _query_text_from_url(url), 98),
        ("product_name", product_name or "", 90),
        ("url", _path_text_from_url(url), 75),
        ("category", category.replace("_", " "), 65),
    ]
    for source_name, text, confidence in sources:
        result = _extract_from_text(source_name, text, confidence)
        if result:
            return result
    return None


def extract_category_quantity(category: str) -> QuantityResult | None:
    return _extract_from_text("category", category.replace("_", " "), 65)


def extract_url_query_quantity(url: str) -> QuantityResult | None:
    return _extract_from_text("url_query", _query_text_from_url(url), 98)


def _format_query_quantity(grams: float, original_value: str) -> str:
    separator = "-" if "-" in original_value else ""
    lowered = original_value.lower()
    if any(unit in lowered for unit in ("kg", "kilo", "kilogram")) and grams % 1000 == 0:
        amount = int(grams / 1000)
        return f"{amount}{separator}kg"
    amount = int(grams) if float(grams).is_integer() else grams
    return f"{amount}{separator}g"


def align_url_quantity_to_category(url: str, category: str) -> str:
    category_quantity = extract_category_quantity(category)
    query_quantity = extract_url_query_quantity(url)
    if category_quantity is None or query_quantity is None:
        return url
    if abs(category_quantity.grams - query_quantity.grams) < 0.01:
        return url

    parsed = urlparse(url)
    query = parse_qsl(parsed.query, keep_blank_values=True)
    aligned: list[tuple[str, str]] = []
    replaced = False
    for key, value in query:
        if not replaced and _extract_from_text("query_value", value.replace("-", " "), 98):
            aligned.append((key, _format_query_quantity(category_quantity.grams, value)))
            replaced = True
        else:
            aligned.append((key, value))
    if not replaced:
        return url
    return urlunparse(parsed._replace(query=urlencode(aligned, doseq=True)))


def unit_price_per_kg(price: float | None, quantity_grams: float | None) -> float | None:
    if price is None or quantity_grams is None or quantity_grams <= 0:
        return None
    return round(price / quantity_grams * 1000, 2)
