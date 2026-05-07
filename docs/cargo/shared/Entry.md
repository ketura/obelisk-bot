# Entry

A generic, hand-curated reference table for **named terms with no
extra structure**. Every row carries:

- a **type** + **subtype** primary key
- a player-facing **display_name** + **description** (English defaults)
- an optional **narrative_description** for flavor/lore text (D-036)
- the canonical L10n **name_sid** + **desc_sid** + optional
  **narrative_description_sid** the row was sourced from
- an optional **icon** filename
- a **source_path** pointer to the L10n file (or source JSON for
  per-patch extracts) the row came from (D-036)
- 15 × per-language **`<lang>_name`** + **`<lang>_desc`** columns

This table is the catch-all for any reference data that fits the
"name + description + i18n" shape and nothing else. As soon as an
entity needs *additional* columns (rank, pattern_token, cost,
prerequisites, etc.) it belongs in its own dedicated table.

Entry rows come from two sources:

1. **Hand-curated seeds** — small enums the wiki ships pre-populated
   (attack archetypes, movement types, creature types). These live in
   the `ENTRY_SEEDS` dict in `src/obelisk/emit/unit.py`.
2. **Per-patch extracted data** — name+i18n-only data harvested from
   the source JSON each patch (currently: faction city names from
   `DB/fractions/*.json`). The extractor module (`extract/faction.py`,
   etc.) hands the SID directly to `emit_entry_page`; no seed-dict
   detour.

In both cases the bot resolves each row's translations from the L10n
corpus on every extract, so per-patch text changes flow through.

## Schema

```mediawiki
{{#cargo_declare:_table=Entry
| type = String (allowed values=attack_archetype,movement,creature_type,FactionCityName,resource,hero_stat,unit_stat)
| subtype = String
| display_name = String
| description = Wikitext
| narrative_description = Wikitext
| icon = String
| name_sid = String
| desc_sid = String
| narrative_description_sid = String
| source_path = String

<!-- Per-language pairs. Each language gets a name + desc column. -->
| pt_br_name = String
| pt_br_desc = Wikitext
| cs_name = String
| cs_desc = Wikitext
| fr_name = String
| fr_desc = Wikitext
| de_name = String
| de_desc = Wikitext
| hu_name = String
| hu_desc = Wikitext
| it_name = String
| it_desc = Wikitext
| ja_name = String
| ja_desc = Wikitext
| ko_name = String
| ko_desc = Wikitext
| pl_name = String
| pl_desc = Wikitext
| ru_name = String
| ru_desc = Wikitext
| es_name = String
| es_desc = Wikitext
| tr_name = String
| tr_desc = Wikitext
| uk_name = String
| uk_desc = Wikitext
| zh_cn_name = String
| zh_cn_desc = Wikitext
| zh_tw_name = String
| zh_tw_desc = Wikitext
}}
```

## Field notes

- **Primary key is `(type, subtype)`** as a tuple. Joins from per-unit
  columns include the type discriminator: e.g.
  `Unit.attack_type` joins to `Entry.subtype WHERE Entry.type='attack_archetype'`.
- **`display_name` / `description`** carry the English defaults
  inline. Translations live in the per-language columns on the same
  row. (No separate translation table — D-024 collapsed the
  `<Entity>` / `<Entity>Translation` pair into one table per row.)
- **`icon`** is optional. Sparse-emit: if a seed has no icon
  configured, the field is omitted from the row.
- **`name_sid` / `desc_sid`** are surfaced for traceability — they
  point at the L10n entries the row was sourced from. Useful for
  "find which game string drives this label" queries.

## Page layout

Each Entry `type` gets its own top-level wiki namespace and on-disk
directory — the `Entry` Cargo table name only surfaces in the table
schema and the `{{Entry | …}}` template invocations *inside* each
page. The `Entry` abstraction is internal; user-facing wiki paths use
the per-domain names that already exist as game concepts.

- **On wiki:** `Data:<PascalType>/<subtype>` (e.g. `Data:Movement/fly`).
- **On disk:** `data/<type>/<subtype>.wiki.txt` (e.g. `data/movement/fly.wiki.txt`).

Examples:

| Type | On disk | On wiki |
| --- | --- | --- |
| `attack_archetype` | `data/attack_archetype/melee.wiki.txt` | `Data:AttackArchetype/melee` |
| `movement` | `data/movement/fly.wiki.txt` | `Data:Movement/fly` |
| `creature_type` | `data/creature_type/demon.wiki.txt` | `Data:CreatureType/demon` (Hive Spawn) |
| `FactionCityName` | (inline on `data/factions/<id>.wiki.txt`) | (inline on `Data:Faction/<id>`) |

The directory→wiki-namespace mapping lives in `_DIR_TO_WIKI_TABLE`
(`src/obelisk/diff/wiki_diff.py`) — extend it when adding a new
Entry type.

## Initial canonical content

These three types ship in the initial Entry rollout. Each row's
`display_name` and `description` come from the L10n corpus via
`name_sid` / `desc_sid` on every extract; the table below summarizes.

### `type=attack_archetype` (3 rows)

| `subtype` | `display_name` | `name_sid` |
| --- | --- | --- |
| `melee` | Melee Attack | `base_passive_melee_attack_name` |
| `ranged` | Ranged Attack | `base_passive_ranged_attack_name` |
| `reach` | Long Reach | `base_passive_remote_attack_name` |

JSON enum mapping (in `extract/unit.py`): `melee → melee`,
`shoot → ranged`, `range → reach`. Naming flip on `range`→`reach`.

### `type=movement` (2 rows)

| `subtype` | `display_name` | `name_sid` |
| --- | --- | --- |
| `fly` | Flying | `base_passive_flyer_name` |
| `teleport` | Blink | `base_passive_blink_name` |

Naming flip on `teleport` enum → "Blink" display. Walkers are encoded
as the absence of `Unit.move_type` — no Entry row.

### `type=creature_type` (7 rows)

| `subtype` | `display_name` | `name_sid` |
| --- | --- | --- |
| `living` | Living | `base_class_living` |
| `undead` | Undead | `base_class_undead` |
| `demon` | Hive Spawn | `base_class_demon` |
| `magic_creature` | Magic Creature | `base_class_magic_creature` |
| `embodiment` | Embodiment | `base_class_embodiment` |
| `dragon` | Dragon | `base_class_dragon` |
| `construct` | Construct | `base_class_construct` |

Naming flip on `demon` enum → "Hive Spawn" display. Description text
contains placeholders that are pre-substituted at extract time via
`Lang/args/unitsAbility.json` + `units.script` (class-wide morale and
luck range bounds).

### `type=FactionCityName` (120 rows; per-patch extracted)

Six factions × 20 names each. Subtype is `<faction>_<index>` (e.g.
`dungeon_1` … `dungeon_20`). Source: `cityNames` array on each
faction record in `DB/fractions/*.json`. Display names are genuinely
translated (8-16 distinct strings per name across the 16 languages —
CJK languages get full character-set translations; Latin scripts mix
preservation, idiomatic translation, and phonetic transliteration).
**No `desc_sid` exists for city names** — description columns are
sparse-emitted. See D-025.

Unlike the rows above, these are not hand-curated seeds — they're
extracted per-patch from the source JSON. They also do *not* live on
individual wiki pages: the 20 city Entry rows for a given faction are
appended to that faction's `Data:Faction/<id>` page (after the
`{{Faction}}` and `{{FactionTranslation}}` blocks, in numeric source
order). Cargo stores the rows in the unified `Entry` table just the
same; the page-name namespace `Data:FactionCityName/…` simply isn't
used. The faction emitter calls `render_entry_block(...)` to inline
each row.

## What does NOT belong here

Anything with structure beyond name/description/i18n keeps its own
table. For example, `AttackPassive` carries `pattern_token` and `rank`
columns and stays separate. The rule: if you'd add a column for a
single use case, it goes in its own dedicated table. Entry is for the
"identical shape, different domain" cases only.

## Related

- D-024 establishes the Entry catch-all rule and supersedes the
  earlier per-domain tables (D-021 partial, D-022, D-023).
- [`Unit`](../Unit.md) — references multiple Entry types via
  `attack_type`, `move_type`, `creature_type` columns.
- [`AttackPassive`](AttackPassive.md) — separate table; has columns
  beyond the Entry shape.

## Wiki template notes

```mediawiki
<noinclude>
Reference table for shared name+description+i18n entries. The Entry
table itself is internal — pages live under per-domain wiki namespaces
(Data:Movement/<subtype>, Data:CreatureType/<subtype>,
Data:AttackArchetype/<subtype>, ...) and each page invokes
{{Entry | type=<type> | subtype=<subtype> | ...}} which routes through
this template's #cargo_store call.
</noinclude><includeonly>{{#cargo_store:_table=Entry
| type={{{type|}}}
| subtype={{{subtype|}}}
| display_name={{{display_name|}}}
| description={{{description|}}}
| icon={{{icon|}}}
| name_sid={{{name_sid|}}}
| desc_sid={{{desc_sid|}}}
| pt_br_name={{{pt_br_name|}}}
| pt_br_desc={{{pt_br_desc|}}}
| cs_name={{{cs_name|}}}
| cs_desc={{{cs_desc|}}}
| fr_name={{{fr_name|}}}
| fr_desc={{{fr_desc|}}}
| de_name={{{de_name|}}}
| de_desc={{{de_desc|}}}
| hu_name={{{hu_name|}}}
| hu_desc={{{hu_desc|}}}
| it_name={{{it_name|}}}
| it_desc={{{it_desc|}}}
| ja_name={{{ja_name|}}}
| ja_desc={{{ja_desc|}}}
| ko_name={{{ko_name|}}}
| ko_desc={{{ko_desc|}}}
| pl_name={{{pl_name|}}}
| pl_desc={{{pl_desc|}}}
| ru_name={{{ru_name|}}}
| ru_desc={{{ru_desc|}}}
| es_name={{{es_name|}}}
| es_desc={{{es_desc|}}}
| tr_name={{{tr_name|}}}
| tr_desc={{{tr_desc|}}}
| uk_name={{{uk_name|}}}
| uk_desc={{{uk_desc|}}}
| zh_cn_name={{{zh_cn_name|}}}
| zh_cn_desc={{{zh_cn_desc|}}}
| zh_tw_name={{{zh_tw_name|}}}
| zh_tw_desc={{{zh_tw_desc|}}}
}}</includeonly>
```

## Notes
