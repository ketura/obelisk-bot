# MapObjectDef

One row per adventure-map structure pulled from `DB/objects_logic/` —
**roughly 150 rows** in the 2026-05-05 corpus across ~22 categories
(resource piles, mines, dwellings, banks, chests, taverns, markets,
portals, shrines, uniques, etc.).

Per D-035: the source data is heterogeneous (chests carry `variants`
loot tables, hires carry `unitsData` + `bonuses`, mines carry
`resArr`, etc.) but most of that variance is deferred. This pass
captures the universal fields players care about — name, description,
icon, basic combat / economy stats — plus a `source_path` pointer
so editors can dig into the raw JSON for specifics the wiki doesn't
yet surface.

Battlefield-side objects (`DB/field_objects/obstacles`, `sentries`,
`traps`) are out of scope for this table; they'll get their own
treatment.

## Page layout

`Data:MapObject/<id>` carries:

1. `{{MapObjectDef | id=… | category=… | name=… | desc=… | …}}`
2. `{{TranslationDef | type=map_object | target_id=<id> | <lang>_name=… | <lang>_desc=… | …}}`

## Schema

```mediawiki
{{#cargo_declare:_table=MapObjectDef
| id = String
| category = String              <!-- res, res_mines, magic_mines, hires, chests, event_banks, taverns, markets, item_markets, res_trade_labs, unit_res_trade_labs, outposts, garrisons, portals, sacrificial_shrine, fickle_shrines, mirages, insaras_eye, eternal_dragon, pocket_dimensions, chimerologist, prisons -->

<!-- Identity / display -->
| name = String
| name_sid = String
| desc = Wikitext
| desc_sid = String
| narrative_desc = Wikitext
| narrative_desc_sid = String

<!-- Core scalars (sparse — only populated when present in source) -->
| goods_value = Integer
| ai_value = Integer
| custom_guard_value = Integer
| view_radius = Integer
| ai_ignore = Boolean

<!-- Combat: who guards this object. List of "<unit_sid>:<amount>" pairs -->
| guard_units = List (,) of String

<!-- Category-specific scalars (sparse) -->
| fraction = String              <!-- hires faction membership: human, demon, ... -->
| tier = Integer                 <!-- hires tier (1-7) -->
| resource_name = String         <!-- res_mines / res producing-resource -->
| resource_value = Integer       <!-- res_mines daily production amount -->

| source_path = String           <!-- e.g. DB/objects_logic/res_mines/mines.json -->
}}
```

## Field notes

- **`id`** is the source JSON id (e.g. `mine_gold`, `barracks_human_3`, `celestial_sphere`, `tavern`, `portal_1`). No synthesis — the source ids are already globally unique.
- **`category`** is the source folder name under `DB/objects_logic/`. Used for filtering (e.g. "all dwellings" → `WHERE category = 'hires'`).
- **`name_sid` / `desc_sid` / `narrative_desc_sid`** follow the convention `<id>_name` / `<id>_description` / `<id>_narrativeDescription` against `Lang/<locale>/texts/mapObjects.json`. ~94 of the ~150 rows have player-facing names; the rest (e.g. `tavern`, `outposts`, single-instance specials) get NULL name fields and rely on category for identification.
- **`goods_value`** is the in-source AI/economy weight (the "value" of taking this object). Universal — present on virtually every entry.
- **`ai_value`** / **`custom_guard_value`** appear on chests, hires, mines, resources — used by AI threat assessment.
- **`guard_units`** is the comma-joined list of `<sid>:<amount>` pairs (e.g. `esquire:2,crossbowman:2`). NULL when source has empty `guardUnits`.
- **`fraction` / `tier`** populated only for `category='hires'` (creature dwellings on the adventure map — *not* the city `Build_Tier_*` dwellings, which live on the Building table).
- **`resource_name` / `resource_value`** populated only for `category='res_mines'` (daily producers like `mine_gold`) and selected `res` rows. The richer `resArr` chance-table for resource-pile randomization (used in `category='res'`) is *not* extracted in this pass — the source path is on the row for editors who need it.

## Categories deliberately not extracted

- **`cities/`** — already modeled in the [`BuildingDef`](BuildingDef.md) table.
- **`items/`** — these are placement metadata for artifacts on the map; the canonical Artifact data is in the [`ArtifactDef`](ArtifactDef.md) table.
- **`blocks/`, `todo/`** — terrain blockers and dev TODOs, not player-facing.
- **`random_hires/`, `unit_upgrades/`, `town_gates/`, `win_condition_objects/`** — generation/AI helpers and campaign-specific mechanics.

## Deliberately not extracted (within in-scope categories)

The rich category-specific payloads — chest `variants` loot tables,
event-bank reward sets, hire `unitsData` weekly/bonus blocks, mine
`bonuses` arrays, magic-mine `bonuses`, market trade rates, etc. —
are out of scope for this pass. They'd each warrant their own side
table (`MapObjectChestVariant`, `MapObjectEventBankReward`,
`MapObjectDwellingUnit`, etc.) following the Building pattern.

The `source_path` column on every row points editors at the source
JSON file for those specifics until structured wiki coverage
catches up.

## Related tables

- [`TranslationDef`](shared/Translation.md) — one row per MapObject with `type='map_object'`, `target_id=id`.
- [`BuildingDef`](BuildingDef.md) — sibling table covering city-buildings (`DB/objects_logic/cities/`).
- [`ArtifactDef`](ArtifactDef.md) — canonical artifact data; map placements in `DB/objects_logic/items/` reference these by id.
- [`UnitDef`](UnitDef.md) — `guard_units` entries reference Unit ids.
