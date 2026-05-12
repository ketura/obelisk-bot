"""Thin idempotent wrapper around :mod:`mwclient`.

Responsibilities:

* Login once with the configured bot password.
* For each (page_title, content) pair: fetch current text, only write if
  it differs (idempotent).
* Throttle every API interaction (``requests_per_second`` from the
  config). The throttle is enforced *before* each call rather than
  after, so the first call after a long idle goes through immediately
  and only subsequent calls within the rate window block.
* Surface clear error messages on auth / quota issues; never raise to the
  caller without context.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from obelisk.upload.config import WikiConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UploadResult:
    title: str
    status: str  # written | unchanged | failed
    detail: str = ""


class WikiClient:
    """Lazy MediaWiki client.

    ``mwclient`` is imported lazily so the diff/emit pipeline doesn't require
    it for read-only / dry-run flows.

    Rate limiting: a leaky-bucket-of-one. Each call to
    :meth:`put_page` sleeps until ``1 / requests_per_second`` has
    elapsed since the last call (sleep is omitted on the first call and
    when ``requests_per_second <= 0`` — i.e. throttling disabled).

    The throttle is intentionally enforced inside the client rather than
    around it, so any caller (CLI, tests, future scripts) gets it for
    free.
    """

    def __init__(self, config: WikiConfig, *, sleep=time.sleep, monotonic=time.monotonic) -> None:
        self.config = config
        self._site = None  # type: ignore[assignment]
        # Injectable for tests — production uses real time.
        self._sleep = sleep
        self._monotonic = monotonic
        self._last_call: float | None = None

    def _throttle(self) -> None:
        rps = self.config.requests_per_second
        if rps <= 0:
            return
        min_interval = 1.0 / rps
        now = self._monotonic()
        if self._last_call is not None:
            elapsed = now - self._last_call
            if elapsed < min_interval:
                self._sleep(min_interval - elapsed)
        self._last_call = self._monotonic()

    def _connect(self):
        if self._site is not None:
            return self._site
        try:
            import mwclient
        except ImportError as exc:
            raise RuntimeError(
                "mwclient not installed — install it to enable wiki uploads"
            ) from exc
        site_kwargs: dict = {
            "path": self.config.path,
            "clients_useragent": self.config.user_agent,
            "scheme": self.config.scheme,
        }
        site = mwclient.Site(self.config.host, **site_kwargs)
        # mwclient exposes maxlag via the api() kwarg path; setting it
        # on the Site is supported and threaded into every write.
        if self.config.maxlag > 0:
            site.maxlag = self.config.maxlag
        if self.config.username and self.config.bot_password:
            site.login(self.config.username, self.config.bot_password)
        self._site = site
        return site

    def put_page(self, title: str, content: str, summary: str | None = None) -> UploadResult:
        """Idempotent write: skip if on-wiki text already matches.

        Throttles before contacting the API. On any error the result
        carries ``status='failed'`` plus a detail string; we never raise
        to the caller — the upload loop wants to keep going and tally.
        """
        self._throttle()
        try:
            site = self._connect()
        except Exception as exc:
            return UploadResult(title=title, status="failed", detail=f"connect: {exc}")

        try:
            page = site.pages[title]
            current = page.text() if page.exists else ""
            if current == content:
                return UploadResult(title=title, status="unchanged")
            page.edit(content, summary=summary or self.config.edit_summary, bot=True)
            return UploadResult(title=title, status="written")
        except Exception as exc:
            return UploadResult(title=title, status="failed", detail=str(exc))
