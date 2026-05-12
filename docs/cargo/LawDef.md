# LawDef

One row per faction law (~198 production laws + 34 test laws across the 2026-05-05 corpus). Each law is a passive faction-wide effect that the player can enact during the Astrology phase by spending law points; effects scale through 1-3 mastery levels, each level costing a separate budget of points.

A law carries identity (name, desc, icon), faction membership, balance-relevant tier placement, a count of how many levels it has, and the source file it came from. Per-level data (cost, description, bonuses) lives on the [`LawLevelDef`](LawLevelDef.md) side table. Display-tree placement (which column / slot it sits in on the in-game law screen) lives on [`LawTreePositionDef`](LawTreePositionDef.md).

## Page layout

`Data:Law/<id>` carries:

1. `{{LawDef | id=… | faction=… | tier=… | name=… | desc_sid=… | icon=… | …}}`
2. `{{TranslationDef | type=law | target_id=<id> | …}}` — name only (one shared name across all levels)
3. N × `{{LawLevelDef | law_id=<id> | level=N | cost=… | description=… }}`
4. N × `{{LawLevelTranslationDef | law_id=<id> | level=N | <lang>_desc=… }}`
5. M × `{{BonusDef | parent_type=law_level | parent_id=<id>_L<level> | ordinal=… | type=… | …}}` — one per `bonuses[]` entry, summed across all levels

## Schema

```mediawiki
{{#cargo_declare:_table=LawDef
| id = String
| faction = String              <!-- human, demon, dungeon, nature, undead, unfrozen; null for test laws -->
| ordinal = Integer             <!-- the trailing N parsed from id -->
| tier = Integer                <!-- 1-5; the balance-relevant tree row; null for test laws -->
| name = String
| name_sid = String
| desc_sid = String             <!-- shared SID; placeholders substitute per level -->
| icon = String
| max_level = Integer           <!-- 1-3, == count(LawLevel rows) -->
| test = Boolean                <!-- true for fractions_laws_test*.json entries -->
| source_path = String
}}
```

## Field notes

- **`id`** is the source JSON id (e.g. `fraction_law_human_1`, `test_fraction_law_1`, `test_new_fraction_law_1`).
- **`faction`** is the in-game faction the law belongs to. NULL for test/dev laws that have no faction tree placement.
- **`tier`** (1-5) is the row of the law tree where this law lives in its faction. Stored on `LawDef` because moving a law from tier 2 → tier 3 is a balance change, not a layout change. NULL for test laws.
- **`name_sid` / `desc_sid`** point at the L10n entries (e.g. `fraction_law_human_1_name`, `fraction_law_human_1_desc`).
- **`name`** carries the resolved English name. Names are shared across all levels of a law.
- **`desc_sid`** is *also* shared across all levels — the same template ("Produces {0} Gold daily.") gets substituted with different per-level numbers. Per-level resolved English text lives on the `LawLevel.description` column. Foreign-language per-level descriptions live on `LawLevelTranslationDef`.
- **`max_level`** equals the length of the source `parametersPerLevel` array.
- **`test`** is true for laws sourced from `fractions_laws_test.json` or `fractions_laws_test_new.json`. Most queries should `WHERE test = false`.

## Related tables

- [`LawLevelDef`](LawLevelDef.md) — joined on `id = law_id` (1:N where N=1..3).
- [`LawTreePositionDef`](LawTreePositionDef.md) — joined on `id = law_id` (1:1 for production laws, 0:1 for test laws).
- [`FactionLawTierDef`](FactionLawTierDef.md) — sibling table; one row per (faction, tier) carrying `count_to_unlock` law-points threshold.
- [`BonusDef`](shared/Bonus.md) — joined on `parent_type='law_level' AND parent_id LIKE id || '_L%'`.
- [`TranslationDef`](shared/Translation.md) — one row per law with `type=law`, `target_id=id`, carrying the name in 16 languages.
- [`FactionDef`](FactionDef.md) — joined on `faction = Faction.id`.
