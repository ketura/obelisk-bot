# LawLevelTranslation

One row per (law, level) pair carrying the law's resolved description in the 15 non-English supported locales. Mirrors the `SpellRankTranslation` pattern: per-level rows because each mastery level substitutes different parameters into the (shared) description template, producing distinct localized strings.

The English `description` lives directly on `LawLevel.description` and is not duplicated here.

## Page layout

Emitted inline on `Data:Law/<id>` immediately after the matching `{{LawLevel}}` row.

## Schema

```mediawiki
{{#cargo_declare:_table=LawLevelTranslation
| law_id = String
| level = Integer
| desc_sid = String
| pt_br_desc = Wikitext
| cs_desc = Wikitext
| fr_desc = Wikitext
| de_desc = Wikitext
| hu_desc = Wikitext
| it_desc = Wikitext
| ja_desc = Wikitext
| ko_desc = Wikitext
| pl_desc = Wikitext
| ru_desc = Wikitext
| es_desc = Wikitext
| tr_desc = Wikitext
| uk_desc = Wikitext
| zh_hans_desc = Wikitext
| zh_hant_desc = Wikitext
}}
```

## Field notes

- **Primary key is `(law_id, level)`**.
- Per-language column naming follows the project-wide `<LANG_CODE>_desc` convention (see `shared/Translation.md` for the canonical lang-dir → code mapping).
- A locale that lacks the `desc_sid` translation is omitted from the emit (Cargo treats absent params as NULL).

## Related tables

- [`LawLevel`](LawLevel.md) — joined on `(law_id, level)`.
- [`Translation`](shared/Translation.md) — sibling table; carries the law *name* in 16 languages (one row per law, since name is shared across levels).
