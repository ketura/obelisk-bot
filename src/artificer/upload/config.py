"""Load uploader credentials from ``artificer.ini``.

Project-local INI file (next to ``pyproject.toml``), git-ignored.
``artificer.ini.example`` is checked in as the template.

Example::

    [wiki]
    host = oldenera.wiki.gg
    path = /
    username = Yourname@artificer-bot
    bot_password = xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    user_agent = artificer-bot/0.1
    edit_summary = artificer-bot: patch sync
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
    user_agent: str = "artificer-bot/0.1"
    edit_summary: str = "artificer-bot: patch sync"


def load_config(config_path: Path) -> WikiConfig:
    if not config_path.is_file():
        raise FileNotFoundError(
            f"missing {config_path} - copy artificer.ini.example and fill in credentials"
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
        user_agent=w.get("user_agent", "artificer-bot/0.1"),
        edit_summary=w.get("edit_summary", "artificer-bot: patch sync"),
    )
