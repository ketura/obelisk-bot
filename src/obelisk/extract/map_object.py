"""Adventure-map structure extraction.

Walks ``DB/objects_logic/<category>/*.json`` for the in-scope
categories listed in ``_INSCOPE_CATEGORIES``. For each entry
captures identity (id, name/desc/narrative_desc SIDs), universal
scalars (goods_value, ai_value, view_radius, etc.), the
``guard_units`` list (`<sid>:<amount>` strings), and four sparse
high-signal category-specific scalars (fraction + tier for hires,
resource_name + resource_value for mines).

Rich category-specific payloads (chest variants, event-bank reward
sets, hire unitsData blocks, mine bonuses, market trade rates) are
deliberately NOT extracted in this pass — see D-035 for the
deferral rationale. The ``source_path`` column on every row points
editors at the raw JSON when they need those specifics.
"""

from __future__ import annotations

from typing import Any

from obelisk.extract.loader import CorePaths, iter_array, load_json
from obelisk.models.map_object import (
    MapObjectExtractionResult,
    MapObjectRecord,
)


# Categories under DB/objects_logic/ that produce MapObject rows.
# `cities` is excluded (modeled as Building); `items` excluded
# (Artifact placement metadata, not the canonical artifact data);
# `blocks`, `todo`, `random_hires`, `unit_upgrades`, `town_gates`,
# `win_condition_objects` are internals/AI helpers/campaign mechanics.
_INSCOPE_CATEGORIES: tuple[str, ...] = (
    "res",
    "res_mines",
    "magic_mines",
    "hires",
    "chests",
    "event_banks",
    "taverns",
    "markets",
    "item_markets",
    "res_trade_labs",
    "unit_res_trade_labs",
    "outposts",
    "garrisons",
    "portals",
    "sacrificial_shrine",
    "fickle_shrines",
    "mirages",
    "insaras_eye",
    "eternal_dragon",
    "pocket_dimensions",
    "chimerologist",
    "prisons",
)


def _build_guard_units(raw: Any) -> tuple[str, ...]:
    """Map source ``guardUnits`` ``[{sid, amount}, ...]`` to a tuple
    of ``<sid>:<amount>`` strings (Cargo HOLDS-friendly)."""
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        sid = entry.get("sid")
        amt = entry.get("amount")
        if not isinstance(sid, str):
            continue
        try:
            out.append(f"{sid}:{int(amt)}")
        except (TypeError, ValueError):
            continue
    return tuple(out)


def _maybe_int(v: Any) -> int | None:
    if isinstance(v, bool):  # bool is subclass of int — exclude
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            return None
    return None


def _build_map_object(
    raw: dict[str, Any],
    *,
    category: str,
    source_path: str,
    has_name_sid: set[str],
) -> MapObjectRecord | None:
    eid = raw.get("id")
    if not isinstance(eid, str):
        return None

    # Only attach name/desc SIDs if the corpus actually carries them
    # (94/287 do — anything else gets NULL display fields and relies
    # on category for identification).
    name_sid = f"{eid}_name" if f"{eid}_name" in has_name_sid else None
    desc_sid = f"{eid}_description" if f"{eid}_description" in has_name_sid else None
    narr_sid = f"{eid}_narrativeDescription" if f"{eid}_narrativeDescription" in has_name_sid else None

    return MapObjectRecord(
        id=eid,
        category=category,
        name_sid=name_sid,
        desc_sid=desc_sid,
        narrative_desc_sid=narr_sid,
        goods_value=_maybe_int(raw.get("goodsValue")),
        ai_value=_maybe_int(raw.get("aiValue")),
        custom_guard_value=_maybe_int(raw.get("customGuardValue")),
        view_radius=_maybe_int(raw.get("viewRadius")),
        ai_ignore=(bool(raw["aiIgnore"]) if isinstance(raw.get("aiIgnore"), bool) else None),
        guard_units=_build_guard_units(raw.get("guardUnits")),
        fraction=raw.get("fraction") if isinstance(raw.get("fraction"), str) else None,
        tier=_maybe_int(raw.get("tier")) if category == "hires" else None,
        resource_name=raw.get("resName") if isinstance(raw.get("resName"), str) else None,
        resource_value=_maybe_int(raw.get("resValue")),
        source_path=source_path,
    )


def _load_mapobjects_sid_set(paths: CorePaths) -> set[str]:
    """Read English ``Lang/english/texts/mapObjects.json`` once to
    get the set of all known SIDs. Used to decide which display
    fields to populate per row."""
    fp = paths.core_root / "Lang" / "english" / "texts" / "mapObjects.json"
    if not fp.is_file():
        return set()
    try:
        doc = load_json(fp)
    except Exception:
        return set()
    if not isinstance(doc, dict):
        return set()
    out: set[str] = set()
    for tok in (doc.get("tokens") or ()):
        if isinstance(tok, dict):
            sid = tok.get("sid")
            if isinstance(sid, str):
                out.add(sid)
    return out


def extract_map_objects(paths: CorePaths) -> MapObjectExtractionResult:
    """Walk DB/objects_logic/<in-scope categories>/*.json and produce
    one MapObjectRecord per entry. See D-035."""
    has_name_sid = _load_mapobjects_sid_set(paths)
    out: list[MapObjectRecord] = []
    base = paths.db / "objects_logic"
    for category in _INSCOPE_CATEGORIES:
        cat_dir = base / category
        if not cat_dir.is_dir():
            continue
        for fp in sorted(cat_dir.glob("*.json")):
            rel = fp.relative_to(paths.core_root).as_posix()
            try:
                doc = load_json(fp)
            except Exception:
                continue
            for raw in iter_array(doc):
                if not isinstance(raw, dict):
                    continue
                obj = _build_map_object(
                    raw, category=category, source_path=rel,
                    has_name_sid=has_name_sid,
                )
                if obj is not None:
                    out.append(obj)
    out.sort(key=lambda o: (o.category, o.id))
    return MapObjectExtractionResult(map_objects=tuple(out))
