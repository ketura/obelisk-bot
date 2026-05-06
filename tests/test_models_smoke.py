"""Smoke tests for the canonical models. Run after `uv pip install -e .[dev]`."""

from __future__ import annotations

from obelisk.models import (
    Faction,
    LocalizationCorpus,
    LocalizationEntry,
    ResourceCost,
    Unit,
    UnitStats,
)


def test_faction_values() -> None:
    assert Faction.HUMAN.value == "human"
    assert {f.value for f in Faction} >= {"human", "undead", "dungeon", "nature", "demon", "unfrozen"}


def test_unit_constructable_with_minimum_fields() -> None:
    u = Unit(
        id="angel",
        faction=Faction.HUMAN,
        tier=7,
        source_path="DB/units/units_logics/humans/angel_l.json",
        name_sid="angel_name",
        stats=UnitStats(
            hp=225, offence=30, defence=30,
            damage_min=50, damage_max=75,
            initiative=8, speed=4,
        ),
    )
    assert u.id == "angel"
    assert u.stats.hp == 225
    assert u.faction is Faction.HUMAN
    # frozen
    try:
        u.id = "demon"  # type: ignore[misc]
    except Exception:
        pass
    else:
        raise AssertionError("Unit should be frozen")


def test_localization_corpus_basic() -> None:
    c = LocalizationCorpus()
    c.add(LocalizationEntry(sid="angel_name", language="english", text="Angel", source_kind="heroInfo"))
    c.add(LocalizationEntry(sid="angel_name", language="russian", text="Ангел", source_kind="heroInfo"))
    assert c.get("angel_name", "english") == "Angel"
    assert c.get("angel_name", "russian") == "Ангел"
    assert c.get("angel_name", "french") is None
    assert c.languages_for("angel_name") == {"english", "russian"}


def test_resource_cost() -> None:
    rc = ResourceCost(resource="gold", amount=2400)
    assert rc.resource == "gold"
    assert rc.amount == 2400
