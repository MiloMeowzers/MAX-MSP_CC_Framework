"""Q38 part 2 (quick 261022-mis): the bundle's `max objectfile` shortcut aliases.

aliases.json keeps its 12 hand aliases and gains 232 objectfile aliases:
13 ``mc_wrapper`` mc.*~ shortcuts, ``hslider``, 31 ``list.*`` -> ``zl.*``,
97 ``max objectfile jit.X jit.op;`` shortcuts and 90 Vizzie short names. The
30 list.* overrides.json entries that kept the RNBO-only list.* entries usable
in Max scope are gone; RNBODatabase (which reads rnbo/objects.json raw) still
sees every list.* name as RNBO-compatible.

Real DB, read-only. The bundle cross-check carries ``requires_max``.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

import tools.sync_max_bundle as sync
from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.rnbo import RNBODatabase
from tests.conftest import MAX_APP_PATH

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_DB = REPO_ROOT / ".claude" / "max-objects"

HAND_ALIASES = {
    "t": "trigger", "b": "bangbang", "i": "int", "f": "float", "p": "patcher",
    "sel": "select", "r": "receive", "s": "send", "r~": "receive~", "s~": "send~",
    "v": "value", "del": "delay",
}

MC_ALIASES = {
    "mc.audiounit~": "mc.vst~", "mc.equals~": "mc.==~", "mc.greaterthaneq~": "mc.>=~",
    "mc.greaterthan~": "mc.>~", "mc.lessthaneq~": "mc.<=~", "mc.lessthan~": "mc.<~",
    "mc.minus~": "mc.-~", "mc.modulo~": "mc.%~", "mc.notequals~": "mc.!=~",
    "mc.plusequals~": "mc.+=~", "mc.plus~": "mc.+~", "mc.rminus~": "mc.!-~",
    "mc.times~": "mc.*~",
}

SHADOWED_LIST = sorted(
    "list." + x
    for x in (
        "change compare delace ecils filter group indexmap join lace len "
        "lookup median mth nth queue reg rev rot scramble sect slice sort "
        "stack stream sub sum swap thin union unique"
    ).split()
)
LIST_ALIASES = [*SHADOWED_LIST, "list.iter"]


def _aliases() -> dict:
    return json.loads((REAL_DB / "aliases.json").read_text())["aliases"]


def _override_keys() -> set[str]:
    return set(json.loads((REAL_DB / "overrides.json").read_text())["objects"])


@pytest.fixture(scope="module")
def db() -> ObjectDatabase:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ObjectDatabase()


def test_q38_aliases_resolve(db: ObjectDatabase) -> None:
    aliases = _aliases()
    assert len(aliases) == 244
    assert list(aliases.items())[:12] == list(HAND_ALIASES.items())
    for name, target in MC_ALIASES.items():
        assert aliases[name] == target, name
    assert aliases["hslider"] == "slider"
    assert len(SHADOWED_LIST) == 30 and len(LIST_ALIASES) == 31
    for name in LIST_ALIASES:
        assert aliases[name] == "zl." + name.split(".", 1)[1], name
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        unresolved = [a for a, t in aliases.items() if (db.lookup(a) or {}).get("name") != t]
    assert unresolved == []
    assert not set(aliases) & _override_keys()


def test_list_names_stay_rnbo_compatible(db: ObjectDatabase) -> None:
    rnbo = RNBODatabase()
    overrides = _override_keys()
    for name in SHADOWED_LIST:
        assert rnbo.is_rnbo_compatible(name), name
        assert rnbo.lookup(name)["domain"] == "RNBO", name
        assert db.get_effective_restrictions(name) == [], name
        assert db.lookup(name)["domain"] != "RNBO", name
        assert name not in overrides, name
    assert "list.ease" in overrides


@pytest.mark.requires_max
def test_q38_alias_groups_match_the_bundle() -> None:
    records = sync.build_bundle_index(MAX_APP_PATH)["objectfiles"]["records"]
    raw_keys: set[str] = set()
    for data in sync.load_raw_db(REAL_DB).values():
        raw_keys.update(data)
    aliases = _aliases()

    jit_op = [n for n, r in records.items() if r["file"] == "jit.op" and n not in raw_keys]
    assert len(jit_op) == 97
    assert {n: aliases.get(n) for n in jit_op} == {n: "jit.op" for n in jit_op}

    vizzie = {
        n: r["file"][: -len(".maxpat")]
        for n, r in records.items()
        if r["package"] == "Vizzie" and r["file"].endswith(".maxpat")
        and r["file"][: -len(".maxpat")] in raw_keys
    }
    assert len(vizzie) == 90
    assert {n: aliases.get(n) for n in vizzie} == vizzie
