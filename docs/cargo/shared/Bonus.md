# Bonus

A unified Cargo table for bonus effects across multiple parent
entity types. Per D-031: hero specializations, hero sub-classes,
artifacts, item-set tiers, and faction laws all carry the same
`(type, parameters, [activationLevel], [upgrade], [receivers], …)`
source pattern, so they share one Bonus table with `parent_type` +
`parent_id` discriminator columns instead of separate `<Entity>Bonus`
tables.

The bot emits each row inline on the parent entity's wiki page.
There are no individual `Data:Bonus/…` pages.

## Schema

```mediawiki
{{#cargo_declare:_table=Bonus
| parent_type = String           <!-- hero_specialization, hero_sub_class, artifact, item_set_tier, law_level -->
| parent_id = String             <!-- the parent entity's id -->
| ordinal = Integer              <!-- 0-based position in the source bonuses[] -->
| type = String                  <!-- bonus effect category (~30 distinct values once laws added) -->
| parameters = List (,) of String <!-- effect arguments; meaning depends on type -->

<!-- Sparse fields (omitted unless populated in source) -->
| activation_level = Integer
| upgrade_increment = Float
| upgrade_level_step = Integer
| receivers = List (,) of String
| battle_type = String
| receiver_role = String
| receiver_allegiance = String
| action_area = String           <!-- e.g. allied; law-bonus extension -->
| fraction = String              <!-- target faction filter; law-bonus extension -->
}}
```

## Field notes

- **Primary key is `(parent_type, parent_id, ordinal)`**.
- **`parent_type`** identifies the parent entity table:
  - `hero_specialization` — joined to `HeroSpecialization.id`
  - `hero_sub_class` — joined to `HeroSubClass.id`
  - `artifact` — joined to `Artifact.id`
  - `item_set_tier` — joined to `ItemSetTier.id`
  - `law_level` — joined to `LawLevel` on `parent_id = law_id || '_L' || level`
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
  - Law-level bonuses use `receivers`, `receiver_allegiance`,
    `action_area`, `fraction`. They never use `activation_level`,
    `upgrade_*`, `battle_type`, or `receiver_role`.
- **`action_area`** (law-bonus only so far) — qualifier for which
  side a `barrackUpgradeUnitsHiring` etc. effect applies to. Values
  observed: `allied`.
- **`fractio