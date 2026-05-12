# TranslationDef

A single shared table for **all per-entity i18n payloads**. Replaces
the parallel `UnitTranslation`, `FactionTranslation`,
`AttackPassiveTranslation`, … tables we used to ship — same shape,
one row per (entity-type, entity-id) pair, discriminated by `type`.
See D-026.

The bot never extracts `TranslationDef` rows on their own; each parent
entity's emit function appends a `{{TranslationDef | type=… | …}}` call
to its own page, right after the entity's structural row. The
`{{TranslationDef}}` MediaWiki template's job is to call `#cargo_store`
on this table.

## Schema

```mediawiki
{{#cargo_declare:_table=TranslationDef
| type = String              <!-- e.g. unit, faction, hero, hero_class, attack_passive -->
| target_id = String         <!-- the parent entity's id (Unit.id, Faction.id, etc.) -->
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

- **Primary key is `(type, target_id)`** as a tuple. Joins from
  parent entities include the type discriminator: e.g.
  `Unit.id = Translation.target_id WHERE Translation.type='unit'`.
- **English defaults are *not* here.** They live on each parent
  entity's row (`Unit.name`, `Faction.name`, `HeroClass.name`,
  etc.) so the most common query — "give me the English label for
  this unit" — needs only a single-table read. Translations are the
  i18n payload only.
- **Language-code mapping** (game directory → two-letter code):
  - `BRportugese` → `pt_br`
  - `czech` → `cs`, `french` → `fr`, `german` → `de`, `hungarian` → `hu`,
    `italian` → `it`, `japanese` → `ja`, `korean` → `ko`, `polish` → `pl`,
    `russian` → `ru`, `spanish` → `es`, `turkish` → `tr`, `ukrainian` → `uk`
  - `zhCN` → `zh_cn`, `zhTW` → `zh_tw`
- **Sparse output**: any per-language slot the bot couldn't resolve
  is omitted. Some entities (e.g. faction-shared `magic_desc` /
  `might_desc` for HeroClass) deliberately reuse a single SID across
  many parents — those parents will all carry the same per-language
  text on their own Translation row.
- **The `desc` field is Wikitext** because translations may include
  HTML-bold and HTML-italic tags from the L10n corpus, which the
  bot's resolver converts to wiki markup (`'''` and `''`) before
  storing.

## Entity types currently emitted

| `type` | Parent entity | `target_id` | Emit site |
| --- | --- | --- | --- |
| `unit` | [`UnitDef`](../Unit.md) | `Unit.id` | `emit_unit_page` |
| `unit_ability` | [`UnitAbilityDef`](../UnitAbility.md) | `UnitAbility.ability_id` (composite) | `emit_unit_page` |
| `attack_passive` | [`AttackPassiveDef`](shared/AttackPassive.md) | `AttackPassive.attack_passive_id` | `emit_attack_passive_page` |
| `faction` | [`FactionDef`](../Faction.md) | `Faction.id` | `emit_faction_page` |

(Hero-side entries: `hero`, `hero_class`, `hero_specialization`,
`hero_sub_class` — added as those entities come online.)

## Page layout

Translation rows do **not** live on their own wiki pages. Each row is
emitted as a `{{TranslationDef | …}}` invocation on the parent entity's
data page, immediately after the entity's structural row. The
`(type, target_id)` discriminator means Cargo can store many rows in
a single table without page-naming collisions.

## Wiki template notes

```mediawiki
<noinclude>
Per-entity i18n payload, shared across all categories. Invoked from
each parent entity's data page (Data:Unit/<id>, Data:Faction/<id>,
etc.) — there is no Data:Translation/… page namespace.
</noinclude><includeonly>{{#cargo_store:_table=TranslationDef
| type={{{type|}}}
| target_id={{{target_id|}}}
| name_sid={{{name_sid|}}}
| desc_sid={{{desc_sid|}}}
| pt_br_name={{{pt_br_name|}}}
| pt_br_desc={{{pt_br_desc|}}}
| cs_name={{{cs_name|}}}
| cs_desc={{{cs_desc|}}}
| fr_name={{{fr_name|}}}
| fr_desc={{{fr_desc|}}}
| de_name={{{de_name|}}}
| de_desc={{{de_desc|}}}
| hu_name={{{hu_name|}}}
| hu_desc={{{hu_desc|}}}
| it_name={{{it_name|}}}
| it_desc={{{it_desc|}}}
| ja_name={{{ja_name|}}}
| ja_desc={{{ja_desc|}}}
| ko_name={{{ko_name|}}}
| ko_desc={{{ko_desc|}}}
| pl_name={{{pl_name|}}}
| pl_desc={{{pl_desc|}}}
| ru_name={{{ru_name|}}}
| ru_desc={{{ru_desc|}}}
| es_name={{{es_name|}}}
| es_desc={{{es_desc|}}}
| tr_name={{{tr_name|}}}
| tr_desc={{{tr_desc|}}}
| uk_name={{{uk_name|}}}
| uk_desc={{{uk_desc|}}}
| zh_cn_name={{{zh_cn_name|}}}
| zh_cn_desc={{{zh_cn_desc|}}}
| zh_tw_name={{{zh_tw_name|}}}
| zh_tw_desc={{{zh_tw_desc|}}}
}}</includeonly>
```

## Notes
