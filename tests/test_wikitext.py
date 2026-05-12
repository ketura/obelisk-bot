"""Tests for :func:`obelisk.resolve.wikitext.html_to_wiki`.

This is the leaf-text normalizer applied to every resolved description
that ends up in a template parameter. The behaviors it owns:

* ``<b>``/``<i>`` -> MediaWiki bold/italic
* U+00A0 (NBSP) -> regular space
* Any newline (``\\n`` / ``\\r\\n`` / ``\\r``) -> ``<br/>``
"""

from __future__ import annotations

from obelisk.resolve.wikitext import html_to_wiki


# ---------------------------------------------------------------------------
# HTML -> wiki bold/italic
# ---------------------------------------------------------------------------


def test_bold_tags_become_wiki_bold() -> None:
    assert html_to_wiki("plain <b>BOLD</b> trailing") == "plain '''BOLD''' trailing"


def test_italic_tags_become_wiki_italic() -> None:
    assert html_to_wiki("plain <i>IT</i> trailing") == "plain ''IT'' trailing"


def test_nested_tags_convert_independently() -> None:
    assert html_to_wiki("<b>bold <i>and italic</i></b>") == "'''bold ''and italic'''''"


def test_html_tags_are_case_insensitive() -> None:
    assert html_to_wiki("<B>X</B>") == "'''X'''"
    assert html_to_wiki("<I>Y</I>") == "''Y''"


# ---------------------------------------------------------------------------
# NBSP flattening
# ---------------------------------------------------------------------------


def test_nbsp_becomes_regular_space() -> None:
    # U+00A0 in the literal — the source data uses it for typography.
    assert html_to_wiki("[ 5 ]") == "[ 5 ]"


# ---------------------------------------------------------------------------
# Newline -> <br/>
# ---------------------------------------------------------------------------


def test_single_newline_becomes_br() -> None:
    assert html_to_wiki("line one\nline two") == "line one<br/>line two"


def test_crlf_becomes_br() -> None:
    assert html_to_wiki("line one\r\nline two") == "line one<br/>line two"


def test_cr_alone_becomes_br() -> None:
    """Old-Mac line endings shouldn't slip through as a literal CR."""
    assert html_to_wiki("line one\rline two") == "line one<br/>line two"


def test_double_newline_becomes_two_brs() -> None:
    # A blank line in the source -> two explicit breaks. This loses the
    # "paragraph" semantics MediaWiki would give a blank line in
    # ordinary wikitext, but inside a template parameter that paragraph
    # break is already useless — explicit breaks are what renders.
    assert html_to_wiki("a\n\nb") == "a<br/><br/>b"


def test_newline_combined_with_html_conversion() -> None:
    """Order matters — make sure the regex passes don't trip each other."""
    result = html_to_wiki("<b>Bold</b>\n<i>Italic</i>")
    assert result == "'''Bold'''<br/>''Italic''"


def test_newline_inside_tag_still_converts() -> None:
    """The tag regex uses DOTALL, so a newline inside <b>...</b> is
    captured as part of the bold text. After bold conversion, the
    newline inside the bolded span gets the <br/> treatment."""
    result = html_to_wiki("<b>line one\nline two</b>")
    assert result == "'''line one<br/>line two'''"


# ---------------------------------------------------------------------------
# Empty / None-safety
# ---------------------------------------------------------------------------


def test_empty_string_passes_through() -> None:
    assert html_to_wiki("") == ""


def test_plain_text_unchanged() -> None:
    assert html_to_wiki("just plain text") == "just plain text"
