# UnitAbilityTranslation

One row per ability slot. Localized name + description across the 15
non-English languages. English defaults sit on the parent `UnitAbility`
row itself (`name`, `desc` columns) — this table is purely the i18n
payload.

The bot emits one `{{UnitAbilityTranslation | …}}` template invocation
per ability slot, immediately after the splinter `#cargo_store` for that
slot.

## Schema

```mediawiki
{{#cargo_declare:_table=UnitAbilityTranslation
| ability_id = String                         <!-- synthetic; joins UnitAbility -->
| unit_id = String
| ability_type = String (allowed values=active,passive,conditional_passive,global_passive,aura,stat_passive,buff,debuff,selfbuff,additionbuff,copy_buff,curse,blood,other)
| ordinal = Integer
| variant = String (allowed values=base,advanced,upg,upg_alt)
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

- **English is on `UnitAbility`, not here.** The parent row carries
  `name` / `desc` for the English defaults. Splitting them avoids
  redundant 17-column rows when most queries only want English.
- **`ability_id` is the join key.** Same synthetic format as
  `UnitAbility.ability_id`:
  `<unit_id>[_<ability_type>]_<ordinal>[_<variant>]`. The redundant
  `unit_id` / `ability_type` / `ordinal` / `variant` columns are stored
  alongside it so wiki-side filters (e.g. "all active-ability
  translations for swordsmen") don't need to parse the composite key.
- **Language-code mapping** (game directory → two-letter code):
  - `BRportugese` → `pt_br`
  - `czech` → `cs`, `french` → `fr`, `german` → `de`, `hungarian` → `hu`,
    `italian` → `it`, `japanese` → `ja`, `korean` → `ko`, `polish` → `pl`,
    `russian` → `ru`, `spanish` → `es`, `turkish` → `tr`, `ukrainian` → `uk`
  - `zhCN` → `zh_cn`, `zhTW` → `zh_tw`
- **Sparse output**: any per-language slot the bot couldn't resolve gets
  omitted. An ability missing one language (rare; usually new content)
  just won't have that column.
- **The `desc` field is Wikitext** because translations may include
  HTML-bold and HTML-italic tags from the game's L10n corpus, which the
  bot's resolver converts to wiki bold/italic syntax (`'''` and `''`)
  before storing. Active-ability descriptions also commonly carry
  resolved scalar placeholders (damage values, durations, etc.).
- **Buff-family rows** (`ability_type` = `buff` / `debuff` / `selfbuff`
  / etc.) get their translations here too, even though their payload
  lives in a future `Buff` table. The join key still works because
  `ability_id` includes the buff's slot identity on the unit.

## Related tables

- [`UnitAbility`](UnitAbility.md) — joined on `ability_id` (1:1).

## Notes
