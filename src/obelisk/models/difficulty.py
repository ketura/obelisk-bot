"""Canonical Difficulty model.

Per D-039: 5 entries from ``DB/difficulties.json`` —
Easy / Normal / Hard / Expert / Impossible. Each carries the balance
inputs the engine actually uses: per-side starting-resource buckets
and the neutral-power multiplier (the global scalar applied to
adventure-map encounter strength).

Two source-data quirks worth flagging:

* ``nameSid`` values like ``EasyDifficultySid`` are *not* L10n
  entries — they don't resolve in any ``Lang/<locale>/`` file.
  Stored as-is for fidelity; the ``id`` (``Easy``/``Normal``/…) is
  the actual display name.
* ``descriptionSid`` carries literal English text ("This is an Easy
  difficulty setting."), not an L10n key. Stored as a plain
  description string column.

The two sibling files ``DB/difficulties_lobby.json`` and
``DB/difficulties_lobby_solo.json`` are present but ship empty
``difficultiesConfigs`` arrays in 2026-05-05 — extracted but
yield no rows.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DifficultyRecord(BaseModel):
    """One difficulty configuration."""

    model_config = ConfigDict(frozen=True)

    id: str                        # source ``sid`` field — Easy / Normal / Hard / Expert / Impossible
    name_sid: str | None = None    # ``nameSid`` from source; not actually in L10n corpus
    description: str | None = None # source ``descriptionSid`` carries literal English text
    neutral_power_multiplier: float | None = None

    # Player + AI starting resources. Source uses 'alchemicalDust';
    # we normalize to 'dust' to match resources_info.json.
    player_gold: int | None = None
    player_wood: int | None = None
    player_ore: int | None = None
    player_gemstones: int | None = None
    player_crystals: int | None = None
    player_mercury: int | None = None
    player_dust: int | None = None

    ai_gold: int | None = None
    ai_wood: int | None = None
    ai_ore: int | None = None
    ai_gemstones: int | None = None
    ai_crystals: int | None = None
    ai_mercury: int | None = None
    ai_dust: int | None = None

    source_path: str


class DifficultyExtractionResult(BaseModel):
    """All difficulty rows produced from a single patch extract."""

    model_config = ConfigDict(frozen=True)

    difficulties: tuple[DifficultyRecord, ...]
