"""Canonical FactionRecord model.

One record per faction loaded from ``Core/DB/fractions/<n>_<id>.json``.
Per D-025: Faction is its own dedicated table (not an Entry); city
names are emitted as Entry rows of ``type=FactionCityName``; faction
laws are deferred (separate decision when we tackle the
``DB/fractions_laws/`` work).

The source JSON's ``narrativeDesc`` field is dropped: the
``<id>_narrative_desc`` SIDs are dead pointers in the L10n corpus
(present in JSON, absent in every language file). If a future patch
populates them we'll add them back.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from artificer.models.common import Sid


class FactionRecord(BaseModel):
    """A single faction's structural data.

    Field renames vs. source JSON:

    * ``fraction*`` → ``faction*`` everywhere (source uses the
      translation-artifact spelling; we normalize on extract).
    * ``iconFractionLaws`` → ``icon_faction_laws``.
    * ``resourceName`` → ``resource``.
    * ``cityNames`` → ``city_names``.
    * ``narrativeDesc`` → dropped (dead L10n pointer; see module
      docstring).
    """

    model_config = ConfigDict(frozen=True)

    id: str
    name_sid: Sid
    desc_sid: Sid

    icon: str
    icon_faction_laws: str

    biome: str
    resource: str

    city_names: tuple[Sid, ...]

    # Source path for traceability (relative to Core/), useful for the
    # diff/audit pipelines.
    source_path: str
