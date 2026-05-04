# AttackPassiveTranslation

One row per `AttackPassive` (~9 rows total). Localized name +
description across the 15 non-English languages. English defaults sit
on the `AttackPassive` row.

This is reference data the wiki ships pre-populated; the bot does not
maintain rows here.

## Schema

```mediawiki
{{#cargo_declare:_table=AttackPassiveTranslation
| attack_passive_id = String
| name_sid = String
| desc_sid = String

<!-- Per-language pairs. -->
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

- **English is on `AttackPassive`, not here.** The parent row carries
  `display_name` / `description` for the English defaults.
- **Language-code mapping** matches the rest of the i18n tables; see
  [`UnitTranslation.md`](../UnitTranslation.md).
- **The `desc` field is Wikitext** because translations may include
  HTML-bold tags from the L10n corpus; the resolver converts them to
  wiki bold (`'''…'''`).

## Related tables

- [`AttackPassive`](AttackPassive.md) — joined on `attack_passive_id` (1:1).

## Notes
