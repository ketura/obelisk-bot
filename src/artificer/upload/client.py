"""Thin idempotent wrapper around :mod:`mwclient`.

Responsibilities:
* Login once with the configured bot password.
* For each (page_title, content) pair: fetch current text, only write if
  it differs (idempotent).
* Surface clear error messages on auth / quota issues; never raise to the
  caller without context.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from artificer.upload.config import WikiConfig

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
    """

    def __init__(self, config: WikiConfig) -> None:
        self.config = config
        self._site = None  # type: ignore[assignment]

    def _connect(self):
        if self._site is not None:
            return self._site
        try:
            import mwclient
        except ImportError as exc:
            raise RuntimeError(
                "mwclient not installed — install it to enable wiki uploads"
            ) from exc
        site = mwclient.Site(
            self.config.host,
            path=self.config.path,
            clients_useragent=self.config.user_agent,
        )
        if self.config.username and self.config.bot_password:
            site.login(self.config.username, self.config.bot_password)
        self._site = site
        return site

    def put_page(self, title: str, content: str, summary: str | None = None) -> UploadResult:
        """Idempotent write: skip if on-wiki text already matches."""
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
