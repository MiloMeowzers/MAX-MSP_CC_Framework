"""quick 261022-ud6 WP6 (review IN-05): tools/extract_pkg_io.py writes
overrides.json through the shared atomic writer and keeps the file's style.

Before the fix it wrote a fixed-name ``.json.tmp`` with ``indent=2`` and
ASCII escaping, no trailing newline, no fsync and no mode preservation, then
``os.replace``d it -- unlike tools/sync_max_bundle.py, which goes through
``atomic_write_bytes`` + ``json_style``.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

import src.maxpat.db_lookup as db_lookup
import tools.extract_pkg_io as epi

PAYLOAD = {
    "inlets": [{"id": 0, "type": "control", "signal": False}],
    "outlets": [{"id": 0, "type": "control", "signal": False}],
    "_audit": {"source": "test"},
}


class _StubDB:
    def audit_empty_io(self):
        return {"critical": []}


@pytest.fixture
def overrides(tmp_path, monkeypatch):
    """A scratch overrides.json in UTF-8 style with a trailing newline."""
    path = tmp_path / "overrides.json"
    data = {"objects": {"existing": {"note": "café"}}}
    path.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    os.chmod(path, 0o640)
    monkeypatch.setattr(epi, "OVERRIDES_PATH", path)
    monkeypatch.setattr(db_lookup, "ObjectDatabase", _StubDB)
    return path, data


def test_merge_keeps_style_mode_and_returns_three_counts(overrides):
    path, data = overrides
    result = epi.merge_into_overrides({"newthing": json.loads(json.dumps(PAYLOAD))})
    assert result == (1, 0, 0)
    expected = json.loads(json.dumps(data))
    expected["objects"]["newthing"] = PAYLOAD
    assert path.read_bytes() == (
        json.dumps(expected, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert sorted(p.name for p in path.parent.iterdir()) == ["overrides.json"]


def test_merge_uses_shared_atomic_writer(overrides, monkeypatch):
    path, _ = overrides
    calls = []
    real = epi.atomic_write_bytes
    monkeypatch.setattr(epi, "atomic_write_bytes",
                        lambda p, b: (calls.append(Path(p)), real(p, b)))
    epi.merge_into_overrides({"newthing": json.loads(json.dumps(PAYLOAD))})
    assert calls == [path]


def test_noop_merge_writes_nothing(overrides, monkeypatch):
    path, _ = overrides
    before = path.read_bytes()
    monkeypatch.setattr(epi, "atomic_write_bytes",
                        lambda p, b: pytest.fail("no-op merge wrote the file"))
    assert epi.merge_into_overrides({}) == (0, 0, 0)
    assert path.read_bytes() == before


def test_ascii_no_newline_style_is_reproduced(tmp_path, monkeypatch):
    """The historical style (ASCII escapes, no trailing newline) stays as is."""
    path = tmp_path / "overrides.json"
    data = {"objects": {"existing": {"note": "café"}}}
    path.write_text(json.dumps(data, indent=2))
    monkeypatch.setattr(epi, "OVERRIDES_PATH", path)
    monkeypatch.setattr(db_lookup, "ObjectDatabase", _StubDB)
    epi.merge_into_overrides({"newthing": json.loads(json.dumps(PAYLOAD))})
    expected = json.loads(json.dumps(data))
    expected["objects"]["newthing"] = PAYLOAD
    assert path.read_text() == json.dumps(expected, indent=2)
