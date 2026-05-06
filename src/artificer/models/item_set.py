"""Canonical ItemSet / ItemSetTier models.

Per D-032: 24 item sets in ``DB/items/item_sets/item_sets.json``.
Each set has 1-3 tiers; each tier has a required-items threshold,
a description SID, and a list of bonus effects. Bonuses flow into
the unified ``Bonus`` table with ``parent_type='item_set_tier'``.

Tier ids are synthesized as ``<set_id>_tier_<ordinal>`` so the Bonus
parent_id join is clean. The "item set" terminology preserves the
source naming (vs the artifact/Artifact rename done elsewhere) at
the user's request — both source and players colloquially call
these "item sets".
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from artificer.models.common import Sid
from artificer.models.hero import Bonus


class ItemSetTierRecord(BaseModel):
    """One unlock tier of an item set. The hero unlocks the tier's
    bonuses by equipping ``required_amount`` items from the set."""

    model_config = ConfigDict(frozen=True)

    id: str           # synthesized: <set_id>_tier_<ordinal>
    set_id: str
    ordinal: int      # 0-based position in the source bonuses[] array
    required_amount: int
    description_sid: Sid
    bonuses: tuple[Bonus, ...]


class ItemSetRecord(BaseModel):
    """A named item set — a curated group of artifacts that grant
    additional bonuses when the hero equips multiple pieces.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name_sid: Sid
    items_in_set: tuple[str, ...]   # references Artifact.id
    tiers: tuple[ItemSetTierRecord, ...]
    source_path: str

    # Source JSON kept for placeholder resolver context.
    # CurrentItemSet reads paths like "config.bonuses[0].heroBonuses[0].parameters[1]"
    # so emit wraps the raw dict as {"config": raw_json}.
    raw_json: dict[str, Any] = Field(default_factory=dict)


class ItemSetExtractionResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    item_sets: tuple[ItemSetRecord, ...]
