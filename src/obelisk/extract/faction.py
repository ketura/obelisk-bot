"""Faction extraction — load Core/DB/fractions/*.json into FactionRecord.

Six files, one per faction. Per D-025 we capture structural data + the
city-name SID list; ``narrativeDesc`` is dropped (dead L10n pointer in
the 2026-05-03 corpus). Faction laws (``fractionLawsLines``) are
intentionally *not* extracted here — they're a separate entity tackled
in the deferred ``DB/fractions_laws/`` work.
"""

from __future__ import annotations

from pathlib import Path

from obelisk.extract.loader import CorePaths, iter_array, load_json
from obelisk.models.faction import FactionRecord


def _factions_dir(paths: CorePaths) -> Path:
    """Returns ``Core/DB/fractions/`` regardless of the source spelling
    quirk — only ``fractions/`` (with the original misspelling) exists in
    every shipped patch we've seen, so this is just for clarity."""
    return paths.db / "fractions"


def extract_factions(paths: CorePaths) -> list[FactionRecord]:
    """Walk ``Core/DB/fractions/*.json`` and return one FactionRecord per
    faction. Sorted by id for stable downstream output."""
    out: list[FactionRecord] = []
    for p in sorted(_factions_dir(paths).glob("*.json")):
        doc = load_json(p)
        for raw in iter_array(doc):
            if not isinstance(raw, dict) or "id" not in raw:
                continue
            out.append(_build_faction(raw, source_path=p.relative_to(paths.core_root).as_posix()))
    return sorted(out, key=lambda f: f.id)


def _build_faction(raw: dict, source_path: str) -> FactionRecord:
    """Map one JSON record to a FactionRecord. Field renames per
    D-025: iconFractionLaws → icon_faction_laws, resourceName → resource,
    cityNames → city_names; narrativeDesc dropped."""
    city_names = raw.get("cityNames") or ()
    if not isinstance(city_names, (list, tuple)):
        city_names = ()
    return FactionRecord(
        id=str(raw["id"]),
        name_sid=str(raw.get("name", "")),
        desc_sid=str(raw.get("desc", "")),
        icon=str(raw.get("icon", "")),
        icon_faction_laws=str(raw.get("iconFractionLaws", "")),
        biome=str(raw.get("biome", "")),
        resource=str(raw.get("resourceName", "")),
        city_names=tuple(str(c) for c in city_names),
        source_path=source_path,
    )
