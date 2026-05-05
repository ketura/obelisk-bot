# HeroClass

One row per hero class — exactly **12 rows**, the cross-product of
the 6 factions and the 2 class types (`might`, `magic`):

| Faction | Might class | Magic class |
| --- | --- | --- |
| `human` | Knight | Cleric |
| `undead` | Death Knight | Necromancer |
| `dungeon` | Overlord | Warlock |
| `nature` | Warden | Druid |
| `demon` | Enforcer | Herald |
| `unfrozen` | Oathkeeper | Riftspeaker |

Each row holds the **default values** that every hero of that class
inherits. Individual `Hero` rows carry only the *deltas* — fields the
hero diverges from the class on (always `id`, `icon`, `specialization`,
`startSquad`, `startSkills`, etc.; sometimes `stats`, `startLevel`,
etc. for campaign and tutorial heroes who deviate from the canonical
template). When a `Hero` row omits a class-level field, the wiki
display layer joins to `HeroClass` to fill it in. See D-026.

Empirical: across all 108 faction heroes, the 11 class-level fields
listed below are **invariant** within each class — there are zero
deviations from the template. Campaign (46) and tutorial (21) heroes
universally override `stats` plus a small subset of other fields,
treating the `HeroClass` row as a starting point.

## Schema

```mediawiki
{{#cargo_declare:_table=HeroClass
| id = String                  <!-- e.g. magic_demon, might_human -->
| name = String                <!-- e.g. Herald, Knight -->
| desc = Wikitext              <!-- shared per classType (might_desc / magic_desc) -->
| name_sid = String
| desc_sid = String

| faction = String (allowed values=human,undead,dungeon,nature,demon,unfrozen)
| class_type = String (allowed values=might,magic)

<!-- Class defaults: every faction hero inherits these unchanged -->
| mesh = String
| mount = String                 <!-- single mount; source is a list, but always length 1 -->
| native_biome = String
| skills_roll_variant = String
| cost_gold = Integer
| start_level = Integer
| attacks_times_before = String  <!-- comma-joined floats, e.g. "0.5" -->

<!-- Stat block (full UnitStats-style flatten) -->
| view_radius = Integer
| stats_num = Integer
| magic_casts_per_round = Integer
| enable_tactics = Boolean
| tactics_placement_size = Integer
| enable_hero_native_biome = Boolean
| offence = Integer
| defence = Integer
| spell_power = Integer
| intelligence = Integer
| luck = Integer
| morale = Integer

<!-- statsRolls flattened: always 2 bands (level 1 / level 24),
     each with chance weights for which stat the level-up bonus
     lands on. Source `v` indexes 0/1/2/3 are interpreted as
     attack / defense / power / knowledge in that order. -->
| roll_lvl1_attack = Integer
| roll_lvl1_defense = Integer
| roll_lvl1_power = Integer
| roll_lvl1_knowledge = Integer
| roll_lvl24_attack = Integer
| roll_lvl24_defense = Integer
| roll_lvl24_power = Integer
| roll_lvl24_knowledge = Integer
}}
```

## Field notes

- **`id`** is `<class_type>_<faction>` (matches the L10n SID prefix).
  12 fixed values: `might_human`, `magic_human`, … `magic_unfrozen`.
- **`name`** comes from `<class_type>_<faction>_name` SIDs (e.g.
  `magic_demon_name` → "Herald"). Full 16-language coverage on all
  12 SIDs.
- **`desc`** comes from one of two shared SIDs: `might_desc` or
  `magic_desc`. The same description appears on all 6 factions of a
  given type — Unfrozen reused it, faction doesn't matter for this
  text. Both SIDs have full 16-language coverage. **All 6 might
  classes share the same `desc_sid='might_desc'`; all 6 magic
  classes share `desc_sid='magic_desc'`** — translation
  duplication is intentional (one SID, six joined rows).
- **`mount`** is singular here even though the source's `mounts` is
  a list, because every faction hero in the 2026-05-03 corpus has
  exactly one mount per class. If a future patch ships heroes with
  multiple mounts, promote this to a list-typed column or split it
  to a side table.
- **`stats`** is flattened from the source's nested `stats` dict.
  All twelve fields present on every hero.
- **`statsRolls`** is uniformly 2 bands × 4 chances across all 108
  faction heroes. The second band always starts at level 24, and
  the chance-value tuple is always `v=(0, 1, 2, 3)` in that exact
  order. The `v` indexes don't appear in source data with any
  player-facing meaning, but their order matches the four primary
  stats — so the schema flattens them to named columns
  `roll_lvl<N>_<stat>` (`attack`, `defense`, `power`, `knowledge`)
  holding the chance weight for that level-band / stat-bonus pair.
  Weights sum to 100 within each band. **If a future patch reveals
  this stat-order assumption is wrong, the column names need to
  change accordingly** — the JSON itself doesn't label them.

## Override semantics

The `Hero` table mirrors most of the columns above. When the bot
emits a hero row:

- **Faction heroes (108):** the bot omits all 11 class-level columns
  from the `Hero` row — they're all defaulted from `HeroClass`.
  Display layer reads the field from `Hero`; if absent, joins
  `HeroClass` on `Hero.class_id = HeroClass.id` and reads from
  there.
- **Campaign / tutorial heroes:** the bot includes only the columns
  where the hero deviates from the class template. Empirically these
  are almost always `stats`, `attacks_times_before`, and
  `start_level`; sometimes `mesh`, `mounts`, `skills_roll_variant`.
  All other class-level columns stay defaulted.

The override rule is a single Cargo query pattern:
`COALESCE(Hero.<col>, HeroClass.<col>)` — Hero wins when present,
HeroClass fills in otherwise.

## Related tables

- [`Hero`](Hero.md) — joined on `Hero.class_id = HeroClass.id` (1:N).
  Hero rows hold only the per-hero data and any fields that override
  the class default.
- [`HeroClassTranslation`](HeroClassTranslation.md) — joined on `id =
  class_id` (1:1) for the 15 non-English locales of `name` + `desc`.
- [`HeroSubClass`](HeroSubClass.md) — the named prestige classes
  (Swashbuckler, Paragon, etc.) that branch off each HeroClass at
  certain skill thresholds. Joined via `HeroSubClass.faction +
  HeroSubClass.class_type`.

## Notes
