"""Load uploader credentials from ``obelisk.ini``.

Project-local INI file (next to ``pyproject.toml``), git-ignored.
``obelisk.ini.example`` is checked in as the template.

Example::

    [wiki]
    host = wiki.hoodedhorse.com
    path = /Heroes_of_Might_and_Magic_Olden_Era/
    username = Yourname@obelisk-bot
    bot_password = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    user_agent = obelisk-bot/0.1
    edit_summary = obelisk-bot: patch sync
    # Conservative defaults — override for local testing wikis.
    requests_per_second = 0.5
    maxlag = 5
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WikiConfig:
    host: str
    path: str = "/"
    scheme: str = "https"
    username: str = ""
    bot_password: str = ""
    user_agent: str = "obelisk-bot/0.1"
    edit_summary: str = "obelisk-bot: patch sync"
    # Throttling. ``requests_per_second`` is enforced client-side by
    # WikiClient (a sleep between each API interaction). ``maxlag`` is
    # the MediaWiki server-side replication-lag hint — mwclient honors
    # it via the ``maxlag`` API parameter.
    requests_per_second: float = 0.5
    maxlag: int = 5
    # Cloudflare / CDN bypass: a semicolon-separated list of
    # ``name=value`` cookie pairs to inject into the requests session
    # mwclient uses, before its first API call. Used for wikis that sit
    # behind a Cloudflare managed-challenge — the operator passes the
    # JS challenge in a browser once, grabs ``cf_clearance`` (and any
    # session cookies) from devtools, and pastes them here. The
    # configured ``user_agent`` must match the UA the browser used to
    # issue cf_clearance, since CF binds the cookie to its issuing UA.
    cookies: str = ""


def parse_cookies(cookie_string: str) -> dict[str, str]:
    """Parse a ``name=value; name=value`` cookie header into a dict.

    Trims whitespace around each pair and around names/values. Silently
    skips malformed pairs (no ``=``). Returns an empty dict for an
    empty / whitespace-only input.
    """
    out: dict[str, str] = {}
    for part in (cookie_string or "").split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, _, value = part.partition("=")
        name = name.strip()
        value = value.strip()
        if name:
            out[name] = value
    return out


def load_config(config_path: Path) -> WikiConfig:
    if not config_path.is_file():
        raise FileNotFoundError(
            f"missing {config_path} - copy obelisk.ini.example and fill in credentials"
        )
    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")
    if "wiki" not in parser:
        raise ValueError(f"{config_path} missing [wiki] section")
    w = parser["wiki"]
    return WikiConfig(
        host=w.get("host", ""),
        path=w.get("path", "/"),
        scheme=w.get("scheme", "https"),
        username=w.get("username", ""),
        bot_password=w.get("bot_password", ""),
        user_agent=w.get("user_agent", "obelisk-bot/0.1"),
        edit_summary=w.get("edit_summary", "obelisk-bot: patch sync"),
        requests_per_second=w.getfloat("requests_per_second", 0.5),
        maxlag=w.getint("maxlag", 5),
        cookies=w.get("cookies", ""),
    )
