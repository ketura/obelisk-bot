# LawTreePosition

One row per law placement in a faction's law screen. Production laws (~198) each get exactly one row; test laws get none (they don't appear in any faction's `fractionLawsLines`).

Captures the *display* layout of the law tree as shown in-game: which side (Faction column / Army column), which slot within that side, and which tier row. The balance-relevant `tier` is duplicated here from `Law.tier` for convenience — `LawTreePosition` is the table to query when reconstructing the screen layout, while `Law.tier` is the table to query when asking "where in the balance-tree does this law live."

## Page layout

`LawTreePosition` rows are emitted inline on the parent `Faction` page (no separate `Data:LawTreePosition/…` pages):

```
{{LawTreePosition | faction=human | tier=1 | side=faction | slot=0 | law_id=fraction_law_human_3}}
{{LawTreePosition | faction=human | tier=1 | side=faction | slot=1 | law_id=fraction_law_human_2}}
…
```

## Schema

```mediawiki
{{#cargo_declare:_table=LawTreePosition
| faction = String           <!-- human, demon, dungeon, nature, undead, unfrozen -->
| tier = Integer             <!-- 1-5 -->
| side = String              <!-- faction | army -->
| slot = Integer             <!-- 0-based position within (faction, tier, side) -->
| law_id = String
}}
```

## Field notes

- **Primary key is `(faction, tier, side, slot)`**, which is also unique on `law_id` (each law occupies exactly one tree position).
- **`side`** is derived from the source `groups[]` index: `groups[0]` → `"faction"`, `groups[1]` → `"army"`. Mirrors the in-game screen labels (left = "Faction", right = "Army").
- **`slot`** is the law's index within its `groups[k].laws[]` array (0-based). Laws per side range from 2 to 4.
- **`tier`** is the row index of `fractionLawsLines[]` (1-based on emit, 0-based in source).

## Related tables

- [`Law`](Law.md) — joined on `law_id = Law.id` (1:1 for placed laws).
- [`FactionLawTier`](FactionLawTier.md) — joined on `(faction, tier)` for the unlock threshold at this row.
- [`Faction`](Faction.md) — joined on `faction = Faction.id`.
