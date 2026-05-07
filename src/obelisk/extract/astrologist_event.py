"""Astrologist event (week + month) extraction.

Walks ``DB/weeks/weeks.json`` (15 entries) and
``DB/weeks/months.json`` (11 entries) for identity rows, plus
``DB/weeks_info.json`` for per-event ``rollChance`` and the
global ``countToReturnWeek`` / ``countToReturnMonth``
re-roll thresholds.

See D-038.
"""

from __future__ import annotations

from typing import Any

from obelisk.extract.loader import CorePaths, iter_array, load_json
from obelisk.models.astrologist_event import (
    AstrologistEventExtractionResult,
    AstrologistEventRecord,
)


def _build_event(
    raw: dict[str, Any], *, category: str, source_path: str,
    roll_chance: int | None, count_to_return: int | None,
) -> AstrologistEventRecord | None:
    rid = raw.get("id")
    name_sid = raw.get("name")
    if not isinstance(rid, str) or not isinstance(name_sid, str):
        return None
    return AstrologistEventRecord(
        id=rid,
        category=category,
        name_sid=name_sid,
        desc_sid=raw.get("desc") if isinstance(raw.get("desc"), str) else None,
        icon=raw.get("icon") if isinstance(raw.get("icon"), str) else None,
        buff_sid=raw.get("buffSid") if isinstance(raw.get("buffSid"), str) else None,
        roll_chance=roll_chance,
        count_to_return=count_to_return,
        source_path=source_path,
    )


def _load_weeks_info(paths: CorePaths) -> tuple[dict[str, int], int | None, dict[str, int], int | None]:
    """Return (week_id → roll_chance, weeks_count_to_return,
    month_id → roll_chance, months_count_to_return)."""
    fp = paths.db / "weeks_info.json"
    weeks_chance: dict[str, int] = {}
    months_chance: dict[str, int] = {}
    weeks_return: int | None = None
    months_return: int | None = None
    if not fp.is_file():
        return weeks_chance, weeks_return, months_chance, months_return
    try:
        doc = load_json(fp)
    except Exception:
        return weeks_chance, weeks_return, months_chance, months_return
    if not isinstance(doc, dict):
        return weeks_chance, weeks_return, months_chance, months_return
    weeks_return = doc.get("countToReturnWeek") if isinstance(doc.get("countToReturnWeek"), int) else None
    months_return = doc.get("countToReturnMonth") if isinstance(doc.get("countToReturnMonth"), int) else None
    for entry in doc.get("weeks") or ():
        if isinstance(entry, dict):
            sid = entry.get("sid")
            chance = entry.get("rollChance")
            if isinstance(sid, str) and isinstance(chance, int):
                weeks_chance[sid] = chance
    for entry in doc.get("months") or ():
        if isinstance(entry, dict):
            sid = entry.get("sid")
            chance = entry.get("rollChance")
            if isinstance(sid, str) and isinstance(chance, int):
                months_chance[sid] = chance
    return weeks_chance, weeks_return, months_chance, months_return


def extract_astrologist_events(
    paths: CorePaths,
) -> AstrologistEventExtractionResult:
    """Extract weeks + months as one unified event catalog. See D-038."""
    weeks_chance, weeks_return, months_chance, months_return = _load_weeks_info(paths)

    out: list[AstrologistEventRecord] = []
    for fname, category, chance_map, return_count in (
        ("weeks.json", "week", weeks_chance, weeks_return),
        ("months.json", "month", months_chance, months_return),
    ):
        fp = paths.db / "weeks" / fname
        if not fp.is_file():
            continue
        rel = fp.relative_to(paths.core_root).as_posix()
        try:
            doc = load_json(fp)
        except Exception:
            continue
        for raw in iter_array(doc):
            if not isinstance(raw, dict):
                continue
            rid = raw.get("id") if isinstance(raw.get("id"), str) else None
            chance = chance_map.get(rid) if rid else None
            rec = _build_event(
                raw, category=category, source_path=rel,
                roll_chance=chance, count_to_return=return_count,
            )
            if rec is not None:
                out.append(rec)

    return AstrologistEventExtractionResult(events=tuple(out))
