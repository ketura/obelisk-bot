# FactionLawTier

One row per (faction, tier) pair — 30 rows total (6 factions × 5 tiers). Captures the law-points threshold a player must accumulate before any tier-N law in a given faction becomes enactable.

In the 2026-05-05 corpus all six factions ship identical thresholds (`[0, 5, 15, 30, 50]`). Stored per-faction so a future patch can rebalance one faction independently.

## Page layout

`FactionLawTier` rows are emitted inline on the parent `Faction` page alongside the `LawTreePosition` rows.

## Schema

```mediawiki
{{#cargo_declare:_table=FactionLawTier
| faction = String           <!-- human, demon, dungeon, nature, undead, unfrozen -->
| tier = Integer             <!-- 1-5 -->
| count_to_unlock = Integer  <!-- law points required to unlock laws in this tier -->
}}
```

## Field notes

- **Primary key is `(faction, tier)`**.
- **`count_to_unlock`** is sourced from `fractionLawsLines[tier-1].countToUnlock`.
- Tier 1 always has `count_to_unlock = 0` (no entry threshold); higher tiers progressively gate.

## Related tables

- [`LawTreePosition`](LawTreePosition.md) — joined on `(faction, tier)`.
- [`Faction`](Faction.md) — joined on `faction = Faction.id`.
