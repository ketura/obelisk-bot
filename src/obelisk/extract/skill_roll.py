"""Skill-roll table extraction.

Walks::

    DB/heroes_skills/skills_by_level_tables/*.json               (24 files)
    DB/heroes_skills/skills_by_level_replace_tables/*.json       (1 file)
    DB/heroes_skills/skills/pseudo_skills.json                   (1 file)

Produces the five record types defined in ``models/skill_roll.py``. Per
the analysis in decisions.md D-041:

* The ``-1`` sentinel band is byte-identical to the default ``[1..50]``
  band in every observed file. Dropped at extract time; the audit
  warns if a future patch breaks the equality.
* The ``-2`` sentinel band is the universal pseudo-skill pool, identical
  across all 24 files. Surfaced once via ``StatBonusRollRecord`` rows
  (built from the ``pseudo_skills.json`` definitions, weight from the
  -2 band of any one file). Not stored per-table.
* The positive-level default band and the ``specialList`` entries get
  emitted as ``SkillRollWeightRecord`` rows with ``band_kind`` discriminators.

Campaign / custom_maps / tutorial subdirectories are explicitly skipped
(per project decision — campaign data is out of scope until display
articles exist for it).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

from obelisk.extract.loader import CorePaths, iter_array, load_json
from obelisk.models.skill_roll import (
    BAND_KINDS,
    SkillRollBandRecord,
    SkillRollExtractionResult,
    SkillRollReplacementRecord,
    SkillRollTableRecord,
    SkillRollWeightRecord,
    StatBonusRollRecord,
)

log = logging.getLogger(__name__)


# Folder-name (plural) → canonical fraction id (singular).
# Mirrors the normalization the bot already does for HeroClass / Unit /
# Faction extraction (see D-027 and models/common.Faction).
_FOLDER_TO_FRACTION: dict[str, str] = {
    "humans": "human",
    "demons": "demon",
    "necros": "undead",
    "dungeon": "dungeon",
    "nature": "nature",
    "unfrozen": "unfrozen",
}

# Stat-name normalization for pseudo skills. Source uses raw stat ids
# (``offence`` / ``defence`` / ``spellPower`` / ``intelligence``); we
# pass these through untouched but pin the allowed set here so a future
# patch with a new stat surfaces as an audit warning rather than silent
# leakage.
_PSEUDO_STATS: frozenset[str] = frozenset(
    {"offence", "defence", "spellPower", "intelligence"}
)


# Canonical descriptions for the four band kinds. Stored on
# SkillRollBandRecord.description; wiki editors may rewrite for prose.
_BAND_DESCRIPTIONS: dict[str, str] = {
    "default": (
        "Applies to every level-up from 1 through 50. The baseline pool "
        "every roll draws from."
    ),
    "magic_levels": (
        "Every 4th level except 20 (which is covered by the level-20 "
        "milestone). Adds the four magic-element schools at their "
        "baseline weights — effectively doubling the chance of a "
        "magic-school offering on those levels."
    ),
    "signature_levels": (
        "Every 5th level from 5 through 30, except 20. Adds +100 weight "
        "to the table's own faction skill and +100 to the class-signature "
        "skill (battle_artistry for might, wisdom for magic)."
    ),
    "level_20_mega": (
        "The level-20 milestone — fires alone. Adds doubled magic-element "
        "weights (160/40/120/80 for day/night/space/primal) plus +100 "
        "faction and +100 class-signature. The single most-distinctive "
        "level in the roll system."
    ),
}


def _classify_special_band(levels: tuple[int, ...]) -> str | None:
    """Return the canonical ``band_kind`` for a specialList entry's level
    list, or ``None`` if the pattern doesn't match any known shape.

    The canonical shapes are class-invariant in the 2026-05-14 corpus
    and identified by exact level-set match:
    """
    if levels == (20,):
        return "level_20_mega"
    if levels == (5, 10, 15, 25, 30):
        return "signature_levels"
    if levels == (4, 8, 12, 16, 24, 28, 32, 36, 40, 44, 48):
        return "magic_levels"
    return None


def _parse_table_filename(name: str) -> tuple[str, str, str] | None:
    """Map ``<faction_folder>_<class_type>_skills_table.json`` (or its
    ``arenaGame_<...>`` arena prefix) to ``(mode, faction_folder, class_type)``.

    Returns ``None`` for filenames not matching the canonical shape (e.g.
    tutorial variants).
    """
    stem = name.removesuffix(".json")
    if not stem.endswith("_skills_table"):
        return None
    body = stem.removesuffix("_skills_table")
    mode = "standard"
    if body.startswith("arenaGame_"):
        body = body.removeprefix("arenaGame_")
        mode = "arena"
    # body is now ``<faction_folder>_<class_type>``; class_type is the
    # trailing token, faction_folder is everything before.
    if "_" not in body:
        return None
    faction_folder, class_type = body.rsplit("_", 1)
    if class_type not in ("might", "magic"):
        return None
    return mode, faction_folder, class_type


def _normalize_levels(raw: Any) -> tuple[int, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[int] = []
    for x in raw:
        if isinstance(x, int):
            out.append(x)
        elif isinstance(x, str):
            try:
                out.append(int(x))
            except ValueError:
                continue
    return tuple(out)


def _extract_one_table(
    path: Path,
    *,
    source_path: str,
    stat_bonus_seen: dict[str, StatBonusRollRecord],
    pseudo_index: dict[str, dict[str, Any]],
    audit: list[str],
) -> tuple[
    SkillRollTableRecord | None, list[SkillRollWeightRecord]
]:
    """Extract one ``*_skills_table.json`` file.

    Side effects: populates ``stat_bonus_seen`` from the -2 band the first
    time it is observed (later observations are checked for equality and
    surfaced as audit warnings on divergence). Appends to ``audit``.
    """
    parsed = _parse_table_filename(path.name)
    if parsed is None:
        audit.append(f"skipped (unrecognised filename): {source_path}")
        return None, []
    mode, faction_folder, class_type = parsed
    fraction = _FOLDER_TO_FRACTION.get(faction_folder)
    if fraction is None:
        audit.append(
            f"skipped (unknown faction folder {faction_folder!r}): {source_path}"
        )
        return None, []
    class_id = f"{class_type}_{fraction}"

    try:
        doc = load_json(path)
    except Exception as e:
        audit.append(f"load failed: {source_path}: {e}")
        return None, []

    rows = list(iter_array(doc))
    if not rows or not isinstance(rows[0], dict):
        audit.append(f"empty/malformed array in {source_path}")
        return None, []

    record = rows[0]
    table_id = record.get("id")
    if not isinstance(table_id, str):
        audit.append(f"missing 'id' in {source_path}")
        return None, []

    default_list = record.get("defaultList") or []
    special_list = record.get("specialList") or []

    # Find the canonical positive band and the negative sentinels.
    main_band: dict[str, Any] | None = None
    neg1_band: dict[str, Any] | None = None
    neg2_band: dict[str, Any] | None = None
    for entry in default_list:
        if not isinstance(entry, dict):
            continue
        levels = _normalize_levels(entry.get("levels"))
        if not levels:
            continue
        if levels == (-1,):
            neg1_band = entry
        elif levels == (-2,):
            neg2_band = entry
        elif all(L > 0 for L in levels):
            # Multiple positive bands aren't expected; take the first
            # and audit the rest. (No file in the 2026-05-14 corpus has
            # more than one positive band.)
            if main_band is None:
                main_band = entry
            else:
                audit.append(
                    f"{table_id}: multiple positive defaultList bands, "
                    f"using the first"
                )
        else:
            audit.append(
                f"{table_id}: unrecognised levels signature {levels!r} "
                f"in defaultList"
            )

    if main_band is None:
        audit.append(f"{table_id}: no positive defaultList band found")
        return None, []

    # Audit: -1 should be byte-identical to the main band. Drop either
    # way; only warn on divergence.
    if neg1_band is not None:
        if neg1_band.get("rollChances") != main_band.get("rollChances"):
            audit.append(
                f"{table_id}: -1 sentinel band diverges from default band "
                f"(expected byte-identical)"
            )

    # Capture / cross-check the universal -2 pseudo-skill pool.
    if neg2_band is not None:
        _record_stat_bonuses(
            neg2_band, table_id=table_id,
            stat_bonus_seen=stat_bonus_seen,
            pseudo_index=pseudo_index, audit=audit,
        )

    weights: list[SkillRollWeightRecord] = []

    # Emit default-band weights.
    for rc in main_band.get("rollChances") or ():
        if not isinstance(rc, dict):
            continue
        sid = rc.get("sid")
        chance = rc.get("chance")
        if isinstance(sid, str) and isinstance(chance, int):
            weights.append(SkillRollWeightRecord(
                table_id=table_id, band_kind="default",
                skill_id=sid, weight=chance,
            ))

    # Emit special-band weights with band_kind classification.
    for entry in special_list:
        if not isinstance(entry, dict):
            continue
        levels = tuple(sorted(_normalize_levels(entry.get("levels"))))
        band_kind = _classify_special_band(levels)
        if band_kind is None:
            audit.append(
                f"{table_id}: specialList entry with unrecognised level "
                f"pattern {levels!r} — skipped"
            )
            continue
        for rc in entry.get("rollChances") or ():
            if not isinstance(rc, dict):
                continue
            sid = rc.get("sid")
            chance = rc.get("chance")
            if isinstance(sid, str) and isinstance(chance, int):
                weights.append(SkillRollWeightRecord(
                    table_id=table_id, band_kind=band_kind,
                    skill_id=sid, weight=chance,
                ))

    table = SkillRollTableRecord(
        id=table_id,
        class_id=class_id,
        faction=fraction,
        class_type=class_type,
        mode=mode,
        source_path=source_path,
    )
    return table, weights


def _record_stat_bonuses(
    neg2_band: dict[str, Any],
    *,
    table_id: str,
    stat_bonus_seen: dict[str, StatBonusRollRecord],
    pseudo_index: dict[str, dict[str, Any]],
    audit: list[str],
) -> None:
    """Promote the universal -2 band into ``StatBonusRollRecord`` rows.

    First occurrence wins; later occurrences are audited for divergence
    (the band is empirically byte-identical across all 24 source files).
    """
    for rc in neg2_band.get("rollChances") or ():
        if not isinstance(rc, dict):
            continue
        sid = rc.get("sid")
        chance = rc.get("chance")
        if not isinstance(sid, str) or not isinstance(chance, int):
            continue
        if sid in stat_bonus_seen:
            # Audit equality with the recorded weight.
            if stat_bonus_seen[sid].weight != chance:
                audit.append(
                    f"{table_id}: -2 band weight for {sid} = {chance} "
                    f"diverges from previously-seen {stat_bonus_seen[sid].weight}"
                )
            continue
        pseudo_raw = pseudo_index.get(sid)
        if pseudo_raw is None:
            audit.append(
                f"{table_id}: -2 band references {sid!r} but pseudo_skills.json "
                f"has no matching entry"
            )
            continue
        bonuses = pseudo_raw.get("parametersPerLevel") or ()
        if not bonuses or not isinstance(bonuses[0], dict):
            audit.append(f"{sid}: pseudo skill has no parametersPerLevel[0]")
            continue
        bonus_list = bonuses[0].get("bonuses") or ()
        if not bonus_list or not isinstance(bonus_list[0], dict):
            audit.append(f"{sid}: pseudo skill bonus block missing")
            continue
        params = bonus_list[0].get("parameters") or ()
        if len(params) < 2:
            audit.append(f"{sid}: pseudo skill bonus parameters shape unexpected")
            continue
        stat = params[0]
        try:
            magnitude = int(params[1])
        except (TypeError, ValueError):
            audit.append(f"{sid}: pseudo skill magnitude not an int: {params[1]!r}")
            continue
        if stat not in _PSEUDO_STATS:
            audit.append(
                f"{sid}: pseudo skill targets unrecognised stat {stat!r} "
                f"— extractor may need to widen the allowed set"
            )
        name_sid = pseudo_raw.get("name")
        desc_sid = pseudo_raw.get("desc")
        if not isinstance(name_sid, str) or not isinstance(desc_sid, str):
            audit.append(f"{sid}: pseudo skill missing name/desc SID")
            continue
        stat_bonus_seen[sid] = StatBonusRollRecord(
            id=sid, stat=stat, magnitude=magnitude, weight=chance,
            name_sid=name_sid, desc_sid=desc_sid,
        )


def _build_hero_variant_map(paths: CorePaths) -> dict[str, str]:
    """Walk DB/heroes/*/*.json to build a ``hero_id -> skillsRollVariant`` map.

    Used to derive ``arena_table_id`` for SkillRollReplacement rows: the
    hero's arena counterpart is ``arenaGame_<standard_variant>``.

    Skips campaign / tutorial / custom-map hero dirs (those don't appear
    in the replace table).
    """
    out: dict[str, str] = {}
    heroes_root = paths.db / "heroes"
    if not heroes_root.is_dir():
        return out
    for faction_dir in heroes_root.iterdir():
        if not faction_dir.is_dir():
            continue
        if faction_dir.name not in _FOLDER_TO_FRACTION:
            continue
        for fp in faction_dir.glob("*.json"):
            try:
                doc = load_json(fp)
            except Exception:
                continue
            for raw in iter_array(doc):
                if not isinstance(raw, dict):
                    continue
                hero_id = raw.get("id")
                variant = raw.get("skillsRollVariant")
                if isinstance(hero_id, str) and isinstance(variant, str):
                    out[hero_id] = variant
    return out


def _extract_replacements(
    paths: CorePaths,
    *,
    hero_variant: dict[str, str],
    audit: list[str],
) -> list[SkillRollReplacementRecord]:
    """Read the single replace-table file and expand per (hero, level)."""
    dir_ = paths.db / "heroes_skills" / "skills_by_level_replace_tables"
    if not dir_.is_dir():
        return []
    out: list[SkillRollReplacementRecord] = []
    for fp in sorted(dir_.glob("*.json")):
        source_path = fp.relative_to(paths.core_root).as_posix()
        try:
            doc = load_json(fp)
        except Exception as e:
            audit.append(f"replace_table load failed: {source_path}: {e}")
            continue
        for entry in iter_array(doc):
            if not isinstance(entry, dict):
                continue
            hero_id = entry.get("id")
            if not isinstance(hero_id, str):
                continue
            standard_variant = hero_variant.get(hero_id)
            if standard_variant is None:
                audit.append(
                    f"replace_table: hero {hero_id!r} not found in "
                    f"DB/heroes/ — arena_table_id will be empty"
                )
                arena_table_id = ""
            else:
                arena_table_id = f"arenaGame_{standard_variant}"
            for band in entry.get("defaultList") or ():
                if not isinstance(band, dict):
                    continue
                levels = _normalize_levels(band.get("levels"))
                for rc in band.get("rollChances") or ():
                    if not isinstance(rc, dict):
                        continue
                    sid = rc.get("sid")
                    chance = rc.get("chance")
                    if not isinstance(sid, str) or not isinstance(chance, int):
                        continue
                    for level in levels:
                        out.append(SkillRollReplacementRecord(
                            hero_id=hero_id,
                            arena_table_id=arena_table_id,
                            level=level,
                            skill_id=sid,
                            weight=chance,
                        ))
    return out


def _build_bands(
    observed_default_levels: tuple[int, ...],
) -> tuple[SkillRollBandRecord, ...]:
    """Construct the 4-row SkillRollBand seed.

    The default band's levels come from what we actually saw in the
    main positive-band entry (usually 1..50). The three overlay bands
    are class-invariant by extract-time assertion.
    """
    return (
        SkillRollBandRecord(
            id="default",
            levels=observed_default_levels,
            description=_BAND_DESCRIPTIONS["default"],
        ),
        SkillRollBandRecord(
            id="magic_levels",
            levels=(4, 8, 12, 16, 24, 28, 32, 36, 40, 44, 48),
            description=_BAND_DESCRIPTIONS["magic_levels"],
        ),
        SkillRollBandRecord(
            id="signature_levels",
            levels=(5, 10, 15, 25, 30),
            description=_BAND_DESCRIPTIONS["signature_levels"],
        ),
        SkillRollBandRecord(
            id="level_20_mega",
            levels=(20,),
            description=_BAND_DESCRIPTIONS["level_20_mega"],
        ),
    )


def _load_pseudo_index(paths: CorePaths) -> dict[str, dict[str, Any]]:
    """Build a ``{pseudo_id -> raw_entry}`` map from ``pseudo_skills.json``."""
    fp = paths.db / "heroes_skills" / "skills" / "pseudo_skills.json"
    if not fp.is_file():
        return {}
    try:
        doc = load_json(fp)
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for raw in iter_array(doc):
        if isinstance(raw, dict):
            sid = raw.get("id")
            if isinstance(sid, str):
                out[sid] = raw
    return out


def extract_skill_rolls(paths: CorePaths) -> SkillRollExtractionResult:
    """Top-level entry point.

    Reads every standard / arena ``*_skills_table.json`` at the top of
    ``DB/heroes_skills/skills_by_level_tables/`` (skipping campaign /
    custom_maps subdirs), plus the single replace-table file and
    pseudo_skills.json. Returns the consolidated records.
    """
    tables_root = paths.db / "heroes_skills" / "skills_by_level_tables"
    audit: list[str] = []

    if not tables_root.is_dir():
        audit.append(f"directory not found: {tables_root}")
        return SkillRollExtractionResult(
            tables=(), weights=(), bands=(),
            stat_bonus_rolls=(), replacements=(),
            audit_warnings=tuple(audit),
        )

    pseudo_index = _load_pseudo_index(paths)
    stat_bonus_seen: dict[str, StatBonusRollRecord] = {}

    tables: list[SkillRollTableRecord] = []
    weights: list[SkillRollWeightRecord] = []
    observed_default_levels: tuple[int, ...] = ()

    for fp in sorted(tables_root.glob("*.json")):
        source_path = fp.relative_to(paths.core_root).as_posix()
        table, table_weights = _extract_one_table(
            fp, source_path=source_path,
            stat_bonus_seen=stat_bonus_seen,
            pseudo_index=pseudo_index, audit=audit,
        )
        if table is None:
            continue
        tables.append(table)
        weights.extend(table_weights)
        # Capture the default-band level list from the first valid table.
        # (Empirical: byte-identical across all 24 — but we surface a
        # warning if anything ever diverges so it doesn't silently rot.)
        if not observed_default_levels:
            try:
                doc = load_json(fp)
                main = next(
                    x for x in doc["array"][0]["defaultList"]
                    if any(L > 0 for L in _normalize_levels(x.get("levels")))
                )
                observed_default_levels = tuple(sorted(
                    _normalize_levels(main.get("levels"))
                ))
            except Exception as e:
                audit.append(f"could not recover default levels from {source_path}: {e}")

    hero_variant = _build_hero_variant_map(paths)
    replacements = _extract_replacements(
        paths, hero_variant=hero_variant, audit=audit,
    )

    bands = _build_bands(observed_default_levels or tuple(range(1, 51)))

    # Deterministic emit order.
    tables.sort(key=lambda t: (t.mode, t.class_id, t.id))
    weights.sort(key=lambda w: (
        w.table_id,
        BAND_KINDS.index(w.band_kind) if w.band_kind in BAND_KINDS else 99,
        -w.weight,
        w.skill_id,
    ))
    stat_bonus_rows = tuple(
        stat_bonus_seen[sid] for sid in sorted(
            stat_bonus_seen.keys(), key=_pseudo_sort_key,
        )
    )
    replacements.sort(key=lambda r: (r.hero_id, r.level, r.skill_id))

    return SkillRollExtractionResult(
        tables=tuple(tables),
        weights=tuple(weights),
        bands=bands,
        stat_bonus_rolls=stat_bonus_rows,
        replacements=tuple(replacements),
        audit_warnings=tuple(audit),
    )


def _pseudo_sort_key(sid: str) -> tuple[int, str]:
    """Sort skill_pseudo_<N> by numeric N when possible, lexicographic
    fallback otherwise."""
    parts = sid.rsplit("_", 1)
    if len(parts) == 2:
        try:
            return (int(parts[1]), sid)
        except ValueError:
            pass
    return (999, sid)
