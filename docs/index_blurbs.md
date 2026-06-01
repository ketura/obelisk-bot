# Index page blurbs

Per-namespace blurbs that appear at the top of each `Data:<Table>` index
page (the bot-emitted listing of every page in that namespace). One
section per namespace, header is the wiki table name exactly as it
appears in `Data:<Table>` URLs.

The body is plain wikitext — multiple paragraphs allowed, internal
templates / links allowed. The emitter inlines it verbatim above the
auto-generated link list.

If a section is missing for a namespace that the extract produces, the
emitter falls back to a one-liner placeholder and logs a warning so it's
visible.

Edit blurbs by hand; the bot doesn't write to this file.

## Unit

Units are the creatures heroes recruit into their armies and command in
tactical battles. Each `Data:Unit/<id>` page carries the unit's combat
stats (HP, attack, defence, damage range, initiative, speed, luck,
morale), its faction and tier, its abilities and passives, its attack
profile, its recruitment cost, its upgrade chain, and its localized name
and description SIDs across all 16 supported languages.

## AttackPassive

Attack passives are the movement-modifier behaviors a unit can have on
its primary attack — Sweeping Strike, Cone Attack, Trample, and so on.
They're shared across many units, so each `Data:AttackPassive/<id>` page
is a single compact record describing the passive's mechanic and its
name SID; units reference these by id rather than duplicating the
definition.

## Faction

The six playable factions plus the neutral pool. Each
`Data:Faction/<id>` page carries the faction's identity (name,
description, icon, biome, primary resource), its twenty procedurally
generated city names, and its five faction-law tiers along with the
law-tree positions of each member law.

## HeroClass

Hero classes are the twelve base classes — two per faction — that
govern starting stats, primary-skill growth tables, and skill
availability for every hero of that class. Each `Data:HeroClass/<id>`
page carries those tables plus the localized class name and
description.

## Hero

Heroes are the individual recruitable champions who lead armies. Each
`Data:Hero/<id>` page carries the hero's identity (name, class, faction,
biography) and their HeroStart records (starting army composition,
starting skills, starting magic), plus any per-hero overrides of the
class defaults (start level, ATB, base stats).

## HeroSpecialization

Every hero has a specialization — a unique passive bonus package that
scales with hero level, targets a specific unit type, or boosts a
particular school of magic. Each `Data:HeroSpecialization/<id>` page
carries the specialization's name, description, and the table of
bonuses it grants.

## HeroSubClass

Hero sub-classes are prestige classes a hero can unlock by meeting
certain criteria — twenty-four total, four per faction across six
factions. Each `Data:HeroSubClass/<id>` page carries the five
activation thresholds (level, skill, artifact-set requirements) plus
the bonuses the sub-class grants once unlocked.

## Spell

Spells include the battle-magic spells cast in combat, the world-magic
spells cast on the adventure map, and a handful of special and test
spells. Each `Data:Spell/<id>` page carries the spell's magic school,
mana cost, and four rank tiers (Basic, Advanced, Expert, Master) each
with its own resolved description and per-rank parameters.

## Artifact

Artifacts are equipable items that grant heroes stat bonuses, spell
effects, or set-completion synergies. Each `Data:Artifact/<id>` page
carries the artifact's slot, rarity, set membership, and the list of
bonuses it provides.

## ItemSet

Item sets are clusters of artifacts that grant additional bonuses as a
hero collects more pieces of the set. Each `Data:ItemSet/<id>` page
lists the member artifacts and the per-tier bonus packages unlocked at
each completion threshold.

## Law

Faction laws are the faction-specific upgrade choices a player makes as
the game progresses, organized into five tiers along a tree. Each
`Data:Law/<id>` page carries the law's tier, prerequisites, one to
three levels, and the per-level bonuses it grants. The parent
[[Data:Faction]] page positions each law in the tree.

## Building

Buildings are the town structures a player constructs to recruit units,
gather resources, and unlock advancement. Pages are grouped per
faction: all creature-dwelling rows for a faction land on one
`<faction>_Build_creature_dwellings` page, and every other building
gets its own `<faction>_<sid>` page covering all upgrade levels.

## MapObject

Map objects are the adventure-map structures heroes interact with —
chests, mines, dwellings, banks, portals, and so on. Each
`Data:MapObject/<id>` page carries the object's category and the
universal display and scalar fields. Rich category-specific payloads
(chest contents, mine bonuses, hire armies) are deferred to follow-up
work and not yet captured.

## Skill

Hero skills are the primary skills heroes train, each with three
mastery levels and a tree of sub-skills. Each `Data:Skill/<id>` page
carries the skill's three levels, the per-level bonus rows, and every
sub-skill the skill's levels reference (with the sub-skill's own bonus
rows folded in). Orphan sub-skills land on the catch-all
`Data:Skill/_orphan_sub_skills` page.

## SkillRollTable

When a hero levels up, the game draws from a weighted skill pool keyed
on the hero's class (Knight, Cleric, Death Knight, etc.). Each
`Data:SkillRollTable/<id>` page carries the header row plus every
weighted skill entry that makes up that class's roll table — both the
default-band weights that apply on every level-up and the milestone
overlays that fire on specific levels. Two parallel sets: 12 standard
tables (one per class), and 12 arena tables (used only in arena game
modes; they reference distinct `arena_skill_*` SIDs and have smaller
pools).

## SkillRollBand

Reference table of four rows describing the level grids the roll
overlays fire on. The default band applies to every level (1-50); the
three milestone overlays add weight to specific skill subsets at
mod-4 levels, mod-5 levels, and level 20. Overlays are *additive* on
top of the default — at level 20 the effective magic-school weights
are tripled, not just doubled.

## StatBonusRoll

The 12 "pseudo-skill" fallback entries the engine draws from when a
hero's main roll pool can't supply three valid offerings — i.e. when
they have no learnable new skills remaining *and* fewer than three
unexpert skills they could rank up. Each row grants a permanent flat
boost to one primary stat (offence, defence, spell power,
intelligence) at one of three magnitude tiers (+1, +2, +3). The +1
tier dominates with 99% of fallback rolls; the +3 tier sits at one in
~40,000.

## SkillRollReplacement

Per-hero overlays that bias certain arena heroes toward specific
skills at the early arena levels. 28 heroes get one or more
`arena_skill_*` SIDs added at levels 2/4/6 with weight 500 or 1000 —
enough to make that skill very likely but not guaranteed. Only fires
in arena mode; standard play sees no replacements.

## AstrologistEvent

Astrologist events are the periodically-rolled global modifiers
announced by the astrologer — "Week of Sorcery," "Month of the Locust,"
and so on. Each `Data:AstrologistEvent/<id>` page carries the event's
category (week or month), its roll chance, and its effect description.

## Difficulty

The five game difficulties: Easy, Normal, Hard, Expert, Impossible.
Each `Data:Difficulty/<id>` page carries the per-side starting-resource
buckets and the neutral-power multiplier that shape the early game.

## AttackArchetype

Attack archetypes are the canonical structural shapes a unit's primary
attack can take — basic melee, ranged, ranged-with-melee-penalty,
breath, and so on. Each `Data:AttackArchetype/<id>` page is a shared
seed describing one archetype; units reference it via their
`attack_archetype` field.

## Movement

Movement types describe how a unit traverses the battlefield — walking,
flying, teleporting, and so on. Each `Data:Movement/<id>` page is a
shared seed describing one type; units reference it via their
`move_type` field.

## CreatureType

Creature types are the broad biological and categorical classifications
used by abilities and bonuses to target groups of units (undead,
mechanical, demon, beast, ...). Each `Data:CreatureType/<id>` page is
a shared seed describing one type.

## Resource

Resources are the materials and currencies a player accumulates — gold,
wood, ore, crystal, gems, mercury, sulfur. Each `Data:Resource/<id>`
page carries the resource's localized name, its description, and its
icon reference.

## HeroStat

Hero stats are the per-hero numerical attributes used by formulas
across the game — attack, defence, intelligence, spell power, luck,
morale. Each `Data:HeroStat/<id>` page is a shared seed naming and
describing one stat.

## UnitStat

Unit stats are the per-unit numerical attributes used in combat — HP,
offence, defence, damage, initiative, speed, luck, morale. Each
`Data:UnitStat/<id>` page is a shared seed naming and describing one
stat.

## Coverage

The auto-generated data-page coverage diagnostic. Lists every `Data:`
page the bot emitted from the latest extract paired with the top-level
article expected to reference it. Pre-launch this is the bot's most
useful gap-report — a redlinked article column means a top-level page
that needs to be authored on the wiki side.
