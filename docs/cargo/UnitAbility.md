# UnitAbility

Parent table. One row per ability slot on every unit, regardless of type.
Identity + L10n keys only — type-specific scalars live in splinter tables
joined on `ability_id`.

The wiki-side templates (`{{ActiveAbility}}`, `{{PassiveAbility}}`, …)
each call `#cargo_store` against this table AND against their respective
splinter table in a single template invocation. The bot picks the right
template name per row based on `ability_type`.

## Schema

```mediawiki
{{#cargo_declare:_table=UnitAbility
| ability_id = String                         <!-- synthetic; primary join key -->
| unit_id = String
| ability_type = String (allowed values=active,passive,conditional_passive,global_passive,aura,stat_passive,buff,debuff,selfbuff,additionbuff,copy_buff,curse,blood,other)
| ordinal = Integer
| variant = String (allowed values=base,advanced,upg,upg_alt)
| name = String
| desc = Wikitext
| name_sid = String
| desc_sid = String
}}
```

## Field notes

- **`ability_id`** is the universal join key. Format:
  `<unit_id>[_<ability_type>]_<ordinal>[_<variant>]`, where `active` is
  omitted from the type slot and `base` is omitted from the variant slot.
  See `docs/cargo/README.md` for the full convention.
- **`ability_type`** is the discriminator. The wiki layer uses it to
  decide which splinter to join against.
  - `active` — formerly named `ability` in older patches. Joined to
    `UnitAbilityActive`.
  - `passive` / `conditional_passive` / `global_passive` / `aura` /
    `stat_passive` — each joined to its like-named splinter.
  - `buff` / `debuff` / `selfbuff` / `additionbuff` / `copy_buff` /
    `curse` / `blood` / `other` — discovered via SID family but have no
    unit-side splinter. Their payload lives in a future `Buff` table
    keyed on `name_sid`.
- **`variant`** is `null` for the base/default form, `"advanced"` /
  `"upg"` / `"upg_alt"` for the appropriate variant SID family. Two rows
  with the same `(unit_id, ability_type, ordinal)` but different
  `variant` represent the same ability slot in different unit tiers.
- **`name` / `desc`** are the English defaults. Translations are in
  `UnitAbilityTranslation`, joined on `ability_id`.

## Related tables

- [`UnitAbilityActive`](UnitAbilityActive.md) — splinter for `active`.
- [`UnitAbilityPassive`](UnitAbilityPassive.md) — splinter for `passive`.
- [`UnitAbilityConditional`](UnitAbilityConditional.md) — splinter for
  `conditional_passive`.
- [`UnitAbilityGlobal`](UnitAbilityGlobal.md) — splinter for
  `global_passive`.
- [`UnitAbilityAura`](UnitAbilityAura.md) — splinter for `aura`.
- [`UnitAbilityStatPassive`](UnitAbilityStatPassive.md) — splinter for
  `stat_passive`.
- [`UnitAbilityTranslation`](UnitAbilityTranslation.md) — i18n companion
  (1:1).
- [`Unit`](Unit.md) — parent on `unit_id = id` (N:1).

## Notes
