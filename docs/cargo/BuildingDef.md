# BuildingDef

One row per (faction, building, level) — **206 rows** in the 2026-05-05 corpus across 6 factions and 18 building categories. The source's `parametersPerLevel` array is *flattened* on extract: a 3-level building like Build_Main produces 3 separate Building rows (`<faction>_Build_Main_L1`, `_L2`, `_L3`).

A building's per-level *passive bonuses* (`bonusesPerLevel`), *optional effects* (`optionalEffectsPerLevel`), magic-guild *spell roll chances* (`rollChances`), and most other category-specific extras are **deliberately not extracted** in this pass — they'd need their own decision/table and the value-to-effort ratio is currently low. Creature-dwelling unit data (`unitsHire`) IS pulled in, simplified to a single base-unit SID + weekly increment.

## Page layout

`Data:Building/<id>` carries:

1. `{{BuildingDef | id=<faction>_<sid>_L<level> | faction=… | sid=… | level=… | name=… | desc=… | …}}`
2. `{{TranslationDef | type=building | target_id=<id> | <lang>_name=… | <lang>_desc=… | …}}`

No side rows — all per-level data flattens onto the Building row itself; multi-resource costs spread across fixed `<resource>_cost` columns; prerequisite list goes into a `List` column queryable via Cargo's `HOLDS` operator.

## Schema

```mediawiki
{{#cargo_declare:_table=BuildingDef
| id = String                   <!-- synthesized: <faction>_<sid>_L<level> -->
| faction = String              <!-- human, demon, dungeon, nature, undead, unfrozen -->
| category = String             <!-- mains, walls, hires, magicGuilds, banks, taverns, markets, graals, etc. -->
| sid = String                  <!-- source-side sid, e.g. Build_Main, Build_Wall, Build_Tier_1 -->
| level = Integer               <!-- 1-based; 1..max_level for this building -->

<!-- Identity / display -->
| name = String
| name_sid = String
| desc = Wikitext
| desc_sid = String
| narrative_desc = Wikitext
| narrative_desc_sid = String
| icon = String
| background_image = String

<!-- Construction state (sparse — only meaningful at level 1; repeated per level for query convenience) -->
| is_constructed_on_start = Boolean
| level_on_start = Integer
| scene_slot = String

<!-- City-screen grid position for this level -->
| node_pos_x = Integer
| node_pos_y = Integer

<!-- Prereqs: List of <sid>_L<level> strings — query with HOLDS -->
| prereqs = List (,) of String

<!-- Costs: one fixed column per source resource, NULL when not required at this level -->
| gold_cost = Integer
| wood_cost = Integer
| ore_cost = Integer
| crystals_cost = Integer
| gemstones_cost = Integer
| mercury_cost = Integer
| dust_cost = Integer
| graal_cost = Integer

<!-- Creature-dwelling fields (only populated when category='hires') -->
| units_hire_sid = String       <!-- base unit SID; the upg / upg_alt variants live on Unit/UnitUpgrade joins -->
| units_weekly = Integer        <!-- weekly increment at this level -->

| source_path = String
}}
```

## Field notes

- **Primary key is `id`**, synthesized as `<faction>_<sid>_L<level>` (e.g. `human_Build_Main_L1`). Building SIDs are unique within a faction but reused across factions (every faction has `Build_Main`), so the faction prefix is needed for global uniqueness.
- **`category`** is the source group key the building came from (one of: `mains`, `walls`, `magicGuilds`, `taverns`, `markets`, `graals`, `banks`, `hires`, `artifactMarkets`, `heroBonusBanks`, `intelligences`, `manaFountains`, `myceliumRoots`, `portalSummonings`, `rebirthShrines`, `trainingRanges`, `unitsConverters`, `artifactChangers`). The single-instance specials (intelligences, manaFountains, etc.) are faction-unique buildings — `category` lets the wiki style/group them.
- **`level`** is 1-based; query `WHERE sid=<x> AND level=<n>` to pull a specific tier of a building, or `WHERE sid=<x>` for all tiers in numeric order.
- **`name` / `desc`** carry English defaults inline; per-language values live on the matching `{{TranslationDef | type=building}}` row.
- **`prereqs`** is a Cargo `List` of `<sid>_L<level>` strings (e.g. `Build_Main_L1,Build_Tier_2_L1`). Empty list when no prereq. Query "what unlocks at Build_Main level 2" via `WHERE prereqs HOLDS 'Build_Main_L2'`.
- **`<resource>_cost`** columns are sparse — each is NULL unless the source's `costs` array includes that resource for this level. Eight columns total (`gold/wood/ore/crystals/gemstones/mercury/dust/graal`). One pre-set column per resource keeps queries scalar-clean ("WHERE gold_cost > 5000").
- **`units_hire_sid`** is the *base* unit SID from `unitsHire.units[0].sids[0]`. The upg / upg_alt variants are reachable via `Unit.upgrade_of` / equivalent join on the Unit table — no need to denormalize them onto Building.
- **`units_weekly`** is `unitsHire.units[0].weeklyIncrement`. The dwellings in 2026-05-05 only ever ship a single units-group entry per building, so we collapse it.

## Deliberately not extracted

- **`bonusesPerLevel`** — per-level passive bonuses on the building (e.g. mains' `+500 gold daily`). The data exists in source but isn't currently emitted; would extend the unified `BonusDef` table with `parent_type='building_level'` if added later. Out of scope for this pass.
- **`optionalEffectsPerLevel`** — the choose-one effects you pick when upgrading certain buildings (e.g. mains level 2 offers gold/law/astrology). Same story — would need its own side table.
- **`rollChances`** on magic guilds — the per-spell offering weights. ~60 entries per guild, would explode into a `BuildingGuildSpell(building_id, spell_sid, chance)` side table; deferred.
- **Wall `bonuses`, market `extraChargePurchase` / `extraChargeSell` / `numberPurchases` / `resArr`, training `trainingStats`, unitsConverter `conversionPairs`, artifactMarket `artifacts` / `itemsCountPerRarity` / `levelStep` / `numberPurchases`, graal `graalType`** — category-specific data the player rarely queries from a wiki perspective. All deferred.
- **`buildOrders`** — 60 build-order presets used by AI / random map generation, not player-facing buildings. Not extracted (per project decision; noted for hypothetical future work as `BuildingPreset`).

## Related tables

- [`FactionDef`](FactionDef.md) — joined on `faction = Faction.id`.
- [`TranslationDef`](shared/Translation.md) — one row per Building with `type='building'`, `target_id=id`, carrying name + desc in 16 languages.
- [`UnitDef`](UnitDef.md) — for `category='hires'` rows, `units_hire_sid` joins to `Unit.id` (the base unit; upgrade variants chain via Unit's own self-joins).
- [`BuildingDef`](BuildingDef.md) (self) — `prereqs HOLDS '<sid>_L<level>'` finds buildings unlocked by a given prereq tier.
