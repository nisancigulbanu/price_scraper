from __future__ import annotations

from .common import ExtractedPrice
from .embedded_json import extract_embedded_json
from .html_price import extract_html_price
from .jsonld import extract_jsonld
from .meta import extract_meta
from .regex_price import extract_regex_price


EXTRACTORS = (
    extract_jsonld,
    extract_meta,
    extract_embedded_json,
    extract_html_price,
    extract_regex_price,
)


def extract_price(html: str) -> ExtractedPrice | None:
    for extractor in EXTRACTORS:
        result = extractor(html)
        if result:
            return result
    return None
