"""Quick-fix payloads and the --fix applier (quick 261022-o2q, fix-plan Q39).

Every git operation here runs inside a throwaway repo under pytest's
``tmp_path``, never in the MAX repo; an autouse fixture strips GIT_DIR,
GIT_WORK_TREE and GIT_INDEX_FILE from the environment as a guard. Committed
patches under ``patches/`` are only read (``git show HEAD:``) and kept in
memory, never written.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import functools
import json
import shutil
import subprocess
import warnings
from pathlib import Path

import pytest

from src.maxpat.patcher import Patcher
from src.maxpat.critics import review_patch
from src.maxpat.critics.base import CriticResult
from src.maxpat.critics.fixes import (
    FIX_KINDS,
    FIX_OPS,
    Fix,
    FixOp,
    check_fix_contract,
    trigger_fix,
)
from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.edit_session import edit_patch
from src.maxpat.hooks import SaveGateWarning
from src.maxpat.quickfix import (
    FixError,
    apply_fix,
    apply_quick_fixes,
    finding_key,
    fixable_findings,
    preview_quick_fixes,
)
from src.maxpat.validation import validate_patch

pytestmark = [
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
    # Saves to tmp_path outside a repository: the auto-commit warns.
    pytest.mark.filterwarnings("ignore:.*not auto-committed:UserWarning"),
]

REPO_ROOT = Path(__file__).resolve().parent.parent
QUICKFIX_PY = REPO_ROOT / "src" / "maxpat" / "quickfix.py"


@functools.lru_cache(maxsize=1)
def _db() -> ObjectDatabase:
    return ObjectDatabase()


# ---------------------------------------------------------------------------
# Fixtures and helpers (copied from tests/test_edit_session.py, not imported)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch):
    """Make sure no inherited git env var can redirect git to another repo."""
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True, check=True,
    )
    return result.stdout


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    hooks = tmp_path / "empty-hooks"
    hooks.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Quick Fix Test")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "config", "core.hooksPath", str(hooks))
    return root.resolve()


def _head_files(root: Path) -> list[str]:
    return [l for l in _git(root, "show", "--name-only", "--format=", "HEAD").splitlines() if l]


def _head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").strip()


def _patch_path(root: Path) -> Path:
    return root / "patches" / "demo" / "generated" / "demo.maxpat"


REL_P = "patches/demo/generated/demo.maxpat"


def _seed(root: Path, P: Path, d: dict) -> str:
    text = json.dumps(d, indent=4)
    P.parent.mkdir(parents=True, exist_ok=True)
    P.write_text(text)
    rel = P.relative_to(root).as_posix()
    _git(root, "add", "--", rel)
    _git(root, "commit", "-q", "-m", "seed", "--", rel)
    return text


def _gate_warnings(record) -> list:
    return [w for w in record if issubclass(w.category, SaveGateWarning)]


def _tracked() -> list:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--", "patches/*.maxpat"],
            cwd=str(REPO_ROOT), capture_output=True, check=True,
        ).stdout
        return sorted(p for p in out.decode("utf-8").split("\0") if p)
    except Exception:
        return []


@functools.lru_cache(maxsize=None)
def _head_bytes(rel: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"HEAD:{rel}"],
        cwd=str(REPO_ROOT), capture_output=True, check=True,
    ).stdout


# ---------------------------------------------------------------------------
# Patch builders
# ---------------------------------------------------------------------------


def _fan_patcher() -> Patcher:
    """FAN: number (obj-1) -> + 0 (obj-2) inlets 0 and 1, + -> print (obj-3)."""
    p = Patcher()
    n = p.add_box("number")
    a = p.add_box("+", ["0"])
    pr = p.add_box("print")
    p.add_connection(n, 0, a, 0)
    p.add_connection(n, 0, a, 1)
    p.add_connection(a, 0, pr, 0)
    return p


def _fan() -> dict:
    return _fan_patcher().to_dict()


def _review(d: dict) -> list:
    return review_patch(copy.deepcopy(d), db=_db())


def _by_rule(results, rule, first_id=None) -> list:
    return [
        r for r in results
        if r.rule == rule and (first_id is None or (r.box_ids and r.box_ids[0] == first_id))
    ]


def _fan_finding(d: dict, src="obj-1"):
    found = _by_rule(_review(d), "fan_out_without_trigger", src)
    assert len(found) == 1, found
    return found[0]


def _ops(fix, op) -> list:
    return [o for o in fix.ops if o.op == op]


def _cord_set(p: Patcher) -> set:
    return {(l.source_id, l.source_outlet, l.dest_id, l.dest_inlet) for l in p.lines}


def _errors(d: dict) -> list:
    return [v for v in validate_patch(copy.deepcopy(d)) if v.level == "error"]


# ---------------------------------------------------------------------------
# Task 1: CriticResult.fix back-compat and the payload model
# ---------------------------------------------------------------------------


def _some_fix() -> Fix:
    return trigger_fix("obj-1", 0, "number", "l", [("obj-2", 1, "+"), ("obj-2", 0, "+")])


def test_critic_result_fix_defaults_to_none():
    r = CriticResult("note", "f", "s")
    assert r.fix is None
    assert "fix" in CriticResult.__slots__
    fx = _some_fix()
    r2 = CriticResult("blocker", "f", "s", rule="r", fix=fx)
    assert r2.fix is fx
    r3 = CriticResult("warning", "f", "s", "obj-1")
    assert (r3.severity, r3.finding, r3.suggestion, r3.path) == ("warning", "f", "s", "obj-1")
    assert repr(r2) == "[blocker] f"


def test_critic_result_fix_is_keyword_only():
    with pytest.raises(TypeError):
        CriticResult("note", "f", "s", "", "rule")  # rule (and fix) stay keyword-only


def test_fix_model_frozen_and_hashable():
    fx = _some_fix()
    op = fx.ops[0]
    assert hash(fx) == hash(_some_fix())
    assert fx == _some_fix()
    with pytest.raises(dataclasses.FrozenInstanceError):
        fx.kind = "set_bach_out"
    with pytest.raises(dataclasses.FrozenInstanceError):
        op.text = "t b b"
    assert set(FIX_KINDS) == {"insert_trigger", "rewrite_gen_param", "insert_gain_normalizer", "set_bach_out"}
    assert set(FIX_OPS) == {"add_box", "remove_cord", "add_cord", "set_text"}
    for o in fx.ops:
        for f in dataclasses.fields(o):
            assert not callable(getattr(o, f.name))


def test_fix_model_rejects_unknown():
    with pytest.raises(ValueError):
        FixOp("bogus")
    with pytest.raises(ValueError):
        Fix("bogus", "d", ())
    with pytest.raises(ValueError):
        Fix("insert_trigger", "d", [FixOp("add_box")])


def test_contract_accepts_builder_and_rejects_breaches():
    fx = _some_fix()
    check_fix_contract(fx)
    # add_box name outside t/trigger
    metro = Fix("insert_trigger", "d", tuple(
        dataclasses.replace(o, text="metro 100") if o.op == "add_box" else o for o in fx.ops
    ))
    with pytest.raises(ValueError):
        check_fix_contract(metro)
    # outlets do not cover the removed destinations
    wrong = Fix("insert_trigger", "d", tuple(
        dataclasses.replace(o, dst="obj-3") if (o.op == "add_cord" and o.src == "$new1" and o.outlet == 1) else o
        for o in fx.ops
    ))
    with pytest.raises(ValueError):
        check_fix_contract(wrong)
    # an outlet used twice
    twice = Fix("insert_trigger", "d", tuple(
        dataclasses.replace(o, outlet=0) if (o.op == "add_cord" and o.src == "$new1") else o
        for o in fx.ops
    ))
    with pytest.raises(ValueError):
        check_fix_contract(twice)


# ---------------------------------------------------------------------------
# Task 1: the insert_trigger payload
# ---------------------------------------------------------------------------


def test_fan_blocker_carries_trigger_fix():
    r = _fan_finding(_fan())
    assert r.severity == "blocker"
    assert r.box_ids == ("obj-1", "obj-2") and r.port == 0
    fx = r.fix
    assert fx is not None and fx.kind == "insert_trigger"
    check_fix_contract(fx)
    adds = _ops(fx, "add_box")
    assert len(adds) == 1 and adds[0].text == "t l l" and adds[0].near == "obj-1"
    new = adds[0].box
    assert {(o.src, o.outlet, o.dst, o.inlet) for o in _ops(fx, "remove_cord")} == {
        ("obj-1", 0, "obj-2", 0), ("obj-1", 0, "obj-2", 1),
    }
    assert {(o.src, o.outlet, o.dst, o.inlet) for o in _ops(fx, "add_cord")} == {
        ("obj-1", 0, new, 0), (new, 1, "obj-2", 1), (new, 0, "obj-2", 0),
    }
    assert "t l l" in fx.description
    assert "obj-2" in fx.description and "inlet 0" in fx.description and "inlet 1" in fx.description


def test_three_branch_order():
    p = Patcher()
    n = p.add_box("number")          # obj-1
    pk = p.add_box("pack", ["0", "0", "0"])  # obj-2
    m = p.add_box("*", ["2"])        # obj-3
    pr = p.add_box("print")          # obj-4
    p.add_connection(n, 0, pk, 0)    # A
    p.add_connection(n, 0, pk, 2)    # B
    p.add_connection(n, 0, m, 0)     # C
    p.add_connection(m, 0, pk, 1)
    p.add_connection(pk, 0, pr, 0)
    fx = _fan_finding(p.to_dict()).fix
    assert fx is not None
    check_fix_contract(fx)
    new = _ops(fx, "add_box")[0].box
    outs = {o.outlet: (o.dst, o.inlet) for o in _ops(fx, "add_cord") if o.src == new}
    assert outs[0] == ("obj-2", 0)
    assert {outs[1], outs[2]} == {("obj-2", 2), ("obj-3", 0)}
    # stable cord order among the cold branches: B (first cord) fires first -> outlet 2
    assert outs[2] == ("obj-2", 2) and outs[1] == ("obj-3", 0)


@pytest.mark.parametrize("kind,letter", [("bang", "b"), ("int", "i"), ("float", "f"), ("list", "l"), ("", "l")])
def test_trigger_letter_from_outlettype(kind, letter):
    d = _fan()
    d["patcher"]["boxes"][0]["box"]["outlettype"][0] = kind
    fx = _fan_finding(d).fix
    assert fx is not None
    assert _ops(fx, "add_box")[0].text == f"t {letter} {letter}"


def test_trigger_letter_unknown_type_no_fix():
    d = _fan()
    d["patcher"]["boxes"][0]["box"]["outlettype"][0] = "jit_matrix"
    r = _fan_finding(d)
    assert r.severity == "blocker"
    assert r.fix is None


def test_conflicting_order_no_fix():
    p = Patcher()
    n = p.add_box("number")      # obj-1
    x = p.add_box("f")           # obj-2
    y = p.add_box("i")           # obj-3
    m1 = p.add_box("+", ["0"])   # obj-4
    m2 = p.add_box("-", ["0"])   # obj-5
    pr1 = p.add_box("print")     # obj-6
    pr2 = p.add_box("print")     # obj-7
    p.add_connection(n, 0, x, 0)
    p.add_connection(n, 0, y, 0)
    p.add_connection(x, 0, m1, 0)
    p.add_connection(x, 0, m2, 1)
    p.add_connection(y, 0, m1, 1)
    p.add_connection(y, 0, m2, 0)
    p.add_connection(m1, 0, pr1, 0)
    p.add_connection(m2, 0, pr2, 0)
    r = _fan_finding(p.to_dict())
    assert r.severity == "blocker"
    assert r.fix is None


def test_warning_fan_out_no_fix():
    p = Patcher()
    n = p.add_box("number")
    a = p.add_box("+", ["0"])
    b = p.add_box("-", ["0"])
    pa = p.add_box("print")
    pb = p.add_box("print")
    p.add_connection(n, 0, a, 0)
    p.add_connection(n, 0, b, 0)
    p.add_connection(a, 0, pa, 0)
    p.add_connection(b, 0, pb, 0)
    r = _fan_finding(p.to_dict())
    assert r.severity == "warning"
    assert r.fix is None


def test_duplicate_branch_cords_no_fix():
    d = _fan()
    lines = d["patcher"]["lines"]
    dup = copy.deepcopy(next(
        e for e in lines
        if e["patchline"]["source"] == ["obj-1", 0] and e["patchline"]["destination"] == ["obj-2", 0]
    ))
    lines.append(dup)
    r = _fan_finding(d)
    assert r.severity == "blocker"
    assert r.fix is None


# ---------------------------------------------------------------------------
# Task 1: the applier
# ---------------------------------------------------------------------------


def test_apply_fix_on_fan_in_memory():
    p = _fan_patcher()
    r = _fan_finding(p.to_dict())
    created = apply_fix(p, r)
    assert len(created) == 1
    tbox = created[0]
    assert tbox.text == "t l l"
    src = next(b for b in p.boxes if b.id == "obj-1")
    assert tbox.patching_rect[1] > src.patching_rect[1]
    after = _review(p.to_dict())
    for rule in ("fan_out_without_trigger", "trigger_order", "hot_cold_ordering"):
        assert not [x for x in after if x.rule == rule and "obj-1" in x.box_ids], rule
    assert not [x for x in after if x.severity == "blocker"]
    assert _errors(p.to_dict()) == []
    assert _cord_set(p) >= {
        ("obj-1", 0, tbox.id, 0), (tbox.id, 1, "obj-2", 1), (tbox.id, 0, "obj-2", 0),
    }
    assert ("obj-1", 0, "obj-2", 0) not in _cord_set(p)


def _guard(p: Patcher, result) -> None:
    before = p.to_dict()
    with pytest.raises(FixError):
        apply_fix(p, result)
    assert p.to_dict() == before


def test_guard_add_box_outside_allowlist():
    p = _fan_patcher()
    r = _fan_finding(p.to_dict())
    bad = Fix("insert_trigger", "d", tuple(
        dataclasses.replace(o, text="metro 100") if o.op == "add_box" else o for o in r.fix.ops
    ))
    _guard(p, CriticResult("blocker", "f", "s", rule=r.rule, box_ids=r.box_ids, port=0, fix=bad))


def test_guard_gain_normalizer_with_metro():
    p = _fan_patcher()
    bad = Fix("insert_gain_normalizer", "d", (
        FixOp("add_box", box="$new1", text="metro 100", near="obj-1"),
        FixOp("remove_cord", src="obj-1", outlet=0, dst="obj-2", inlet=1),
        FixOp("add_cord", src="obj-1", outlet=0, dst="$new1", inlet=0),
        FixOp("add_cord", src="$new1", outlet=0, dst="obj-2", inlet=1),
    ))
    _guard(p, CriticResult("blocker", "f", "s", rule="x", fix=bad))


def test_guard_absent_cord():
    p = _fan_patcher()
    bad = trigger_fix("obj-1", 0, "number", "l", [("obj-3", 0, "print"), ("obj-2", 0, "+")])
    check_fix_contract(bad)
    _guard(p, CriticResult("blocker", "f", "s", rule="x", fix=bad))


def test_guard_set_text_mismatch():
    p = _fan_patcher()
    bad = Fix("rewrite_gen_param", "d", (FixOp("set_text", box="obj-2", text="x 1", old_text="nope"),))
    _guard(p, CriticResult("warning", "f", "s", rule="x", fix=bad))


def test_guard_unknown_scope_path():
    p = _fan_patcher()
    r = _fan_finding(p.to_dict())
    _guard(p, CriticResult("blocker", "f", "s", "obj-99", rule=r.rule, box_ids=r.box_ids, port=0, fix=r.fix))


def test_guard_no_fix():
    p = _fan_patcher()
    _guard(p, CriticResult("blocker", "f", "s", rule="x"))


def _nested() -> Patcher:
    p = Patcher()
    box, inner = p.add_subpatcher("sub", inlets=1, outlets=0)
    n = inner.add_box("number")
    a = inner.add_box("+", ["0"])
    pr = inner.add_box("print")
    inner.add_connection(inner.get_inlets()[0], 0, n, 0)
    inner.add_connection(n, 0, a, 0)
    inner.add_connection(n, 0, a, 1)
    inner.add_connection(a, 0, pr, 0)
    top_n = p.add_box("number")
    p.add_connection(top_n, 0, box, 0)
    return p


def test_nested_fix_edits_only_inner():
    p = _nested()
    sub = next(b for b in p.boxes if b.text == "p sub")
    found = fixable_findings(p, db=_db())
    assert len(found) == 1
    r = found[0]
    assert r.rule == "fan_out_without_trigger" and r.path == sub.id
    top_before = p.to_dict()
    top_boxes = [e["box"] for e in top_before["patcher"]["boxes"] if e["box"]["id"] != sub.id]
    top_lines = top_before["patcher"]["lines"]
    inner = sub._inner_patcher
    n_inner = len(inner.boxes)
    applied = apply_quick_fixes(p, [finding_key(r)], db=_db())
    assert [finding_key(x) for x in applied] == [finding_key(r)]
    after = p.to_dict()
    assert [e["box"] for e in after["patcher"]["boxes"] if e["box"]["id"] != sub.id] == top_boxes
    assert after["patcher"]["lines"] == top_lines
    assert len(after["patcher"]["boxes"]) == len(top_before["patcher"]["boxes"])
    assert len(inner.boxes) == n_inner + 1
    assert any(b.text == "t l l" for b in inner.boxes)
    assert not _by_rule(_review(after), "fan_out_without_trigger")


def test_finding_key_and_tuple_passthrough():
    r = _fan_finding(_fan())
    k = finding_key(r)
    assert k == ("fan_out_without_trigger", ("obj-1", "obj-2"), 0, "")
    assert finding_key(k) == k
    assert finding_key(("r", ["a"], None, "")) == ("r", ("a",), None, "")


def test_fixable_findings_does_not_mutate_dict():
    d = _fan()
    before = copy.deepcopy(d)
    found = fixable_findings(d, db=_db())
    assert d == before
    assert [r.rule for r in found] == ["fan_out_without_trigger"]


def test_apply_quick_fixes_missing_key_in_memory():
    p = _fan_patcher()
    before = p.to_dict()
    with pytest.raises(FixError):
        apply_quick_fixes(p, [("fan_out_without_trigger", ("obj-9",), 0, "")], db=_db())
    assert p.to_dict() == before


# ---------------------------------------------------------------------------
# Task 1: preview and edit_patch end to end
# ---------------------------------------------------------------------------


def _no_save(monkeypatch) -> None:
    def _boom(*a, **k):
        raise AssertionError("must not save or write")

    monkeypatch.setattr("src.maxpat.hooks.save_patch_roundtrip", _boom)
    monkeypatch.setattr("src.maxpat.hooks._write_and_sync", _boom)


def test_preview_writes_nothing(tmp_path, monkeypatch):
    P = tmp_path / "fan.maxpat"
    P.write_text(json.dumps(_fan(), indent=4))
    before = P.read_bytes()
    _no_save(monkeypatch)
    diff = preview_quick_fixes(P, fixable_findings(json.loads(before), db=_db()), db=_db())
    assert P.read_bytes() == before
    assert len(diff.of("box_added")) == 1
    assert len(diff.of("cord_removed")) == 2
    assert len(diff.of("cord_added")) == 3
    assert "t l l" in diff.render()


def test_edit_patch_applies_trigger_fix(tmp_path):
    root = _repo(tmp_path)
    P = _patch_path(root)
    _seed(root, P, _fan())
    keys = [finding_key(r) for r in fixable_findings(json.loads(P.read_text()), db=_db())]
    assert keys == [("fan_out_without_trigger", ("obj-1", "obj-2"), 0, "")]

    s = edit_patch(P)
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        with s as p:
            apply_quick_fixes(p, keys, db=_db())
    assert s.saved is True
    assert s.commit_hash
    assert _head_files(root) == [REL_P]
    saved = json.loads(P.read_text())
    assert not _by_rule(_review(saved), "fan_out_without_trigger")
    gate = _gate_warnings(record)
    assert len(gate) == 1, [str(w.message) for w in gate]
    msg = str(gate[0].message)
    assert "2 cord(s) removed" in msg
    assert "obj-1:0 -> obj-2:0" in msg and "obj-1:0 -> obj-2:1" in msg
    assert len(s.diff.of("box_added")) == 1


def test_edit_patch_missing_key_writes_nothing(tmp_path):
    root = _repo(tmp_path)
    P = _patch_path(root)
    _seed(root, P, _fan())
    before = P.read_bytes()
    head = _head(root)
    s = edit_patch(P)
    with pytest.raises(FixError):
        with s as p:
            apply_quick_fixes(p, [("fan_out_without_trigger", ("obj-9",), 0, "")], db=_db())
    assert P.read_bytes() == before
    assert _head(root) == head
    assert s.saved is False


def test_quickfix_module_never_saves():
    tree = ast.parse(QUICKFIX_PY.read_text())
    banned = {"save_patch_roundtrip", "_write_and_sync", "auto_commit_patch"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            assert not [k for k in node.keywords if k.arg == "force"], ast.dump(node)
        if isinstance(node, ast.Name):
            assert node.id not in banned, node.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in banned, node.attr
        if isinstance(node, ast.alias):
            assert node.name not in banned, node.name


# ---------------------------------------------------------------------------
# Task 2: gen~ @param rewrite
# ---------------------------------------------------------------------------


def _gen_param_patcher(text: str, to_gen: bool = True) -> Patcher:
    p = Patcher()
    fl = p.add_box("flonum")             # obj-1
    msg = p.add_message(text)            # obj-2
    dst = p.add_box("gen~") if to_gen else p.add_box("print")  # obj-3
    p.add_connection(fl, 0, msg, 0)
    p.add_connection(msg, 0, dst, 0)
    return p


def _gen_param_validation_ids(d: dict) -> set:
    out = set()
    for v in validate_patch(copy.deepcopy(d)):
        if "plain name messages" in v.message:
            out.add(v.message.rsplit("(", 1)[1].rstrip(")"))
    return out


def test_gen_param_warning_and_fix():
    d = _gen_param_patcher("@depth $1").to_dict()
    found = _by_rule(_review(d), "gen_param_message_syntax")
    assert len(found) == 1
    r = found[0]
    assert r.severity == "warning"
    assert r.box_ids == ("obj-2", "obj-3")
    assert r.fix is not None and r.fix.kind == "rewrite_gen_param"
    check_fix_contract(r.fix)
    (op,) = r.fix.ops
    assert op.op == "set_text" and op.box == "obj-2"
    assert (op.old_text, op.text) == ("@depth $1", "depth $1")


def test_gen_param_multi_segment():
    d = _gen_param_patcher("@a $1, @b $2").to_dict()
    (r,) = _by_rule(_review(d), "gen_param_message_syntax")
    assert r.fix.ops[0].text == "a $1, b $2"


def test_gen_param_not_cabled_to_gen_no_finding():
    d = _gen_param_patcher("@depth $1", to_gen=False).to_dict()
    assert not _by_rule(_review(d), "gen_param_message_syntax")


@pytest.mark.parametrize("text,to_gen", [
    ("@depth $1", True), ("@a $1, @b $2", True), ("depth $1", True),
    ("@depth $1", False), ("@depth 3", True),
])
def test_gen_param_parity_with_validation(text, to_gen):
    d = _gen_param_patcher(text, to_gen).to_dict()
    critic = {r.box_ids[0] for r in _by_rule(_review(d), "gen_param_message_syntax")}
    assert critic == _gen_param_validation_ids(d)


def test_gen_param_apply_clears_both():
    p = _gen_param_patcher("@depth $1")
    (r,) = _by_rule(_review(p.to_dict()), "gen_param_message_syntax")
    apply_fix(p, r)
    msg = next(b for b in p.boxes if b.id == "obj-2")
    assert msg.text == "depth $1"
    d = p.to_dict()
    assert not _by_rule(_review(d), "gen_param_message_syntax")
    assert _gen_param_validation_ids(d) == set()


# ---------------------------------------------------------------------------
# Task 2: unsafe gain -> scale / clip
# ---------------------------------------------------------------------------


def _gain_patcher(build) -> Patcher:
    """cycle~ (obj-1) -> *~ (obj-2) inlet 0, *~ -> dac~ (obj-3) 0/1; build(p, gain) adds the source."""
    p = Patcher()
    osc = p.add_box("cycle~", ["440"])
    gain = p.add_box("*~")
    dac = p.add_box("dac~")
    p.add_connection(osc, 0, gain, 0)
    p.add_connection(gain, 0, dac, 0)
    p.add_connection(gain, 0, dac, 1)
    build(p, gain)
    return p


def _gain_finding(d: dict):
    found = _by_rule(_review(d), "unsafe_gain_sources")
    assert len(found) == 1, found
    return found[0]


def _assert_gain_fix_applies(p: Patcher, r) -> None:
    apply_fix(p, r)
    assert not _by_rule(_review(p.to_dict()), "unsafe_gain_sources")
    assert _errors(p.to_dict()) == []


def test_gain_slider_scale_fix():
    def build(p, gain):
        s = p.add_box("slider")  # obj-4
        p.add_connection(s, 0, gain, 1)
    p = _gain_patcher(build)
    r = _gain_finding(p.to_dict())
    assert r.severity == "blocker" and r.box_ids == ("obj-4", "obj-2") and r.port == 1
    fx = r.fix
    assert fx is not None and fx.kind == "insert_gain_normalizer"
    check_fix_contract(fx)
    (add,) = _ops(fx, "add_box")
    assert add.text == "scale 0. 127. 0. 1." and add.near == "obj-4"
    assert [(o.src, o.outlet, o.dst, o.inlet) for o in _ops(fx, "remove_cord")] == [("obj-4", 0, "obj-2", 1)]
    assert {(o.src, o.outlet, o.dst, o.inlet) for o in _ops(fx, "add_cord")} == {
        ("obj-4", 0, add.box, 0), (add.box, 0, "obj-2", 1),
    }
    _assert_gain_fix_applies(p, r)
    assert any(b.text == "scale 0. 127. 0. 1." for b in p.boxes)


def test_gain_live_dial_bounds():
    def build(p, gain):
        dl = p.add_box("live.dial")  # obj-4
        p.add_connection(dl, 0, gain, 1)
    d = _gain_patcher(build).to_dict()
    for e in d["patcher"]["boxes"]:
        if e["box"]["id"] == "obj-4":
            e["box"]["saved_attribute_attributes"] = {
                "valueof": {"parameter_mmin": -12, "parameter_mmax": 12},
            }
    r = _gain_finding(d)
    assert _ops(r.fix, "add_box")[0].text == "scale -12. 12. 0. 1."
    _assert_gain_fix_applies(Patcher.from_dict(d), r)


def test_gain_via_line_tilde():
    def build(p, gain):
        s = p.add_box("slider")   # obj-4
        ln = p.add_box("line~")   # obj-5
        p.add_connection(s, 0, ln, 0)
        p.add_connection(ln, 0, gain, 1)
    p = _gain_patcher(build)
    r = _gain_finding(p.to_dict())
    fx = r.fix
    assert fx is not None
    assert [(o.src, o.dst, o.inlet) for o in _ops(fx, "remove_cord")] == [("obj-4", "obj-5", 0)]
    assert _ops(fx, "add_box")[0].text == "scale 0. 127. 0. 1."
    _assert_gain_fix_applies(p, r)


def test_gain_constant_clip():
    def build(p, gain):
        m = p.add_message("127")  # obj-4
        f = p.add_box("f")        # obj-5
        p.add_connection(m, 0, f, 0)
        p.add_connection(f, 0, gain, 1)
    p = _gain_patcher(build)
    r = _gain_finding(p.to_dict())
    fx = r.fix
    assert fx is not None
    assert _ops(fx, "add_box")[0].text == "clip 0. 1."
    assert [(o.src, o.dst, o.inlet) for o in _ops(fx, "remove_cord")] == [("obj-4", "obj-5", 0)]
    _assert_gain_fix_applies(p, r)


def test_gain_no_fix_message_into_line():
    def build(p, gain):
        m = p.add_message("0, 127 500")
        ln = p.add_box("line~")
        p.add_connection(m, 0, ln, 0)
        p.add_connection(ln, 0, gain, 1)
    r = _gain_finding(_gain_patcher(build).to_dict())
    assert r.severity == "blocker" and r.fix is None


def test_gain_no_fix_two_path_cords():
    def build(p, gain):
        s = p.add_box("slider")
        f = p.add_box("f")
        p.add_connection(s, 0, gain, 1)
        p.add_connection(s, 0, f, 0)
        p.add_connection(f, 0, gain, 1)
    found = _by_rule(_review(_gain_patcher(build).to_dict()), "unsafe_gain_sources")
    assert found and all(r.fix is None for r in found)


def test_gain_no_fix_ops_push_past_one():
    def build(p, gain):
        s = p.add_box("slider")
        m = p.add_box("*", ["200"])
        p.add_connection(s, 0, m, 0)
        p.add_connection(m, 0, gain, 1)
    r = _gain_finding(_gain_patcher(build).to_dict())
    assert r.fix is None


# ---------------------------------------------------------------------------
# Task 2: bach @out t
# ---------------------------------------------------------------------------


def _bach_patcher(text_args, consumers=("expr",), outlet=0, bach_name="bach.nth") -> Patcher:
    p = Patcher()
    b = p.add_box(bach_name, list(text_args))  # obj-1
    for c in consumers:
        if c == "p":
            box, _inner = p.add_subpatcher("x", inlets=1, outlets=0)
        elif c == "expr":
            box = p.add_box("expr", ["$i1", "+", "1"])
        else:
            box = p.add_box(c)
        p.add_connection(b, outlet, box, 0)
    return p


def _bach_findings(p: Patcher) -> list:
    return _by_rule(_review(p.to_dict()), "bach_out_mode")


def test_bach_out_warning_and_fix():
    p = _bach_patcher(["1"])
    (r,) = _bach_findings(p)
    assert r.severity == "warning"
    assert r.box_ids[0] == "obj-1" and r.box_ids == ("obj-1", "obj-2") and r.port == 0
    assert r.fix is not None and r.fix.kind == "set_bach_out"
    check_fix_contract(r.fix)
    (op,) = r.fix.ops
    assert (op.box, op.old_text, op.text) == ("obj-1", "bach.nth 1", "bach.nth 1 @out t")


@pytest.mark.parametrize("args,expected", [
    (["1", "@out", "n"], "bach.nth 1 @out t"),
    (["1", "@out", "tn"], "bach.nth 1 @out tt"),
])
def test_bach_out_replaces_existing_value(args, expected):
    (r,) = _bach_findings(_bach_patcher(args))
    assert r.fix.ops[0].text == expected


def test_bach_out_t_no_finding():
    assert not _bach_findings(_bach_patcher(["1", "@out", "t"]))


def test_bach_out_one_finding_per_box():
    p = _bach_patcher(["1"], consumers=("expr", "print"))
    (r,) = _bach_findings(p)
    assert r.box_ids == ("obj-1", "obj-2", "obj-3")


@pytest.mark.parametrize("consumer", ["bach.flat", "outlet", "send", "p"])
def test_bach_out_exempt_consumers(consumer):
    if consumer == "outlet":
        outer = Patcher()
        _box, inner = outer.add_subpatcher("x", inlets=0, outlets=1)
        b = inner.add_box("bach.nth", ["1"])
        inner.add_connection(b, 0, inner.get_outlets()[0], 0)
        assert not _by_rule(_review(outer.to_dict()), "bach_out_mode")
        return
    assert not _bach_findings(_bach_patcher(["1"], consumers=(consumer,)))


def test_bach_roll_bang_outlet_exempt():
    assert not _bach_findings(_bach_patcher([], consumers=("print",), outlet=7, bach_name="bach.roll"))
    (r,) = _bach_findings(_bach_patcher([], consumers=("print",), outlet=0, bach_name="bach.roll"))
    # bach.roll is a UI box: its @out is the saved "out" attribute, which no
    # Q39 fix op sets, so the warning carries no fix.
    assert r.box_ids == ("obj-1", "obj-2") and r.port == 0
    assert r.fix is None


def test_bach_ui_out_attribute_read():
    p = _bach_patcher([], consumers=("print",), outlet=0, bach_name="bach.roll")
    d = p.to_dict()
    d["patcher"]["boxes"][0]["box"]["out"] = "ttttttt"
    assert not _by_rule(_review(d), "bach_out_mode")
    d["patcher"]["boxes"][0]["box"]["out"] = "nnnnnnn"
    assert _by_rule(_review(d), "bach_out_mode")


def test_bach_out_apply_keeps_io_and_cords():
    p = _bach_patcher(["1"], consumers=("expr", "print"))
    b = next(x for x in p.boxes if x.id == "obj-1")
    io = (b.numinlets, b.numoutlets)
    cords = _cord_set(p)
    (r,) = _bach_findings(p)
    apply_fix(p, r)
    assert b.text == "bach.nth 1 @out t"
    assert (b.numinlets, b.numoutlets) == io
    assert _cord_set(p) == cords
    assert not _bach_findings(p)


def test_bach_out_guard_rejects_non_bach_box():
    p = _bach_patcher(["1"])
    bad = Fix("set_bach_out", "d", (FixOp("set_text", box="obj-2", text="expr $i1 + 2", old_text="expr $i1 + 1"),))
    _guard(p, CriticResult("warning", "f", "s", rule="x", fix=bad))


# ---------------------------------------------------------------------------
# Task 3: exports, /max-iterate --fix doc, corpus safety
# ---------------------------------------------------------------------------


def test_exports():
    import src.maxpat as m
    import src.maxpat.critics as c
    from src.maxpat import fixable_findings as ff, preview_quick_fixes as pq, apply_quick_fixes as aq, FixError as fe  # noqa: F401
    from src.maxpat.critics import Fix as F, FixOp as FO  # noqa: F401
    for name in ("FixError", "finding_key", "fixable_findings", "apply_fix",
                 "apply_quick_fixes", "preview_quick_fixes"):
        assert name in m.__all__, name
        assert getattr(m, name) is not None
    for name in ("Fix", "FixOp", "FIX_KINDS", "check_fix_contract"):
        assert name in c.__all__, name
        assert getattr(c, name) is not None
    assert m.FixError is FixError and c.Fix is Fix


ITERATE_MD = REPO_ROOT / ".claude" / "commands" / "max-iterate.md"


def test_max_iterate_documents_fix():
    text = ITERATE_MD.read_text(encoding="utf-8")
    front = text.split("---", 2)[1]
    hint = next(l for l in front.splitlines() if l.startswith("argument-hint:"))
    assert "--fix" in hint
    flags = text.split("## Flags", 1)[1].split("\n## ", 1)[0]
    assert "| --fix |" in flags
    for name in ("fixable_findings", "preview_quick_fixes", "apply_quick_fixes",
                 "edit_patch", "session.diff.render()"):
        assert name in text, name
    assert "/max-iterate --fix" in text
    section = text.split("## Quick-fix mode", 1)[1].split("\n## ", 1)[0]
    assert "force=True" not in section and "apply_quick_fixes(patcher, selected)" in section


def test_corpus_fixes_apply_cleanly():
    db = _db()
    exercised = 0
    files = _tracked()
    assert files, "no tracked patches"
    for rel in files:
        d = json.loads(_head_bytes(rel))
        found = fixable_findings(d, db=db)
        if not found:
            continue
        pre = review_patch(copy.deepcopy(d), db=db)
        pre_blockers = {finding_key(r) for r in pre if r.severity == "blocker"}
        pre_errors = len(_errors(d))
        for r in found:
            key = finding_key(r)
            p = Patcher.from_dict(copy.deepcopy(d))
            apply_quick_fixes(p, [key], db=db)
            after_d = p.to_dict()
            post = review_patch(copy.deepcopy(after_d), db=db)
            post_keys = {finding_key(x) for x in post}
            assert key not in post_keys, (rel, key)
            new_blockers = {finding_key(x) for x in post if x.severity == "blocker"} - pre_blockers
            assert not new_blockers, (rel, key, new_blockers)
            assert len(_errors(after_d)) <= pre_errors, (rel, key)
            exercised += 1
    assert exercised >= 1, f"corpus: {len(files)} patches, {exercised} fixes exercised"
