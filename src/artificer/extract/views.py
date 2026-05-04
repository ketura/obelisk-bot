"""Load units_views/<faction>/<id>_v.json files.

The view files are the authoritative SID list per unit — they enumerate the
named abilities and passives a unit displays, with explicit ``name`` and
``description`` SIDs. We use them as the primary source for UnitAbility row
generation. Animation/mesh fields are ignored (out of scope).
"""

from __future__ import annotations

from typing import Any

from artificer.extract.loader import CorePaths, iter_array, load_json


def load_views(paths: CorePaths) -> dict[str, dict[str, Any]]:
    """Walk all ``units_views/<faction>/*_v.json`` and key by unit id."""
    views: dict[str, dict[str, Any]] = {}
    root = paths.units_views_dir()
    if not root.is_dir():
        return views
    for jp in sorted(root.rglob("*_v.json")):
        if not jp.is_file():
            continue
        try:
            doc = load_json(jp)
            for entry in iter_array(doc):
                if not isinstance(entry, dict):
                    continue
                uid = entry.get("id")
                if isinstance(uid, str):
                    views[uid] = entry
        except Exception:
            continue
    return views
