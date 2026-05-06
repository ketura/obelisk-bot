# Bonus

A unified Cargo table for bonus effects across multiple parent
entity types. Per D-031: hero specializations, hero sub-classes, and
artifacts all carry the same `(type, parameters, [activationLevel],
[upgrade], [receivers], …)` source pattern, so they share one Bonus
table with `parent_type` + `parent_id` discriminator columns instead
of separate `<Entity>Bonus` tables.

The bot emits each row inline on the parent entity's wiki page.
There are no individual `Data:Bonus/…` pages.

## Schema

```mediawiki
{{#cargo_declare:_table=Bonus
| parent_type = String           <!-- hero_specialization, hero_sub_class, artifact -->
| parent_id = String             <!-- the parent entity's id -->
| ordinal = Integer              <!-- 0-based position in the source bonuses[] -->
| type = String                  <!-- bonus effect category (~13 distinct values) -->
| parameters = List (,) of String <!-- effect arguments; meaning depends on type -->

<!-- Sparse fields (omitted unless populated in source) -->
| activation_level = Integer
| upgrade_increment = Float
| upgrade_level_step = Integer
| receivers = List (,) of String
| battle_type = String
| receiver_role = String
| receiver_allegiance = String
}}
```

## Field notes

- **Primary key is `(parent_type, parent_id, ordinal)`**.
- **`parent_type`** identifies the parent entity table:
  - `hero_specialization` — joined to `HeroSpecialization.id`
  - `hero_sub_class` — joined to `HeroSubClass.id`
  - `artifact` — joined to `Artifact.id`
  - `item_set_tier` — joined to `ItemSetTier.id`
  Add new values as new bonus-bearing entities come online.
- **`type`** is the effect category. ~13 distinct values across the
  2026-05-03 corpus, with `heroStat` (~895), `unitStat` (~330),
  `heroBattleAbility` (~235) the most common. Artifacts add a few
  new ones (`heroMagicAddition` for spell scrolls,
  `heroTemporallyActiveSubSkills`).
- **`parameters`** is comma-joined, type-dependent. Same encoding
  as the original *Bonus tables. Wiki side parses by `type`.
- **Sparse fields** vary by parent type:
  - Spec bonuses use the full schema.
  - Sub-class bonuses don't carry `activation_level`, `upgrade_*`,
    `battle_type`, or `receiver_role` in the 2026-05-03 corpus.
  - Artifact bonuses use most fields except `battle_type` and
    `receiver_role`.

## Why one table, not three

Per D-031: schema overlap is total — all three previous tables
(`HeroSpecializationBonus`, `HeroSubClassBonus`, `ItemBonus`) shared
the same column set with different fill-rate patterns. Same play as
D-024 (Entry) and D-026 (Translation): collapse identical-shape
parallel tables into a single discriminated table. Filtered queries
(e.g. "all bonuses on this artifact") use
`WHERE parent_type='artifact' AND parent_id='<id>'`.

## Related tables

- [`HeroSpecialization`](../HeroSpecialization.md)
- [`HeroSubClass`](../HeroSubClass.md)
- [`Artifact`](../Artifact.md)
- `Unit` — `receivers` entries reference `Unit.id`.

## Notes
