# Architectural Decisions

Locked decisions captured at scaffolding time. Updates as design evolves should append, not overwrite — keep the history.

## D-001 — Language: Python

**Date:** 2026-05-01
**Status:** Locked.

We're shipping a public-release wiki bot. The Python ecosystem (pywikibot, mwclient, pydantic) is the canonical fit, lower-friction for casual contributors, and avoids any GPL-3 entanglement with [OldenEraExplorer](https://github.com/laszlo-gilanyi/OldenEraExplorer).

**Considered and rejected:**
- C# / .NET — would let us crib OEE's `Domain` entities and `Localization/Scripting` resolver wholesale, but contaminates our license (OEE is GPL-3.0) and shrinks the contributor pool. The "C# isn't a scripting language" objection isn't load-bearing for a tool that's read-JSON → emit-wikitext → POST-API.
- Node/TypeScript — `mwn` is solid, but Python's pydantic data-modeling story is decisively better for this shape of work.

## D-002 — License: Apache 2.0

**Date:** 2026-05-01
**Status:** Locked.

Permissive enough for community uptake, with the patent-grant clause that MIT lacks (matters if upstream Olden Era devs ever contribute). One-way compatible with GPL-3 — OEE devs can fold our code into theirs; we cannot pull theirs into ours. Acceptable.

## D-003 — Placeholder resolver: not in v1

**Date:** 2026-05-01
**Status:** Locked.

OEE re-implements the game's script engine to resolve `{0}`/`{1}`/etc. placeholders in description text. We don't need this for Cargo data: the structured fields (stats, costs, IDs, tiers) carry no placeholders, and translatable description templates can be stored in Cargo as raw `{0}`-bearing strings. Display layer or human authors handle resolution.

If resolution becomes critical for some category later, two paths:
1. Shell out to OEE's CLI as a subprocess (separate-process aggregation, GPL-safe).
2. Port `Localization/Scripting/` (~2k LOC) to Python.

## D-004 — Wiki access: existing wiki, no bot account yet

**Date:** 2026-05-01
**Status:** Locked.

Target: `https://oldenera.wiki.gg/` (placeholder until bot account exists). Until then the uploader writes to local files only; the upload phase scaffold is stubbed.

## D-005 — Page granularity: one page per entity

**Date:** 2026-05-01
**Status:** Locked.

Each entity gets one wiki page (e.g. `Data:Unit/Angel`) hosting all of its data — invariant `#cargo_store` row plus all 16 localization rows. Atomic per-entity update; one page edit = one consistent transaction.

**Considered and rejected:**
- Subpages per language (`Data:Unit/Angel/en`, `…/ru`) — clean for translator workflows, but multiplies page count by ~16 and complicates atomic updates.
- Mega-pages per category — too large, edit-conflict prone.

## D-006 — i18n schema: single global Localization table

**Date:** 2026-05-01
**Status:** Locked.

The source data is already shaped this way: every L10n file under `Core/Lang/<lang>/texts/*.json` is a flat `(sid, text)` mapping. Empirical: 12,497 SIDs in English, exact parity across all 14 languages (Russian off by 1 — typo, not a translation gap).

**Cargo schema:**
- `Localization(sid String, language String, text Text, source_kind String)` — one row per (sid, language). ~175k rows total.
- Per-entity invariant tables (`Unit`, `Spell`, `Hero`, …) reference SIDs in dedicated columns (e.g. `Unit.name_sid`).
- Display-side queries join: `tables=Unit,Localization | join on=Unit.name_sid=Localization.sid | where=Localization.language='en'`.

**Where rows live (page sense):**
- For SIDs an entity "owns", the L10n rows are stored on that entity's page (`Data:Unit/Angel` includes its 14× SID rows for `angel_name`, `angel_desc`, `angel_class_*`, plus its abilities' SIDs).
- For orphan SIDs (UI strings, biome names, etc. that no specific entity claims), they go to bucket pages: `Data:Localization/UI`, `Data:Localization/Misc`, etc.

**SID ownership rule:** discover from JSON (walk for `*Sid`/`*_sid` fields and explicit SID slots) + supplement with convention (`<id>_name`, `<id>_desc`) + log orphans for the bucket pages.

## D-007 — Languages: all 16 from v1

**Date:** 2026-05-01 (originally said 14; corrected to 16 on 2026-05-01 after extracting against real data)
**Status:** Locked.

Given source parity is essentially perfect (12,497 SIDs in every language with no gaps), ingesting all 16 from day one costs us bytes, not architecture. Languages observed in the 2026-04-30 corpus: BRportugese, czech, english, french, german, hungarian, italian, japanese, korean, polish, russian, spanish, turkish, ukrainian, zhCN, zhTW.

OEE's README claims 14; the data ships 16 (zhCN and zhTW are distinct, and BRportugese is its own dir). Trusting empirics over secondary claims.

## D-008 — Diff scope: everything in JSON

**Date:** 2026-05-01
**Status:** Locked.

Stat changes, ability changes, cost changes, English text changes, non-English translation changes, asset references. Every field reachable from the canonical record types is in scope for the diff engine. We can decide later how to *render* translation churn in patch notes (probably summarized rather than enumerated), but it's all detected.

## D-009 — Tooling: modern stack

**Date:** 2026-05-01
**Status:** Locked.

- Runtime: pydantic v2, mwclient, typer, rich
- Dev: ruff, mypy strict, pytest
- Env: stdlib `venv` + `pip` (no uv required; uv works fine if developer prefers)
- Python: 3.10+ (see horizon note below)

The diff is hand-rolled, not `deepdiff`. Wikitext is f-string-rendered, not jinja. Both decisions are about *quality of output*, not avoiding deps for their own sake.

**Python 3.10 horizon note (2026-05-01):** Floor was originally 3.11 but lowered to 3.10 to match the assistant's sandbox runtime. CPython 3.10 reaches EOL October 2026; revisit and bump the floor to 3.11+ when the sandbox upgrades or before the project's first stable release, whichever comes first. The only feature this floor change cost us was `enum.StrEnum` (replaced with `class Faction(str, Enum)` — equivalent for our uses).

## D-010 — First entity end-to-end: Units

**Date:** 2026-05-01
**Status:** Locked.

Units are the richest category (stats, abilities, passives, costs, upgrades, faction, biome, AI tags). Driving Units end-to-end first will surface the architecture's edge cases. Other categories follow once the framework settles.

## D-011 — OEE is a peer reference, not authoritative

**Date:** 2026-05-01
**Status:** Locked.

OldenEraExplorer was built against the demo and only partially updated for the released game (per ketura). When OEE's data model and the source JSON disagree, the **JSON is ground truth, OEE is a hint**.

This came up concretely twice already:

* OEE's `AbilityRef` type carries `NameSid` / `DescriptionSid` fields that don't exist in source unit JSON. We initially modeled abilities the same way and it was wrong. (Resolved by separating JSON logic blocks from L10n-discovered SID slots — see D-012.)
* Unit-level descriptions were claimed to live under `<id>_description`; they actually live under `<id>_narrativeDescription`. OEE may not have updated for this either.

**Practical implication:** when designing extractor logic for a new entity kind, sample real source data first, *then* glance at OEE for confirmation/contrast. Don't start from OEE's model and back-fit the JSON to it.

## D-012 — Unit named-ability SIDs: discovered from L10n, not from JSON

**Date:** 2026-05-01
**Status:** SUPERSEDED by D-015. We now read ``Core/DB/units/units_views/<faction>/<id>_v.json`` directly — it lists the unit's named abilities/passives explicitly with name and description SIDs. The original heuristics (regex + ordinal discovery + JSON-block-to-SID correlation) are gone.

The source unit JSON describes abilities/passives as logic graphs with no `nameSid` field. The L10n corpus contains SIDs of the form `<id>_(ability|passive|buff|debuff|selfbuff)_<N>_(name|description)` — but the ordinals don't map cleanly to JSON list indices: angel has 4 JSON passives but only 2 named-passive SIDs, because the JSON list mixes player-visible passives with internal mechanic-implementation flags (`data.disablers`, immunity bundles).

**Resolution:** maintain two parallel structures on each unit, with no claimed 1:1 mapping:

1. **`passives` / `abilities`** — JSON logic blocks, opaque, preserved verbatim. Drives diffs of mechanic changes.
2. **`named_ability_slots`** — discovered from the L10n corpus by walking SIDs matching the convention. Each slot is `(kind, ordinal, name_sid, description_sid)`. Drives L10n storage and gives the display layer a clean list of named ability slots to query.

The JSON-block-to-SID-ordinal reconciliation is deferred to the future Ability category, where we can fingerprint structurally across all units. May or may not be solvable without help from the OE devs.

## D-013 — Wiki output goes through helper templates, not raw Cargo syntax

**Date:** 2026-05-01
**Status:** Locked. Per-entity-kind template hierarchy design is an ongoing effort.

`#cargo_store` and `#cargo_declare` syntax is hostile to non-technical wiki editors. The bot emits data through a layer of helper templates instead. Pattern, per entity kind:

**Master template** (e.g. `Template:Unit`) owns the schema. It declares `#cargo_declare` for the entity's Cargo table, accepts every possible field as a named parameter with appropriate optional-default handling, and internally calls `#cargo_store` to write the row. Editors who invoke `{{Unit | id=angel | hp=225 | ...}}` never see Cargo syntax.

**Subset templates** narrow the parameter list for common archetypes — e.g. `Template:RangedUnit`, `Template:MeleeUnit`, `Template:MidRangeUnit`, or `Template:BaseUnit` / `Template:UpgradedUnit`. A subset template fills in the master template's parameters with sensible defaults for fields the archetype doesn't use, so editors see only the parameters that actually matter for their case. Subset clusters are designed empirically per entity kind by clustering real records.

**Emitter behavior:**

* For each canonical record, pick the *most specific* template that fits. If a unit qualifies as a `RangedUnit`, emit `{{RangedUnit | ...}}`, not `{{Unit | ...}}`.
* Output order is deterministic and stable: a fixed field order within each template invocation, and a fixed template order on multi-store data pages. This makes "did this page change?" trivially diffable both for the bot's own diff engine and for human reviewers comparing wiki revision history.
* Data pages (`Data:Unit/<id>` etc.) are **bot-owned**. Discrepancies between wiki state and source JSON should be fixed by updating the extractor or the emitter, not by editing the data page by hand. Display articles that query Cargo are the human-edited surface.

**Implications for our codebase:**

1. The emitter needs a per-entity-kind *template registry*: a Python data structure mapping template name → ordered parameter list → mapping rule from canonical record fields to template parameters.
2. The emitter needs a *classifier*: given a canonical record, return the most specific template whose preconditions it satisfies. Preconditions are predicates over the record (e.g. "has only ranged attack" → `RangedUnit`).
3. Template definitions on the wiki side are out of scope for this project — someone else writes the wikitext for `Template:Unit` etc. We design the schema (field names, types, defaults) and produce invocations.

**Parameter style:** named parameters everywhere. ``{{Unit | id=angel | hp=225 | ...}}``, never positional. Eliminates ordering as a correctness concern (the bot still emits in a stable order for diff readability, but ordering becomes cosmetic, not load-bearing).

**Sparseness:** the emitter omits fields whose source JSON didn't define them. Empty/null values are not emitted. Reasoning: parameter lists for the master template will be large; sparse output keeps real-world data pages readable, and the diff engine handles "added line" vs "modified line" identically — there's no diff-quality advantage to verbose output. Concretely, "default" means *absent in source*, not *equal to a Python default value*; numeric stats like ``morale=0`` are still emitted because the source set them, while truly absent fields stay out.

**Cross-reference:** D-006 describes data pages as containing ``#cargo_store`` rows; D-013 supersedes that surface description (the wikitext is template invocations now), but the underlying Cargo schema D-006 specifies is unchanged — the templates ultimately call ``#cargo_store`` internally.

**Open per-entity work** (will accumulate as D-013-N as we tackle them):

* D-013-Unit (TBD) — full Unit field set, subset template clusters, classifier predicates.
* D-013-Spell, D-013-Hero, D-013-Artifact, etc. — same exercise per category.

## D-014 — Upgraded units inherit named ability slots from their base

**Date:** 2026-05-01
**Status:** SUPERSEDED by D-015. Each upgrade variant has its own views file with its own explicit ability/passive list. There is no inheritance — each variant emits exactly what its views file enumerates. The empty-page-on-upgrade behavior described below was an artifact of the old SID-prefix-matching scheme.

In Olden Era, an upgraded unit (``phoenix_upg``, ``angel_upg``, etc.) only
redefines ``<id>_name`` and ``<id>_narrativeDescription`` in the L10n corpus.
Its abilities and passives use the **base unit's** named-slot SIDs
(``phoenix_passive_1_name``, not ``phoenix_upg_passive_1_name``). Empirically
confirmed against ``phoenix``/``phoenix_upg``/``phoenix_upg_alt``: 7 / 0 / 0
named slots discovered respectively. Same holds for other unit chains.

**Implications:**

1. **Empty `UnitNamedSlot` and `UnitNamedSlotTranslation` tables on upgrade
   pages are correct,** not a bug to fix. Don't try to populate them from
   the base — that would duplicate data and require synchronization on
   patches.
2. **Display layer queries follow the ``base_sid`` chain.** When rendering
   an upgraded unit's ability list, the template walks
   ``Unit.base_sid -> Unit.base_sid -> ...`` until ``base_sid`` is empty,
   then queries `UnitNamedSlot` / `UnitNamedSlotTranslation` for whichever
   ancestor owns the slots. Cargo's recursive query support is limited;
   may need template-level recursion or a flattened resolved view.
3. **Diff engine awareness:** when a base unit's named-slot text changes,
   the upgrade variants are *visually* affected even though their own rows
   don't change. The patch-notes generator should surface "ability
   description changed on `phoenix`, affects `phoenix_upg` and
   `phoenix_upg_alt`" — that's a reporting-layer concern, not a schema one.

**Side observation (not a decision, just noted):** ``upgradeSid`` in source
forms a chain (``phoenix.upgradeSid = phoenix_upg``,
``phoenix_upg.upgradeSid = phoenix_upg_alt``) rather than a binary fork from
the base. The game presents these as alternative upgrade choices in UI, so
the chain is likely vestigial source data; we faithfully store what's there
and let display decide.

## D-015 — Views file is the authoritative SID source per unit

**Date:** 2026-05-02
**Status:** Locked. Supersedes D-012 and D-014.

Each unit has a ``Core/DB/units/units_views/<faction>/<id>_v.json`` file that
explicitly lists its named abilities and passives:

```json
"abilities": [
    {"name": "godslayer_ability_1_name", "description": "godslayer_ability_1_description", ...}
],
"passives": [
    {"name": "base_passive_melee_attack_name", ...},
    {"name": "demon_passive_1_name", ...},
    {"name": "godslayer_passive_1_name", "description": "godslayer_passive_1_description_upg", ...}
]
```

Each entry has explicit ``name`` and ``description`` SIDs — no heuristic,
no ordinal discovery, no positional fallback. Variant-specific descriptions
(``_description_upg``, ``_description_upg_alt``) are pre-resolved by the
views file itself; we just take the SID and look up the L10n entry.

**Practical implication:** the entire heuristic stack (match/patterns,
match/registry, alt-upgrade ordinal jumps, variant SID fallback, family
inheritance) is dead code. Removed.

The views file is the *display layer* — what the player sees. The logic
file is still the source of truth for stats, mechanics, and the diff
engine. We use both, with views authoritative for which abilities
exist and logic authoritative for what they do.

## D-016 — Base and faction passives are NOT stored on each unit's page

**Date:** 2026-05-02
**Status:** Locked.

The views file's passive/ability lists include three flavors of SIDs:

* **Unit-specific** (``godslayer_passive_1_*``, ``angel_ability_1_*``):
  STORED on the unit's page as full ``UnitAbility`` rows + translation
  rows.
* **Universal base passives** (``base_passive_melee_attack_*``,
  ``base_passive_flyer_*``, ``base_passive_staunch_<rank>_*``): DROPPED.
  Recovered by the wiki display layer from unit attributes (creature_type,
  move_type, attack_penetration, etc.). Stored once in a shared
  ``Data:BasePassive`` table — emission is Phase 2 work.
* **Faction-shared passives** (``demon_passive_1_*``, ``human_passive_2_*``):
  DROPPED. Recovered via the unit's ``faction`` enum. Shared
  ``Data:FactionPassive`` table — also Phase 2.

Filtering rule: drop any name SID whose prefix is ``base_`` or matches a
known faction id (one of: human, undead, dungeon, nature, demon, unfrozen,
neutral). Everything else is unit-specific.

**Why drop them:** these passives are repeated across dozens of units. A
demon faction passive applies to ~20 demon units; storing 20 copies of the
same name + 16 translations is pure duplication. The shared tables hold
each definition once.

## D-017 — Audit reports JSON content not represented in views

**Date:** 2026-05-02
**Status:** Locked. Replaces the heuristic-driven audit from D-013/early audit work.

The audit's job is now narrow: **compare the unit's logic JSON against its
views file and surface anything in the logic that isn't reflected in the
views.** Examples:

* A passive block in ``logic.passives[]`` whose mechanic doesn't appear in
  ``views.passives[]`` (could be internal-only, or could be a missing views
  entry — worth flagging).
* A stat field in ``logic.stats`` (e.g. ``outDamageIfLevelAbove``) that no
  named view passive corresponds to.
* Any ability in ``logic.abilities[]`` that has no matching ``views.abilities[]``
  entry.

The audit does not drive emission anymore; it's purely a sanity-check
report (``out/audit.json``). Maintainers review it after each patch to
catch new patterns Unfrozen ships that we don't yet handle.

## D-018 — Patch-cycle pipeline (diff + upload)

**Date:** 2026-05-03
**Status:** Locked.

The patch-cycle command takes a new core-JSON dump plus the previous patch's
emitted wiki output and produces:

1. **Fresh emit** of the new patch's wiki pages (reuses the existing emit pipeline).
2. **Per-page wiki diff** for every page that changed between previous and new
   emit. Stored locally as drilldown files (`<out>/diff/changed_pages/<id>.diff`),
   not uploaded.
3. **Deep JSON diff** between the two core dumps, written to
   `<out>/diff/json_diff.txt`. Operator-only artifact for data miners; never
   uploaded. The wiki-text diff is the right filter for "did the player-visible
   thing change"; the JSON dump is for forensic debugging.
4. **Patch article** at `Data:Patches/<date>` listing all changed data pages
   as wiki links, grouped by entity type.
5. **Operator summary** (`<out>/diff/summary.md`) — table of changed pages,
   line-count deltas, etc.

Default mode is **dry-run**: artifacts are written, nothing is uploaded.
`--force-upload` actually pushes the changed wiki pages and the patch article.

**Previous output is supplied by the user** as a folder path. The bot does not
re-emit the old patch. (If they want a fresh old emit, they run `emit-all-units`
on the old patch dump first.) This keeps the cycle command's I/O explicit and
caching-free.

**Wiki credentials** live in a project-local `artificer.toml` (gitignored), not
env vars. Keeps multi-environment setups straightforward.

## D-020 — Unused-unit detection: english-name signal only

**Date:** 2026-05-04
**Status:** Locked.

`Unit.unused = True` is set during enrichment when the unit's primary
`name_sid` has no English entry in the localization corpus. In the
2026-05-03 corpus that catches exactly 5 deprecated units: `dragon`,
`dragon_upg_alt`, `avatar_nature`, `avatar_unfrozen`, `peasant_normal`.
The flag emits as `unused = yes` in the wiki row, omitted otherwise so
queries can filter `WHERE unused != "yes"` without weighing down the
common case.

**Why only this signal, no manual override list:**
The community has identified additional units the game doesn't actively
use (jaw family, lava_larva, trick_demon_upg/_upg_alt) but their data
layer is fully populated — full English name, description, AI archetype,
gold cost, abilities. The data was kept after model reworks: jaw was a
zerg-like creature reworked into a scorpion; trick_demon's base form was
rebranded as the neutral `gnat`. The unit data is still active for the
gameplay system; only the visual assets were swapped.

There is no JSON-side signal that distinguishes "data-active unit with
swapped model" from "data-active unit with original model", so we don't
attempt to flag those as unused. False-negatives there are the right
tradeoff — claiming a unit is unused when it might be referenced by
gameplay paths we don't see is worse than missing a few cosmetic
deprecations.

**Future work (deferred): unused-asset detection.** A separate pipeline
that inspects Unity asset bundles could find icons/meshes that no JSON
references, or vice versa. Would require AssetRipper-style asset
extraction (OEE bundles this). Out of scope for the current data layer.

## D-021 — UnitAttack: shared reference tables + one per-unit fat row

**Date:** 2026-05-04
**Status:** PARTIALLY SUPERSEDED by D-024. The `AttackArchetype` /
`AttackArchetypeTranslation` halves of this decision migrated into
the unified `Entry` table as `type=attack_archetype` rows; the seed
values and the JSON-enum naming flip (`range` → `reach`) remain
authoritative. The `UnitAttack` and `AttackPassive` halves are
**unchanged** and remain in their own dedicated tables (they have
columns beyond the Entry name+desc+i18n shape, so they don't fit
the catch-all rule).

Empirical analysis of the 2026-05-03 patch found 376 attack entries
across 152 units boil down to a small fixed structure plus a few dials.
The split:

1. **`AttackArchetype`** — hand-curated reference table, **exactly 3
   rows** (`melee`, `ranged`, `reach`). Each row carries the canned
   per-attack-type passive name and description that every unit's
   tooltip inherits ("Melee Attack — Can only attack adjacent enemies.
   Provokes counterattacks."). Names align with the L10n family
   (`base_passive_melee_attack_*`, `base_passive_ranged_attack_*`,
   `base_passive_remote_attack_*`). Note: JSON `attackType_=range` =
   player-facing "Long Reach" = bot enum `reach`. Translations live in
   `AttackArchetypeTranslation`.

2. **`UnitAttack`** — **one row per unit** (revised; was per-slot).
   All four attack categories — `default`, `counter`, `alt`, `alt2` —
   collapse into a single wide row with slot-prefixed fields
   (`default_attack_type`, `counter_stat_dmg_mult`, `alt_passive`, etc.).
   Each slot has its own role-aware defaults; the bot sparse-emits only
   fields where the unit deviates.

3. **`AttackPassive`** (shared, ~9 rows) — Sweeping Strike, Whirlwind,
   Dragonbreath, Cone, Area Strike + falloff variants. These appear in
   player tooltips as passives but exist purely as a side-effect of the
   unit's `attack_pattern_sid`. Each `UnitAttack` slot references one
   via `<slot>_passive` (e.g. `default_passive=sweeping_strike`). The
   wiki layer joins on `attack_passive_id` to render the player-facing
   name and description. **Pattern-passives are no longer synthesized
   as `UnitAbility` rows** — that duplicated the same name/desc on
   every Hydra-and-friends page. Reference > duplication.

4. **`shared/` subfolder** under `docs/cargo/` collects the
   reference-data tables (`AttackArchetype`, `AttackArchetypeTranslation`,
   `AttackPassive`, `AttackPassiveTranslation`). These are hand-curated
   wiki seed data, not patch-extracted; segregating them keeps the
   per-patch table list focused.

**Naming flip:** the bot's enum uses `melee` / `ranged` / `reach`,
matching player-facing terminology. JSON values map: `melee → melee`,
`shoot → ranged`, `range → reach`. The L10n SID for "reach" lives
under `base_passive_remote_attack_*` — the data-side name there is
"remote", but the wiki uses "Long Reach" / `reach` consistently.

**Per-slot defaults** live on each slot prefix (`default_*` defaults to
1.0× / triggers counter; `counter_*` to 1.0× / no counter; `alt_*` and
`alt2_*` to 0.5× / no counter). Bot suppresses fields that match the
slot's default. A typical Crossbowman row emits ~8 fields total across
all four slots; a basic Peasant emits ~4.

**Explicitly out of scope:** projectile range/falloff/ammo
(`shootRange`, `shootThreshold`, `shootRedCount`, `shootDmgBuff`) and
`target_mechanics` arrays. Stable enough that freeform wiki copy on the
rare deviating unit is cheaper than schema weight.

**Why not fold attacks into UnitAbility:** attacks and abilities share
the underlying combat engine (identical `damageDealer` shape), but the
player-facing distinction is real — "what this unit does as its baseline
hit" vs. "what special things it can do." Separate tables match how the
wiki renders them and how readers think about them.

**Pattern_sid mapping is hand-curated, not auto-derived.** Several
mappings are non-trivial — `attack_massive_x1_x100_x100_with_dalay_*`
maps to Cone Strike (`base_passive_strike_tri_reach_1_*`) despite no
shared token. Confirmed via Black Dragon's `black_dragon_ability_1`
description ("Performs a Cone Strike"). Unconfirmed mappings (a handful
of `_x2` and `swirl_xN` variants) are flagged with `# TODO` placeholders
in code; the bot synthesizes a clearly-named placeholder passive
(`pattern_passive_TODO_<pattern_sid>`) and logs a warning so the
mismatch is visible in wiki output and easy to resolve later.

**Future work:** Fighting Style abilities (Hydra: Whirlwind Strike;
Medusa: Arrow Barrage; Black Dragon: Sulfurous Assault; etc.) are alt
attacks the L10n names with unit-specific SIDs `<unit>_ability_<N>`,
sharing the SID namespace with entries in the JSON `abilities[]` array.
The current ability extraction needs to learn that an alt-attack on
some units owns the next-available `<unit>_ability_<N>` slot. Separate
decision when we tackle that.

**Piercing Strike is a stat-passive, not an attack-pattern.** The L10n
family `base_passive_strike_pierce_<rank>_*` exists, but no unit has an
`attack_pierce_*` pattern_sid. "Piercing Strike I/II/III" is the
player-facing name for the `attackPen` stat passive (rank derives from
the value: 0.3 → I, 0.4 → II, 0.5 → III). The current `stat_passive`
synthesis with the placeholder name "Unyielding" should be updated to
use the `pierce` family.

## D-022 — Movement reference table: 2 rows, hand-curated

**Date:** 2026-05-04
**Status:** SUPERSEDED by D-024. The schema and seed values described
here are unchanged in spirit — they migrated wholesale into the
unified `Entry` table as `type=movement` rows. The naming-flip note
(`teleport` → "Blink") and the eldritch_flyer divergence note remain
authoritative; only the table structure is replaced.

Movement type is a small enum carried by `stats.moveType` in each
unit's logic file. Empirical analysis of the 2026-05-03 patch found
exactly three values across 149 units: `fly` (32), `teleport` (17), and
absent (100, implicit walker). Same shape as D-021's `AttackArchetype`
collapse — small fixed enum, shared player-facing name/description text
in the L10n corpus, currently flowing through `shared_abilities` as
duplicated SID tokens on every flyer/teleporter unit page.

**Resolution:** add `Movement` + `MovementTranslation` reference tables
under `docs/cargo/shared/`, mirroring the `AttackArchetype` pair.

**Schema:** exactly **2 rows** — `fly` and `teleport`. Each row carries
the canned passive name/description from the L10n family.

| `move_type` | `name_sid` | `desc_sid` |
| --- | --- | --- |
| `fly` | `base_passive_flyer_name` | `base_passive_flyer_description` |
| `teleport` | `base_passive_blink_name` | `base_passive_blink_description` |

**Walkers are encoded as absence**, not as a row. Units without
`move_type` set on their `Unit` row are walkers — matches how the
source data treats them (`stats.moveType` is omitted on walkers; there
is no `base_passive_walker_*` SID family). Sparse, consistent with the
"omit fields whose source JSON didn't define them" rule from D-013.

**Considered and rejected:**

- **3 rows including `walk` with hand-curated text** — would have
  given consistent table coverage, but introduced a synthesized row
  with no source-data analog. Sparse-by-default wins on principle
  (D-013) and on diff cleanliness (the walker row would never change
  upstream, so storing it adds noise to no benefit).

**Naming flip:** JSON enum `teleport` → L10n family token `blink`.
Same pattern as D-021's `range` → `reach`. The bot keeps the JSON
value through to `Unit.move_type` (`teleport`, not `blink`); the
display name "Blink" lives on the `Movement` reference row.

**Divergence (3 units): `eldritch_flyer` family.** Has
`stats.moveType=teleport` mechanically but lists `base_passive_flyer_name`
in `views.passives[]`, so the in-game tooltip shows "Flying" while the
mechanical move type is teleport. Per D-011 (JSON is ground truth), we
trust `stats.moveType`: `Unit.move_type=teleport` for these units. The
audit can flag the divergence so wiki readers know the views display
differs from the mechanical truth.

**`shared_abilities` not changed.** The `base_passive_flyer_name` /
`base_passive_blink_name` SIDs continue to flow into `Unit.shared_abilities`
via the existing views-passive path. Slight redundancy with the new
reference table, but safer than risking template-side breakage in the
existing wiki layer. Future cleanup if/when shared_abilities gets
restructured.

**Pattern reuse:** identical to D-021's AttackArchetype/AttackPassive
work. Same code path (`MOVEMENT_SEEDS` dict + `emit_movement_page`
function in `emit/unit.py`), same output shape (`Data:Movement/<move_type>`
pages under `data/movement/`), same translation discovery (full
16-language coverage confirmed in 2026-05-03 corpus).

## D-023 — CreatureType reference table: 7 rows, hand-curated

**Date:** 2026-05-04
**Status:** SUPERSEDED by D-024. The schema and seed values described
here are unchanged in spirit — they migrated wholesale into the
unified `Entry` table as `type=creature_type` rows. The naming-flip
note (`demon` → "Hive Spawn"), the missing-views-baseClass observation
for `avatar`/`halfling`, and the placeholder-resolution explanation
all remain authoritative; only the table structure is replaced.

Creature class is a small enum carried indirectly by each unit's
`<type>_immunities` passive tag. The bot's existing extractor
(`_classify_passive_attributes` in `extract/unit.py`) walks those tags,
strips the `_immunities` suffix, and stashes the result on
`Unit.creature_type`. Empirical analysis of the 2026-05-03 patch found
exactly seven values across all 152 units: `living` (44),
`magic_creature` (32), `undead` (23), `demon` (23), `embodiment` (20),
`dragon` (8), `construct` (2). All seven have full English text and
descriptions in the L10n corpus.

Same shape as D-022's `Movement` collapse — small fixed enum, shared
player-facing name/description text in the L10n corpus, currently
flowing through the `Unit.creature_type` column with no canonical
display label or description anywhere on the wiki side.

**Resolution:** add `CreatureType` + `CreatureTypeTranslation`
reference tables under `docs/cargo/shared/`, mirroring the `Movement`
pair.

**Schema:** exactly **7 rows** — `living`, `undead`, `demon`,
`magic_creature`, `embodiment`, `dragon`, `construct`. Each row
carries the canned class name/description from the L10n family.

| `creature_type` | `display_name` | `name_sid` | `desc_sid` |
| --- | --- | --- | --- |
| `living` | Living | `base_class_living` | `base_class_living_description` |
| `undead` | Undead | `base_class_undead` | `base_class_undead_description` |
| `demon` | Hive Spawn | `base_class_demon` | `base_class_demon_description` |
| `magic_creature` | Magic Creature | `base_class_magic_creature` | `base_class_magic_creature_description` |
| `embodiment` | Embodiment | `base_class_embodiment` | `base_class_embodiment_description` |
| `dragon` | Dragon | `base_class_dragon` | `base_class_dragon_description` |
| `construct` | Construct | `base_class_construct` | `base_class_construct_description` |

**Naming flip:** the `demon` enum displays as **"Hive Spawn"** in the
in-game class panel (lore reframe of OE's demon faction as a
hivemind). Same kind of JSON-vs-display flip as `range`→`reach`
(D-021) and `teleport`→`blink` (D-022). The bot keeps `demon` as the
join key everywhere; the "Hive Spawn" label lives on this row's
`display_name`.

**SID family**: `base_class_*` (NOT `base_passive_*` — distinguishes
class labels from gameplay passives). Description text contains
`{0}`/`{1}`/`{2}`/`{3}` placeholders for morale and luck range
bounds. These are resolved by the existing pipeline at extract time:
`Lang/args/unitsAbility.json` maps each `base_class_*_description` SID
to a list of arg SIDs (e.g. `base_passive_luck_moral_5`), each of
which `units.script` resolves to a literal via `Text(return, "5")`.
The args are class-wide constants, not per-unit values — so the
description ships fully substituted ("Morale range: –5 to 5.") on the
reference table row, no per-unit context required.

**Missing-data note:** four units in the 2026-05-03 patch have a
derived `creature_type` (immunity tags present) but no
`views.baseClass` entry — `avatar`, `avatar_nature`, `avatar_unfrozen`,
`halfling`. Three are unused per D-020. This is *not* a "two-signal
disagreement" case like the eldritch_flyer movement divergence
(D-022) — the immunity tags are authoritative; the views file simply
doesn't render a class label for these units. Wiki layer joins on
`Unit.creature_type` and surfaces the canonical class name regardless.

**Pattern reuse:** identical to D-022's Movement work. Same code path
(`CREATURE_TYPE_SEEDS` dict + `emit_creature_type_page` function in
`emit/unit.py`), same output shape (`Data:CreatureType/<creature_type>`
pages under `data/creature_types/`), same translation discovery (full
16-language coverage confirmed in 2026-05-03 corpus).

## D-024 — Unified `Entry` catch-all table; supersedes D-022, D-023, and AttackArchetype halves of D-021

**Date:** 2026-05-04
**Status:** Locked.

`AttackArchetype`, `Movement`, and `CreatureType` (each with its own
`<Entity>Translation` sibling) were three pairs of tables of
**identical shape**: an enum primary key, English `display_name` +
`description`, source `name_sid` + `desc_sid`, and 15 per-language
`<lang>_name` / `<lang>_desc` columns. Six tables encoding the same
abstraction. Adding the next domain (e.g. faction, biome, resource
category) would have repeated the pattern again.

**Resolution:** collapse them into one table called `Entry`, keyed
on `(type, subtype)`. Translations merge into the same row as
inline per-language columns — no separate translation table.

```mediawiki
{{#cargo_declare:_table=Entry
| type = String         <- attack_archetype, movement, creature_type, ...
| subtype = String      <- melee, fly, undead, ...
| display_name = String
| description = Wikitext
| icon = String         <- optional
| name_sid = String
| desc_sid = String
| pt_br_name = String
| pt_br_desc = Wikitext
| ...                   <- 15 langs total, name + desc each
}}
```

**Page layout:** per-domain top-level pages
(`Data:Movement/<subtype>`, `Data:CreatureType/<subtype>`,
`Data:AttackArchetype/<subtype>`, ...) with on-disk files at
`data/<type>/<subtype>.wiki.txt`. The `Entry` abstraction surfaces
*only* in the Cargo table name and the `{{Entry | …}}` template
invocations inside each page — user-facing wiki paths stay rooted in
game concepts (Movement, CreatureType, AttackArchetype) that already
have meaning to readers and editors.

**Subtype collision risk:** by going flat per-domain, two unrelated
domains can't share a subtype value at the wiki path level (since
they live under different namespaces — `Data:Movement/fly` and a
hypothetical `Data:Buff/fly` would coexist cleanly). Inside the
single `Entry` Cargo table, `(type, subtype)` is still the primary
key, so the data side handles collisions naturally.

**Directory→namespace mapping:** lives in `_DIR_TO_WIKI_TABLE`
(`src/artificer/diff/wiki_diff.py`). Add an entry there when
introducing a new Entry type so the diff/upload pipeline knows the
PascalCase name to use in `Data:<…>/<subtype>` page titles.

**Initial migration:** three types, 12 rows total.
- `attack_archetype`: melee, ranged, reach (was `AttackArchetype`)
- `movement`: fly, teleport (was `Movement`)
- `creature_type`: living, undead, demon, magic_creature, embodiment,
  dragon, construct (was `CreatureType`)

All naming flips, divergence notes, and seed values from D-021
(partial), D-022, and D-023 carry through unchanged. The display name
"Hive Spawn" for the `demon` subtype, "Long Reach" for `reach`,
"Blink" for `teleport` — all live as the row's `display_name`.

**The catch-all rule (worth memorizing):** if a piece of reference
data has *only* a name, description, and translations — and nothing
else — it goes into `Entry` as a new `type` value. As soon as it
needs an additional column (rank, cost, prerequisite, formula, etc.)
it earns its own dedicated table.

**Why `AttackPassive` stays separate:** it carries `pattern_token`
and `rank` columns. Adding those to `Entry` would either pollute the
generic schema with one-off fields or push the AttackPassive data
into wikitext-only sidecars that lose Cargo queryability. Reference
> duplication only when shapes match exactly.

**`icon` field included from the start.** None of the migrated
domains carry an icon today, so the column is universally empty in
the initial rollout — but it's the most likely "what we'd add next"
field for future Entry types (resources, hero stats, magic schools,
etc.). Sparse-emit semantics mean the field costs nothing for rows
that don't use it.

**Code shape:** one `ENTRY_SEEDS: dict[type, dict[subtype, info]]` in
`emit/unit.py`, one `emit_entry_page(type, subtype, ...)` function,
one CLI writer loop that walks the nested seeds dict. Replaces three
parallel seed dicts and three parallel emit functions. Net: ~200
lines deleted, one cohesive code path remaining.

**Considered and rejected:**

- **Keep the per-domain tables, add a base template they all inherit
  from.** MediaWiki templates can compose, but Cargo tables can't —
  a shared base wouldn't cut the table count, just the wikitext
  duplication. The point is to consolidate the *data*, not the
  rendering.

- **Use one Entry table but keep separate `EntryTranslation` for
  i18n.** Theoretical normalization win; in practice the tables are
  always queried together (every wiki render of an entry needs both
  the English defaults and the active locale's translation), so the
  join cost outweighs any storage benefit. Inline columns also let
  the bot emit one row per file instead of two, halving the page
  count.

- **Naming: `Glossary`, `Codex`, `Lexicon`, `Term`, ...** — `Entry`
  won on neutrality; the table isn't fantasy-flavored or
  dictionary-flavored, just a generic "named thing with a
  description."

## D-025 — Faction tables + city-name Entry rows

**Date:** 2026-05-04
**Status:** Locked.

Faction is the first "complex enough to need its own table" category
we've extracted (vs the simple Entry-shaped reference data tackled in
D-022/D-023/D-024). Captures the faction-level structural data plus
the city-name pool, and defers the law tree to a separate decision.

**Source:** `Core/DB/fractions/<n>_<id>.json`. Six files, one per
faction. `id` ∈ {`human`, `undead`, `dungeon`, `nature`, `demon`,
`unfrozen`}. (The source spelling is `fraction*`; the bot already
normalizes to `faction*` everywhere visible — `Faction` enum
established for the unit `faction` column lives in
`models/common.py`.)

**Per-faction fields captured on `Faction` table:**
- `id`
- `name` (resolved English) + `name_sid`
- `desc` (resolved English Wikitext) + `desc_sid`
- `icon` (asset filename, source: `icon`)
- `icon_faction_laws` (asset filename, source: `iconFractionLaws` —
  normalized)
- `biome` (`Grass` | `Deathland` | `Dirt` | `Autumn` | `Lava` |
  `Snow`)
- `resource` (`gemstones` | `mercury` | `crystals`, source:
  `resourceName` — normalized)
- `source_path` (for traceability)

**`FactionTranslation`** mirrors the `UnitTranslation` shape: one row
per faction with `name_sid` / `desc_sid` plus 15 × per-language
(name, desc) pairs. Full 16-language coverage on both SIDs in the
2026-05-03 corpus.

**`narrativeDesc` is dropped.** Source JSON references
`<id>_narrative_desc` SIDs (e.g. `human_narrative_desc`); none of
those SIDs exist in *any* language file in the 2026-05-03 corpus —
dead pointer. Storing the SID with no resolvable text adds noise; if
a future patch populates the L10n we'll revisit.

**City names → `Entry` rows** with `type=FactionCityName`, subtype
`<faction>_<index>` (e.g. `dungeon_1` … `dungeon_20`). 6 × 20 = 120
rows. Each row carries the city's `name_sid` and the resolved English
+ 15 non-English translations. **City names are genuinely localized**
(8-16 distinct strings per name across the 16 languages — CJK
languages get full character-set translations; Latin scripts mix
preservation, idiomatic translation, and phonetic transliteration).
Description columns are sparse-emitted (no description SIDs exist
for city names).

**City Entry rows live on the parent faction page,** not on individual
`Data:FactionCityName/…` pages. The 20 `{{Entry | type=FactionCityName |
…}}` invocations are appended to the faction's wiki page in numeric
source order (1..N), after `{{Faction}}` and `{{FactionTranslation}}`.
Cargo doesn't care which page does the `#cargo_store` call — the rows
land in the unified `Entry` table either way — and consolidating them
keeps the per-faction view (one wiki page → all data for that faction)
intact for editors and readers alike. There is no `data/faction_city_name/`
output directory.

**Why Entry rows for city names instead of a dedicated
`FactionCityName` table:** the per-row shape is exactly
name+i18n-only, which is what Entry is for. Promoting it to its own
table would be premature when the Entry catch-all already has the
right schema. Per the D-024 rule: "if it has *only* a name,
description, and translations — and nothing else — it goes into
`Entry` as a new `type` value."

**Why Faction is *not* an Entry row:** the structural fields (icon,
icon_faction_laws, biome, resource) push it past the
name+desc+i18n-only line. Per the D-024 rule, that earns a dedicated
table.

**Code shape:**
- `models/faction.py` (new) — `FactionRecord` model
- `extract/faction.py` (new) — `extract_factions(paths)` walks
  `DB/fractions/*.json`
- `emit/faction.py` (new) — `emit_faction_page(faction, corpus,
  resolver)` renders `{{Faction}}` + `{{FactionTranslation}}`
- `emit/unit.py` — `emit_entry_page` refactored to take SID
  parameters directly so it serves both curated seed data and
  per-patch extracted Entry data; `emit_entry_page_from_seed`
  added for the curated path
- CLI: extract factions, emit faction pages, emit per-faction city
  Entry rows

**Output layout** (consistent with established conventions):
- `data/factions/<id>.wiki.txt` → `Data:Faction/<id>` (plural dir,
  matches the Unit/AttackPassive convention for dedicated tables).
  Each file holds three concerns: the `{{Faction}}` row, the
  `{{FactionTranslation}}` row, and the 20 inline city `{{Entry}}`
  rows.

**Deferred:**
- `fractionLawsLines` (the 5-line × 2-group × 2-4-law skill tree
  shape on each faction). Captured-or-not pending the FactionLaw
  work that ingests `DB/fractions_laws/`.
- Promoting Entry data flow to support extract-time-derived rows
  beyond city names is now possible (the refactored
  `emit_entry_page` accepts SID params directly); no dedicated Entry
  type registry needed for the per-patch case — extract/emit modules
  hand-call `emit_entry_page` with the `(type, subtype, name_sid,
  desc_sid)` they want.

## D-026 — Unified `Translation` table; supersedes per-entity *Translation tables

**Date:** 2026-05-04
**Status:** Locked.

`UnitTranslation`, `FactionTranslation`, `AttackPassiveTranslation`
(and prospective `HeroTranslation`, `HeroClassTranslation`,
`HeroSpecializationTranslation`, `HeroSubClassTranslation`) all share
the **identical** shape: `<entity>_id`, `name_sid`, `desc_sid`, then
15 × `<lang>_name` / `<lang>_desc` columns. Same play as D-024 did
for the small reference tables: collapse the parallel structure into
one shared `Translation` table with a `type` discriminator column.

**Resolution:** introduce `Translation` (in
`docs/cargo/shared/Translation.md`) keyed on `(type, target_id)`.
Delete the per-entity translation docs. Refactor each entity emitter
(`emit_unit_page`, `emit_faction_page`, `emit_attack_passive_page`,
…) to render `{{Translation | type=… | target_id=… | …}}` instead
of `{{<Entity>Translation | …}}`.

**Schema:** identical to the deleted per-entity tables, plus a `type`
column at the head:

```mediawiki
{{#cargo_declare:_table=Translation
| type = String              <!-- unit, faction, attack_passive, hero, hero_class, ... -->
| target_id = String
| name_sid = String
| desc_sid = String
| pt_br_name = String
| pt_br_desc = Wikitext
| ...                        <!-- 15 langs -->
}}
```

**Page layout unchanged.** Each translation row still lives on its
parent entity's data page (`Data:Unit/<id>`, `Data:Faction/<id>`,
…), appended after the structural row. There is no
`Data:Translation/…` page namespace — the table is store-only.

**Why this is *not* an Entry:** Entry rows carry inline English
defaults (`display_name`, `description`) and an `icon` field, plus
they're the *primary* representation of small reference enums (no
parent table). Translation is a *side* payload alongside an existing
parent entity (Unit, Faction, …) which carries its own English
defaults; the Translation row holds the 15 non-English locales only.
Same shape ≠ same role. Keeping them separate avoids the schema
gymnastics of "is this Entry row a primary or a side payload?"

**Code shape:** one `render_translation_block(type, target_id,
name_sid, desc_sid, corpus, resolver)` helper alongside
`render_entry_block` in `emit/unit.py`. Each entity emitter calls
the helper instead of building its own per-entity translation
parameter dict.

**Deletes:**
- `docs/cargo/UnitTranslation.md`
- `docs/cargo/UnitAbilityTranslation.md`
- `docs/cargo/FactionTranslation.md`
- `docs/cargo/AttackPassiveTranslation.md`

The convenience filter columns previously on `UnitAbilityTranslation`
(`unit_id`, `ability_type`, `ordinal`, `variant`) are dropped. Any
display-side query that needs them joins to `UnitAbility` on
`target_id` — those columns already live there. Cargo joins are
cheap; column duplication for filter convenience is the kind of
schema drift this consolidation exists to prevent.

**Considered and rejected:**
- **Merge into Entry.** Tempting given the shape overlap, but
  conflates two semantics: "this row IS the entity" (Entry) vs
  "this row is the i18n alongside the entity" (Translation).
  Display-side queries differ in pattern, and Entry's `(type,
  subtype)` PK doesn't quite match Translation's natural
  `(type, target_id)` shape (entries can stand alone; translations
  always join to a parent).
- **Per-entity `<Entity>Translation` tables, keep parallel.** Status
  quo with growing surface area as new entities come online — the
  D-024 lesson rerunning.

## D-027 — Hero + HeroClass with class-default override semantics

**Date:** 2026-05-04
**Status:** Locked.

Heroes carry a player-facing identity (name, motto, description,
specialization, starting army/skills/spells) on top of a class
template (Knight / Cleric / Death Knight / etc.). Empirically the
12 (faction × `might`/`magic`) classes are *implicit* in the source —
no `DB/heroes_classes/` file exists — but every faction hero of a
given class shares 11 fields' values exactly. Devs almost certainly
designed each class then copy-pasted the template into per-hero
records and customized only the deltas.

**Resolution:** introduce two paired tables.

`HeroClass` (12 rows, derived) carries the class defaults: faction,
class_type, name (e.g. "Herald"), mesh, mount, native_biome,
skills_roll_variant, cost_gold, start_level, attacks_times_before,
the 12 stat columns, and the 8 stat-roll columns. The class id is
`<class_type>_<faction>` (matches the L10n SID convention —
`magic_demon` → "Herald"). Description SID is shared per
classType: `might_desc` / `magic_desc`.

`Hero` (one row per hero, ~177 in the 2026-05-03 corpus) carries
the per-hero identity plus class-default fields encoded as **sparse
overrides**. When the hero's value matches the class default, the
column is omitted from the Hero row; the wiki-side join falls
through to HeroClass via `COALESCE(Hero.<col>, HeroClass.<col>)`.

Empirically:
- **Faction heroes (108):** zero overrides. Every one of the 11
  class-shared columns is omitted from the Hero row — every query
  inherits from HeroClass.
- **Campaign heroes (46):** universally override `stats`,
  `start_level`, and `attacks_times_before`. Some additionally
  override `mesh`, `mount`, or `skills_roll_variant`.
- **Tutorial heroes (21):** universally override `stats` and
  `attacks_times_before`. Most override `start_level`.

**Cluster discovery:** `HeroClass` defaults are derived at extract
time by taking the first faction hero in each (faction, classType)
cell. The 11-field signature is invariant within each cell across
the 108 faction heroes — no within-cell deviations exist in the
2026-05-03 corpus, so first-hero is sufficient. (If a future patch
ships within-cell drift, the bot would need to either pick a
canonical hero or surface the conflict in the audit.)

**Page layout:**
- `Data:HeroClass/<class_id>` — `{{HeroClass}}` row + `{{Translation
  type=hero_class}}` row. 12 pages total.
- `Data:Hero/<hero_id>` — `{{Hero}}` row (sparse), two `{{Translation}}`
  rows (`type=hero` for name+desc, `type=hero_motto` for the motto SID),
  plus N side-table rows (HeroStartSquad, HeroStartSkill,
  HeroStartMagic). ~177 pages total.

**Why two Translation rows for one hero:** the hero record has three
localizable fields (name, motto, description) but the `Translation`
table per D-026 has slots for one (name, desc) pair. Adding `motto`
columns would specialize the schema for heroes; emitting a second
`Translation` row with `type=hero_motto` reuses the unified table
cleanly. One extra row per hero is negligible.

**List-shaped per-hero data:**
- `startSquad` + `startSquadAlt` → `HeroStartSquad` side table with a
  `variant` discriminator (`primary` / `alt`). Squad min/max ranges
  are preserved (they define the random count at battle start).
- `startSkills` → two parallel inline list columns on Hero:
  `start_skills` (List of skill SIDs) and `start_skill_levels` (List
  of Integers). The Nth element of `start_skill_levels` is the level
  for the Nth SID — empirically mostly 1, but 8/208 entries are
  level 2 so the level data is preserved. Originally proposed as a
  `HeroStartSkill` side table, then collapsed to a single SID-only
  list, then expanded to parallel SID + level lists once the level
  variation came back into scope.
- `startMagics` → `Hero.start_magics` inline column, same shape.
  Level + isLearned dropped (constant `1` / `True` in the 2026-05-03
  corpus).

The `start*` lists are *not* promoted to HeroClass defaults despite
~8/9 within-cell sharing — list-shape "match = omit" semantics is
awkward to express, and per-hero is the simpler invariant.

**Folder name → faction id drift:** source uses `humans/`, `necros/`,
`demons/` (plural / archaic) but the JSON `fraction` field uses the
singular `human`, `undead`, `demon`. The bot reads the JSON's
`fraction` field directly; folder names are ignored except for
discovery.

**Naming normalization:**
- `iconFractionLaws` → `icon_faction_laws`
- `costGold` → `cost_gold`
- `stats.moral` → `morale` (source typo; reused elsewhere in the
  bot — see D-018-era discussion of `fraction` → `faction`).
- `attacksTimesBefore` → `attacks_times_before` (kept as-is — the
  source name is non-obvious but stable).

**Code shape:**
- `models/hero.py` — `HeroClassRecord`, `HeroRecord`,
  `HeroStartSquadSlot`, `HeroStartSkill`, `HeroStartMagic`,
  `HeroStats`, `HeroStatsRolls`, `HeroExtractionResult`.
- `extract/hero.py` — `extract_heroes(paths)` does the two-pass
  walk: first pass gathers faction-hero raws to derive class
  defaults; second pass builds every HeroRecord with sparse override
  fields against its class.
- `emit/hero.py` — `emit_hero_class_page` and `emit_hero_page`.

**Deferred:**
- `HeroSpecialization` (135 rows) — a separate table; one
  specialization per hero, points back via `Hero.specialization_id`.
  Schema lands in a follow-up.
- `HeroSubClass` (24 prestige classes per the player-facing
  unlocks: Swashbuckler, Paragon, Grand Inquisitor, etc.) — also
  follow-up.

## D-028 — HeroSpecialization with structured bonus side table

**Date:** 2026-05-04
**Status:** PARTIALLY SUPERSEDED by D-031. The `HeroSpecialization`
table itself is unchanged. The `HeroSpecializationBonus` side table
collapsed into the unified `Bonus` table — same fields, plus a
`parent_type='hero_specialization'` discriminator.

Hero specializations are the per-hero unique passive — what makes
Pauper a "Flea Bites" hero vs Pip a "Wish to Learn" hero. Each
spec has a name, description, icon, and a list of structured
`bonuses[]` effects. 126 specs in the 2026-05-03 corpus (108
faction + 9 campaign + 5 tutorial + 4 test); 1367 total bonus rows.

**Top-level fields (uniform across all 126 specs):** `id`, `name`
(SID), `desc` (SID), `icon`, `bonuses[]`.

**Bonus shape:** each `bonuses[]` entry has `type` + `parameters`
(always present), plus optional `activationLevel`, `upgrade`,
`receivers`, `battleType`, `receiverRole`, `receiverAllegiance`.
12 distinct `type` values (heroStat, unitStat, heroBattleAbility,
battleSubskillBonus, heroMagicReplace, cityUnitsIncrement,
upgradeUnitsBonus, sideRes, heroStatBattle, unitBoolStat,
learnMagicRemoteFromMagicGuild, cityUnitsIncrementPer).

**Resolution:** two paired tables.

`HeroSpecialization` (126 rows) carries identity + Translation join.
`HeroSpecializationBonus` (~1367 rows) is a side table keyed on
`(spec_id, ordinal)` carrying each bonus row.

**`parameters` stored as `List (,) of String`.** Each bonus type has
its own parameter shape (e.g. `heroStat` is `[stat, value]`,
`heroMagicReplace` is `[from_spell, to_spell]`); the bot does no
interpretation. Wiki display layer parses by `type`. Same encoding
strategy as `Unit.shared_abilities` and `Hero.start_skills` — flat
strings now, structure later if a real wiki need surfaces.

**Considered and rejected:**
- **Per-type typed columns** (e.g. `stat_name + stat_value` for
  heroStat, `ability_id + ability_version` for heroBattleAbility).
  Schema bloat: 12 types × 1-3 columns each, with most columns
  always null. Cargo doesn't gain anything from typed columns
  here — `parameters` is opaque to filtering anyway since the
  meaning isn't lookable up by SQL.
- **Single JSON-string blob.** Compact but Cargo can't index into
  it. List columns at least let `HOLDS` queries work.

**Forward-only join** (no `hero_id` back-reference on
HeroSpecialization). `Hero.specialization_id = HeroSpecialization.id`
suffices for both directions; reverse queries ("which hero has this
spec") use the same join the other way. Saves one column.

**Page layout:** `Data:HeroSpecialization/<id>` carries the
`{{HeroSpecialization}}` row, the `{{Translation |
type=hero_specialization | …}}` row, and N inline
`{{HeroSpecializationBonus}}` rows in source order. No individual
`Data:HeroSpecializationBonus/…` pages.

**Code shape:** `extract_hero_specializations(paths)` walks
`DB/heroes_specializations/*.json`. `emit_hero_specialization_page`
renders the three-block page. CLI loops over the result.

**Scope:** all 126 specs (faction + campaign + tutorial + test) are
extracted — campaign and tutorial heroes have specs that need to
resolve when those Hero records render.

## D-029 — HeroSubClass: prestige classes with flat activation thresholds + dedicated bonus table

**Date:** 2026-05-04
**Status:** PARTIALLY SUPERSEDED by D-031. The `HeroSubClass` table
itself, the 5 flat activation columns, and the bonus shape decisions
are unchanged. The `HeroSubClassBonus` side table collapsed into
the unified `Bonus` table with `parent_type='hero_sub_class'` —
reversing this decision's "separate table per editor preference"
choice once Items came online and a third copy of the same shape
loomed.

Hero sub-classes are the named prestige progressions
(Swashbuckler, Paragon, Grand Inquisitor, Ascendant, etc.) a hero
unlocks by hitting 5 specific skill thresholds. 24 records in the
2026-05-03 corpus: 4 per faction × 6 factions, split 2 might + 2
magic per faction.

**Source:** `Core/DB/heroes_sub_classes/sub_classes_<faction>.json`.
Folder uses singular faction ids (`human`, `undead`, `demon`) — note
this diverges from the `heroes/` folder naming (`humans`, `necros`,
`demons`).

**Per-sub-class fields (uniform across all 24):** `id`, `icon`,
`name` (SID), `desc` (SID), `faction`, `classType`,
`activationConditions[]`, `bonuses[]`.

**Activation conditions: 5 flat columns on `HeroSubClass`.**
Empirically every sub-class has exactly 5 activation thresholds
(`{skillSid, skillLevel, subSkillSids[]}`) and `subSkillSids` is
always empty. Two paths considered:

- **Side table HeroSubClassActivation** — clean, queryable, supports
  variable count.
- **Flat columns** (`activation_skill_<1..5>_sid` +
  `activation_skill_<1..5>_level`) — denormalized but every sub-class
  has exactly 5 in the corpus. 10 columns vs a 120-row side table.

Chose **flat columns** per editor preference. The 5-condition
invariant is strong (all 120 conditions across all 24 sub-classes
follow it); if a future patch breaks it we'd have to migrate. The
empty `subSkillSids` is dropped — adding the column "just in case"
would carry no data in any present row.

**Bonuses: dedicated `HeroSubClassBonus` table.** The bonus shape
overlaps with `HeroSpecializationBonus` (both have `type` +
`parameters` + optional `receivers` / `receiverAllegiance`) but
sub-class bonuses don't carry `activationLevel`, `upgrade`,
`battleType`, or `receiverRole`. Two paths considered:

- **Consolidate into a generic `Bonus` table** with `parent_type`
  discriminator (same play as Translation/Entry).
- **Separate `HeroSubClassBonus` table** alongside the existing
  `HeroSpecializationBonus`.

Chose **separate** per editor preference. Reasoning: the bonus
shapes are *similar* but not identical (sub-class drops 4
columns); the smaller table makes filtered queries faster; the
semantics stay self-evident for editors writing display
templates. Schema duplication is real but bounded — only 2 tables
share this shape, not the open-ended set Translation faces.

**Code shape:**
- `models/hero.py`: `HeroSubClassRecord` + `HeroSubClassBonus` +
  `HeroSubClassExtractionResult`.
- `extract/hero.py`: `extract_hero_sub_classes(paths)` walks
  `DB/heroes_sub_classes/sub_classes_<faction>.json`.
- `emit/hero.py`: `emit_hero_sub_class_page` renders the three
  blocks per sub-class.

**Page layout:** `Data:HeroSubClass/<id>` with `{{HeroSubClass}}` +
`{{Translation | type=hero_sub_class | …}}` + N inline
`{{HeroSubClassBonus}}` rows.

**Description placeholder substitution:** sub-class descriptions
mostly leave `{N}` for the wiki display layer to fill from joined
bonus parameter values (e.g. "Heroic Strike deals +{0} basic
Damage" — the {0} comes from the heroStat bonus's parameter[1]).
Only one sub-class (`sub_class_demons_might_2`) has an args entry
in `heroSkills.json`, and its referenced script function isn't
defined in the script files. So no spec_json-style threading is
needed; the resolver pipeline runs as-is and any unresolved {N}
markers persist for the display side to handle.

## D-030 — Spell + SpellRank with split learn-cost columns and hero-dependent placeholders left unsubstituted

**Date:** 2026-05-04
**Status:** Locked.

Spells are the most structurally complex entity yet — each carries
identity + classification, a 4-element per-mastery-level array of
descriptions and mana costs, a 0-or-3-element per-upgrade bonus
description list, multi-resource learn cost, plus optional fields
for special-magic / unique-magic variants.

**131-137 spells** in the 2026-05-03 corpus across 5 schools (day,
night, primal, space, neutral) and 5 ranks. Two contexts (mutually
exclusive via `usedOnMap`): battle (105) vs world (26). 38 are
`_special` upgraded variants pointing back at base spells via
`normalMagicSid`. Test scope includes the test/punishment files
per editor preference.

**Schema split:** `Spell` main table + `SpellRank` side table.
SpellRank carries the per-mastery-level data — exactly 4 rows per
spell (levels 1=no skill, 2=basic, 3=advanced, 4=expert). The
level-up bonus message and the upgrade cost paid to reach a level
attach to that level's SpellRank row (so level 1 has no bonus_*
fields).

**`learnCost` flattened** into 4 explicit columns on Spell:
`learn_cost_gemstones`, `learn_cost_crystals`, `learn_cost_mercury`,
`learn_cost_star_dust`. Most spells (94) use the
gemstones/crystals/mercury triple; 6 unique-magic specials use
star_dust. Other resources don't appear in learn costs.
Sparse-emit: omit any column that's zero/missing.

**Description resolution: hero-dependent placeholders intentionally
stay as `{N}`.** Spell descriptions reference scripts like
`current_day_1_magic_healing_water` that combine static spell
config (read via the new `CurrentMagicBattle` op against
`battleMagic.targetMechanics.*`) with hero-dependent values
(`SpellpowerForCurrentMagic`, `CurrentHero` ops). The bot:

- Adds `CurrentMagicBattle` and `CurrentMagicWorld` ops to the
  interpreter, threading `magic_json` context through the same
  pipeline as `spec_json` (D-027) and `unit_json`.
- Does *not* implement `SpellpowerForCurrentMagic` or `CurrentHero`.
  Their function calls fall through, returning None — the
  corresponding `{N}` markers persist in the rendered description.

This matches editor intent: a spell page shows the formula generally;
specific numeric outcomes depend on the casting hero and live on
hero-context displays the wiki templates can build via Cargo joins.

**`battleMagic` / `worldMagic` sub-trees not extracted as columns.**
These dicts hold the in-game effect mechanics (dealersPerLevels,
hexEffect, magicSettings, etc.) and are used for resolver context
only via `raw_json`. If the wiki ever needs columns for "duration",
"hex shape", "effect type", etc., they get added then.

**Page layout:** `Data:Spell/<id>` carrying `{{Spell}}` row, then
4 paired `{{SpellRank}}` + `{{SpellRankTranslation}}` blocks (one
pair per mastery level). ~137 spell pages; ~548 each of SpellRank
and SpellRankTranslation rows.

**Translation: dedicated `SpellRankTranslation` table, per-rank,
3-SID shape.** Per D-030 (revised): the unified `Translation` table
(D-026) has `(name, desc)` slots — spells have a third localizable
field per rank (`bonus_description`). Rather than pollute the
shared schema, spells get their own translation table. Each
SpellRankTranslation row carries the spell name (repeated per
rank for clean per-rank queries) plus the rank-specific desc and
bonus_description, with 15 per-language triples. The per-spell
`{{Translation | type=spell}}` row from the original D-030 is
dropped — translations now flow exclusively through the per-rank
SpellRankTranslation rows.

**Code shape:**
- `models/spell.py`: `SpellRecord` + `SpellRankRecord` +
  `SpellExtractionResult`. Spell carries `raw_json` for the
  placeholder resolver context (same pattern as
  `HeroSpecializationRecord`).
- `extract/spell.py`: walks `DB/magics/*.json`. Splits learnCost
  into per-resource columns; partitions level-indexed arrays into
  the 4 SpellRank rows; preserves source typos
  (`excaptionInTooltip` → `excaption_in_tooltip_sid`) since the
  field is rare and the Pythonic "exception" rename would obscure
  the source.
- `emit/spell.py`: `emit_spell_page`. Calls `_lookup_text` with
  `magic_json=spell.raw_json` so the resolver can read
  `battleMagic.*` / `worldMagic.*` paths. SpellRank rows resolve
  their description and bonus_description English text inline.
- `resolve/interpreter.py`: adds `CurrentMagicBattle` and
  `CurrentMagicWorld` ops keyed on `context["magic_json"]`.
- `resolve/resolver.py`: threads `magic_json` parameter through
  `resolve` / `_resolve_inner` / `_eval_expr` / `_evaluate_args`.

## D-031 — Unified `Bonus` table + Artifact entity; supersedes per-domain *Bonus tables

**Date:** 2026-05-04
**Status:** Locked.

Artifact (equipment) ingest brought a third entity carrying the same
``{type, parameters, [activationLevel], [upgrade], [receivers],
[battleType], [receiverRole], [receiverAllegiance]}`` bonus shape
that hero specializations and hero sub-classes also use. Three
parallel tables of identical shape would have rerun the lesson
D-024 (Entry) and D-026 (Translation) already taught:
identical-shape parallel tables collapse into one discriminated
table.

**Resolution:** introduce a unified `Bonus` Cargo table at
`docs/cargo/shared/Bonus.md`, keyed on `(parent_type, parent_id,
ordinal)`. Migrate `HeroSpecializationBonus` and `HeroSubClassBonus`
into it; `Artifact.bonuses` flow through it directly.

**Schema** is the original `HeroSpecializationBonus` columns plus
two discriminator columns at the head:

```mediawiki
{{#cargo_declare:_table=Bonus
| parent_type = String     <!-- hero_specialization, hero_sub_class, artifact, ... -->
| parent_id = String
| ordinal = Integer
| type = String
| parameters = List (,) of String
| activation_level = Integer
| upgrade_increment = Float
| upgrade_level_step = Integer
| receivers = List (,) of String
| battle_type = String
| receiver_role = String
| receiver_allegiance = String
}}
```

**Artifacts: own dedicated `Artifact` table.** 304 records spanning
13 source slot files (armor, head, ring, boots, magic_scroll,
mythic_scroll_box, item_slot, etc.). Source folder
(`DB/items/items/`) uses the JSON's "item" terminology, but the
wiki side surfaces these as **artifacts** per the in-game
player-facing label — the table, template, directory, and
translation discriminator (`type=artifact`) all use the artifact
spelling. Source field names that contain "item" (`itemSet`,
`isSpecialItem`) are renamed where they're a normalized concept
(`artifact_set_id`) and preserved where they're a near-source
flag (`is_special_item`).

Carries identity + slot/rarity classification + four localizable
SIDs (name, description, upgrade_description, narrative_description).
Artifact bonuses flow into `Bonus` per the above.

**Artifact sets deferred.** Source has 24 sets in
`DB/items/item_sets/item_sets.json` with nested
`bonuses[].heroBonuses[]` structures (set-completion thresholds +
per-tier bonus lists). The schema needs a separate design pass —
the nested-bonus shape doesn't cleanly fit the flat Bonus table.
Tracked as future work; the future table is `ArtifactSet`.

**Translation:** artifacts use the standard
`{{Translation | type=artifact}}` row carrying name + description
(per D-026). The `upgrade_description` and `narrative_description`
SIDs are stored on the Artifact row with their English-resolved text
inline; their non-English translations are not extracted — a future
pass can either extend Translation to a 3- or 4-SID shape (like
SpellRankTranslation per D-030 revised) or accept that flavor text
only ships in English.

**`useExpandTooltip` source-typing inconsistency.** Source ships this
field as both a proper bool and the string `"false"` on different
artifacts. The bot normalizes to a real bool via `_coerce_bool`.

**Code shape:**
- `models/hero.py`: `HeroSpecializationBonus` and `HeroSubClassBonus`
  collapsed into a single `Bonus` model with `parent_type` /
  `parent_id` columns. Old names kept as aliases for backward compat.
- `models/artifact.py` (new): `ArtifactRecord`,
  `ArtifactExtractionResult`.
- `extract/hero.py`: `_build_bonus` renamed to public `build_bonus`,
  takes `parent_type` and `parent_id` parameters. The sub-class
  extractor uses it. The dedicated `_build_sub_class_bonus` helper
  is gone.
- `extract/artifact.py` (new): `extract_artifacts(paths)`. Re-uses
  `build_bonus` for artifact bonuses.
- `emit/hero.py`: `_render_spec_bonus` and `_render_sub_class_bonus`
  collapsed into a single public `render_bonus(b)`.
- `emit/artifact.py` (new): `emit_artifact_page`. Uses `render_bonus`
  for artifact bonuses.

**Naming flip:** the old `HeroSpecializationBonus` template name
disappears from page output — every bonus now renders as
`{{Bonus | parent_type=… | parent_id=… | …}}`.

**Considered and rejected:**
- **Three separate tables (status quo extended).** Would have made
  Item the third copy of the same shape. The pattern is now
  well-established (D-024 Entry, D-026 Translation): consolidate.

## D-032 — ItemSet + ItemSetTier with synthesized tier IDs into the unified Bonus table

**Date:** 2026-05-04
**Status:** Locked.

Item sets are curated artifact groups granting threshold-unlocked
bonuses. 24 sets in the 2026-05-03 corpus, 1-3 unlock tiers per
set. The source's nested `bonuses[].heroBonuses[]` shape needed a
specific decision on how to flatten it for Cargo.

**Source shape:** each set has `id`, `name`, `itemsInSet[]` (list
of artifact ids), and `bonuses[]` where each entry is
`{requiredItemsAmount, desc, heroBonuses[]}`. ~37 tiers and 80
total bonus effects across all 24 sets.

**Resolution:** two paired tables plus integration with the unified
Bonus table.

`ItemSet` (24 rows) carries identity + name SID + the comma-joined
`items_in_set` list. No description on the set itself — each tier
has its own description.

`ItemSetTier` (~37 rows) is a side table keyed on `id =
<set_id>_tier_<ordinal>`. Carries `set_id` back-pointer, ordinal,
required_amount, description SID + resolved English. The
synthesized id format lets `Bonus.parent_id` join cleanly.

`Bonus` rows for set tiers use `parent_type='item_set_tier'` and
`parent_id = <set_id>_tier_<ordinal>`. The bonus shape is a subset
of the existing Bonus columns (only `type`, `parameters`, optional
`receivers` and `receiver_allegiance`); no new columns needed.

**Translation:**
- `{{Translation | type=item_set | target_id=<set_id>}}` for the set
  name (15 non-English locales).
- `{{Translation | type=item_set_tier | target_id=<tier_id>}}` for
  each tier's description (desc-only — tiers have no name field).

**"Item set" terminology preserved** despite the artifact rename
(D-031). Source JSON uses `itemSet`, `itemsInSet`,
`item_sets.json`, and players colloquially call them "item sets"
rather than "artifact sets". The Cargo table is `ItemSet`, the
template is `{{ItemSet}}`, the directory is `data/item_sets/`, and
`Translation.type='item_set'` — all preserve the source spelling.
The cross-pointer `Artifact.artifact_set_id` still references
`ItemSet.id` despite the naming asymmetry.

**Considered and rejected:**
- **Composite `parent_id` like `<set_id>::<tier_ordinal>`** for
  Bonus rows. Awkward to parse for queries that just want the set
  id. Synthesized tier id (`<set_id>_tier_<ordinal>`) plus a
  separate `set_id` column on ItemSetTier is cleaner.
- **Add a `tier` column to Bonus** for the item-set case. Pollutes
  the generic Bonus schema for one specific use.
- **Single ItemSet table with all tiers' bonuses inlined as
  comma-joined data.** Lossy — heroBonuses can have multiple
  effects per tier with structured fields.

**Code shape:**
- `models/item_set.py` (new): `ItemSetRecord`, `ItemSetTierRecord`,
  `ItemSetExtractionResult`.
- `extract/item_set.py` (new): `extract_item_sets`. Reuses
  `build_bonus` from `extract/hero.py` per the unified Bonus
  pipeline (D-031).
- `emit/item_set.py` (new): `emit_item_set_page`. Uses
  `render_bonus` and `render_translation_block`.

**Open follow-up:** the cross-pointer naming asymmetry —
`Artifact.artifact_set_id` references `ItemSet.id` — is intentional
per the user's call to keep "item set" naming, but a future tidying
pass could align them either direction.

## Open questions / known unknowns

- **Faction laws have nested arrays** (`fractionLawsLines: [{groups: [{laws: [...]}]}]`). Cargo doesn't natively support nested structures; will need either a side table with foreign keys or list-typed fields. Cross when we get there.
- **`fraction` vs `faction`** — source JSON uses "fraction" (likely a translation artifact); we normalize to "faction" on extract. OEE's domain entities also normalize this.
- **Bot account creation** — blocking the upload phase. User to create when we're closer to that milestone.
- **Bucket page structure for orphan SIDs** — exact split (one big page? per-source-file?) deferred until we know the orphan distribution.
