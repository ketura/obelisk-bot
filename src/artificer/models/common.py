"""Shared types used across multiple entity kinds."""

from __future__ import annotations

from enum import Enum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict


class Faction(str, Enum):
    """The six factions in Olden Era as of release, plus neutral.

    Source files use "fraction" (translation artifact); we normalize to the
    correct English here. The string values match the ``id`` field in
    ``Core/DB/fractions/*.json``.

    Subclasses ``str`` rather than ``StrEnum`` to support Python 3.10
    (``StrEnum`` is 3.11+). Behavior is equivalent for our uses.
    """

    HUMAN = "human"
    UNDEAD = "undead"
    DUNGEON = "dungeon"
    NATURE = "nature"
    DEMON = "demon"
    UNFROZEN = "unfrozen"
    NEUTRAL = "neutral"

    def __str__(self) -> str:
        return self.value


# Type alias: a SID is just a string, but giving it a name makes intent obvious
# in canonical record types and emitter code. Using PEP 484 TypeAlias rather
# than PEP 695 ``type`` syntax to keep Python 3.10 compatibility.
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
