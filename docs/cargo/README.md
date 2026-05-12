# Cargo schema reference

Each file in this directory is a `#cargo_declare` definition for one Cargo
table the bot writes to. They're meant to be pasted into a wiki page (one
table per page is the MediaWiki convention) when the wiki maintainers are
ready to provision Cargo storage.

## Tables

Tables are grouped by parent entity. Splinters of `UnitAbilityDef`
join back via `ability_id`; every other relationship uses the parent
entity's natural id.

### Units

| Table | Purpose |
| --- | --- |
| [`UnitDef`](UnitDef.md) | One row per creature. Combat stats, resource costs, faction, tier, classification flags, English name/desc. |
| [`UnitAttackDef`](UnitAttackDef.md) | One row per unit. All four attack slots (`default_*` / `counter_*` / `alt_*` / `alt2_*`) collapsed into a single wide row. `<slot>_attack_type` references the `attack_archetype` Entry; `<slot>_passive` references [`AttackPassiveDef`](shared/AttackPassiveDef.md). |
| [`UnitAbilityDef`](UnitAbilityDef.md) | One row per ability slot on a unit. Identity + i18n SIDs. Splintered by `ability_type` into one of the six tables below. |
| [`UnitAbilityActiveDef`](UnitAbilityActiveDef.md) | Active-ability scalars (dealer, buff, target, shoot range, cooldown, …). Splinter of `UnitAbilityDef`. |
| [`UnitAbilityPassiveDef`](UnitAbilityPassiveDef.md) | Passive-only fields. Splinter of `UnitAbilityDef`. |
| [`UnitAbilityConditionalDef`](UnitAbilityConditionalDef.md) | Condition triple + stat bonus for `conditional_passive` rows. Splinter of `UnitAbilityDef`. |
| [`UnitAbilityGlobalDef`](UnitAbilityGlobalDef.md) | Side-wide passive (target, power, tag) for `global_passive` rows. Splinter of `UnitAbilityDef`. |
| [`UnitAbilityAuraDef`](UnitAbilityAuraDef.md) | Range-1 aura fields (target, power, radius, tag) for `aura` rows. Splinter of `UnitAbilityDef`. |
| [`UnitAbilityStatPassiveDef`](UnitAbilityStatPassiveDef.md) | Synthesized stat passive (e.g. `attackPen` → "Unyielding"). Splinter of `UnitAbilityDef`. |

### Factions

| Table | Purpose |
| --- | --- |
| [`FactionDef`](FactionDef.md) | One row per faction. Identity, biome, primary resource, city names. |
| [`FactionLawTierDef`](FactionLawTierDef.md) | Five rows per faction. Per-tier `count_to_unlock` gating for the faction law tree. |
| [`LawTreePositionDef`](LawTreePositionDef.md) | One row per (faction, law). Tree position (tier + slot) of a law in its faction's law tree. |

### Heroes

| Table | Purpose |
| --- | --- |
| [`HeroDef`](HeroDef.md) | One row per hero. Identity, class, faction, biography, per-hero overrides of class defaults. |
| [`HeroClassDef`](HeroClassDef.md) | One row per class. Stat-growth tables and skill-availability matrix. |
| [`HeroSpecializationDef`](HeroSpecializationDef.md) | One row per specialization. Name, description, source path. Bonuses live on [`BonusDef`](shared/BonusDef.md). |
| [`HeroSubClassDef`](HeroSubClassDef.md) | One row per prestige sub-class. Five activation thresholds (skill + level) inline. Bonuses on `BonusDef`. |
| [`HeroStartSquadDef`](HeroStartSquadDef.md) | Multiple rows per hero. Starting army composition per (variant, slot). |

### Spells

| Table | Purpose |
| --- | --- |
| [`SpellDef`](SpellDef.md) | One row per spell. School, costs, identity. |
| [`SpellRankDef`](SpellRankDef.md) | Four rows per spell (level 1–4). English description + bonus_description + costs, plus 15 × (name, desc, bonus_description) language columns. Self-contained — no separate translation table. |

### Laws

| Table | Purpose |
| --- | --- |
| [`LawDef`](LawDef.md) | One row per faction law. Faction, tier, ordinal, max_level. |
| [`LawLevelDef`](LawLevelDef.md) | One to three rows per law. Per-level cost + resolved English description. Non-English descriptions live on `EntryDef` rows keyed by `(type='law_level', subtype=<law_id>, variant=<level>)`. |

### Artifacts

| Table | Purpose |
| --- | --- |
| [`ArtifactDef`](ArtifactDef.md) | One row per artifact. Slot, rarity, set membership. Bonuses on `BonusDef`. |
| [`ItemSetDef`](ItemSetDef.md) | One row per set. Member artifacts. |
| [`ItemSetTierDef`](ItemSetTierDef.md) | One to three rows per set. Per-completion-tier description. Bonuses on `BonusDef`. |

### Skills

| Table | Purpose |
| --- | --- |
| [`SkillDef`](SkillDef.md) | One row per hero skill (primary skills + pseudo + arena + campaign). Identity, max_level. |
| [`SkillLevelDef`](SkillLevelDef.md) | One to three rows per skill. Per-level English name/desc + `offered_sub_skills`. Non-English per-level overrides live on `EntryDef` rows keyed by `(type='skill_level', subtype=<skill_id>, variant=<level>)`. |
| [`SubSkillDef`](SubSkillDef.md) | One row per sub-skill. Identity, parent skill, English name/desc. Bonuses on `BonusDef`. |

### Other entities

| Table | Purpose |
| --- | --- |
| [`BuildingDef`](BuildingDef.md) | One row per (faction, building, upgrade level). Resource costs, weekly-creature payloads, identity. |
| [`MapObjectDef`](MapObjectDef.md) | One row per adventure-map structure (chests, mines, banks, portals, dwellings, etc.). Category + universal scalars. |
| [`AstrologistEventDef`](AstrologistEventDef.md) | One row per weekly or monthly event. Category, roll_chance, return-to-pool count. |
| [`DifficultyDef`](DifficultyDef.md) | One row per game difficulty. Per-side starting-resource buckets + `neutralPowerMultiplier`. |

## Shared reference tables

These tables live in [`shared/`](shared/). Per-entity tables join into
them by string id.

| Table | Purpose |
| --- | --- |
| [`EntryDef`](shared/EntryDef.md) | Generic `(type, subtype, variant)` table for any data that fits the "name + description + i18n" shape: hand-curated seeds (attack archetypes, movement types, creature types, hero/unit stats), per-patch extracted reference data (resources, faction city names), and per-(entity, level) translation rows for laws and skill levels. Each row carries English defaults plus 15 non-English language pairs inline. |
| [`TranslationDef`](shared/TranslationDef.md) | Per-entity i18n with a `type` discriminator. One row per (entity-type, entity-id) carrying `name_sid` + `desc_sid` plus 15 × (name, desc) language columns. Used by units, factions, heroes, hero classes, hero specializations, hero sub-classes, artifacts, item sets, item-set tiers, laws, buildings, map objects, skills, sub-skills, astrologist events, attack passives, and unit abilities. |
| [`AttackPassiveDef`](shared/AttackPassiveDef.md) | One row per named pattern-passive (Sweeping Strike, Whirlwind Strike, Dragonbreath Strike, Cone Strike, Area Strike — with falloff variants). Referenced from `UnitAttackDef.<slot>_passive`. Translations on `TranslationDef` with `type='attack_passive'`. |
| [`BonusDef`](shared/BonusDef.md) | Unified bonus table shared across hero specializations, hero sub-classes, artifacts, item-set tiers, and law levels. Discriminated by `(parent_type, parent_id)`. |

## Join key conventions

The bot synthesizes a deterministic `ability_id` for every
`UnitAbilityDef` row, formatted as:

```
<unit_id>[_<ability_type>]_<ordinal>[_<variant>]
```

with `active` omitted from the ability-type slot and `base` omitted
from the variant slot. Examples:

```
crossbowman_1                   active ability, base
crossbowman_passive_1           passive
inquisitor_2_upg_alt            active, upg_alt variant
godslayer_stat_passive_1        synthesized stat passive
```

The six `UnitAbility*Def` splinter tables and `TranslationDef`
(with `type='unit_ability'`) all carry this same `ability_id` so a
single-column join reaches every related row. See `D-019` in
`docs/decisions.md` for rationale.

## Sentinels and defaults

A few columns use sentinel values that wiki templates need to handle:

- `cd = -1` → once per battle. `cd = 0` → no cooldown.
- `action_cost = 0` → ability does not end the unit's turn (default is 1).
- `buff_duration = -1` → infinite. `buff_duration = 999` → until end of battle.
- `shoot_range = -1` → melee-only. `shoot_range = 99` → "infinite" for the engine.
- `unused = yes` → deprecated content the bot ships rows for to keep
  diff visibility. Most queries should filter `WHERE unused != "yes"`.
  The column is absent (NULL) for active units; this keeps the column
  off the emit on the typical row.

`UnitAttackDef` columns are **slot-prefixed** (`default_*`,
`counter_*`, `alt_*`, `alt2_*`). Each slot carries its own set of
defaults. See [`UnitAttackDef.md`](UnitAttackDef.md) for the full
table; the gist:

- `default_*` → 1.0× damage, triggers counter, no cooldown.
- `counter_*` → 1.0× damage, does *not* trigger counter, no cooldown.
- `alt_*` / `alt2_*` → 0.5× damage, no counter. `cd=0` is the default;
  Fighting Style alts emit `cd=-1` explicitly. Most ranged-unit melee
  fallbacks emit zero override columns.
