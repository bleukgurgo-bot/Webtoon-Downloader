from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import AsyncIterator, Optional

import httpx

from webtoon_downloader.core.exceptions import RateLimitedError

log = logging.getLogger(__name__)


class WebtoonHttpClient:
    def __init__(
        self,
        *,
        proxy: str | None = None,
        cookies_file: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._cookies = self._load_cookies(cookies_file)
        self._client = httpx.AsyncClient(
            timeout=timeout,
            proxies=proxy,
            cookies=self._cookies,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "*/*",
            },
            follow_redirects=True,
        )

    @staticmethod
    def _load_cookies(path: str | None) -> Optional[httpx.Cookies]:
        if not path:
            return None

        cookie_path = Path(path)
        if not cookie_path.exists():
            raise FileNotFoundError(f"Cookie file not found: {path}")

        cookies = httpx.Cookies()
        for line in cookie_path.read_text().splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain, _, path, secure, _, name, value = parts
            cookies.set(
                name=name,
                value=value,
                domain=domain,
                path=path,
                secure=(secure.lower() == "true"),
            )
        return cookies

    async def stream_image(self, url: str, quality: int) -> AsyncIterator[httpx.Response]:
        try:
            async with self._client.stream("GET", url) as response:
                if response.status_code == 429:
                    raise RateLimitedError("Rate limited while downloading image")
                yield response
        except httpx.HTTPError:
            raise

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> WebtoonHttpClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()
