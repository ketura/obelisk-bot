# SkillLevelTranslation

One row per (skill, level) pair carrying per-level localized name + desc *overrides* in the 16 supported languages. Most levels inherit from the parent skill (covered by `{{Translation | type=skill}}`), so this table is sparse — only emitted when a level carries its own `name_sid` or `desc_sid`.

Mirrors the `LawLevelTranslation` and `SpellRankTranslation` pattern but with both `<LANG>_name` and `<LANG>_desc` columns since either the name, the description, or both may be overridden at a given level.

## Page layout

Emitted inline on `Data:Skill/<id>` immediately after the matching `{{SkillLevel}}` row, only when the level has at least one override SID.

## Schema

```mediawiki
{{#cargo_declare:_table=SkillLevelTranslation
| skill_id = String
| level = Integer
| name_sid = String                <!-- nullable; matches SkillLevel.name_sid -->
| desc_sid = String                <!-- nullable; matches SkillLevel.desc_sid -->
| en_name = String
| en_desc = Wikitext
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
| zh_hans_name = String
| zh_hans_desc = Wikitext
| zh_hant_name = String
| zh_hant_desc = Wikitext
}}
```

## Field notes

- **Primary key is `(skill_id, level)`**.
- Per-language column naming follows the project-wide `<LANG_CODE>_name` / `<LANG_CODE>_desc` convention (see `shared/Translation.md`).
- A locale that lacks the relevant SID translation is omitted from the emit (Cargo treats absent params as NULL).
- A level with neither `name_sid` nor `desc_sid` set produces no row at all — fall back to the parent skill's `Translation` row.

## Related tables

- [`SkillLevel`](SkillLevel.md) — joined on `(skill_id, level)`.
- [`Translation`](shared/Translation.md) — sibling table carrying the parent skill's shared name + desc in 16 languages (one row per skill with `type=skill`).
