"""Stub — concept-to-SID registry no longer used (see D-015).

The views file's name SIDs are taken verbatim; we don't resolve concepts to
SID slots anymore. Empty registries kept here so legacy audit imports keep
working until cleanup.
"""

from __future__ import annotations

UNIVERSAL_CONCEPT_SIDS: dict[str, dict[str, str]] = {}
FAMILY_REGISTRY: dict[str, dict[str, tuple[str, int]]] = {}


def resolve_concept_sids(
    concept: str,  # noqa: ARG001
    rank: int | None,  # noqa: ARG001
    family_root: str | None,  # noqa: ARG001
    unit_variant: str | None,  # noqa: ARG001
) -> tuple[str | None, str | None, tuple[str, int | None] | None]:
    """No-op. Returns ``(None, None, None)``."""
    return (None, None, None)
