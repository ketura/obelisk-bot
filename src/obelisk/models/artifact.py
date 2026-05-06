"""Canonical Artifact model.

Per D-031: artifacts (the in-game equipment items) live in the
``Artifact`` Cargo table; their bonuses flow into the unified
``Bonus`` table with ``parent_type='artifact'``. Artifact sets are
deferred (the nested bonuses[].heroBonuses[] structure needs a
separate decision pass).

Source folder is ``DB/items/items/`` — the file/folder naming uses
the source's "item" terminology since that's what the JSON ships,
but the wiki side surfaces them as "artifacts" per the in-game
player-facing label.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from obelisk.models.common import Sid
from obelisk.models.hero import Bonus


class ArtifactRecord(BaseModel):
    """One artifact / equipment record.

    Identity, slot/rarity classification, English name + description
    inline, plus the resolved English upgrade and narrative
    descriptions. Bonuses are emitted as separate Bonus rows with
    ``parent_type='artifact'``.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name_sid: Sid
    description_sid: Sid
    upgrade_description_sid: Sid | None = None
    narrative_description_sid: Sid | None = None
    icon: str

    slot: str  # armor, head, ring, item_slot, ...
    rarity: str  # common, rare, epic, legendary
    artifact_set_id: str | None = None

    goods_value: int
    max_level: int

    # Sparse: only present on artifacts that can level up
    cost_base: int | None = None
    cost_per_level: int | None = None

    reward_for_destroy: int | None = None

    is_special_item: bool = False
    use_expand_tooltip: bool | None = None  # source sometimes ships string "false"
    can_destroy: bool | None = None
    can_apply_bonus_always: bool | None = None

    bonuses: tuple[Bonus, ...]
    source_path: str

    # Source JSON kept for placeholder resolver context if needed.
    raw_json: dict[str, Any] = Field(default_factory=dict)


class ArtifactExtractionResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    artifacts: tuple[ArtifactRecord, ...]
