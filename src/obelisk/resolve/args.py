"""Load ``Core/Lang/args/*.json`` into a SID → arg-list index.

Each entry maps a translatable SID to a list of script function names.
When resolving the SID's text, each ``{N}`` placeholder is filled by
evaluating the N-th arg function.
"""

from __future__ import annotations

import json
from pathlib import Path


class ArgsIndex:
    """SID → list of script function names."""

    def __init__(self) -> None:
        self._map: dict[str, list[str]] = {}

    def load_dir(self, root: Path) -> None:
        for fp in sorted(root.glob("*.json")):
            try:
                with fp.open(encoding="utf-8-sig") as f:
                    doc = json.load(f)
            except Exception:
                continue
            if isinstance(doc, list):
                entries = doc
            elif isinstance(doc, dict):
                entries = doc.get("tokensArgs") or doc.get("array") or []
            else:
                entries = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                sid = entry.get("sid")
                args = entry.get("args")
                if isinstance(sid, str) and isinstance(args, list):
                    self._map[sid] = [str(a) for a in args]

    def get(self, sid: str) -> list[str]:
        return self._map.get(sid, [])

    def __len__(self) -> int:
        return len(self._map)


def load_args_index(args_root: Path) -> ArgsIndex:
    idx = ArgsIndex()
    idx.load_dir(args_root)
    return idx
