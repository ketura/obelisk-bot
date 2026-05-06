"""PlaceholderResolver: substitute ``{N}`` in L10n text.

Composes :class:`ArgsIndex` (SID -> arg names) and :class:`Interpreter`
(arg name -> string value), plus :func:`html_to_wiki` for the inline
HTML->wiki tag conversion.

Pipe-syntax semantics (mirroring OldenEraExplorer):

  ``leftExpr|altSid``

Always renders the alt template. The left value is only spliced into
``{0}`` if the alt template needs more placeholders than its own args
provide. (NOT a fallback / try-each-in-order semantics.)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from artificer.models.localization import LocalizationCorpus
from artificer.resolve.args import ArgsIndex, load_args_index
from artificer.resolve.buffs import BuffIndex, load_buff_index
from artificer.resolve.interpreter import Interpreter
from artificer.resolve.obstacles import ObstacleIndex, load_obstacle_index
from artificer.resolve.scripts import ScriptRegistry
from artificer.resolve.side_buffs import SideBuffIndex, load_side_buff_index
from artificer.resolve.traps import TrapIndex, load_trap_index
from artificer.resolve.wikitext import html_to_wiki

_PLACEHOLDER_RE = re.compile(r"\{(\d+)\}")


class PlaceholderResolver:
    def __init__(
        self,
        args_index: ArgsIndex,
        interpreter: Interpreter,
        corpus: LocalizationCorpus | None = None,
    ) -> None:
        self.args_index = args_index
        self.interpreter = interpreter
        self.corpus = corpus

    def resolve(
        self,
        sid: str,
        text: str,
        unit_json: dict[str, Any] | None,
        lang: str = "english",
        ability_json: dict[str, Any] | None = None,
        spec_json: dict[str, Any] | None = None,
        magic_json: dict[str, Any] | None = None,
        set_json: dict[str, Any] | None = None,
        artifact_json: dict[str, Any] | None = None,
    ) -> str:
        if not text:
            return text or ""
        return self._resolve_inner(
            sid, text, unit_json, lang, ability_json, spec_json, magic_json,
            set_json, artifact_json, _seen=set(),
        )

    def _resolve_inner(
        self,
        sid: str,
        text: str,
        unit_json: dict[str, Any] | None,
        lang: str,
        ability_json: dict[str, Any] | None,
        spec_json: dict[str, Any] | None,
        magic_json: dict[str, Any] | None,
        set_json: dict[str, Any] | None,
        artifact_json: dict[str, Any] | None,
        _seen: set[str],
    ) -> str:
        args = self.args_index.get(sid)
        if not args:
            return html_to_wiki(text)

        ctx = {
            "unit_json": unit_json or {},
            "ability_json": ability_json or {},
            "spec_json": spec_json or {},
            "magic_json": magic_json or {},
            "set_json": set_json or {},
            "artifact_json": artifact_json or {},
        }
        values = self._evaluate_args(
            args, ctx, unit_json, lang, ability_json, spec_json, magic_json,
            set_json, artifact_json, _seen,
        )

        def sub(match: re.Match[str]) -> str:
            i = int(match.group(1))
            if i < len(values) and values[i] is not None:
                return values[i]  # type: ignore[return-value]
            return match.group(0)

        result = _PLACEHOLDER_RE.sub(sub, text)
        return html_to_wiki(result)

    def _evaluate_args(
        self,
        args: list[str],
        ctx: dict[str, Any],
        unit_json: dict[str, Any] | None,
        lang: str,
        ability_json: dict[str, Any] | None,
        spec_json: dict[str, Any] | None,
        magic_json: dict[str, Any] | None,
        set_json: dict[str, Any] | None,
        artifact_json: dict[str, Any] | None,
        _seen: set[str],
    ) -> list[str | None]:
        values: list[str | None] = []
        for arg_name in args:
            values.append(
                self._eval_expr(arg_name, ctx, unit_json, lang, ability_json,
                                spec_json, magic_json, set_json, artifact_json, _seen)
            )
        return values

    def _eval_expr(
        self,
        expr: str,
        ctx: dict[str, Any],
        unit_json: dict[str, Any] | None,
        lang: str,
        ability_json: dict[str, Any] | None,
        spec_json: dict[str, Any] | None,
        magic_json: dict[str, Any] | None,
        set_json: dict[str, Any] | None,
        artifact_json: dict[str, Any] | None,
        _seen: set[str],
    ) -> str | None:
        """Evaluate one args-side expression.

        Mirrors OldenEraExplorer's resolution semantics.

        * Empty -> "".
        * Quoted literal -> as-is (without quotes).
        * Numeric literal -> as-is.
        * ``leftExpr|altSid`` -> always renders the alt template. Left value
          only fills ``{0}`` when alt template has more placeholders than
          its own args provide.
        * Otherwise -> try as a script function, then as an aux SID.
        """
        expr = expr.strip()
        if not expr:
            return ""

        if len(expr) >= 2 and expr[0] == '"' and expr[-1] == '"':
            return expr[1:-1]
        if _is_numeric_literal(expr):
            return expr

        if "|" in expr:
            left_expr, _pipe, alt_sid = expr.partition("|")
            alt_sid = alt_sid.strip()
            left_val = self._eval_expr(
                left_expr, ctx, unit_json, lang, ability_json,
                spec_json, magic_json, set_json, artifact_json, _seen
            )
            if self.corpus is None:
                return left_val
            alt_text = self.corpus.get(alt_sid, lang)
            alt_lang = lang
            if not alt_text and lang != "english":
                alt_text = self.corpus.get(alt_sid, "english")
                alt_lang = "english"
            if not alt_text:
                return left_val
            alt_indices = sorted(set(int(m) for m in _PLACEHOLDER_RE.findall(alt_text)))
            if not alt_indices:
                return alt_text
            alt_args = self.args_index.get(alt_sid)
            use_left_for_zero = 0 in alt_indices and len(alt_args) < len(alt_indices)
            sub_map: dict[int, str | None] = {}
            sub_seen = _seen | {alt_sid}
            for j in alt_indices:
                if use_left_for_zero and j == 0:
                    sub_map[j] = left_val
                    continue
                k = j - 1 if use_left_for_zero else j
                if k >= len(alt_args):
                    continue
                sub_map[j] = self._eval_expr(
                    alt_args[k], ctx, unit_json, alt_lang, ability_json,
                    spec_json, magic_json, set_json, artifact_json, sub_seen
                )

            def _sub(m: re.Match[str]) -> str:
                idx = int(m.group(1))
                v = sub_map.get(idx)
                return v if v is not None else m.group(0)

            return _PLACEHOLDER_RE.sub(_sub, alt_text)

        v = self.interpreter.evaluate(expr, ctx)
        if v is not None:
            return v
        if self.corpus is not None and expr not in _seen:
            sub_text = self.corpus.get(expr, lang)
            if sub_text is not None:
                return self._resolve_inner(
                    expr, sub_text, unit_json, lang, ability_json,
                    spec_json, magic_json, set_json, artifact_json, _seen | {expr}
                )
        return None


def _is_numeric_literal(s: str) -> bool:
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def build_resolver(
    core_root: Path,
    corpus: LocalizationCorpus | None = None,
) -> PlaceholderResolver:
    """Convenience: parse scripts + args + buffs from a Core/ directory."""
    from artificer.resolve._overrides import OVERRIDES_TEXT

    registry = ScriptRegistry()
    registry.parse_dir(core_root / "DB" / "info")
    registry.parse_text(OVERRIDES_TEXT)
    args = load_args_index(core_root / "Lang" / "args")
    buffs = load_buff_index(core_root / "DB" / "buffs")
    obstacles = load_obstacle_index(core_root / "DB" / "field_objects" / "obstacles")
    side_buffs = load_side_buff_index(core_root / "DB" / "side_buffs")
    traps = load_trap_index(core_root / "DB" / "field_objects" / "traps")
    return PlaceholderResolver(
        args,
        Interpreter(
            registry, buffs=buffs, obstacles=obstacles,
            side_buffs=side_buffs, traps=traps,
        ),
        corpus=corpus,
    )
