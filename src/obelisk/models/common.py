"""Shared types used across multiple entity kinds."""

from __future__ import annotations

from enum import StrEnum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict


class Faction(StrEnum):
    """The six factions in Olden Era as of release, plus neutral.

    Source files use "fraction" (translation artifact); we normalize to the
    correct English here. The string values match the ``id`` field in
    ``Core/DB/fractions/*.json``.
    """

    HUMAN = "human"
    UNDEAD = "undead"
    DUNGEON = "dungeon"
    NATURE = "nature"
    DEMON = "demon"
    UNFROZEN = "unfrozen"
    NEUTRAL = "neutral"


# Type alias: a SID is just a string, but giving it a name makes intent obvious
# in canonical record types and emitter code. Using PEP 484 TypeAlias rather
# than PEP 695 ``type`` syntax to keep Python 3.11 compatibility (``type`` is 3.12+).
Sid: TypeAlias = str


class SidRef(BaseModel):
    """A reference to a localizable string.

    Sometimes the source JSON gives us just the SID; sometimes it gives us a
    SID plus extra metadata (icon path, etc.). Wrap them uniformly so the
    emitter has a stable shape to render.
    """

    model_config = ConfigDict(frozen=True)

    sid: Sid
    icon: str | None = None


class ResourceCost(BaseModel):
    """A single (resource, amount) entry in a multi-resource cost.

    Source shape: ``{"name": "gold", "cost": 2400}``. Renamed for clarity.
    """

    model_config = ConfigDict(frozen=True)

    resource: str
    amount: int
