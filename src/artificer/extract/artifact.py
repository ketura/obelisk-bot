"""Artifact (equipment) extraction.

Walks ``DB/items/items/*.json`` (13 source slot files: armor, head,
ring, boots, etc., plus magic_scroll, enchante_magic_scroll,
mythic_scroll_box, item_slot, unic_slot). 304 records in the
2026-05-03 corpus.

Bonuses are emitted into the unified ``Bonus`` Cargo table with
``parent_type='artifact'`` per D-031. Artifact sets are deferred —
their nested ``bonuses[].heroBonuses[]`` structure needs separate
design.

The source folder name (``items/``) is the JSON's spelling; the
wiki side surfaces these as artifacts per the in-game player-facing
label.
"""

from __future__ import annotations

from typing import Any

from artificer.extract.hero import build_bonus
from artificer.extract.loader import CorePaths, iter_array, load_json
from artificer.models.artifact import ArtifactExtractionResult, ArtifactRecord
from artificer.models.hero import Bonus


def _coerce_bool(value: Any) -> bool | None:
    """Source ships ``useExpandTooltip`` as both bool and the string
    ``"false"``. Normalize."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v == "true":
            return True
        if v == "false":
            return False
    return None


def _build_artifact(raw: dict[str, Any], source_path: str) -> ArtifactRecord | None:
    artifact_id = raw.get("id")
    if not isinstance(artifact_id, str):
        return None

    bonuses: list[Bonus] = []
    for i, b in enumerate(raw.get("bonuses") or ()):
        if isinstance(b, dict):
            bonus = build_bonus(b, parent_type="artifact",
                                parent_id=artifact_id, ordinal=i)
            if bonus is not None:
                bonuses.append(bonus)

    return ArtifactRecord(
        id=artifact_id,
        name_sid=str(raw.get("name", "")),
        description_sid=str(raw.get("description", "")),
        upgrade_description_sid=(
            raw["upgradeDescription"]
            if isinstance(raw.get("upgradeDescription"), str) else None
        ),
        narrative_description_sid=(
            raw["narrativeDescription"]
            if isinstance(raw.get("narrativeDescription"), str) else None
        ),
        icon=str(raw.get("icon", "")),
        slot=str(raw.get("slot_", "")),
        rarity=str(raw.get("rarity", "")),
        artifact_set_id=(
            raw["itemSet"] if isinstance(raw.get("itemSet"), str) else None
        ),
        goods_value=int(raw.get("goodsValue", 0)),
        max_level=int(raw.get("maxLevel", 0)),
        cost_base=(
            int(raw["costBase"])
            if isinstance(raw.get("costBase"), (int, float)) else None
        ),
        cost_per_level=(
            int(raw["costPerLevel"])
            if isinstance(raw.get("costPerLevel"), (int, float)) else None
        ),
        reward_for_destroy=(
            int(raw["rewardForDestroy"])
            if isinstance(raw.get("rewardForDestroy"), (int, float)) else None
        ),
        is_special_item=bool(raw.get("isSpecialItem", False)),
        use_expand_tooltip=_coerce_bool(raw.get("useExpandTooltip")),
        can_destroy=_coerce_bool(raw.get("canDestroy")),
        can_apply_bonus_always=_coerce_bool(raw.get("canApplyBonusAlways")),
        bonuses=tuple(bonuses),
        source_path=source_path,
        raw_json=raw,
    )


def extract_artifacts(paths: CorePaths) -> ArtifactExtractionResult:
    """Walk ``DB/items/items/*.json`` and return all ArtifactRecord
    entries. See D-031."""
    out: list[ArtifactRecord] = []
    for p in sorted((paths.db / "items" / "items").glob("*.json")):
        rel = p.relative_to(paths.core_root).as_posix()
        doc = load_json(p)
        for raw in iter_array(doc):
            if not isinstance(raw, dict):
                continue
            artifact = _build_artifact(raw, source_path=rel)
            if artifact is not None:
                out.append(artifact)
    out.sort(key=lambda a: a.id)
    return ArtifactExtractionResult(artifacts=tuple(out))
