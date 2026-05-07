"""City-building extraction.

Walks ``DB/objects_logic/cities/<faction>_city.json`` (six files,
one per faction). Each city carries 18 building-group keys; each
group entry has ``parametersPerLevel`` which we *flatten* — a 3-level
building produces 3 BuildingRecord rows.

See D-034.
"""

from __future__ import annotations

from typing import Any

from obelisk.extract.loader import CorePaths, iter_array, load_json
from obelisk.models.building import BuildingExtractionResult, BuildingRecord


# 18 categories of building-instance lists that live on a city dict.
# `buildOrders` is intentionally omitted (AI build-order presets, not
# player-visible buildings).
_BUILDING_GROUP_KEYS: tuple[str, ...] = (
    "mains",
    "walls",
    "magicGuilds",
    "taverns",
    "markets",
    "graals",
    "banks",
    "hires",
    "artifactMarkets",
    "heroBonusBanks",
    "intelligences",
    "manaFountains",
    "myceliumRoots",
    "portalSummonings",
    "rebirthShrines",
    "trainingRanges",
    "unitsConverters",
    "artifactChangers",
)

# Resource name → BuildingRecord field name. Source uses lowercase
# names like "gold", "wood", "ore", "crystals", "gemstones", "mercury",
# "dust", "graal".
_RESOURCE_FIELD: dict[str, str] = {
    "gold": "gold_cost",
    "wood": "wood_cost",
    "ore": "ore_cost",
    "crystals": "crystals_cost",
    "gemstones": "gemstones_cost",
    "mercury": "mercury_cost",
    "dust": "dust_cost",
    "graal": "graal_cost",
}


def _list_at(arr: Any, idx: int) -> Any:
    """``arr[idx]`` if arr is a list and the index is in range, else None."""
    if isinstance(arr, list) and 0 <= idx < len(arr):
        return arr[idx]
    return None


def _build_one(
    raw: dict[str, Any],
    *,
    faction: str,
    category: str,
    level_idx: int,
    source_path: str,
) -> BuildingRecord | None:
    """Map one (building, level) source pair to a BuildingRecord."""
    sid = raw.get("sid")
    if not isinstance(sid, str):
        return None
    level = level_idx + 1
    bid = f"{faction}_{sid}_L{level}"

    name_sid = _list_at(raw.get("names"), level_idx)
    if not isinstance(name_sid, str):
        return None  # need at least a name SID
    desc_sid = _list_at(raw.get("descriptions"), level_idx) or ""
    narr_sid = _list_at(raw.get("narrativeDescriptions"), level_idx)
    icon = _list_at(raw.get("icons"), level_idx)
    bg = _list_at(raw.get("backgroundImages"), level_idx)

    ppl = raw.get("parametersPerLevel") or []
    level_data = ppl[level_idx] if isinstance(ppl, list) and level_idx < len(ppl) else {}
    if not isinstance(level_data, dict):
        level_data = {}

    # Costs: scatter into per-resource columns.
    cost_kwargs: dict[str, int | None] = {}
    for entry in level_data.get("costs") or ():
        if not isinstance(entry, dict):
            continue
        rname = entry.get("name")
        rcost = entry.get("cost")
        field = _RESOURCE_FIELD.get(rname)
        if field is None:
            continue
        try:
            cost_kwargs[field] = int(rcost)
        except (TypeError, ValueError):
            continue

    # Prereqs as <sid>_L<level> strings, Cargo HOLDS-friendly.
    prereqs: list[str] = []
    for pr in level_data.get("prevBuildings") or ():
        if not isinstance(pr, dict):
            continue
        psid = pr.get("sid")
        plvl = pr.get("level")
        if not isinstance(psid, str):
            continue
        try:
            prereqs.append(f"{psid}_L{int(plvl)}")
        except (TypeError, ValueError):
            continue

    # Grid position for this level.
    np = level_data.get("nodePos") or {}
    np_x = np.get("xPos") if isinstance(np, dict) else None
    np_y = np.get("yPos") if isinstance(np, dict) else None

    # Construction state: only populate at level 1 (the sparse-by-default
    # rule per the cargo doc — keeps queries unambiguous).
    if level == 1:
        is_const = raw.get("isConstructedOnStart")
        lvl_start = raw.get("levelOnStart")
        scene_slot = raw.get("sceneSlot")
        construction_kwargs = {
            "is_constructed_on_start": (
                bool(is_const) if isinstance(is_const, bool) else None
            ),
            "level_on_start": (
                int(lvl_start) if isinstance(lvl_start, int) else None
            ),
            "scene_slot": scene_slot if isinstance(scene_slot, str) else None,
        }
    else:
        construction_kwargs = {}

    # Dwelling-only: take the first units group's first variant + weekly.
    units_kwargs: dict[str, Any] = {}
    if category == "hires":
        uh = raw.get("unitsHire")
        units = uh.get("units") if isinstance(uh, dict) else None
        if isinstance(units, list) and units:
            first = units[0]
            if isinstance(first, dict):
                sids = first.get("sids")
                if isinstance(sids, list) and sids and isinstance(sids[0], str):
                    units_kwargs["units_hire_sid"] = sids[0]
                wi = first.get("weeklyIncrement")
                if isinstance(wi, int):
                    units_kwargs["units_weekly"] = wi

    return BuildingRecord(
        id=bid,
        faction=faction,
        category=category,
        sid=sid,
        level=level,
        name_sid=name_sid,
        desc_sid=desc_sid if isinstance(desc_sid, str) else "",
        narrative_desc_sid=narr_sid if isinstance(narr_sid, str) else None,
        icon=icon if isinstance(icon, str) else None,
        background_image=bg if isinstance(bg, str) else None,
        node_pos_x=int(np_x) if isinstance(np_x, int) else None,
        node_pos_y=int(np_y) if isinstance(np_y, int) else None,
        prereqs=tuple(prereqs),
        source_path=source_path,
        **cost_kwargs,
        **construction_kwargs,
        **units_kwargs,
    )


def extract_buildings(paths: CorePaths) -> BuildingExtractionResult:
    """Walk DB/objects_logic/cities/*_city.json and produce one
    BuildingRecord per (faction, building, level) triple."""
    out: list[BuildingRecord] = []
    cities_dir = paths.db / "objects_logic" / "cities"
    for fp in sorted(cities_dir.glob("*_city.json")):
        rel = fp.relative_to(paths.core_root).as_posix()
        doc = load_json(fp)
        for city in iter_array(doc):
            if not isinstance(city, dict):
                continue
            faction = city.get("fraction")
            if not isinstance(faction, str):
                # Fall back to filename stem (e.g. "human_city") when
                # the city dict is missing the field — shouldn't happen
                # in the prod corpus.
                faction = fp.stem.replace("_city", "")
            for category in _BUILDING_GROUP_KEYS:
                items = city.get(category) or ()
                if not isinstance(items, list):
                    continue
                for raw in items:
                    if not isinstance(raw, dict):
                        continue
                    n_levels = len(raw.get("parametersPerLevel") or ())
                    for level_idx in range(n_levels):
                        b = _build_one(
                            raw,
                            faction=faction,
                            category=category,
                            level_idx=level_idx,
                            source_path=rel,
                        )
                        if b is not None:
                            out.append(b)
    out.sort(key=lambda b: (b.faction, b.category, b.sid, b.level))
    return BuildingExtractionResult(buildings=tuple(out))
