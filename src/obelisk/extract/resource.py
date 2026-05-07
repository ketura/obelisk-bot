"""Resource extraction from ``DB/res/resources_info.json``.

Per D-036: 16 entries covering nine economy resources (gold, wood,
ore, gemstones, crystals, mercury, dust, graal, starDust) plus
seven progression-counter "resources" (hero_mana, hero_move_points,
hero_exp, side_exp, faction_laws_points, astrology_exp). Each
entry has identity (id, icon) plus three SID pointers
(name / desc / narrativeDesc) that resolve via the standard L10n
pipeline.

Emitted as ``{{Entry | type=resource | …}}`` rows on
``Data:Resource/<id>`` pages — same pattern as the FactionCityName
per-patch extract (D-025), but with their own pages instead of
inlining onto a parent.
"""

from __future__ import annotations

from dataclasses import dataclass

from obelisk.extract.loader import CorePaths, iter_array, load_json


@dataclass(frozen=True)
class ResourceRecord:
    """One row from ``DB/res/resources_info.json``."""

    id: str
    icon: str | None
    name_sid: str
    desc_sid: str | None
    narrative_desc_sid: str | None
    source_path: str


def extract_resources(paths: CorePaths) -> tuple[ResourceRecord, ...]:
    """Walk ``DB/res/resources_info.json`` and return the resource
    catalog in source order. See D-036."""
    fp = paths.db / "res" / "resources_info.json"
    if not fp.is_file():
        return ()
    rel = fp.relative_to(paths.core_root).as_posix()
    doc = load_json(fp)
    out: list[ResourceRecord] = []
    for raw in iter_array(doc):
        if not isinstance(raw, dict):
            continue
        rid = raw.get("id")
        name_sid = raw.get("name")
        if not isinstance(rid, str) or not isinstance(name_sid, str):
            continue
        out.append(ResourceRecord(
            id=rid,
            icon=raw.get("icon") if isinstance(raw.get("icon"), str) else None,
            name_sid=name_sid,
            desc_sid=raw.get("desc") if isinstance(raw.get("desc"), str) else None,
            narrative_desc_sid=(
                raw.get("narrativeDesc")
                if isinstance(raw.get("narrativeDesc"), str)
                else None
            ),
            source_path=rel,
        ))
    return tuple(out)
