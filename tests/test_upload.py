"""Mock-based tests for the upload pipeline.

These never touch the network. We mock the ``mwclient`` Site/Page surface
that :class:`WikiClient` uses and verify:

* Idempotency — when the on-wiki text already matches, ``put_page``
  returns ``unchanged`` and never calls ``page.edit``.
* Write path — when the text differs, ``put_page`` returns ``written``
  and forwards content + summary + bot=True to ``page.edit``.
* Error handling — exceptions from the mwclient layer become
  ``failed`` results with the message in ``detail``, never raised.
* Rate limiting — the inter-call sleep actually fires when
  ``requests_per_second`` is set, and the first call goes through
  immediately.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from obelisk.upload import (
    Manifest,
    ManifestEntry,
    WikiClient,
    WikiConfig,
    build_full_manifest,
)
from obelisk.upload.client import UploadResult


# ---------------------------------------------------------------------------
# Test helpers — a minimal in-memory mwclient stand-in.
# ---------------------------------------------------------------------------


class _FakePage:
    def __init__(self, exists: bool, text: str = "") -> None:
        self.exists = exists
        self._text = text
        self.edits: list[tuple[str, str, bool]] = []

    def text(self) -> str:
        return self._text

    def edit(self, content: str, summary: str = "", bot: bool = False) -> None:
        self.edits.append((content, summary, bot))
        self._text = content
        self.exists = True


class _FakePages:
    """``site.pages[title]`` accessor — returns a FakePage from the store."""

    def __init__(self, store: dict[str, _FakePage]) -> None:
        self._store = store

    def __getitem__(self, title: str) -> _FakePage:
        if title not in self._store:
            # Mirror mwclient: missing pages return an empty non-existent page.
            self._store[title] = _FakePage(exists=False, text="")
        return self._store[title]


class _FakeSite:
    """Stand-in for mwclient.Site that records logins and edits."""

    def __init__(self, host: str, **kwargs) -> None:
        self.host = host
        self.kwargs = kwargs
        self.maxlag: int | None = None
        self.logins: list[tuple[str, str]] = []
        self.store: dict[str, _FakePage] = {}
        self.pages = _FakePages(self.store)

    def login(self, username: str, password: str) -> None:
        self.logins.append((username, password))


def _install_fake_mwclient(monkeypatch: pytest.MonkeyPatch) -> type[_FakeSite]:
    """Inject a stub ``mwclient`` module so WikiClient._connect picks it up."""
    fake_module = types.ModuleType("mwclient")
    fake_module.Site = _FakeSite  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "mwclient", fake_module)
    return _FakeSite


def _config(**overrides) -> WikiConfig:
    base = dict(
        host="example.test",
        path="/",
        username="bot@obelisk",
        bot_password="secret",
        requests_per_second=0.0,  # disable throttle for most tests
        maxlag=5,
    )
    base.update(overrides)
    return WikiConfig(**base)


# ---------------------------------------------------------------------------
# WikiClient: idempotency & write path
# ---------------------------------------------------------------------------


def test_put_page_unchanged_when_on_wiki_text_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_mwclient(monkeypatch)
    client = WikiClient(_config())
    site = client._connect()  # type: ignore[assignment]
    site.store["Data:Unit/angel"] = _FakePage(exists=True, text="body")

    result = client.put_page("Data:Unit/angel", "body")

    assert result.status == "unchanged"
    assert result.detail == ""
    # And critically: edit() was never called.
    assert site.store["Data:Unit/angel"].edits == []


def test_put_page_writes_when_text_differs(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_mwclient(monkeypatch)
    client = WikiClient(_config(edit_summary="cycle 42"))
    site = client._connect()  # type: ignore[assignment]
    site.store["Data:Unit/angel"] = _FakePage(exists=True, text="old body")

    result = client.put_page("Data:Unit/angel", "new body")

    assert result.status == "written"
    page = site.store["Data:Unit/angel"]
    assert page.edits == [("new body", "cycle 42", True)]


def test_put_page_writes_new_page_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_mwclient(monkeypatch)
    client = WikiClient(_config())
    site = client._connect()  # type: ignore[assignment]
    # Not pre-seeded — _FakePages auto-creates a non-existent page.

    result = client.put_page("Data:Unit/imp", "fresh body")

    assert result.status == "written"
    assert site.store["Data:Unit/imp"].edits[0][0] == "fresh body"


def test_put_page_passes_explicit_summary_over_config(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_mwclient(monkeypatch)
    client = WikiClient(_config(edit_summary="default"))
    site = client._connect()  # type: ignore[assignment]

    client.put_page("Data:Spell/heal", "x", summary="explicit one-off")

    assert site.store["Data:Spell/heal"].edits[0][1] == "explicit one-off"


# ---------------------------------------------------------------------------
# WikiClient: error handling
# ---------------------------------------------------------------------------


def test_put_page_returns_failed_on_edit_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_mwclient(monkeypatch)
    client = WikiClient(_config())
    site = client._connect()  # type: ignore[assignment]
    bad = _FakePage(exists=True, text="prior")
    bad.edit = MagicMock(side_effect=RuntimeError("quota exceeded"))  # type: ignore[method-assign]
    site.store["Data:Unit/angel"] = bad

    result = client.put_page("Data:Unit/angel", "new")

    assert result.status == "failed"
    assert "quota exceeded" in result.detail


def test_put_page_returns_failed_when_mwclient_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force the import inside _connect to raise.
    monkeypatch.setitem(sys.modules, "mwclient", None)  # type: ignore[arg-type]
    client = WikiClient(_config())

    result = client.put_page("Data:Unit/angel", "body")

    assert result.status == "failed"
    assert "connect" in result.detail


# ---------------------------------------------------------------------------
# WikiClient: login + maxlag plumbing
# ---------------------------------------------------------------------------


def test_connect_logs_in_with_configured_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_mwclient(monkeypatch)
    cfg = _config(username="bot@obelisk", bot_password="hunter2", maxlag=7)
    client = WikiClient(cfg)

    site = client._connect()

    assert site.logins == [("bot@obelisk", "hunter2")]
    assert site.maxlag == 7


def test_connect_skips_login_when_no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_mwclient(monkeypatch)
    cfg = _config(username="", bot_password="")
    client = WikiClient(cfg)

    site = client._connect()

    assert site.logins == []


def test_connect_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_mwclient(monkeypatch)
    client = WikiClient(_config())
    first = client._connect()
    second = client._connect()
    assert first is second


# ---------------------------------------------------------------------------
# WikiClient: rate limiting
# ---------------------------------------------------------------------------


def test_throttle_sleeps_between_calls_when_rps_set(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_mwclient(monkeypatch)
    sleeps: list[float] = []
    # Monotonic clock: each tick is one call to monotonic(); we return
    # 0.0 for the first call, then 0.1 for the second (so 0.1s has
    # "elapsed" between the first call's _last_call stamp and the
    # second call's pre-sleep timestamp). With rps=1.0 the throttle
    # wants 1.0s between calls -> it should sleep 0.9s.
    ticks = iter([0.0, 0.1, 0.1, 0.2])
    client = WikiClient(
        _config(requests_per_second=1.0),
        sleep=lambda s: sleeps.append(s),
        monotonic=lambda: next(ticks),
    )
    client._connect()  # prime; no API calls yet

    client.put_page("Data:Unit/a", "x")
    client.put_page("Data:Unit/b", "y")

    # First call: no sleep (no prior _last_call). Second: 1.0 - 0.1 = 0.9.
    assert sleeps == [pytest.approx(0.9)]


def test_throttle_disabled_when_rps_nonpositive(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_mwclient(monkeypatch)
    sleeps: list[float] = []
    client = WikiClient(
        _config(requests_per_second=0.0),
        sleep=lambda s: sleeps.append(s),
    )

    client.put_page("Data:Unit/a", "x")
    client.put_page("Data:Unit/b", "y")
    client.put_page("Data:Unit/c", "z")

    assert sleeps == []


# ---------------------------------------------------------------------------
# Manifest: full-push builder
# ---------------------------------------------------------------------------


def _make_extract_dir(root: Path) -> Path:
    """Create a tiny but realistic extract layout."""
    (root / "data" / "units").mkdir(parents=True)
    (root / "data" / "factions").mkdir(parents=True)
    (root / "data" / "movement").mkdir(parents=True)
    (root / "data" / "units" / "angel.wiki.txt").write_text("{{Unit | id=angel}}")
    (root / "data" / "units" / "imp.wiki.txt").write_text("{{Unit | id=imp}}")
    (root / "data" / "factions" / "human.wiki.txt").write_text("{{Faction | id=human}}")
    (root / "data" / "movement" / "fly.wiki.txt").write_text("{{Entry | id=fly}}")
    (root / "coverage.wiki.txt").write_text("= Coverage =")
    # Non-wiki sidecars should be ignored.
    (root / "audit.json").write_text("{}")
    (root / "_meta.json").write_text("{}")
    return root


def test_build_full_manifest_includes_data_and_coverage(tmp_path: Path) -> None:
    extract = _make_extract_dir(tmp_path / "2026-05-08")

    manifest = build_full_manifest(extract)

    titles = [e.title for e in manifest.pages]
    assert titles == sorted(titles), "manifest should be sorted by title"
    assert "Data:Unit/angel" in titles
    assert "Data:Unit/imp" in titles
    assert "Data:Faction/human" in titles
    assert "Data:Movement/fly" in titles
    assert "Data:Coverage" in titles
    # All entries marked as 'added' for a full push.
    assert all(e.status == "added" for e in manifest.pages)
    assert manifest.kind == "full"
    assert manifest.label == "2026-05-08"
    assert manifest.patch_article is None


def test_build_full_manifest_excludes_coverage_when_disabled(tmp_path: Path) -> None:
    extract = _make_extract_dir(tmp_path / "2026-05-08")

    manifest = build_full_manifest(extract, include_coverage=False)

    titles = [e.title for e in manifest.pages]
    assert "Data:Coverage" not in titles
    # Data pages should still be present.
    assert "Data:Unit/angel" in titles


def test_build_full_manifest_handles_missing_coverage(tmp_path: Path) -> None:
    extract = _make_extract_dir(tmp_path / "2026-05-08")
    (extract / "coverage.wiki.txt").unlink()

    manifest = build_full_manifest(extract, include_coverage=True)

    # Coverage requested but file missing — just absent from the manifest.
    assert all(e.title != "Data:Coverage" for e in manifest.pages)


def test_build_full_manifest_dedupes_on_case_insensitive_fs(tmp_path: Path) -> None:
    """Regression: on Windows/macOS the legacy 'Data' probe collides with
    the canonical 'data' dir (case-insensitive filesystem) and every
    file gets walked twice. The builder must dedupe by relpath.

    We simulate the case-insensitive behavior by having the builder see
    the same file under both casings.
    """
    extract = _make_extract_dir(tmp_path / "2026-05-08")
    # On a case-sensitive fs (Linux CI) we have to fake the collision —
    # create a parallel 'Data' tree with one of the same files and
    # verify the builder dedupes regardless of how the duplication
    # arises. This catches *any* future double-walk bug, not just the
    # case-insensitive-fs flavor.
    (extract / "Data" / "units").mkdir(parents=True, exist_ok=True)
    (extract / "Data" / "units" / "angel.wiki.txt").write_text("dup")

    manifest = build_full_manifest(extract)

    angel_entries = [e for e in manifest.pages if e.title == "Data:Unit/angel"]
    assert len(angel_entries) == 1, (
        f"expected exactly one Data:Unit/angel entry, got {len(angel_entries)}: "
        f"{[e.relpath for e in angel_entries]}"
    )


def test_manifest_round_trips_to_json(tmp_path: Path) -> None:
    extract = _make_extract_dir(tmp_path / "2026-05-08")
    manifest = build_full_manifest(extract)
    out = tmp_path / "manifest.json"

    manifest.write(out)

    blob = json.loads(out.read_text(encoding="utf-8"))
    assert blob["kind"] == "full"
    assert blob["label"] == "2026-05-08"
    assert blob["old_label"] is None
    assert blob["patch_article"] is None
    assert isinstance(blob["pages"], list)
    # Spot-check entry shape.
    sample = next(p for p in blob["pages"] if p["title"] == "Data:Unit/angel")
    assert sample == {
        "title": "Data:Unit/angel",
        "relpath": "data/units/angel.wiki.txt",
        "status": "added",
    }
