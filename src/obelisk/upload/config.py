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
    )
