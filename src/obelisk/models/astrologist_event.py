"""Canonical AstrologistEvent model.

Per D-038: one row per astrologist week or month event — the
periodically-rolled global modifiers the in-game Astrologer
announces ("Week of Sorcery: All heroes' mana is fully restored").

Sourced from ``DB/weeks/weeks.json`` (15 weeks) and
``DB/weeks/months.json`` (11 months) as identity rows; per-entry
``rollChance`` and the global "count to return" thresholds come
from ``DB/weeks_info.json``.

The mechanical effect of each event lives in a buff entry pointed
at by ``buff_sid`` (in ``DB/buffs/`` for weeks, also ``DB/buffs/``
for months). The buff data itself is not extracted here — the
description text on the event covers the player-facing summary.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from obelisk.models.common import Sid


class AstrologistEventRecord(BaseModel):
    """One astrologist week or month event."""

    model_config = ConfigDict(frozen=True)

    id: str
    category: str            # 'week' | 'month'
    name_sid: Sid
    desc_sid: Sid | None = None
    icon: str | None = None

    # Mechanical pointer — buff applied while this event is active.
    buff_sid: str | None = None

    # Roll-table membership (from weeks_info.json).
    roll_chance: int | None = None

    # Global threshold for the same event re-rolling: weeks_info.json's
    # ``countToReturnWeek`` / ``countToReturnMonth``. Per-event the
    # value is shared across the whole category, but storing on each
    # row keeps queries to one table.
    count_to_return: int | None = None

    source_path: str


class AstrologistEventExtractionResult(BaseModel):
    """All astrologist-event rows produced from a single patch extract."""

    model_config = ConfigDict(frozen=True)

    events: tuple[AstrologistEventRecord, ...]
