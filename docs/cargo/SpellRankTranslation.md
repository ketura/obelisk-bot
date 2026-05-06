# SpellRankTranslation

Per-rank i18n payload for a spell. One row per `(spell_id, level)`
pair — 4 rows per spell — carrying the 15 non-English locales of:

- the **spell name** (same SID across all 4 ranks for a given spell;
  duplicated per-row for clean per-rank queries),
- the **rank's description** (varies by mastery level),
- the **rank's bonus description** (the unlock blurb for this level;
  null for level 1).

Per D-030 (revised): spells use this dedicated translation table
instead of the unified `Translation` table because the per-rank
shape carries three localizable fields (name + desc +
bonus_description), one more than `Translation` accommodates.

The bot emits each row inline on the parent `Data:Spell/<id>` page,
right after the matching `{{SpellRank}}` row.

## Schema

```mediawiki
{{#cargo_declare:_table=SpellRankTranslation
| spell_id = String
| level = Integer

| name_sid = String
| desc_sid = String
| bonus_description_sid = String

<!-- Per-language triples. Each language gets name + desc + bonus_description. -->
| pt_br_name = String
| pt_br_desc = Wikitext
| pt_br_bonus_description = Wikitext
| cs_name = String
| cs_desc = Wikitext
| cs_bonus_description = Wikitext
| fr_name = String
| fr_desc = Wikitext
| fr_bonus_description = Wikitext
| de_name = String
| de_desc = Wikitext
| de_bonus_description = Wikitext
| hu_name = String
| hu_desc = Wikitext
| hu_bonus_description = Wikitext
| it_name = String
| it_desc = Wikitext
| it_bonus_description = Wikitext
| ja_name = String
| ja_desc = Wikitext
| ja_bonus_description = Wikitext
| ko_name = String
| ko_desc = Wikitext
| ko_bonus_description = Wikitext
| pl_name = String
| pl_desc = Wikitext
| pl_bonus_description = Wikitext
| ru_name = String
| ru_desc = Wikitext
| ru_bonus_description = Wikitext
| es_name = String
| es_desc = Wikitext
| es_bonus_description = Wikitext
| tr_name = String
| tr_desc = Wikitext
| tr_bonus_description = Wikitext
| uk_name = String
| uk_desc = Wikitext
| uk_bonus_description = Wikitext
| zh_cn_name = String
| zh_cn_desc = Wikitext
| zh_cn_bonus_description = Wikitext
| zh_tw_name = String
| zh_tw_desc = Wikitext
| zh_tw_bonus_description = Wikitext
}}
```

## Field notes

- **Primary key is `(spell_id, level)`**.
- **English defaults are *not* here.** They live on:
  - `Spell.name` (English spell name)
  - `SpellRank.description` (English per-rank description)
  - `SpellRank.bonus_description` (English level-up bonus)
  Same split-storage convention as the unified `Translation` table.
- **`name_sid`** is the spell's name SID, repeated on all 4 rows
  for a given spell. Storing it per-row lets the wiki query the
  spell's name alongside the rank-specific text in one join.
- **`bonus_description_sid` / `<lang>_bonus_description`** are null
  on the level-1 row (no level-up bonus when you've just learned
  the spell). Sparse-emit: empty fields are omitted.
- **The `desc` and `bonus_description` fields are Wikitext** because
  translations may include HTML markup the resolver converts to
  wiki bold/italic syntax. They also commonly contain `{N}`
  placeholders for spell-power-scaled values that the bot
  intentionally leaves unresolved (per D-030 — the value depends on
  the casting hero).

## Why not the unified Translation table?

Per D-026 the standard pattern is one `Translation` table with `type`
discriminator and `(name, desc)` slots. Spells need a third slot
(`bonus_description`); adding it to `Translation` would pollute the
shared schema. SpellRankTranslation is the single divergence — and
it's also the only entity in the corpus with a 3-SID-per-row
translation pattern.

## Related tables

- [`Spell`](Spell.md) — joined on `spell_id = id` (N:1 — 4 rows
  per spell).
- [`SpellRank`](SpellRank.md) — joined on `(spell_id, level)` (1:1).

## Notes
