from __future__ import annotations

from abc import ABC, abstractmethod

from ..extractors.common import ExtractedPrice


class BaseAdapter(ABC):
    confidence = 92

    @abstractmethod
    def matches(self, url: str, domain: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def extract(self, html: str, url: str, category: str | None = None) -> ExtractedPrice | None:
        raise NotImplementedError
