"""Hero extraction.

Walks ``DB/heroes/<faction-folder>/*.json`` plus ``campaign/`` and
``campaign_tutorial/`` subdirs, derives the 12 ``HeroClass`` records
from the faction-hero corpus, then emits ``HeroRecord`` entries with
class-default fields encoded as sparse overrides. See D-027.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from obelisk.extract.loader import CorePaths, iter_array, load_json
from obelisk.models.common import Sid
from obelisk.models.hero import (
    Bonus,
    HeroClassRecord,
    HeroExtractionResult,
    HeroRecord,
    HeroSpecializationExtractionResult,
    HeroSpecializationRecord,
    HeroStartSquadSlot,
    HeroStats,
    HeroStatsRolls,
    HeroSubClassExtractionResult,
    HeroSubClassRecord,
)


# Folder name on disk → faction id (for the necros / demons drift).
_FOLDER_TO_FACTION: dict[str, str] = {
    "humans": "human",
    "necros": "undead",
    "dungeon": "dungeon",
    "nature": "nature",
    "demons": "demon",
    "unfrozen": "unfrozen",
}


def _heroes_root(paths: CorePaths) -> Path:
    return paths.db / "heroes"


def _build_stats(raw: dict[str, Any]) -> HeroStats:
    """Map source ``stats`` dict to :class:`HeroStats`."""
    return HeroStats(
        view_radius=int(raw.get("viewRadius", 0)),
        stats_num=int(raw.get("statsNum", 0)),
        magic_casts_per_round=int(raw.get("magicCastsPerRound", 0)),
        enable_tactics=bool(raw.get("enableTactics", False)),
        tactics_placement_size=int(raw.get("tacticsPlacementSize", 0)),
        enable_hero_native_biome=bool(raw.get("enableHeroNativeBiome", False)),
        offence=int(raw.get("offence", 0)),
        defence=int(raw.get("defence", 0)),
        spell_power=int(raw.get("spellPower", 0)),
        intelligence=int(raw.get("intelligence", 0)),
        luck=int(raw.get("luck", 0)),
        morale=int(raw.get("moral", 0)),  # source uses "moral", we normalize to "morale"
    )


def _build_stats_rolls(raw: list[dict[str, Any]]) -> HeroStatsRolls:
    """Flatten 2-band × 4-chance source into 8 named columns.

    Source: ``[{levelFrom: 1, rollChances: [{v:0,c:35}, {v:1,c:35}, ...]}, {levelFrom: 24, ...}]``.
    Bands always start at level 1 and 24 in faction heroes; if a
    campaign hero ships fewer bands or different boundaries, we
    default the missing band to all-zeros and keep going (the audit
    can flag).
    """
    bands_by_level: dict[int, dict[int, int]] = {1: {}, 24: {}}
    for band in raw:
        if not isinstance(band, dict):
            continue
        lvl = int(band.get("levelFrom", -1))
        if lvl not in bands_by_level:
            # Unfamiliar boundary — store under the closest known band.
            # (Empirically this hasn't happened in 2026-05-03; keep simple.)
            continue
        for rc in band.get("rollChances", []) or ():
            if not isinstance(rc, dict):
                continue
            v = int(rc.get("v", -1))
            c = int(rc.get("c", 0))
            if 0 <= v <= 3:
                bands_by_level[lvl][v] = c

    def get(lvl: int, v: int) -> int:
        return bands_by_level[lvl].get(v, 0)

    return HeroStatsRolls(
        lvl1_attack=get(1, 0),
        lvl1_defense=get(1, 1),
        lvl1_power=get(1, 2),
        lvl1_knowledge=get(1, 3),
        lvl24_attack=get(24, 0),
        lvl24_defense=get(24, 1),
        lvl24_power=get(24, 2),
        lvl24_knowledge=get(24, 3),
    )


def _build_squad(
    primary: list[Any], alt: list[Any]
) -> tuple[HeroStartSquadSlot, ...]:
    """Merge primary + alt into a single tuple, marking variant."""
    out: list[HeroStartSquadSlot] = []
    for variant, raw in (("primary", primary), ("alt", alt)):
        for slot, item in enumerate(raw or (), start=1):
            if not isinstance(item, dict):
                continue
            sid = item.get("sid")
            if not isinstance(sid, str):
                continue
            out.append(
                HeroStartSquadSlot(
                    variant=variant,
                    slot=slot,
                    unit_sid=sid,
                    min=int(item.get("min", 0)),
                    max=int(item.get("max", 0)),
                )
            )
    return tuple(out)


def _build_skills(raw: list[Any]) -> tuple[tuple[Sid, int], ...]:
    """Extract starting-skill (sid, level) pairs. Per D-027 (revised
    twice): level is preserved as a parallel list because 8/208
    entries differ from the default of 1."""
    out: list[tuple[Sid, int]] = []
    for item in raw or ():
        if not isinstance(item, dict):
            continue
        sid = item.get("sid")
        if isinstance(sid, str):
            out.append((sid, int(item.get("skillLevel", 1))))
    return tuple(out)


def _build_magics(raw: list[Any]) -> tuple[Sid, ...]:
    """Extract starting-spell SIDs only. ``level`` and ``isLearned``
    are dropped per D-027 (revised) — both are constant in the
    2026-05-03 corpus (1 / True)."""
    out: list[Sid] = []
    for item in raw or ():
        if not isinstance(item, dict):
            continue
        sid = item.get("sidConfig") or item.get("sid")
        if isinstance(sid, str):
            out.append(sid)
    return tuple(out)


def _class_id(faction: str, class_type: str) -> str:
    """e.g. ('demon', 'magic') -> 'magic_demon' (matches L10n SID prefix)."""
    return f"{class_type}_{faction}"


def _derive_hero_classes(faction_heroes: list[dict[str, Any]]) -> dict[str, HeroClassRecord]:
    """Cluster faction heroes by (faction, classType); take the first
    hero in each cell as the class template. Empirically every faction
    hero in a cell shares the 11 class-shared field values, so the
    first hero suffices.

    Returns a dict keyed by class id (e.g. ``magic_demon``).
    """
    seen: dict[str, HeroClassRecord] = {}
    for raw in faction_heroes:
        faction = raw.get("fraction")
        class_type = raw.get("classType")
        if not (isinstance(faction, str) and isinstance(class_type, str)):
            continue
        cid = _class_id(faction, class_type)
        if cid in seen:
            continue
        mounts = raw.get("mounts") or ()
        mount = mounts[0] if mounts else ""
        atb = tuple(float(x) for x in (raw.get("attacksTimesBefore") or ()))
        seen[cid] = HeroClassRecord(
            id=cid,
            name_sid=f"{cid}_name",
            desc_sid=f"{class_type}_desc",  # shared per classType (see D-026 / HeroClass.md)
            faction=faction,
            class_type=class_type,
            mesh=str(raw.get("mesh", "")),
            mount=str(mount),
            native_biome=str(raw.get("nativeBiome", "")),
            skills_roll_variant=str(raw.get("skillsRollVariant", "")),
            cost_gold=int(raw.get("costGold", 0)),
            start_level=int(raw.get("startLevel", 1)),
            attacks_times_before=atb,
            stats=_build_stats(raw.get("stats") or {}),
            stats_rolls=_build_stats_rolls(raw.get("statsRolls") or []),
        )
    return seen


def _build_hero(
    raw: dict[str, Any],
    *,
    source_path: str,
    faction: str,
    class_type: str,
    class_defaults: HeroClassRecord | None,
) -> HeroRecord:
    """Map one source hero record to :class:`HeroRecord`, with
    class-default fields encoded as sparse overrides when the hero's
    value diverges. Faction heroes uniformly match their class, so
    every override field stays ``None``."""
    hero_id = str(raw["id"])

    # SIDs: faction heroes use implicit conventions; campaign heroes set
    # them explicitly in JSON (and they happen to point at hero_id, but
    # we honor whatever the JSON says).
    name_sid = str(raw.get("name") or hero_id)
    motto_sid = str(raw.get("motto") or f"{hero_id}_motto")
    desc_sid = str(raw.get("description") or f"{hero_id}_description")

    mounts = raw.get("mounts") or ()
    mount = mounts[0] if mounts else ""
    atb = tuple(float(x) for x in (raw.get("attacksTimesBefore") or ()))
    stats = _build_stats(raw.get("stats") or {})
    stats_rolls = _build_stats_rolls(raw.get("statsRolls") or [])

    def diverge(value: Any, default: Any) -> Any | None:
        return value if value != default else None

    # Sparse override fields: present only when divergent from class default.
    if class_defaults is not None:
        cost_gold_override = diverge(int(raw.get("costGold", 0)), class_defaults.cost_gold)
        start_level_override = diverge(int(raw.get("startLevel", 1)), class_defaults.start_level)
        attacks_times_before_override = diverge(atb, class_defaults.attacks_times_before)
        mesh_override = diverge(str(raw.get("mesh", "")), class_defaults.mesh)
        mount_override = diverge(str(mount), class_defaults.mount)
        native_biome_override = diverge(str(raw.get("nativeBiome", "")), class_defaults.native_biome)
        skills_roll_variant_override = diverge(
            str(raw.get("skillsRollVariant", "")), class_defaults.skills_roll_variant
        )
        stats_override = diverge(stats, class_defaults.stats)
        stats_rolls_override = diverge(stats_rolls, class_defaults.stats_rolls)
    else:
        # No class defaults available — pass everything through as overrides.
        cost_gold_override = int(raw.get("costGold", 0))
        start_level_override = int(raw.get("startLevel", 1))
        attacks_times_before_override = atb
        mesh_override = str(raw.get("mesh", ""))
        mount_override = str(mount)
        native_biome_override = str(raw.get("nativeBiome", ""))
        skills_roll_variant_override = str(raw.get("skillsRollVariant", ""))
        stats_override = stats
        stats_rolls_override = stats_rolls

    return HeroRecord(
        id=hero_id,
        name_sid=name_sid,
        motto_sid=motto_sid,
        desc_sid=desc_sid,
        class_id=_class_id(faction, class_type),
        faction=faction,
        class_type=class_type,
        icon=str(raw.get("icon", "")),
        specialization_id=str(raw.get("specialization", "")),
        source_path=source_path,
        start_squad=_build_squad(
            raw.get("startSquad") or [],
            raw.get("startSquadAlt") or [],
        ),
        start_skills=_build_skills(raw.get("startSkills") or []),
        start_magics=_build_magics(raw.get("startMagics") or []),
        cost_gold_override=cost_gold_override,
        start_level_override=start_level_override,
        attacks_times_before_override=attacks_times_before_override,
        mesh_override=mesh_override,
        mount_override=mount_override,
        native_biome_override=native_biome_override,
        skills_roll_variant_override=skills_roll_variant_override,
        stats_override=stats_override,
        stats_rolls_override=stats_rolls_override,
    )


def extract_heroes(paths: CorePaths) -> HeroExtractionResult:
    """Walk all hero subfolders, derive class defaults from faction
    heroes, then build HeroRecords for every hero (faction, campaign,
    tutorial, custom). Skips heroes whose ``fraction``/``classType``
    don't resolve to a known class — they get an empty class_id and
    every field as an override."""
    root = _heroes_root(paths)

    # First pass: gather faction-hero raws to derive class defaults.
    faction_raws: list[dict[str, Any]] = []
    for folder in _FOLDER_TO_FACTION:
        for p in sorted((root / folder).glob("*.json")):
            doc = load_json(p)
            for raw in iter_array(doc):
                if isinstance(raw, dict) and "id" in raw:
                    faction_raws.append(raw)

    classes = _derive_hero_classes(faction_raws)

    # Second pass: build every hero (faction + campaign + tutorial + custom).
    heroes: list[HeroRecord] = []
    for sub in sorted(p.name for p in root.iterdir() if p.is_dir()):
        for p in sorted((root / sub).glob("*.json")):
            rel = p.relative_to(paths.core_root).as_posix()
            doc = load_json(p)
            for raw in iter_array(doc):
                if not (isinstance(raw, dict) and "id" in raw):
                    continue
                faction = raw.get("fraction")
                class_type = raw.get("classType")
                if not (isinstance(faction, str) and isinstance(class_type, str)):
                    continue
                cid = _class_id(faction, class_type)
                heroes.append(
                    _build_hero(
                        raw,
                        source_path=rel,
                        faction=faction,
                        class_type=class_type,
                        class_defaults=classes.get(cid),
                    )
                )

    heroes.sort(key=lambda h: h.id)
    class_list = tuple(sorted(classes.values(), key=lambda c: c.id))
    return HeroExtractionResult(hero_classes=class_list, heroes=tuple(heroes))


# -----------------------------------------------------------------------------
# Hero specializations
# -----------------------------------------------------------------------------


def build_bonus(
    raw: dict[str, Any],
    *,
    parent_type: str,
    parent_id: str,
    ordinal: int,
) -> Bonus | None:
    """Map one source bonus dict to :class:`Bonus`. Returns ``None``
    for entries missing the required ``type``. Per D-031: callers
    supply parent_type + parent_id discriminators so the resulting
    rows land in the unified Bonus Cargo table."""
    btype = raw.get("type")
    if not isinstance(btype, str):
        return None
    parameters = tuple(str(p) for p in (raw.get("parameters") or ()))
    upgrade = raw.get("upgrade") if isinstance(raw.get("upgrade"), dict) else None
    return Bonus(
        parent_type=parent_type,
        parent_id=parent_id,
        ordinal=ordinal,
        type=btype,
        parameters=parameters,
        activation_level=(int(raw["activationLevel"])
                          if "activationLevel" in raw else None),
        upgrade_increment=(float(upgrade["increment"])
                           if upgrade and "increment" in upgrade else None),
        upgrade_level_step=(int(upgrade["levelStep"])
                            if upgrade and "levelStep" in upgrade else None),
        receivers=tuple(
            str(r) for r in (raw.get("receivers") or ())
        ),
        battle_type=raw.get("battleType") if isinstance(raw.get("battleType"), str) else None,
        receiver_role=raw.get("receiverRole") if isinstance(raw.get("receiverRole"), str) else None,
        receiver_allegiance=(raw.get("receiverAllegiance")
                             if isinstance(raw.get("receiverAllegiance"), str) else None),
    )


def _build_specialization(
    raw: dict[str, Any], source_path: str
) -> HeroSpecializationRecord | None:
    """Map one source spec dict to :class:`HeroSpecializationRecord`.
    Returns ``None`` for entries missing the required ``id``."""
    spec_id = raw.get("id")
    if not isinstance(spec_id, str):
        return None
    bonuses: list[Bonus] = []
    for i, b in enumerate(raw.get("bonuses") or ()):
        if isinstance(b, dict):
            bonus = build_bonus(b, parent_type="hero_specialization",
                                parent_id=spec_id, ordinal=i)
            if bonus is not None:
                bonuses.append(bonus)
    return HeroSpecializationRecord(
        id=spec_id,
        name_sid=str(raw.get("name", "")),
        desc_sid=str(raw.get("desc", "")),
        icon=str(raw.get("icon", "")),
        bonuses=tuple(bonuses),
        source_path=source_path,
        raw_json=raw,
    )


def extract_hero_specializations(paths: CorePaths) -> HeroSpecializationExtractionResult:
    """Walk ``DB/heroes_specializations/*.json`` and return all
    HeroSpecializationRecord entries (faction + campaign + tutorial +
    test). See D-028.
    """
    out: list[HeroSpecializationRecord] = []
    for p in sorted((paths.db / "heroes_specializations").glob("*.json")):
        rel = p.relative_to(paths.core_root).as_posix()
        doc = load_json(p)
        for raw in iter_array(doc):
            if not isinstance(raw, dict):
                continue
            spec = _build_specialization(raw, source_path=rel)
            if spec is not None:
                out.append(spec)
    out.sort(key=lambda s: s.id)
    return HeroSpecializationExtractionResult(specializations=tuple(out))


# -----------------------------------------------------------------------------
# Hero sub-classes (prestige classes)
# -----------------------------------------------------------------------------


def _activation_at(conditions: list[Any], idx: int) -> tuple[str, int]:
    """Read the (skill_sid, skill_level) pair at position ``idx`` from
    the source ``activationConditions`` array. Returns empty/zero if
    the slot is missing — every sub-class in the 2026-05-03 corpus has
    exactly 5, so this fallback is just defensive."""
    if 0 <= idx < len(conditions):
        c = conditions[idx]
        if isinstance(c, dict):
            sid = c.get("skillSid")
            level = c.get("skillLevel")
            return (
                sid if isinstance(sid, str) else "",
                int(level) if isinstance(level, (int, float)) else 0,
            )
    return ("", 0)


def _build_sub_class(
    raw: dict[str, Any], source_path: str
) -> HeroSubClassRecord | None:
    sub_id = raw.get("id")
    if not isinstance(sub_id, str):
        return None
    conditions = raw.get("activationConditions") or []
    bonuses: list[Bonus] = []
    for i, b in enumerate(raw.get("bonuses") or ()):
        if isinstance(b, dict):
            bonus = build_bonus(b, parent_type="hero_sub_class",
                                parent_id=sub_id, ordinal=i)
            if bonus is not None:
                bonuses.append(bonus)
    a1 = _activation_at(conditions, 0)
    a2 = _activation_at(conditions, 1)
    a3 = _activation_at(conditions, 2)
    a4 = _activation_at(conditions, 3)
    a5 = _activation_at(conditions, 4)
    return HeroSubClassRecord(
        id=sub_id,
        name_sid=str(raw.get("name", "")),
        desc_sid=str(raw.get("desc", "")),
        icon=str(raw.get("icon", "")),
        faction=str(raw.get("faction", "")),
        class_type=str(raw.get("classType", "")),
        activation_skill_1_sid=a1[0],
        activation_skill_1_level=a1[1],
        activation_skill_2_sid=a2[0],
        activation_skill_2_level=a2[1],
        activation_skill_3_sid=a3[0],
        activation_skill_3_level=a3[1],
        activation_skill_4_sid=a4[0],
        activation_skill_4_level=a4[1],
        activation_skill_5_sid=a5[0],
        activation_skill_5_level=a5[1],
        bonuses=tuple(bonuses),
        source_path=source_path,
    )


def extract_hero_sub_classes(paths: CorePaths) -> HeroSubClassExtractionResult:
    """Walk ``DB/heroes_sub_classes/sub_classes_<faction>.json``. 24
    sub-classes total (4 per faction × 6). See D-029."""
    out: list[HeroSubClassRecord] = []
    for p in sorted((paths.db / "heroes_sub_classes").glob("*.json")):
        rel = p.relative_to(paths.core_root).as_posix()
        doc = load_json(p)
        for raw in iter_array(doc):
            if not isinstance(raw, dict):
                continue
            sub = _build_sub_class(raw, source_path=rel)
            if sub is not None:
                out.append(sub)
    out.sort(key=lambda s: s.id)
    return HeroSubClassExtractionResult(sub_classes=tuple(out))
