# Widget inventory — what we could extract

A standing TODO list of game data the bot could plausibly export to Cargo
tables and wikitext. Categorized by **status** and **complexity**. Counts
are from the 2026-04-30 patch dump.

## Legend

* **Status:** ✅ done / 🚧 partial / 📋 planned / ❓ uncertain it's worth doing
* **Complexity:** S / M / L / XL — extractor effort, not just row count
* **Stub-shaped fields:** name, desc, icon (and SID-equivalents), narrative
  text. Most categories share this skeleton; the *non-stub* part is what
  varies.

---

## ✅ Done

### Units
- **Path:** `DB/units/units_logics/<faction>/*_l.json`, `units_views/<faction>/*_v.json`
- **Count:** 152 units across 6 factions + neutrals
- **Cargo:** `Unit`, `UnitAbility`, `UnitTranslation`, `UnitAbilityTranslation`
- **Notes:** Variant chain via `base_sid`. Per-variant ability slots resolved via
  views file. Stat passives synthesized via mechanic registry. L10n placeholders
  resolved via the `resolve/` framework (97.5% coverage on english).

---

## 📋 High-priority next targets

These are the categories most likely to be browsed/searched on the wiki, with
clean data shapes.

### Heroes
- **Path:** `DB/heroes/<faction>/*.json`
- **Count:** ~157 (including campaign + tutorial); 18 per faction × 6 = 108 baseline
- **Top fields:** `id, fraction, classType, costGold, startLevel, startSquad,
  startSkills, startMagics, specialization, mounts, stats, statsRolls, nativeBiome`
- **Complexity:** M — straightforward record shape, but many cross-refs (squad,
  specialization, skills, magics) need resolved labels.
- **Suggested tables:** `Hero`, `HeroStartingSquad`, `HeroTranslation`.

### Hero specializations
- **Path:** `DB/heroes_specializations/specializations_<faction>.json`
- **Count:** ~135 (18 × 7 sub-files + campaign)
- **Top fields:** `id, name, desc, icon, bonuses[]` where each bonus has
  `activationLevel, type (heroStat|...), parameters[], upgrade`.
- **Complexity:** M — bonuses are nested but uniform.
- **Suggested tables:** `HeroSpecialization`, `HeroSpecializationBonus`.

### Hero skills
- **Path:** `DB/heroes_skills/skills/*.json` (4 files), `sub_skills/*.json` (4 files)
- **Count:** main skills small; sub_skills 203 entries in one file
- **Top fields:** `id, name, desc, icon, bonuses[]`; for level tables:
  `id, parametersPerLevel`.
- **Complexity:** M — but per-level scaling tables in `skills_by_level_tables/`
  (33 files) need to be joined to express "rank N of skill X gives Y."
- **Suggested tables:** `HeroSkill`, `HeroSubSkill`, `HeroSkillLevelTable`.

### Hero abilities
- **Path:** `DB/heroes_abilities/heroes_abilities_base/`, `_bonuses/`, `_infos/`
- **Count:** 22 base + 61 bonuses + 91 infos
- **Top fields:** `id, levels[]`; infos link `targetAbilitySid + deltaAbilitySid`.
- **Complexity:** M — same level-table shape as skills.
- **Suggested tables:** `HeroAbility`, `HeroAbilityLevel`, `HeroAbilityBonus`.

### Magic spells
- **Path:** `DB/magics/battle_<school>_magics*.json` (8 files)
- **Count:** ~16 per file × 8 ≈ 130 spells
- **Top fields:** `id, name, icon, magicTypeDescription, description[], excaptionInTooltip,
  bonusDescriptions[level], cost, schoolLevel, ...`
- **Complexity:** L — descriptions are arrays indexed by mastery rank, plus per-level
  bonus text. Heavy placeholder use; `Lang/args/magic.json` is the args side.
- **Suggested tables:** `Spell`, `SpellRank`, `SpellTranslation`.

### Artifacts (items)
- **Path:** `DB/items/items/*.json` (13 files by slot)
- **Count:** ~302 across all slots (12+12+12+10+72+15+37+13+72+6+13+16+14)
  - Includes 72 "magic scroll" + 72 "enchanted magic scroll" + 6 mythic boxes
  - Equipment: ~140 across head, armor, belt, boots, back, ring, hands, etc.
- **Top fields:** `id, slot_, rarity, itemSet, icon, name, description,
  upgradeDescription, narrativeDescription, goodsValue, costBase, costPerLevel,
  rewardForDestroy, maxLevel, bonuses[]`
- **Complexity:** L — bonuses use the same shape as hero specializations
  (`type, parameters, upgrade`); needs a placeholder pass for upgrade scaling
  text. Some bonuses are stat passives that should resolve via the same
  mechanic-name registry the units use.
- **Suggested tables:** `Item`, `ItemBonus`, `ItemTranslation`.

### Item sets
- **Path:** `DB/items/item_sets/item_sets.json`
- **Count:** 24
- **Top fields:** `id, name, itemsInSet[], bonuses[]`.
- **Complexity:** S — small, but worth a table because set bonuses are a
  search-frequent thing on wikis.

### Buildings
- **Path:** `DB/buildings_constructions/<map>_buildings_presets.json` (8 files)
  + `DB/buildings_settings/buildings_settings.json` (8 entries — looks like the
  per-faction master list)
- **Count:** 8 entries in master settings, each with a `buildings` array.
- **Top fields:** `id, buildings[]` — each building entry has its own substructure.
- **Complexity:** L — buildings have prereqs, costs, effects, faction-specific
  variants. Needs a closer look to figure out the shape; the per-map presets
  files might just be selection sets, not the source-of-truth.
- **Suggested tables:** `Building`, `BuildingCost`, `BuildingPrereq`.

### Factions (the 6 races)
- **Path:** `DB/fractions/<n>_<id>.json`
- **Count:** 6 (human/undead/dungeon/nature/demon/unfrozen)
- **Top fields:** `id, name, desc, narrativeDesc, icon, iconFractionLaws,
  biome, resourceName, fractionLawsLines[], cityNames[]`
- **Complexity:** S — flat record per faction.
- **Suggested table:** `Faction`.

### Faction laws (per-faction skill tree)
- **Path:** `DB/fractions_laws/fractions_laws_table_<faction>.json`
- **Count:** ~34 per faction × 6 = ~204 law nodes
- **Top fields:** `id, icon, name, desc, parametersPerLevel`
- **Complexity:** M — per-level scaling tables again. Args present in
  `Lang/args/factionLaws.json`.
- **Suggested tables:** `FactionLaw`, `FactionLawLevel`.

---

## 📋 Mid-priority targets

### Mounts
- **Path:** `DB/mounts/*.json` — 9 files, 1 entry each
- **Top fields:** `id, idlesNum` (and presumably more — check fully)
- **Complexity:** S, but tiny.
- **Suggested table:** `Mount`.

### Squads (starting army composition)
- **Path:** `DB/squads/**/*.json` (4204 files — but most are scenario-specific)
- **Top fields:** `id, squad, useOldSquads, rollChance, canBeMainGuard,
  baseSquad, dynamicSquad, randomSquad, tier, fraction`
- **Complexity:** L (volume) / S (per-record). Probably only emit a curated
  subset (the ones referenced from heroes' `startSquad`/`startSquadAlt`).
- **Suggested table:** `Squad` (filter to referenced ones).

### Buffs (the actual buff database)
- **Path:** `DB/buffs/*.json` — 19 files
  - `buffs_<school>_magics.json` — the spell-effect buffs
  - `units_buffs_<faction>.json` — the unit-ability buffs (already loaded by resolver)
  - `sub_skills_battle_hero_*.json` — hero-skill battle buffs
- **Count:** 411 (from BuffIndex)
- **Top fields:** `id, aiValue, icon, name_, description_, tags, isPositive,
  data.stats, addition, ...`
- **Complexity:** M — already loaded for resolver use; making them browsable
  on the wiki adds value (e.g. "Crossbowman Fine Bolts buff: +20% ranged").
- **Suggested table:** `Buff`.

### Sub-classes (hero specialization paths?)
- **Path:** `DB/heroes_sub_classes/sub_classes_<faction>.json`
- **Count:** 6 files
- **Complexity:** S/M — need to inspect entry shape; probably tied to hero classes.
- **Suggested table:** `HeroSubClass`.

### Field objects (battlefield obstacles, sentries, traps)
- **Path:** `DB/field_objects/{obstacles,sentries,traps}/*.json`
- **Count:** ~5–10 per category, 8 files total
- **Top fields:** `id, name, vfx, aiValue, isEffect, startTime, endTime, tags,
  lifetime, useHeroHpBonus, stats, onTimeoutMechanic`
- **Complexity:** M — cross-refs to buff effects.
- **Suggested table:** `FieldObject`.

### Adventure map objects
- **Path:** `DB/map/objects/*.json` (9 files)
  - `1_environments` (296), `2_animals`, `3_resources`, `4_interactables`,
    `6_artifacts` (artifact pickups, distinct from items), `7_spawns`, etc.
- **Plus:** `DB/objects_logic/{cities,chests,event_banks,garrisons,hires,...}/*.json`
  (227 files) — the *behavioral* logic for each map object.
- **Complexity:** L — two-table join (visual config + logic config).
- **Suggested tables:** `MapObject`, `MapObjectLogic`.

### Resources
- **Path:** `DB/res/resources_info.json` — 15 entries
- **Top fields:** `id, icon, name, desc, narrativeDesc`
- **Complexity:** S.
- **Suggested table:** `Resource`. (Already implicitly used by `RESOURCE_COLUMN`
  in the unit emitter.)

### Hero stats (the 6 primary stats)
- **Path:** `DB/stats/stats_info.json` — 6 entries
- **Top fields:** `id, icon, name, desc`
- **Complexity:** S.
- **Suggested table:** `HeroStat`.

### Rewards (encounter loot tables)
- **Path:** `DB/rewards/reward_infos.json` — 29 entries
- **Top fields:** `id, icon, name, desc`.
- **Complexity:** S.
- **Suggested table:** `Reward`.

### Market items (taverns / market post-game)
- **Path:** `DB/market_items/market_items.json` — 146 entries
- **Top fields:** `id, sid, costInGold, rollChance`
- **Complexity:** S — but cross-refs to other entity ids; render the linked thing.

### Hero action bonuses
- **Path:** `DB/hero_action_bonuses/*.json` — 3 files
- **Complexity:** M — needs inspection.
- **Suggested table:** `HeroActionBonus`.

### Astrology / weeks / months
- **Path:** `DB/astrology_exp/`, `DB/weeks/`
- **Count:** small (1 + 2 files)
- **Top fields:** `id, parameters` (months/weeks)
- **Complexity:** S — but flavor-relevant for the wiki (which week buffs what).
- **Suggested tables:** `Week`, `AstrologyEvent`.

### Notifications (event toast text)
- **Path:** `DB/notifications/*.json` — 11 files, ~50 entries total
- **Top fields:** `id, parameters`
- **Complexity:** S — useful for documenting in-game pop-ups.

### Side / global / hero buffs (skill-sourced)
- **Path:** `DB/heroes_buffs/`, `DB/side_buffs/`, `DB/logic_global_buffs/`,
  `DB/logic_side_buffs/`
- **Complexity:** M — overlapping with the unit buffs already in `BuffIndex`.
  Good to consolidate so they're cross-referenceable from skills/specs.

### Bonus upgrade units (alt-upgrade tier 7s?)
- **Path:** `DB/bonus_upgrade_units/bonus_upgrade_units.json`
- **Complexity:** S/M — inspect to confirm shape.

### Unit sets (creature synergies, e.g. cavalier+pegasus bonuses?)
- **Path:** `DB/unit_sets/*.json`
- **Count:** 14 entries
- **Top fields:** `id, units[], bonuses[]`
- **Complexity:** S.

---

## 📋 Lower-priority / niche

### Attack patterns (combat geometry)
- **Path:** `DB/attack_patterns/*.json` — 46 files
- **Each:** describes a hex-pattern (single, line, cone, mass, etc.)
- **Complexity:** M — useful as a `Data:AttackPattern` reference table that
  unit/spell pages can link to ("Hits: massive_x1_x100_x100").
- **Suggested table:** `AttackPattern`.

### Buildings ban/construction lists (per-map presets)
- **Path:** `DB/buildings_bans/*.json` (10 files), `DB/buildings_constructions/*.json` (11 files)
- **Complexity:** S — but specific to scenario presets; emit only if scenario pages exist.

### Arenas (gladiator arenas / tournaments)
- **Path:** `DB/arenas/*.json` — 548 files
- **Complexity:** XL by volume; probably only the master `arenas_info.json`
  is broadly useful.

### AI configs
- **Path:** `DB/ai_battle/`, `DB/ai_pick/`, `DB/ai_world/` (~85 files)
- **Complexity:** L. Probably skip — mostly not player-facing.

### Dialogs (campaign quest dialogue)
- **Path:** `DB/dialogs/dialogs/{custom_maps,M1,...,M10}/*.json` — 770 files
- **Complexity:** XL. Probably skip the bulk; might extract only character
  rosters / scene lists.

### Guides (in-game tutorial popups)
- **Path:** `DB/guides/*.json` — 71 files
- **Top fields:** `id, contentHeight, slides[]`
- **Complexity:** M — these are paginated tutorial slides; could become
  individual wiki "tip" pages.

### Other niche
- `DB/balance/`, `DB/luck_distributions/`, `DB/moral_distributions/`,
  `DB/heroes_exp/`, `DB/sides_exp/`, `DB/statistics/`, `DB/test/`, `DB/demo/` —
  tuning tables. Mostly internal; emit only if useful for wiki transparency.
- `DB/world_magic_cast_info/`, `DB/map_bonuses/` — small specialized configs.

---

## Cross-cutting infrastructure

### Bonus / parameters DSL
A *lot* of these entities (specializations, sub-skills, hero abilities,
faction laws, item bonuses, set bonuses, hero specializations) share the
same `bonuses[]` shape:
```json
{ "type": "heroStat", "parameters": ["spellPower", "12"], "upgrade": {...} }
```
**Worth building once**: a renderer that maps `(type, parameters)` to readable
wikitext (`+12 Spell Power`). The interpreter framework can be reused — these
parameters point at the same stat-name registry the units use. This pays back
across at least 8 entity types.

### Level / rank tables
`parametersPerLevel`, `levels[]`, `bonusDescriptions[level]`, and the
`skills_by_level_tables/` files all encode the same rank-scaling pattern.
A shared `LevelTable` component would deduplicate the per-rank emit logic.

### L10n args coverage
The `Lang/args/*.json` index has entries for all of: `artifacts`, `magic`,
`magic_buff`, `heroSkills`, `heroInfo`, `factionLaws`, `cities`,
`mapObjects`, `unitsAbility`, `unitsBuff`, `customMaps`, `dialogues`,
`tutorial`, `ui`, `menu`. The resolver already handles all of them — every
new emitter category gets placeholder resolution for free.

---

## Recommended sequence

1. **Heroes + specializations + sub-classes** — most-browsed, clean shape, big
   payoff. Reuses the existing resolver/L10n pipeline directly.
2. **Hero skills + sub-skills + hero abilities** — needs the level-table
   helper, but builds the foundation for everything that uses ranked bonuses.
3. **Spells (magic)** — heavy resolver use; tests the framework on a different
   entity family.
4. **Items + item sets + faction laws** — bonus DSL renderer pays off here,
   plus mounts and item slots for completeness.
5. **Buffs (consolidated table)** — already loaded for resolver use; making
   them queryable from the wiki adds depth.
6. **Buildings** — needs a closer survey to nail the schema.
7. **Adventure-map objects + their logic** — the open-world data layer.
8. **Field objects, attack patterns, mounts, resources, stats, rewards** —
   small reference tables that round out cross-linking.
9. **Niche/skip:** AI, dialogs, arenas, scenario presets — emit only if a
   user-facing wiki need surfaces.

---

## Open questions

- Are scenario/campaign-specific entities (heroes/squads/buildings under
  `campaign`, `M1`–`M10`, `Tutorial`, `custom_maps`) worth their own pages,
  or do they belong in scenario-page subsections?
- For **squads** (4204 files), do we want every starting roster as a row,
  or only the ones referenced from a hero's `startSquad`?
- Should building-presets-per-map be modeled as scenarios (`Data:Scenario/M2`)
  rather than as building data?
