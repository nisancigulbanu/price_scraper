from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..config import settings


@dataclass(frozen=True)
class FetchResponse:
    html: str
    status_code: int
    final_url: str


class FetchError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def fetch_static(url: str) -> FetchResponse:
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    }
    try:
        with httpx.Client(follow_redirects=True, timeout=settings.request_timeout_seconds) as client:
            response = client.get(url, headers=headers)
    except httpx.TimeoutException as exc:
        raise FetchError("Request timed out") from exc
    except httpx.HTTPError as exc:
        raise FetchError(str(exc)) from exc

    if response.status_code in {403, 429}:
        raise FetchError(f"Blocked with HTTP {response.status_code}", response.status_code)
    if response.status_code >= 500:
        raise FetchError(f"Server error HTTP {response.status_code}", response.status_code)
    return FetchResponse(
        html=response.text,
        status_code=response.status_code,
        final_url=str(response.url),
    )
