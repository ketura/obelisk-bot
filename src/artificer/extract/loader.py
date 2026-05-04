"""Source JSON loading and path conventions.

Olden Era source JSON has three quirks we centralize here:

1. UTF-8 BOM on every file (load with ``utf-8-sig``).
2. Most files wrap their content in ``{"array": [...]}`` (DB files) or
   ``{"tokens": [...]}`` (Lang files). A few are bare dicts.
3. Trailing commas / whitespace are valid JSON since the game ships clean
   JSON, but we read defensively anyway.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class CorePaths(BaseModel):
    """Resolved paths into one extracted patch dump.

    A patch dump is a directory containing the unzipped contents of
    ``Core.zip`` for that release. Construct via :meth:`from_root`.
    """

    model_config = ConfigDict(frozen=True)

    core_root: Path
    """The directory containing 'DB/' and 'Lang/' subdirs."""

    @classmethod
    def from_root(cls, root: str | Path) -> CorePaths:
        """Construct from a path that is either:

        * The directory holding ``Core/`` (e.g. ``2026-04-30/``)
        * The ``Core/`` directory itself
        * A directory containing ``DB/`` and ``Lang/`` directly
        """
        root = Path(root)
        candidates = [root, root / "Core"]
        for c in candidates:
            if (c / "DB").is_dir() and (c / "Lang").is_dir():
                return cls(core_root=c)
        raise FileNotFoundError(
            f"No 'DB/' + 'Lang/' subdirs found under {root} or {root}/Core"
        )

    @property
    def db(self) -> Path:
        return self.core_root / "DB"

    @property
    def lang(self) -> Path:
        return self.core_root / "Lang"

    def units_logics_dir(self) -> Path:
        return self.db / "units" / "units_logics"

    def units_views_dir(self) -> Path:
        return self.db / "units" / "units_views"

    def language_dirs(self) -> list[Path]:
        """Every language directory under Lang/, excluding 'args/' (script
        argument data, not localization text)."""
        return sorted(
            d for d in self.lang.iterdir()
            if d.is_dir() and d.name != "args"
        )


def load_json(path: str | Path) -> Any:
    """Read a Core JSON file. Handles BOM. Returns the parsed object as-is."""
    p = Path(path)
    with p.open(encoding="utf-8-sig") as f:
        return json.load(f)


def iter_array(doc: Any) -> Iterator[dict[str, Any]]:
    """Iterate the ``array`` element of a DB-style JSON document.

    The convention across ``Core/DB/**.json`` is ``{"array": [...]}``. If a
    file uses a different wrapper key, log it and yield from the first list
    we find — better to be loose on input than fragile.
    """
    if isinstance(doc, dict) and "array" in doc and isinstance(doc["array"], list):
        yield from doc["array"]
        return
    # Fallback: any single list-typed value
    if isinstance(doc, dict):
        for v in doc.values():
            if isinstance(v, list):
                yield from v
                return
    if isinstance(doc, list):
        yield from doc
        return
    raise ValueError(f"Cannot find iterable array in JSON document of type {type(doc).__name__}")


def iter_tokens(doc: Any) -> Iterator[dict[str, Any]]:
    """Iterate the ``tokens`` element of a Lang-style JSON document.

    Convention: ``{"tokens": [{"sid": ..., "text": ...}, ...]}``.
    """
    if isinstance(doc, dict) and "tokens" in doc and isinstance(doc["tokens"], list):
        yield from doc["tokens"]
        return
    # Fallback to iter_array shape if the file uses 'array' instead.
    yield from iter_array(doc)
