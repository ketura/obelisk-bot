"""SID-ownership analyzer (unit-first).

Each unit walks its ``base_sid`` chain to collect ancestor IDs, then claims
SIDs whose primary owner is in that ancestor set. Primary owner = the unit
whose id is the longest exact-prefix match (computed once per SID upfront).

For ability-slot SIDs that come in upgrade-tier variants
(``..._description_upg``, ``..._description_upg_alt``), each unit picks the
most appropriate variant based on its own variant level (derived from its id
suffix), with fallback to the base form.

For unit-level SIDs (``_name``, ``_narrativeDescription``), the most specific
ancestor wins — godslayer_upg gets ``godslayer_upg_name``, not
``godslayer_name``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from obelisk.models.localization import LocalizationCorpus
from obelisk.models.unit import Unit, UnitAbility


# Ordinal slot. Two variant positions:
#   pre-field (advanced) → distinct slot
#   post-field (upg/upg_alt/alt) → same slot, different upgrade-tier text
_ORDINAL_SLOT_RE = re.compile(
    r"^(?P<kind>ability|passive|buff|debuff|selfbuff|additionbuff)"
    r"_(?P<ordinal>\d+)"
    r"(?:_(?P<variant_pre>advanced))?"
    r"_(?P<field>name|description|info)"
    r"(?:_(?P<variant_post>upg|upg_alt|alt))?$"
)

# Singleton slot (no ordinal).
_SINGLETON_SLOT_RE = re.compile(
    r"^(?P<kind>buff|debuff|selfbuff|additionbuff|copy_buff|curse|blood)"
    r"_(?P<field>name|description|info)"
    r"(?:_(?P<variant_post>upg|upg_alt|alt))?$"
)

_UNIT_LEVEL_SUFFIXES: dict[str, str] = {
    "name": "name_sid",
    "narrativeDescription": "narrative_description_sid",
    "description": "description_sid",
    "lore": "lore_sid",
    "story": "story_sid",
    "info": "info_sid",
}


@dataclass
class OwnershipClaims:
    """The set of SIDs an entity claims, partitioned by what they map to."""

    name_sid: str | None = None
    narrative_description_sid: str | None = None
    description_sid: str | None = None

    unit_abilities: list[UnitAbility] = field(default_factory=list)
    extra_sids: list[tuple[str, str]] = field(default_factory=list)

    @property
    def all_owned_sids(self) -> set[str]:
        owned: set[str] = set()
        for sid in (self.name_sid, self.narrative_description_sid, self.description_sid):
            if sid:
                owned.add(sid)
        for ability in self.unit_abilities:
            owned.add(ability.name_sid)
            if ability.desc_sid:
                owned.add(ability.desc_sid)
        for _, sid in self.extra_sids:
            owned.add(sid)
        return owned


def _variant_level(unit_id: str) -> str | None:
    """Derive a unit's upgrade-tier from its id suffix.

    Returns 'upg_alt' for ``_upg_alt`` ids, 'upg' for ``_upg`` ids,
    None for base.
    """
    if unit_id.endswith("_upg_alt"):
        return "upg_alt"
    if unit_id.endswith("_upg"):
        return "upg"
    return None


def _variant_priority(unit_variant: str | None) -> tuple[str | None, ...]:
    """Ordered fallback list of post-field variants for this unit.

    A unit at variant level X tries its own variant first, then progressively
    less-specific variants, ending at the base (None).
    """
    if unit_variant == "upg_alt":
        return ("upg_alt", "upg", None)
    if unit_variant == "upg":
        return ("upg", None)
    return (None,)


def assign_ownership(
    *,
    units: Sequence[Unit],
    corpus: LocalizationCorpus,
) -> dict[str, OwnershipClaims]:
    """Assign SIDs to units. Each unit gets its own claims, with abilities
    duplicated across upgrade chains using the appropriate variant text."""
    unit_index: dict[str, Unit] = {u.id: u for u in units}
    sorted_ids = sorted(unit_index.keys(), key=len, reverse=True)

    # Step 1: primary owner per SID (one-shot longest exact-prefix match).
    primary_owner: dict[str, str] = {}
    for sid in corpus.all_sids():
        for cid in sorted_ids:
            if sid.startswith(cid + "_") and len(sid) > len(cid) + 1:
                primary_owner[sid] = cid
                break

    # Step 2: bucket SIDs by primary owner and parsed shape.
    # raw_slots: owner_id -> (kind, ordinal, pre_variant) -> post_variant -> field -> sid
    raw_slots: dict[str, dict[tuple[str, int | None, str | None], dict[str | None, dict[str, str]]]] = {}
    raw_unit_level: dict[str, dict[str, str]] = {}
    raw_extras: dict[str, list[tuple[str, str]]] = {}

    for sid, owner in primary_owner.items():
        suffix = sid[len(owner) + 1 :]

        m = _ORDINAL_SLOT_RE.match(suffix)
        if m:
            slot_key = (m.group("kind"), int(m.group("ordinal")), m.group("variant_pre"))
            post = m.group("variant_post")
            (
                raw_slots
                .setdefault(owner, {})
                .setdefault(slot_key, {})
                .setdefault(post, {})[m.group("field")]
            ) = sid
            continue

        m = _SINGLETON_SLOT_RE.match(suffix)
        if m:
            slot_key = (m.group("kind"), None, None)
            post = m.group("variant_post")
            (
                raw_slots
                .setdefault(owner, {})
                .setdefault(slot_key, {})
                .setdefault(post, {})[m.group("field")]
            ) = sid
            continue

        canonical = _UNIT_LEVEL_SUFFIXES.get(suffix)
        if canonical:
            raw_unit_level.setdefault(owner, {})[canonical] = sid
            continue

        raw_extras.setdefault(owner, []).append((suffix, sid))

    # Step 3: for each unit, walk ancestor chain and gather claims.
    claims: dict[str, OwnershipClaims] = {u.id: OwnershipClaims() for u in units}

    for unit in units:
        my_variant = _variant_level(unit.id)
        priority = _variant_priority(my_variant)

        # Walk ancestors, most-specific first (self → base → base.base → ...)
        ancestor_ids: list[str] = []
        cur: Unit | None = unit
        while cur is not None and cur.id not in ancestor_ids:
            ancestor_ids.append(cur.id)
            cur = unit_index.get(cur.base_sid) if cur.base_sid else None

        # Unit-level fields: most-specific ancestor wins
        for ancestor_id in ancestor_ids:
            level_fields = raw_unit_level.get(ancestor_id, {})
            for canonical, sid in level_fields.items():
                if canonical == "name_sid" and claims[unit.id].name_sid is None:
                    claims[unit.id].name_sid = sid
                elif canonical == "narrative_description_sid" and claims[unit.id].narrative_description_sid is None:
                    claims[unit.id].narrative_description_sid = sid
                elif canonical == "description_sid" and claims[unit.id].description_sid is None:
                    claims[unit.id].description_sid = sid

        # Ability slots: each (kind, ordinal, pre_variant) becomes one row,
        # with the post-variant chosen by priority.
        seen_slot_keys: set[tuple[str, int | None, str | None]] = set()
        for ancestor_id in ancestor_ids:
            for slot_key, post_map in raw_slots.get(ancestor_id, {}).items():
                if slot_key in seen_slot_keys:
                    continue  # more-specific ancestor already claimed this

                kind, ordinal, pre_variant = slot_key
                resolved: dict[str, str] = {}
                for post in priority:
                    fields = post_map.get(post)
                    if fields:
                        for f, s in fields.items():
                            resolved.setdefault(f, s)
                # If no fields resolved through priority, fall through to any
                # other available variant (e.g., 'alt' when the unit isn't
                # an upgrade — rare but observed).
                for post, fields in post_map.items():
                    if post in priority:
                        continue
                    for f, s in fields.items():
                        resolved.setdefault(f, s)

                if not resolved:
                    continue

                seen_slot_keys.add(slot_key)
                name_sid = resolved.get("name") or resolved.get("description") or resolved.get("info") or ""
                claims[unit.id].unit_abilities.append(
                    UnitAbility(
                        ability_type=kind,
                        ordinal=ordinal,
                        variant=pre_variant,
                        name_sid=name_sid,
                        desc_sid=resolved.get("description"),
                    )
                )

        # Extras: union from each ancestor (deduped).
        seen_extras: set[tuple[str, str]] = set()
        for ancestor_id in ancestor_ids:
            for entry in raw_extras.get(ancestor_id, []):
                if entry not in seen_extras:
                    seen_extras.add(entry)
                    claims[unit.id].extra_sids.append(entry)

    # Stable ordering
    for c in claims.values():
        c.unit_abilities.sort(
            key=lambda a: (a.ability_type, -1 if a.ordinal is None else a.ordinal, a.variant or "")
        )
        c.extra_sids.sort()

    return claims
