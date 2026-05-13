= Cargo schema reference =
Each file in this directory is a <code>#cargo_declare</code> definition for one Cargo
table the bot writes to. They're meant to be pasted into a wiki page (one
table per page is the MediaWiki convention) when the wiki maintainers are
ready to provision Cargo storage.

== Tables ==
Tables are grouped by parent entity. Splinters of <code>UnitAbilityDef</code>
join back via <code>ability_id</code>; every other relationship uses the parent
entity's natural id.

=== Units ===
{| class="wikitable"
! Table !! Purpose
|-
| [[UnitDef]] || One row per creature. Combat stats, resource costs, faction, tier, classification flags, English name/desc.
|-
| [[UnitAttackDef]] || One row per unit. All four attack slots (<code>default_*</code> / <code>counter_*</code> / <code>alt_*</code> / <code>alt2_*</code>) collapsed into a single wide row. <code><slot>_attack_type</code> references the <code>attack_archetype</code> Entry; <code><slot>_passive</code> references [[AttackPassiveDef]].
|-
| [[UnitAbilityDef]] || One row per ability slot on a unit. Identity + i18n SIDs. Splintered by <code>ability_type</code> into one of the six tables below.
|-
| [[UnitAbilityActiveDef]] || Active-ability scalars (dealer, buff, target, shoot range, cooldown, …). Splinter of <code>UnitAbilityDef</code>.
|-
| [[UnitAbilityPassiveDef]] || Passive-only fields. Splinter of <code>UnitAbilityDef</code>.
|-
| [[UnitAbilityConditionalDef]] || Condition triple + stat bonus for <code>conditional_passive</code> rows. Splinter of <code>UnitAbilityDef</code>.
|-
| [[UnitAbilityGlobalDef]] || Side-wide passive (target, power, tag) for <code>global_passive</code> rows. Splinter of <code>UnitAbilityDef</code>.
|-
| [[UnitAbilityAuraDef]] || Range-1 aura fields (target, power, radius, tag) for <code>aura</code> rows. Splinter of <code>UnitAbilityDef</code>.
|-
| [[UnitAbilityStatPassiveDef]] || Synthesized stat passive (e.g. <code>attackPen</code> → "Unyielding"). Splinter of <code>UnitAbilityDef</code>.
|}

=== Factions ===
{| class="wikitable"
! Table !! Purpose
|-
| [[FactionDef]] || One row per faction. Identity, biome, primary resource, city names.
|-
| [[FactionLawTierDef]] || Five rows per faction. Per-tier <code>count_to_unlock</code> gating for the faction law tree.
|-
| [[LawTreePositionDef]] || One row per (faction, law). Tree position (tier + slot) of a law in its faction's law tree.
|}

=== Heroes ===
{| class="wikitable"
! Table !! Purpose
|-
| [[HeroDef]] || One row per hero. Identity, class, faction, biography, per-hero overrides of class defaults.
|-
| [[HeroClassDef]] || One row per class. Stat-growth tables and skill-availability matrix.
|-
| [[HeroSpecializationDef]] || One row per specialization. Name, description, source path. Bonuses live on [[BonusDef]].
|-
| [[HeroSubClassDef]] || One row per prestige sub-class. Five activation thresholds (skill + level) inline. Bonuses on <code>BonusDef</code>.
|-
| [[HeroStartSquadDef]] || Multiple rows per hero. Starting army composition per (variant, slot).
|}

=== Spells ===
{| class="wikitable"
! Table !! Purpose
|-
| [[SpellDef]] || One row per spell. School, costs, identity.
|-
| [[SpellRankDef]] || Four rows per spell (level 1–4). English description + bonus_description + costs, plus 15 × (name, desc, bonus_description) language columns. Self-contained — no separate translation table.
|}

=== Laws ===
{| class="wikitable"
! Table !! Purpose
|-
| [[LawDef]] || One row per faction law. Faction, tier, ordinal, max_level.
|-
| [[LawLevelDef]] || One to three rows per law. Per-level cost + resolved English description. Non-English descriptions live on <code>EntryDef</code> rows keyed by <code>(type='law_level', subtype=<law_id>, variant=<level>)</code>.
|}

=== Artifacts ===
{| class="wikitable"
! Table !! Purpose
|-
| [[ArtifactDef]] || One row per artifact. Slot, rarity, set membership. Bonuses on <code>BonusDef</code>.
|-
| [[ItemSetDef]] || One row per set. Member artifacts.
|-
| [[ItemSetTierDef]] || One to three rows per set. Per-completion-tier description. Bonuses on <code>BonusDef</code>.
|}

=== Skills ===
{| class="wikitable"
! Table !! Purpose
|-
| [[SkillDef]] || One row per hero skill (primary skills + pseudo + arena + campaign). Identity, max_level.
|-
| [[SkillLevelDef]] || One to three rows per skill. Per-level English name/desc + <code>offered_sub_skills</code>. Non-English per-level overrides live on <code>EntryDef</code> rows keyed by <code>(type='skill_level', subtype=<skill_id>, variant=<level>)</code>.
|-
| [[SubSkillDef]] || One row per sub-skill. Identity, parent skill, English name/desc. Bonuses on <code>BonusDef</code>.
|}

=== Other entities ===
| Table | Purpos