"""quick-261013-e43 (Q11): overrides merge per port and match MAX-saved boxes.

Review findings (.planning/reviews/2026-10-11-repo-review.md):

* C6 -- ``overrides.json`` ``inlets``/``outlets`` arrays used to replace the
  base arrays whole, so a generator-written port (digest "Control output",
  type "") wiped the base digest, ``hot`` flag and type. They now merge per
  port: the override sets the port count, and each port replaces only the
  keys it sets (generator placeholders never replace base text).
* C7 -- override keys that are aliases (``r``, ``del``, ``v``) were silently
  ignored. Keys are now canonicalized through ``aliases.json``; an unknown or
  duplicate key fails at load.

Test hygiene: everything except ``requires_max`` classes uses only the repo
DB (CI runs Python 3.10 / 3.12 without Max). Tests never write to the repo;
tmp_path only.
"""

from __future__ import annotations

import copy
import json
import warnings
from pathlib import Path

import pytest

from src.maxpat.db_lookup import (
    DOMAIN_LOAD_ORDER,
    OVERRIDE_PLACEHOLDER_DIGESTS,
    ObjectDatabase,
    merge_override_ports,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_ROOT = REPO_ROOT / ".claude" / "max-objects"


@pytest.fixture(scope="module")
def db() -> ObjectDatabase:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ObjectDatabase()


def _base_entries() -> dict:
    """Pre-override domain-file entries, rebuilt the way ObjectDatabase._load
    does it: DOMAIN_LOAD_ORDER, package subdirectories sorted, last wins."""
    base: dict = {}
    for domain in DOMAIN_LOAD_ORDER:
        if domain == "packages":
            pkg_root = DB_ROOT / "packages"
            if not pkg_root.is_dir():
                continue
            for pkg_dir in sorted(pkg_root.iterdir()):
                path = pkg_dir / "objects.json"
                if pkg_dir.is_dir() and path.exists():
                    base.update(json.loads(path.read_text()))
        else:
            path = DB_ROOT / domain / "objects.json"
            if path.exists():
                base.update(json.loads(path.read_text()))
    return base


def _override_objects() -> dict:
    return json.loads((DB_ROOT / "overrides.json").read_text()).get("objects", {})


def _aliases() -> dict:
    return json.loads((DB_ROOT / "aliases.json").read_text()).get("aliases", {})


# ---------------------------------------------------------------------------
# merge_override_ports (pure function)
# ---------------------------------------------------------------------------

_CTRL = {
    "id": 0, "type": "control", "signal": False,
    "digest": "Start", "hot": True, "name": "start", "optional": False,
}
_SIG = {"id": 1, "type": "signal", "signal": True, "digest": "Audio", "hot": True}


class TestMergeOverridePorts:

    def test_override_key_wins(self):
        out = merge_override_ports([_CTRL], [{"id": 0, "digest": "New text"}])
        assert out[0]["digest"] == "New text"

    def test_missing_keys_keep_base(self):
        out = merge_override_ports([_CTRL], [{"id": 0, "signal": False}])
        assert out[0]["hot"] is True
        assert out[0]["name"] == "start"
        assert out[0]["optional"] is False

    @pytest.mark.parametrize("placeholder", sorted(OVERRIDE_PLACEHOLDER_DIGESTS))
    def test_placeholder_digest_keeps_base(self, placeholder):
        out = merge_override_ports([_CTRL], [{"id": 0, "digest": placeholder}])
        assert out[0]["digest"] == "Start"

    @pytest.mark.parametrize("placeholder", sorted(OVERRIDE_PLACEHOLDER_DIGESTS))
    def test_placeholder_digest_fills_empty_base(self, placeholder):
        empty = dict(_CTRL, digest="")
        assert merge_override_ports([empty], [{"digest": placeholder}])[0]["digest"] == placeholder
        missing = {k: v for k, v in _CTRL.items() if not k == "digest"}
        assert merge_override_ports([missing], [{"digest": placeholder}])[0]["digest"] == placeholder

    def test_placeholder_description_keeps_base(self):
        base = {"id": 0, "description": "Real text"}
        out = merge_override_ports([base], [{"id": 0, "description": "Control output"}])
        assert out[0]["description"] == "Real text"

    def test_empty_type_on_control_base_keeps_base_type(self):
        out = merge_override_ports([_CTRL], [{"id": 0, "type": "", "signal": False}])
        assert out[0]["type"] == "control"

    def test_empty_type_on_signal_base_applies(self):
        out = merge_override_ports([_SIG], [{"id": 0, "type": "", "signal": False}])
        assert out[0]["type"] == ""
        assert out[0]["signal"] is False
        # A "signal" type alone (no signal: true) also counts as a signal port.
        typed = {"id": 0, "type": "signal/float", "digest": "x"}
        assert merge_override_ports([typed], [{"type": ""}])[0]["type"] == ""

    def test_non_empty_type_always_applies(self):
        out = merge_override_ports([_CTRL], [{"id": 0, "type": "int"}])
        assert out[0]["type"] == "int"

    def test_id_stub_inherits_base_port(self):
        base = [dict(_CTRL, id=i) for i in range(4)]
        out = merge_override_ports(base, [{"id": 0}, {"id": 1}, {"id": 2}, {"id": 3}])
        assert out[3] == base[3]

    def test_longer_override_appends_copies(self):
        extra = {"id": 1, "type": "", "signal": False, "digest": "Control output"}
        out = merge_override_ports([_CTRL], [{"id": 0}, extra])
        assert len(out) == 2
        assert out[1] == extra
        assert out[1] is not extra

    def test_shorter_override_truncates(self):
        out = merge_override_ports([_CTRL, _SIG], [{"id": 0}])
        assert len(out) == 1

    def test_inputs_not_mutated(self):
        base = [copy.deepcopy(_CTRL), copy.deepcopy(_SIG)]
        over = [{"id": 0, "digest": "x", "type": ""}, {"id": 1, "signal_role": "audio"}]
        base_before, over_before = copy.deepcopy(base), copy.deepcopy(over)
        out = merge_override_ports(base, over)
        out[0]["hot"] = "mutated"
        assert base == base_before
        assert over == over_before

    def test_non_dict_override_passes_through(self):
        assert merge_override_ports([_CTRL], ["junk"]) == ["junk"]
        assert merge_override_ports(["junk"], [{"id": 0}]) == [{"id": 0}]


# ---------------------------------------------------------------------------
# Real DB anchors: base metadata survives the merge
# ---------------------------------------------------------------------------

class TestRealDbRestore:

    def test_line_tilde(self, db):
        obj = db.lookup("line~")
        assert obj["inlets"][1]["digest"] == "Ramp Time"
        assert obj["inlets"][1]["hot"] is True
        assert obj["outlets"][0]["digest"] == "Output Ramp"

    def test_uzi(self, db):
        obj = db.lookup("uzi")
        assert obj["outlets"][1]["digest"] == "Done banging bang (carry)"
        assert obj["inlets"][0]["hot"] is True

    def test_coll(self, db):
        assert db.lookup("coll")["outlets"][0]["digest"] == "Data Contents"

    def test_no_placeholder_clobbers_base_digest(self, db):
        base = _base_entries()
        clobbered = []
        for name in sorted(db._overridden_objects):
            b = base.get(name)
            merged = db._objects.get(name)
            if not isinstance(b, dict) or merged is None:
                continue
            for side in ("inlets", "outlets"):
                bp, mp = b.get(side) or [], merged.get(side) or []
                for i in range(min(len(bp), len(mp))):
                    if not isinstance(bp[i], dict) or not isinstance(mp[i], dict):
                        continue
                    bd = bp[i].get("digest")
                    # Some domain files themselves carry placeholder text
                    # (e.g. jit.* "Control output"); keeping it is not a
                    # clobber, so only real base text counts.
                    real = isinstance(bd, str) and bd not in OVERRIDE_PLACEHOLDER_DIGESTS
                    if real and mp[i].get("digest") in OVERRIDE_PLACEHOLDER_DIGESTS:
                        clobbered.append((name, side, i))
        assert clobbered == []


# ---------------------------------------------------------------------------
# Alias canonicalization and data hygiene (C7)
# ---------------------------------------------------------------------------

class TestAliasCanonicalization:

    def test_alias_lookup_resolves_override(self, db):
        assert db.lookup("del") == db.lookup("delay")
        assert db.lookup("del")["name"] == "delay"
        assert db.is_overridden("del") is True
        assert db.is_overridden("value") is True

    def test_no_override_key_is_an_alias(self):
        aliases = _aliases()
        assert sorted(k for k in _override_objects() if k in aliases) == []

    def test_r_override_removed(self, db):
        assert "r" not in _override_objects()
        assert db.compute_io_counts("r", ["foo"]) == (0, 1)
        assert db.compute_io_counts("receive", []) == (1, 1)

    def test_no_stale_inactive_notes(self):
        stale = [
            k for k, v in _override_objects().items()
            if isinstance(v, dict) and "No base domain entry" in str(v.get("_note", ""))
        ]
        assert stale == []


def _make_db(tmp_path: Path, overrides: dict, aliases: dict | None = None) -> Path:
    root = tmp_path / "db"
    (root / "max").mkdir(parents=True)
    objects = {
        "metro": {
            "name": "metro",
            "inlets": [
                {"id": 0, "type": "control", "signal": False, "digest": "On/Off", "hot": True},
                {"id": 1, "type": "control", "signal": False, "digest": "Interval", "hot": False},
            ],
            "outlets": [{"id": 0, "type": "control", "signal": False, "digest": "Output"}],
        },
    }
    (root / "max" / "objects.json").write_text(json.dumps(objects))
    (root / "aliases.json").write_text(json.dumps({"aliases": aliases or {}}))
    (root / "overrides.json").write_text(
        json.dumps({"objects": overrides, "variable_io_rules": {}})
    )
    return root


class TestOverrideKeyFailFast:

    def test_unknown_key_raises(self, tmp_path):
        root = _make_db(tmp_path, {"nosuchobj": {"inlets": []}})
        with pytest.raises(ValueError, match="nosuchobj"):
            ObjectDatabase(root)

    def test_alias_plus_canonical_raises(self, tmp_path):
        root = _make_db(
            tmp_path,
            {"m": {"_note": "x"}, "metro": {"_note": "y"}},
            aliases={"m": "metro"},
        )
        with pytest.raises(ValueError) as exc:
            ObjectDatabase(root)
        assert "'m'" in str(exc.value) and "'metro'" in str(exc.value)

    def test_alias_only_key_applies_to_canonical(self, tmp_path):
        root = _make_db(
            tmp_path,
            {"m": {"outlets": [{"id": 0, "type": "", "signal": False, "digest": "Control output"}]}},
            aliases={"m": "metro"},
        )
        mdb = ObjectDatabase(root)
        assert mdb.is_overridden("metro")
        out = mdb.lookup("metro")["outlets"][0]
        assert out["digest"] == "Output"
        assert out["type"] == "control"
        assert mdb.lookup("metro")["inlets"][0]["hot"] is True
