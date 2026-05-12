"""Golden Goose Egg loot-table renderer.

The Golden Goose Egg is a unique artifact you can keep upgrading
with alchemical dust as long as you have any. Each upgrade rolls
the table in ``DB/reward_golden_egg.json`` for a possible reward
(with ``baseRewardChance`` controlling the chance the roll
succeeds at all). The reward set covers gold, dust, ore, units,
hero stats, hero XP, and bonus spells from any one of the four
schools.

Five reward types appear:

* ``SideResReward``  ``[resource_id, amount]`` — a stack of one
  resource (gold/dust/wood/ore/crystals/mercury/gemstones; rarely
  graal).
* ``HeroExpReward``  ``[amount]`` — straight hero XP.
* ``HeroUnitsReward`` ``[unit_sid, count]`` — a stack of units
  joins the hero.
* ``HeroMagicMassAdditionReward`` ``[school, level, rank]`` — adds
  a random spell from a school. ``any`` is a wildcard.
* ``HeroStatsReward``  pairs of ``[stat, amount]`` — uniformly
  distributes ``+N`` across all four primary stats.

In the 2026-05-05 file every entry has exactly one reward, so the
table renders one reward per row.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from obelisk.models.localization import LocalizationCorpus


# Resource id → human-readable name. Lower-case source ids; title-case
# wiki output. Includes the rare-end entries (graal).
_RESOURCE_DISPLAY: dict[str, str] = {
    "gold": "Gold",
    "wood": "Wood",
    "ore": "Ore",
    "crystals": "Crystals",
    "mercury": "Mercury",
    "gemstones": "Gemstones",
    "dust": "Alchemical Dust",
    "graal": "Grail",
}

# Stat keys observed on HeroStatsReward → in-game UI label. Stat names
# follow the HoMM tradition (Knowledge/Spell Power/Attack/Defense).
_STAT_DISPLAY: dict[str, str] = {
    "offence": "Attack",
    "defence": "Defense",
    "spellPower": "Spell Power",
    "intelligence": "Knowledge",
    "luck": "Luck",
    "morale": "Morale",
    "mana": "Mana",
    "movePoints": "Movement Points",
}

# Magic-school keys observed on HeroMagicMassAdditionReward → display.
_SCHOOL_DISPLAY: dict[str, str] = {
    "day": "Day",
    "night": "Night",
    "space": "Space",
    "primal": "Primal",
    "any": "any",
}


def _format_int(n: int) -> str:
    """Thousands-separator integer."""
    return f"{n:,}"


def _resolve_unit_name(
    unit_sid: str, corpus: LocalizationCorpus,
) -> str:
    """Look up the unit's English display name. Unit name SIDs follow
    the ``<unit_id>_name`` convention. Falls back to a title-cased id."""
    text = corpus.get(f"{unit_sid}_name", "english")
    if text:
        return text
    # Fallback: turn snake_case into Title Case.
    return unit_sid.replace("_", " ").title()


def _pluralize(name: str, count: int) -> str:
    """Naive English plural — append 's' when count != 1 unless the
    name already ends in s/z/x. Olden Era unit names are English-style;
    this is good enough."""
    if count == 1:
        return name
    if name.endswith(("s", "x", "z")):
        return name
    return name + "s"


def _format_resource(parameters: list[str]) -> str:
    """``[resource_id, amount]`` → ``"5,000 Gold"``."""
    if len(parameters) < 2:
        return "?"
    res_id = parameters[0]
    try:
        amount = int(parameters[1])
    except (TypeError, ValueError):
        return f"{parameters[1]} {_RESOURCE_DISPLAY.get(res_id, res_id.title())}"
    name = _RESOURCE_DISPLAY.get(res_id, res_id.title())
    return f"{_format_int(amount)} {name}"


def _format_exp(parameters: list[str]) -> str:
    """``[amount]`` → ``"5,000 hero XP"``."""
    if not parameters:
        return "?"
    try:
        return f"{_format_int(int(parameters[0]))} hero XP"
    except (TypeError, ValueError):
        return f"{parameters[0]} hero XP"


def _format_units(parameters: list[str], corpus: LocalizationCorpus) -> str:
    """``[unit_sid, count]`` → ``"3 Sentinels"``."""
    if len(parameters) < 2:
        return "?"
    unit_sid = parameters[0]
    try:
        count = int(parameters[1])
    except (TypeError, ValueError):
        count = 0
    name = _resolve_unit_name(unit_sid, corpus)
    plural = _pluralize(name, count)
    if count:
        return f"{count} {plural}"
    return plural


def _format_magic(parameters: list[str]) -> str:
    """``[school, level, rank]`` → human description.

    All three fields can be ``"any"`` (wildcard). The 2026-05-05 file
    only ever uses ``[school, "any", "any"]`` patterns, but the
    renderer handles arbitrary combinations defensively."""
    if len(parameters) < 3:
        return "Random spell"
    school, level, rank = parameters[0], parameters[1], parameters[2]
    school_disp = _SCHOOL_DISPLAY.get(school, school.title())
    bits: list[str] = []
    if school != "any":
        bits.append(f"{school_disp} school")
    if level != "any":
        bits.append(f"level {level}")
    if rank != "any":
        bits.append(f"rank {rank}")
    if not bits:
        return "Random spell (any school)"
    return "Random " + ", ".join(bits) + " spell"


def _format_stats(parameters: list[str]) -> str:
    """``[stat1, amount1, stat2, amount2, ...]`` → uniform-or-listed.

    When every stat in the list shares the same amount, render
    ``+N to all primary stats`` (compact). Otherwise list each
    ``+N <Stat>`` separately."""
    pairs: list[tuple[str, str]] = []
    it = iter(parameters)
    for stat in it:
        try:
            amount = next(it)
        except StopIteration:
            break
        pairs.append((stat, amount))
    if not pairs:
        return "?"
    amounts = {a for _s, a in pairs}
    if len(amounts) == 1:
        amount = pairs[0][1]
        # Detect "all four primary stats": offence + defence + spellPower + intelligence
        primary = {"offence", "defence", "spellPower", "intelligence"}
        listed = {s for s, _ in pairs}
        if primary.issubset(listed) and listed.issubset(primary):
            return f"+{amount} to all primary stats"
        # Otherwise list the stats with the shared amount.
        labels = ", ".join(_STAT_DISPLAY.get(s, s.title()) for s, _ in pairs)
        return f"+{amount} to {labels}"
    # Heterogeneous amounts.
    return ", ".join(
        f"+{a} {_STAT_DISPLAY.get(s, s.title())}" for s, a in pairs
    )


def _format_reward(reward: dict[str, Any], corpus: LocalizationCorpus) -> str:
    rtype = reward.get("rewardType")
    params = reward.get("parameters") or []
    if not isinstance(params, list):
        params = []
    if rtype == "SideResReward":
        return _format_resource(params)
    if rtype == "HeroExpReward":
        return _format_exp(params)
    if rtype == "HeroUnitsReward":
        return _format_units(params, corpus)
    if rtype == "HeroMagicMassAdditionReward":
        return _format_magic(params)
    if rtype == "HeroStatsReward":
        return _format_stats(params)
    return f"({rtype} {params})"


def _format_entry(entry: dict[str, Any], corpus: LocalizationCorpus) -> str:
    """Combine multi-reward entries into one cell. The 2026-05-05 file
    has no multi-reward entries, but the format supports it."""
    rewards = entry.get("rewardSet", {}).get("rewards", [])
    parts = [_format_reward(r, corpus) for r in rewards if isinstance(r, dict)]
    return " + ".join(parts) if parts else "(empty reward set)"


def render_golden_egg_table(
    egg_doc: dict[str, Any],
    corpus: LocalizationCorpus,
) -> str:
    """Render the loot table as a sortable wikitable.

    Columns: Weight (raw roolChance) / Rate (weight ÷ total, as a
    percentage to two significant places) / Reward (human-readable).
    Weight and Rate fixed at 10% each; Reward takes the remainder."""
    arr = egg_doc.get("array") or []
    if not isinstance(arr, list):
        arr = []
    total_weight = 0
    for e in arr:
        try:
            total_weight += int(e.get("roolChance", 0))
        except (TypeError, ValueError):
            pass

    base_chance = egg_doc.get("baseRewardChance")
    addition_chance = egg_doc.get("additonRewardChance")

    out: list[str] = []
    out.append("= Golden Goose Egg Loot Table =")
    out.append("")
    out.append(
        "Each upgrade of the Golden Goose Egg rolls this table for a "
        "possible reward. ``baseRewardChance`` is the chance any roll "
        "succeeds; ``additonRewardChance`` raises that chance with each "
        "successive failed roll. Weights are raw ``roolChance`` values; "
        "rates are weights as a fraction of the total weight pool."
    )
    out.append("")
    if base_chance is not None or addition_chance is not None or total_weight:
        meta_bits = []
        if base_chance is not None:
            meta_bits.append(
                f"; Base reward chance: {float(base_chance) * 100:.0f}%"
            )
        if addition_chance is not None:
            meta_bits.append(
                f"; Failure-bump chance: +{float(addition_chance) * 100:.0f}% "
                f"per failed roll"
            )
        meta_bits.append(f"; Total weight pool: {_format_int(total_weight)}")
        out.extend(meta_bits)
        out.append("")

    out.append('{| class="wikitable sortable"')
    out.append('! style="width: 10%" | Weight')
    out.append('! style="width: 10%" | Rate')
    out.append('! Reward')
    for entry in arr:
        if not isinstance(entry, dict):
            continue
        try:
            weight = int(entry.get("roolChance", 0))
        except (TypeError, ValueError):
            weight = 0
        rate = (weight / total_weight * 100) if total_weight else 0
        reward_text = _format_entry(entry, corpus)
        out.append("|-")
        out.append(
            f"| {weight} || {rate:.2f}% || {reward_text}"
        )
    out.append("|}")
    return "\n".join(out) + "\n"


def load_golden_egg(path: Path) -> dict[str, Any]:
    """Load + parse the source JSON. Handles the BOM that the file
    sometimes ships with."""
    with path.open(encoding="utf-8-sig") as fh:
        return json.load(fh)
