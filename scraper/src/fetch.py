import hashlib
import os
import time

import httpx

from . import config

_last_request_at = 0.0


class FetchError(Exception):
    """Raised when a URL could not be fetched. Carries the status code (if any)
    so callers can decide whether the failure is worth retrying elsewhere."""

    def __init__(self, url: str, status_code: int | None, reason: str):
        self.url = url
        self.status_code = status_code
        self.reason = reason
        super().__init__(f"{reason} (status={status_code}) for {url}")


def _cache_path(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    tail = url.rstrip("/").split("/")[-1] or "index"
    tail = "".join(c if c.isalnum() or c in "-_." else "_" for c in tail)
    return os.path.join(config.CACHE_DIR, f"{tail}-{digest}.html")


def _throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    wait = config.REQUEST_DELAY_SECONDS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def fetch(url: str, use_cache: bool = True, max_retries: int = 1) -> str:
    """Fetch a URL's HTML.

    - Serves from the on-disk cache when present, so a rerun during
      development never re-hits the live site for a page it already has.
    - Applies a minimum delay between real (non-cached) requests.
    - Retries once on a timeout or a 5xx response. Never retries 404/403 —
      those are treated as final, not transient.
    """
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    path = _cache_path(url)

    if use_cache and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    attempt = 0
    while True:
        attempt += 1
        _throttle()
        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": config.USER_AGENT},
                timeout=config.REQUEST_TIMEOUT_SECONDS,
                follow_redirects=True,
            )
        except httpx.TimeoutException as exc:
            if attempt <= max_retries:
                continue
            raise FetchError(url, None, "timeout") from exc
        except httpx.RequestError as exc:
            if attempt <= max_retries:
                continue
            raise FetchError(url, None, f"request error: {exc}") from exc

        if resp.status_code == 200:
            with open(path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            return resp.text

        if resp.status_code in (404, 403):
            raise FetchError(url, resp.status_code, "client error, not retried")

        if resp.status_code >= 500 and attempt <= max_retries:
            continue

        raise FetchError(url, resp.status_code, "unexpected status")
