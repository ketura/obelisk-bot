"""Build the global :class:`LocalizationCorpus` from a patch dump."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from artificer.extract.loader import CorePaths, iter_tokens, load_json
from artificer.models.localization import (
    SUPPORTED_LANGUAGES,
    LocalizationCorpus,
    LocalizationEntry,
)


def load_localization_corpus(
    paths: CorePaths,
    languages: Iterable[str] | None = None,
) -> LocalizationCorpus:
    """Walk ``Core/Lang/<lang>/texts/*.json`` and assemble the corpus.

    Args:
        paths: Resolved core paths.
        languages: Optional restricted set of language directory names. If
            None, ingests all directories present (sanity-checked against
            :data:`SUPPORTED_LANGUAGES` — unknown dirs trigger a warning but
            are still ingested).

    Returns:
        A populated :class:`LocalizationCorpus`.
    """
    selected = set(languages) if languages else None
    corpus = LocalizationCorpus()

    for lang_dir in paths.language_dirs():
        lang_name = lang_dir.name
        if selected is not None and lang_name not in selected:
            continue
        if lang_name not in SUPPORTED_LANGUAGES:
            # Don't fail — a future patch may add a language. Just log via
            # caller's logger eventually; for now, ingest anyway.
            pass

        texts_dir = lang_dir / "texts"
        if not texts_dir.is_dir():
            continue

        for json_path in sorted(texts_dir.glob("*.json")):
            source_kind = json_path.stem  # e.g. "unitsAbility"
            doc = load_json(json_path)
            for token in iter_tokens(doc):
                sid = token.get("sid")
                text = token.get("text")
                if sid is None or text is None:
                    continue
                corpus.add(
                    LocalizationEntry(
                        sid=str(sid),
                        language=lang_name,
                        text=str(text),
                        source_kind=source_kind,
                    )
                )

    return corpus


def load_english_only(paths: CorePaths) -> LocalizationCorpus:
    """Convenience: ingest just English. Useful for fast iteration during dev."""
    return load_localization_corpus(paths, languages={"english"})
