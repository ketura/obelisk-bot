"""Project-local script overrides.

When Unfrozen ships an args entry that references a script function they
forgot to define, the resolver leaves ``{N}`` placeholders in the wiki text.
This module provides a small inline ``.script``-format string that the
resolver parses *on top of* the patch's scripts, plugging the gaps.

Anything in this file is a best-effort guess against the JSON data plus
any cross-checks against in-game text. When a guess produces obviously
wrong output, edit the relevant block here and re-extract.

Currently patched:

* ``unic_unit_twinkleManaAbility_base`` / ``_perCount`` / ``_Count``
  (Twinkle Leeching Hop). The args entry references three undefined
  functions. The upstream ``unic_unit_twinkle_ability_1`` formula
  ``baseMana + floor(stacks * unitsBonusMana / unitsCount)`` reads:

    baseMana = values[2]   (the always-stolen base)
    unitsCount = values[3]   (units per bonus group)
    unitsBonusMana = values[4]   (extra mana per group)

  Mapping to the alt template ``[ {0} + {1} per {2} units ... ]``:
    {0} = baseMana       -> values[2]
    {1} = unitsBonusMana -> values[4]
    {2} = unitsCount     -> values[3]

* ``unic_unit_ent_passive_4`` (Ent Upg "Stoneheart"). Reads the spawned
  obstacle id, then ``DbObstacle(stats.hp)``. Confirmed: 2 hits.

* ``unic_unit_black_dragon_ability_3`` (Ashen/Black Dragon "Dragonflight").
  Reads ``damageDealer.statDmgMult`` from the ability; missing -> defaults
  to 1.0 (= 100%) via the interpreter's numeric-config fallback.

* ``unic_unit_hydra_passive_2`` (Hydra Upg passive_3 "adjacent enemies
  deal -X% damage"). Reads ``hydra_debuff.data.stats.outAllDmgMod``.

* ``unic_unit_hydra_passive_2_duration`` (paired with above).

* ``unic_unit_ent_passive_3`` (Ent Upg Alt passive). Reads
  ``ent_passive_buff``'s revenge_damage mech count via DbBuff.

* ``unic_unit_lich_dragon_passive`` (Lich Dragon corpse absorb). Reads
  ``lich_dragon_corpse_buff.data.stats.finalAbilityDamageBonusPercent``.

* ``unic_unit_lich_dragon_passive_2`` (Lich Dragon revive). Reads
  ``ability[1].selfMechanics[0].values[2]`` -> 1.0 -> 100%.

* ``unic_unit_twinkle_ability_3`` (Twinkle Upg Alt "Spell Power by X").
  Reads side_buff_unit_twinkle's effect base via DbSideBuff.
"""

OVERRIDES_TEXT = """
modInt unic_unit_twinkleManaAbility_base
{
    CurrentAbility( base, "damageDealer.targetMechanics[0].values[2]" )
    Text( return, base )
}

modInt unic_unit_twinkleManaAbility_perCount
{
    CurrentAbility( perCount, "damageDealer.targetMechanics[0].values[4]" )
    Text( return, perCount )
}

modInt unic_unit_twinkleManaAbility_Count
{
    CurrentAbility( count, "damageDealer.targetMechanics[0].values[3]" )
    Text( return, count )
}

int unic_unit_ent_passive_4
{
    CurrentUnitConfig( obstacleSid, "passives[1].actions[0].damageDealer.targetMechanics[0].values[1]" )
    DbObstacle( hp, obstacleSid, "stats.hp" )
    Text( return, hp )
}

modPercentNumeric unic_unit_black_dragon_ability_3
{
    CurrentAbility( mult, "damageDealer.statDmgMult" )
    Text( return, mult )
}

modPercentNumeric unic_unit_hydra_passive_2
{
    CurrentUnitConfig( buffSid, "passives[0].actions[2].damageDealer.buff.sid" )
    DbBuff( mod, buffSid, "data.stats.outAllDmgMod" )
    Text( return, mod )
}

int unic_unit_hydra_passive_2_duration
{
    CurrentUnitConfig( dur, "passives[0].actions[2].damageDealer.buff.duration" )
    Text( return, dur )
}

int unic_unit_ent_passive_3
{
    CurrentUnitConfig( buffSid, "passives[2].actions[0].damageDealer.buff.sid" )
    DbBuff( count, buffSid, "actions[0].damageDealer.targetMechanics[0].values[2]" )
    Text( return, count )
}

modPercentNumeric unic_unit_lich_dragon_passive
{
    CurrentUnitConfig( buffSid, "passives[0].actions[0].damageDealer.targetMechanics[0].values[2]" )
    DbBuff( pct, buffSid, "data.stats.finalAbilityDamageBonusPercent" )
    Text( return, pct )
}

modPercentNumeric unic_unit_lich_dragon_passive_2
{
    CurrentUnitConfig( pct, "abilities[1].selfMechanics[0].values[2]" )
    Text( return, pct )
}

int unic_unit_twinkle_ability_3
{
    CurrentAbility( infoSid, "damageDealer.targetMechanics[0].values[0]" )
    DbSideBuff( sp, infoSid, "heroStat.spellPower" )
    Text( return, sp )
}
"""
