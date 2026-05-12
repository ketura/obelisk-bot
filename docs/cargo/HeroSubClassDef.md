# HeroSubClassDef

A named prestige class — Swashbuckler, Paragon, Grand Inquisitor,
Ascendant, etc. — that a hero unlocks by hitting **5 specific skill
thresholds**. 24 rows total: 4 per faction × 6 factions, split
2 might + 2 magic per faction.

The bot emits each sub-class at `Data:HeroSubClass/<id>` carrying:

1. `{{HeroSubClassDef | id=… | name=… | desc=… | activation_skill_1_sid=… | …}}`
   — main row with the 5 activation thresholds inline.
2. `{{TranslationDef | type=hero_sub_class | target_id=<id> | …}}`
   — name/description translations (per D-026).
3. N × `{{HeroSubClassBonus | sub_class_id=<id> | ordinal=N | …}}`
   — the unlocked passive bonuses (~2 per sub-class, 46 total).

## Schema

```mediawiki
{{#cargo_declare:_table=HeroSubClassDef
| id = String                            <!-- sub_class_<faction>_<might|magic>_<1|2> -->
| name = String
| desc = Wikitext
| name_sid = String
| desc_sid = String
| icon = String

| faction = String (allowed values=human,undead,dungeon,nature,demon,unfrozen)
| class_type = String (allowed values=might,magic)

<!-- 5 activation thresholds, flattened. Every sub-class has exactly 5
     in the 2026-05-03 corpus. Each pair references a future Skill SID
     and the rank the hero must reach. subSkillSids (always empty in
     2026-05-03) is dropped per D-029. -->
| activation_skill_1_sid = String
| activation_skill_1_level = Integer
| activation_skill_2_sid = String
| activation_skill_2_level = Integer
| activation_skill_3_sid = String
| activation_skill_3_level = Integer
| activation_skill_4_sid = String
| activation_skill_4_level = Integer
| activation_skill_5_sid = String
| activation_skill_5_level = Integer

| source_path = String
}}
```

## Field notes

- **`id`** matches the L10n SID prefix
  (e.g. `sub_class_human_might_1` → "Swashbuckler").
- **`name_sid` / `desc_sid`** point at
  `<id>_name` / `<id>_desc`. Full 16-language coverage.
- **`name` / `desc`** carry the resolved English text inline.
  Translations live on the `{{TranslationDef | type=hero_sub_class}}` row.
- **Activation conditions are joined by AND** — the hero must hit
  all 5 skill thresholds to unlock the sub-class.
- **Per-faction-class matchup:** every (faction × class_type) cell
  has exactly 2 sub-classes. Looking up "what sub-classes are
  available to a magic Demon hero?" → `WHERE faction='demon' AND
  class_type='magic'` → 2 rows (Progenitor, Lord of Chaos).

## Related tables

- [`HeroDef`](HeroDef.md) — joins via `Hero.faction = HeroSubClass.faction
  AND Hero.class_type = HeroSubClass.class_type`. Each hero qualifies
  for the 2 sub-classes in their faction × class_type cell.
- [`HeroClassDef`](HeroClassDef.md) — same join; HeroSubClass is the
  prestige progression on top of the broader HeroClass.
- [`HeroSubClassBonus`](HeroSubClassBonus.md) — joined on
  `id = sub_class_id` (1:N).
- `SkillDef` — *(future table; joined on activation_skill_<N>_sid)*.
- [`TranslationDef`](shared/Translation.md) — one row per sub-class with
  `type=hero_sub_class`.

## Notes
