"""Placeholder resolution: substitute ``{0}``/``{1}`` etc in L10n text.

Per D-003, OEE re-implements the game's script engine for placeholder
resolution. We do the same in Python: parse ``Core/DB/info/info_script_unit/*.script``
files, parse ``Core/Lang/args/*.json`` to map SIDs to script function
names, and walk text replacing ``{N}`` placeholders with computed values.

Plus HTML-to-wiki tag conversion (``<b>...</b>`` → ``'''...'''``) since the
two passes coexist on every L10n string.
"""

from artificer.resolve.args import ArgsIndex, load_args_index
from artificer.resolve.interpreter import Interpreter
from artificer.resolve.resolver import PlaceholderResolver, build_resolver
from artificer.resolve.scripts import Function, ScriptRegistry, Statement
from artificer.resolve.wikitext import html_to_wiki

__all__ = [
    "ArgsIndex",
    "Function",
    "Interpreter",
    "PlaceholderResolver",
    "ScriptRegistry",
    "Statement",
    "build_resolver",
    "html_to_wiki",
    "load_args_index",
]
