"""Load uploader credentials from ``obelisk.ini``.

Project-local INI file (next to ``pyproject.toml``), git-ignored.
``obelisk.ini.example`` is checked in as the template.

Example::

    [wiki]
    host = oldenera.wiki.gg
    path = /
    username = Yourname@obelisk-bot
    bot_password = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    user_agent = obelisk-bot/0.1
    edit_summary = obelisk-bot: patch sync
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WikiConfig:
    host: str
    path: str = "/"
    username: str = ""
    bot_password: str = ""
    user_agent: str = "obelisk-bot/0.1"
    edit_summary: str = "obelisk-bot: patch sync"


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
        username=w.get("username", ""),
        bot_password=w.get("bot_password", ""),
        user_agent=w.get("user_agent", "obelisk-bot/0.1"),
        edit_summary=w.get("edit_summary", "obelisk-bot: patch sync"),
    )
