"""The global localization corpus.

The source data lives at ``Core/Lang/<language>/texts/*.json``. Every file is a
flat ``{"tokens": [{"sid": "...", "text": "..."}, ...]}``. There is no
per-entity localization structure — every translatable string is just a SID
mapping. We mirror that exactly.

For Cargo:

* One global table ``Localization(sid, language, text, source_kind)``.
* ``source_kind`` is the source filename stem (``unitsAbility``, ``magic``,
  ``factionLaws``, etc.) and is preserved so the diff engine can categorize
  text changes.
* ~12,500 SIDs × 16 languages = ~200,000 rows total. Cargo handles that fine
  when distributed across entity pages and bucket pages.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


# 16 languages present in the source corpus as of release 2026-04-30 — note
# OEE's README says 14, but empirically the corpus ships 16 (zhCN and zhTW are
# distinct Simplified and Traditional Chinese; BRportugese is its own entry).
# Names match the directory names under Core/Lang/ verbatim, including the
# source's "BRportugese" spelling.
SUPPORTED_LANGUAGES: frozenset[str] = frozenset(
    {
        "BRportugese",
        "czech",
        "english",
        "french",
        "german",
        "hungarian",
        "italian",
        "japanese",
        "korean",
        "polish",
        "russian",
        "spanish",
        "turkish",
        "ukrainian",
        "zhCN",
        "zhTW",
    }
)


class LocalizationEntry(BaseModel):
    """One row in the Localization Cargo table."""

    model_config = ConfigDict(frozen=True)

    sid: str
    language: str
    text: str
    source_kind: str


class LocalizationCorpus(BaseModel):
    """All localization entries for one extracted patch.

    Indexed by ``(sid, language)`` for fast lookup. Ownership of SIDs to
    entities is determined separately (see ``obelisk.extract.ownership``);
    the corpus itself is just the raw mapping.
    """

    model_config = ConfigDict(frozen=False)

    entries: dict[tuple[str, str], LocalizationEntry] = {}

    def get(self, sid: str, language: str) -> str | None:
        entry = self.entries.get((sid, language))
        return entry.text if entry else None

    def has_sid(self, sid: str) -> bool:
        return any(s == sid for s, _ in self.entries)

    def all_sids(self) -> set[str]:
        return {s for s, _ in self.entries}

    def languages_for(self, sid: str) -> set[str]:
        return {lang for s, lang in self.entries if s == sid}

    def add(self, entry: LocalizationEntry) -> None:
        self.entries[(entry.sid, entry.language)] = entry
