"""Review C8 / Q14: inherited group names from groups.json.

``ObjectDatabase.messages()`` / ``attributes()`` / ``selectors()`` merge the
groups.json profiles at call time; ``lookup()`` keeps returning only an
object's own data. The fixture section builds an isolated DB under
``tmp_path`` and never touches the repo.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from src.maxpat.db_lookup import ObjectDatabase

_OWN = {"type": "int", "get": True, "set": True}


def _obj(name: str) -> dict:
    return {
        "name": name,
        "maxclass": "newobj",
        "module": "max",
        "domain": "Max",
        "inlets": [{"id": 0, "type": "", "signal": False, "hot": True}],
        "outlets": [{"id": 0, "type": "", "signal": False}],
        "arguments": [],
        "messages": ["bang"],
        "attributes": {"own": dict(_OWN)},
        "min_version": "5.0",
        "verified": True,
        "rnbo_compatible": False,
        "variable_io": False,
    }


def _groups(
    messages: list[str] | None = None,
    attributes: list[str] | None = None,
    definitions: dict | None = None,
    member: str = "thing",
) -> dict:
    return {
        "_comment": "test",
        "max_version": "9.2.0",
        "attribute_definitions": definitions or {},
        "profiles": {
            "mc-00000000": {
                "family": "mc",
                "messages": messages or [],
                "attributes": attributes or [],
                "source": "refpage <mcwrapper>",
            }
        },
        "members": {member: ["mc-00000000"]},
    }


def _root(tmp_path: Path, groups: dict | None = None) -> Path:
    root = tmp_path / "groups-db"
    (root / "max").mkdir(parents=True)
    (root / "max" / "objects.json").write_text(json.dumps({"thing": _obj("thing")}))
    (root / "aliases.json").write_text(json.dumps({"aliases": {"al": "thing"}}))
    (root / "overrides.json").write_text(json.dumps({"objects": {}, "variable_io_rules": {}}))
    if groups is not None:
        (root / "groups.json").write_text(json.dumps(groups))
    return root


def _db(root: Path) -> ObjectDatabase:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ObjectDatabase(root)


# ---------------------------------------------------------------------------
# Fixture DB
# ---------------------------------------------------------------------------


def test_missing_groups_file_is_fine(tmp_path: Path) -> None:
    db = _db(_root(tmp_path))
    assert db.messages("thing") == ["bang"]
    assert db.attributes("thing") == {"own": _OWN}
    assert db.selectors("thing") == {"bang", "own"}


def test_messages_merge_after_own_in_order(tmp_path: Path) -> None:
    db = _db(_root(tmp_path, _groups(messages=["bang", "zap"])))
    assert db.messages("thing") == ["bang", "zap"]


def test_own_attribute_definition_wins(tmp_path: Path) -> None:
    groups = _groups(
        attributes=["own", "fresh"],
        definitions={
            "own": {"definition": {"type": "float", "get": True, "set": False}, "source": "x"},
            "fresh": {"definition": {"type": "symbol", "get": True, "set": True}, "source": "x"},
        },
    )
    db = _db(_root(tmp_path, groups))
    attributes = db.attributes("thing")
    assert attributes["own"] == _OWN
    assert attributes["fresh"] == {"type": "symbol", "get": True, "set": True}


def test_undefined_inherited_attribute_is_selector_only(tmp_path: Path) -> None:
    db = _db(_root(tmp_path, _groups(attributes=["mystery"])))
    assert "mystery" not in db.attributes("thing")
    assert "mystery" in db.selectors("thing")


def test_unknown_member_raises(tmp_path: Path) -> None:
    root = _root(tmp_path, _groups(messages=["zap"], member="nosuch"))
    with pytest.raises(ValueError, match="groups.json"):
        _db(root)


def test_missing_profile_raises(tmp_path: Path) -> None:
    groups = _groups(messages=["zap"])
    groups["members"]["thing"] = ["mc-ffffffff"]
    with pytest.raises(ValueError, match="mc-ffffffff"):
        _db(_root(tmp_path, groups))


def test_alias_member_key_canonicalises(tmp_path: Path) -> None:
    db = _db(_root(tmp_path, _groups(messages=["zap"], member="al")))
    assert "zap" in db.messages("thing")
    assert "zap" in db.messages("al")


def test_returned_values_are_copies(tmp_path: Path) -> None:
    groups = _groups(
        messages=["zap"],
        attributes=["fresh"],
        definitions={"fresh": {"definition": {"type": "int", "get": True, "set": True}, "source": "x"}},
    )
    db = _db(_root(tmp_path, groups))
    db.messages("thing").append("junk")
    attributes = db.attributes("thing")
    attributes["own"]["type"] = "junk"
    attributes["fresh"]["type"] = "junk"
    attributes["extra"] = {}
    db.selectors("thing").add("junk")
    assert db.messages("thing") == ["bang", "zap"]
    assert db.attributes("thing") == {
        "own": _OWN,
        "fresh": {"type": "int", "get": True, "set": True},
    }
    assert "junk" not in db.selectors("thing")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        own = db.lookup("thing")
    assert own["messages"] == ["bang"]
    assert own["attributes"] == {"own": _OWN}


def test_unknown_name_returns_none(tmp_path: Path) -> None:
    db = _db(_root(tmp_path, _groups(messages=["zap"])))
    assert db.messages("nosuch") is None
    assert db.attributes("nosuch") is None
    assert db.selectors("nosuch") is None


# ---------------------------------------------------------------------------
# Real repo DB (the committed groups.json; no Max needed except where marked)
# ---------------------------------------------------------------------------

_REPO_DB = Path(__file__).resolve().parents[1] / ".claude" / "max-objects"


@pytest.fixture(scope="module")
def real_db() -> ObjectDatabase:
    return _db(_REPO_DB)


def _own(db: ObjectDatabase, name: str) -> dict:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return db.lookup(name)


_MC_CYCLE_OWN = ["float", "(mouse)", "reset", "set", "setall", "signal"]
_THISPATCHER_OWN = ["anything", "end", "savewindow", "setactivetab", "showparameterwindow"]


def test_mc_cycle_messages_include_applyvalues_and_setvalue(real_db: ObjectDatabase) -> None:
    messages = real_db.messages("mc.cycle~")
    assert messages[: len(_MC_CYCLE_OWN)] == _MC_CYCLE_OWN
    assert {"applyvalues", "setvalue"} <= set(messages)


def test_jit_gl_mesh_has_ob3d_attributes(real_db: ObjectDatabase) -> None:
    attributes = real_db.attributes("jit.gl.mesh")
    ob3d = {
        "position", "rotatexyz", "scale", "blend_enable",
        "depth_enable", "lighting_enable", "drawto", "enable",
    }
    assert ob3d <= set(attributes)
    assert attributes["position"] == {"type": "float", "get": True, "set": True}
    assert attributes["alpha_mode"] == _own(real_db, "jit.gl.mesh")["attributes"]["alpha_mode"]


def test_thispatcher_has_script_write_wclose(real_db: ObjectDatabase) -> None:
    assert {"script", "write", "wclose"} <= set(real_db.messages("thispatcher"))


def test_lookup_dict_is_not_mutated(real_db: ObjectDatabase) -> None:
    real_db.messages("mc.cycle~")
    real_db.selectors("thispatcher")
    assert _own(real_db, "mc.cycle~")["messages"] == _MC_CYCLE_OWN
    assert _own(real_db, "thispatcher")["messages"] == _THISPATCHER_OWN


def test_override_message_list_still_gains_group_names(real_db: ObjectDatabase) -> None:
    overrides = json.loads((_REPO_DB / "overrides.json").read_text())["objects"]
    assert _own(real_db, "mc.sig~")["messages"] == overrides["mc.sig~"]["messages"]
    messages = real_db.messages("mc.sig~")
    assert messages[: len(overrides["mc.sig~"]["messages"])] == overrides["mc.sig~"]["messages"]
    assert {"applymessages", "decide"} <= set(messages)


@pytest.mark.parametrize("name", ["mc.pack~", "mc.record~"])
def test_native_mc_object_is_not_a_member(real_db: ObjectDatabase, name: str) -> None:
    assert real_db.messages(name) == _own(real_db, name)["messages"]
    assert "applyvalues" not in real_db.messages(name)


def test_undefined_inherited_attr_is_selector_not_attribute(real_db: ObjectDatabase) -> None:
    assert "fun" in real_db.selectors("mc.cycle~")
    attributes = real_db.attributes("mc.cycle~")
    assert "fun" not in attributes
    assert attributes["chans"]["type"] == "int"


def test_groups_file_is_canonical() -> None:
    raw = (_REPO_DB / "groups.json").read_bytes()
    data = json.loads(raw)
    assert raw == (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


@pytest.mark.requires_max
def test_bundle_has_no_pending_group_names() -> None:
    import tools.sync_max_bundle as sync

    report = sync.run_report(sync.DEFAULT_DB_ROOT, sync.DEFAULT_MAX_APP)
    assert report["sections"]["groups"]["pending_names"] == 0
