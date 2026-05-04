"""Curated map: JSON pattern_sid -> shared AttackPassive id (D-021)."""

from __future__ import annotations


# Shared AttackPassive registry — one row per (pattern_token, rank) combo.
ATTACK_PASSIVES: dict[str, dict[str, object]] = {
    "sweeping_strike": {
        "pattern_token": "swipe", "rank": 1,
        "canonical_pattern_sid": "attack_swipe_x100_x100",
        "name_sid": "base_passive_strike_swipe_1_name",
        "desc_sid": "base_passive_strike_swipe_1_description",
        "display_name": "Sweeping Strike",
    },
    "sweeping_strike_falloff": {
        "pattern_token": "swipe", "rank": 2,
        "canonical_pattern_sid": "",
        "name_sid": "base_passive_strike_swipe_2_name",
        "desc_sid": "base_passive_strike_swipe_2_description",
        "display_name": "Sweeping Strike",
    },
    "whirlwind_strike": {
        "pattern_token": "swirl", "rank": 1,
        "canonical_pattern_sid": "attack_swirl_with_target_x100",
        "name_sid": "base_passive_strike_swirl_1_name",
        "desc_sid": "base_passive_strike_swirl_1_description",
        "display_name": "Whirlwind Strike",
    },
    "whirlwind_strike_falloff": {
        "pattern_token": "swirl", "rank": 2,
        "canonical_pattern_sid": "attack_swirl_with_target_x50",
        "name_sid": "base_passive_strike_swirl_2_name",
        "desc_sid": "base_passive_strike_swirl_2_description",
        "display_name": "Whirlwind Strike",
    },
    "dragonbreath_strike": {
        "pattern_token": "reach", "rank": 1,
        "canonical_pattern_sid": "attack_reach_x1_x100_x100_with_delay",
        "name_sid": "base_passive_strike_reach_1_name",
        "desc_sid": "base_passive_strike_reach_1_description",
        "display_name": "Dragonbreath Strike",
    },
    "dragonbreath_strike_falloff": {
        "pattern_token": "reach", "rank": 2,
        "canonical_pattern_sid": "attack_reach_x2_x100_x100_x100_with_delay",
        "name_sid": "base_passive_strike_reach_2_name",
        "desc_sid": "base_passive_strike_reach_2_description",
        "display_name": "Dragonbreath Strike",
    },
    "area_strike": {
        "pattern_token": "rumble", "rank": 1,
        "canonical_pattern_sid": "attack_rumble_x1_x100",
        "name_sid": "base_passive_strike_rumble_1_name",
        "desc_sid": "base_passive_strike_rumble_1_description",
        "display_name": "Area Strike",
    },
    "area_strike_falloff": {
        "pattern_token": "rumble", "rank": 2,
        "canonical_pattern_sid": "attack_rumble_x1_x100_x50",
        "name_sid": "base_passive_strike_rumble_2_name",
        "desc_sid": "base_passive_strike_rumble_2_description",
        "display_name": "Area Strike",
    },
    "cone_strike": {
        "pattern_token": "tri_reach", "rank": 1,
        "canonical_pattern_sid": "attack_massive_x1_x100_x100_with_dalay",
        "name_sid": "base_passive_strike_tri_reach_1_name",
        "desc_sid": "base_passive_strike_tri_reach_1_description",
        "display_name": "Cone Strike",
    },
}


# pattern_sid -> attack_passive_id lookup.
PATTERN_PASSIVE_MAP: dict[str, str] = {
    "attack_single_x100": "",
    "attack_swipe_x100_x100": "sweeping_strike",
    "attack_swipe_x100_x100_x2": "cone_strike",
    "attack_swirl_with_target_x100": "whirlwind_strike",
    "attack_swirl_with_target_x50": "whirlwind_strike_falloff",
    "attack_swirl_x1_x100": "whirlwind_strike",
    "attack_swirl_x2_x100": "whirlwind_strike_falloff",
    "attack_reach_x1_x100_x100_with_delay": "dragonbreath_strike",
    "attack_reach_x1_x100_x100": "dragonbreath_strike",
    "attack_reach_x2_x100_x100_x100_with_delay": "dragonbreath_strike_falloff",
    "attack_rumble_x1_x100": "area_strike",
    "attack_rumble_x1_x100_x50": "area_strike_falloff",
    "attack_rumble_without_self_x1_x100_x100": "area_strike",
    "attack_rumble_without_self_x1_x100_x50": "area_strike_falloff",
    "attack_rumble_x2_x100": "area_strike",
    "attack_massive_x1_x100_x100_with_dalay": "cone_strike",
}


NON_ATTACK_PATTERNS: frozenset[str] = frozenset({"attack_single_buff"})


def _strip_unit_suffix(pattern_sid: str, unit_id: str) -> str:
    candidates = [unit_id]
    if unit_id.endswith("_upg_alt"):
        candidates.append(unit_id.removesuffix("_upg_alt"))
    elif unit_id.endswith("_upg"):
        candidates.append(unit_id.removesuffix("_upg"))
    for cand in sorted(candidates, key=len, reverse=True):
        suffix = "_" + cand
        if pattern_sid.endswith(suffix):
            return pattern_sid[: -len(suffix)]
    return pattern_sid


def lookup_attack_passive(
    *, pattern_sid: str | None, unit_id: str
) -> tuple[str | None, bool]:
    """Resolve a pattern_sid to an AttackPassive id.

    Returns (attack_passive_id, is_placeholder).
    """
    if not pattern_sid:
        return (None, False)
    if pattern_sid in NON_ATTACK_PATTERNS:
        return (None, False)
    canonical = _strip_unit_suffix(pattern_sid, unit_id)
    if canonical in PATTERN_PASSIVE_MAP:
        mapped = PATTERN_PASSIVE_MAP[canonical]
        if not mapped:
            return (None, False)
        return (mapped, False)
    return (f"pattern_passive_TODO_{pattern_sid}", True)


def canonical_pattern_sid_for(attack_passive_id: str) -> str | None:
    info = ATTACK_PASSIVES.get(attack_passive_id)
    if info is None:
        return None
    sid = info.get("canonical_pattern_sid")
    return sid if isinstance(sid, str) and sid else None
