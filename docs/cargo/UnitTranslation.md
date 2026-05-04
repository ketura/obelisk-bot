# UnitTranslation

One row per unit. Localized name + narrative description across the 15
non-English languages. English defaults sit on the `Unit` row itself
(`name`, `desc` columns) — this table is purely the i18n payload.

The bot emits one `{{UnitTranslation | …}}` template invocation per
unit, immediately after the `{{Unit | …}}` row.

## Schema

```mediawiki
{{#cargo_declare:_table=UnitTranslation
| unit_id = String
| name_sid = String
| desc_sid = String

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

- **English is on `Unit`, not here.** The Unit row carries `name` / `desc`
  for the English defaults. Splitting them avoids redundant 17-column
  rows when most queries only want English.
- **Language-code mapping** (game directory → two-letter code):
  - `BRportugese` → `pt_br`
  - `czech` → `cs`, `french` → `fr`, `german` → `de`, `hungarian` → `hu`,
    `italian` → `it`, `japanese` → `ja`, `korean` → `ko`, `polish` → `pl`,
    `russian` → `ru`, `spanish` → `es`, `turkish` → `tr`, `ukrainian` → `uk`
  - `zhCN` → `zh_cn`, `zhTW` → `zh_tw`
- **Sparse output**: any per-language slot the bot couldn't resolve gets
  omitted. A unit missing one language (rare; usually new content) just
  won't have that column.
- **The `desc` field is Wikitext** because translations may include
  HTML-bold and HTML-italic tags from the game's L10n corpus, which the
  bot's resolver converts to wiki bold/italic syntax (`'''` and `''`)
  before storing.

## Related tables

- [`Unit`](Unit.md) — joined on `unit_id = id` (1:1).

## Notes
