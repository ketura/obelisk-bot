"""Difficulty extraction from ``DB/difficulties.json``.

5 entries total: Easy / Normal / Hard / Expert / Impossible. The
sibling ``difficulties_lobby.json`` / ``difficulties_lobby_solo.json``
files exist but ship empty ``difficultiesConfigs`` arrays in
2026-05-05; we extract them anyway so future content is captured.

See D-039.
"""

from __future__ import annotations

from typing import Any

from obelisk.extract.loader import CorePaths, load_json
from obelisk.models.difficulty import (
    DifficultyExtractionResult,
    DifficultyRecord,
)


_RESOURCE_KEYS: tuple[tuple[str, str], ...] = (
    # (source_key, normalized_column_suffix)
    ("gold", "gold"),
    ("wood", "wood"),
    ("ore", "ore"),
    ("gemstones", "gemstones"),
    ("crystals", "crystals"),
    ("mercury", "mercury"),
    ("alchemicalDust", "dust"),
)


def _resource_int(block: Any, key: str) -> int | None:
    if not isinstance(block, dict):
        return None
    v = block.get(key)
    return v if isinstance(v, int) else None


def _build_difficulty(
    raw: dict[str, Any], *, source_path: str,
) -> DifficultyRecord | None:
    sid = raw.get("sid")
    if not isinstance(sid, str):
        return None
    player = raw.get("playerStartResources")
    ai = raw.get("aiStartResources")
    npm = raw.get("neutralPowerMultiplier")
    fields: dict[str, Any] = {
        "id": sid,
        "name_sid": raw.get("nameSid") if isinstance(raw.get("nameSid"), str) else None,
        "description": (
            raw.get("descriptionSid")
            if isinstance(raw.get("descriptionSid"), str) else None
        ),
        "neutral_power_multiplier": float(npm) if isinstance(npm, (int, float)) else None,
        "source_path": source_path,
    }
    for src_key, col in _RESOURCE_KEYS:
        fields[f"player_{col}"] = _resource_int(player, src_key)
        fields[f"ai_{col}"] = _resource_int(ai, src_key)
    return DifficultyRecord(**fields)


def extract_difficulties(paths: CorePaths) -> DifficultyExtractionResult:
    """Walk ``DB/difficulties*.json`` and return all difficulty rows.

    Three source files: ``difficulties.json`` (5 entries in
    2026-05-05), ``difficulties_lobby.json`` (empty), and
    ``difficulties_lobby_solo.json`` (empty)."""
    out: list[DifficultyRecord] = []
    for fname in ("difficulties.json", "difficulties_lobby.json",
                  "difficulties_lobby_solo.json"):
        fp = paths.db / fname
        if not fp.is_file():
            continue
        rel = fp.relative_to(paths.core_root).as_posix()
        try:
            doc = load_json(fp)
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        configs = doc.get("difficultiesConfigs")
        if not isinstance(configs, list):
            continue
        for raw in configs:
            if not isinstance(raw, dict):
                continue
            rec = _build_difficulty(raw, source_path=rel)
            if rec is not None:
                out.append(rec)
    return DifficultyExtractionResult(difficulties=tuple(out))
