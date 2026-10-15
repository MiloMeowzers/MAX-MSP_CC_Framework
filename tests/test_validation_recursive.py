"""Recursive, per-scope validation (Q19; review A7, S1, S2, G8 part).

validate_patch walks every embedded patcher (``p``, embedded bpatcher, gen~,
mc.gen~ ``data.patcher``, jit.gen, rnbo~ ...) through ``walk.iter_patchers``
and runs Layers 1-5 on each with that scope's own rules. Nested findings
carry ``ValidationResult.path`` (the box-id chain, ``obj-1/obj-2``) and a
``[label > label] `` message prefix; top-level findings are unchanged.
apply_fixes removes nested cords in their own scope only, and the save gate
refuses a new file with a nested blocker.

Saves run inside a throwaway git repo under ``tmp_path`` (fixture and
helper copied from tests/test_save_gate.py, not imported).
"""

from __future__ import annotations

import copy
import shutil
import subprocess
from pathlib import Path

import pytest

from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.patcher import Patcher
from src.maxpat.validation import (
    ValidationResult,
    apply_fixes,
    has_blocking_errors,
    validate_patch,
)


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


# ---------------------------------------------------------------------------
# Builders (local, in the style of tests/test_domain_scope.py)
# ---------------------------------------------------------------------------


def _box(box_id, text, n_in=1, n_out=1, maxclass="newobj", outlettype=None, **extra):
    box = {
        "id": box_id,
        "maxclass": maxclass,
        "numinlets": n_in,
        "numoutlets": n_out,
        "outlettype": outlettype if outlettype is not None else [""] * n_out,
        "patching_rect": [10.0, 10.0, 80.0, 22.0],
    }
    if text is not None:
        box["text"] = text
    box.update(extra)
    return {"box": box}


def _line(src, outlet, dst, inlet):
    return {"patchline": {"source": [src, outlet], "destination": [dst, inlet]}}


def _inner(boxes=None, lines=None, **keys):
    d = {"boxes": boxes if boxes is not None else [], "lines": lines if lines is not None else []}
    d.update(keys)
    return d


def _container(box_id, text, inner, n_in=1, n_out=1, maxclass="newobj", **extra):
    entry = _box(box_id, text, n_in=n_in, n_out=n_out, maxclass=maxclass, **extra)
    entry["box"]["patcher"] = inner
    return entry


def _patch(boxes=None, lines=None, **keys):
    return {"patcher": _inner(boxes, lines, **keys)}


def _sig(results):
    return [(r.layer, r.level, r.message, r.proposed_removal, r.path) for r in results]


def _a7_content():
    """The A7 reproduction: osc~ (PD), *~ 0.5, cycle~ outlet 2 -> *~ (OOR)."""
    boxes = [
        _box("obj-1", "osc~ 440", 2, 1, outlettype=["signal"]),
        _box("obj-2", "*~ 0.5", 2, 1, outlettype=["signal"]),
        _box("obj-3", "cycle~ 440", 2, 1, outlettype=["signal"]),
    ]
    lines = [_line("obj-3", 2, "obj-2", 0)]
    return boxes, lines


def _osc_p(box_id="obj-1", label="p synth"):
    return _container(box_id, label, _inner([_box("obj-10", "osc~ 440", 2, 1, outlettype=["signal"])]))


def _osc_hits(results):
    return [r for r in results if "'osc~' is a Pure Data object" in r.message]


# ---------------------------------------------------------------------------
# A7: nested findings are reported with their path
# ---------------------------------------------------------------------------


class TestNestedFindings:
    def test_osc_in_p_synth(self, db):
        results = validate_patch(_patch([_osc_p()]), db=db)
        hits = _osc_hits(results)
        assert len(hits) == 1, results
        r = hits[0]
        assert r.layer == "objects" and r.level == "error"
        assert r.path == "obj-1"
        assert r.message == "[p synth] 'osc~' is a Pure Data object, not MAX. Use cycle~ instead."

    def test_top_level_path_empty(self, db):
        boxes, lines = _a7_content()
        results = validate_patch(_patch(boxes, lines), db=db)
        assert results
        assert all(r.path == "" for r in results)
        assert not any(r.message.startswith("[") for r in results)

    def test_nested_parity_with_top_level(self, db):
        """Invariant: content wrapped in `p synth` gives exactly its top-level
        findings, prefixed and tagged with the p's path."""
        boxes, lines = _a7_content()
        top = validate_patch(_patch(copy.deepcopy(boxes), copy.deepcopy(lines)), db=db)
        wrapped = _patch([_container("obj-1", "p synth", _inner(boxes, lines))])
        res = validate_patch(wrapped, db=db)
        nested = [r for r in res if r.path == "obj-1"]
        expected = [
            (r.layer, r.level, "[p synth] " + r.message, r.proposed_removal, "obj-1")
            for r in top
        ]
        assert _sig(nested) == expected
        assert [r for r in res if r.path not in ("", "obj-1")] == []
        # The A7 content is a real blocker set at either depth.
        assert any(r.proposed_removal == ("obj-3", 2, "obj-2", 0) for r in nested)
        assert has_blocking_errors(res)

    def test_oor_cord_in_subpatcher_proposed_with_path(self, db):
        boxes, lines = _a7_content()
        res = validate_patch(_patch([_container("obj-1", "p synth", _inner(boxes, lines))]), db=db)
        props = [r for r in res if r.proposed_removal is not None]
        assert len(props) == 1
        assert props[0].proposed_removal == ("obj-3", 2, "obj-2", 0)
        assert props[0].path == "obj-1"
        assert props[0].message.startswith("[p synth] Outlet index 2 out of bounds on 'obj-3'")

    def test_order_top_then_preorder(self, db):
        d = _patch([
            _box("obj-9", "osc~ 1", 2, 1, outlettype=["signal"]),
            _container("obj-1", "p a", _inner([
                _box("obj-10", "osc~ 2", 2, 1, outlettype=["signal"]),
                _container("obj-2", "p b", _inner([
                    _box("obj-20", "osc~ 3", 2, 1, outlettype=["signal"]),
                ])),
            ])),
            _container("obj-3", "p c", _inner([
                _box("obj-30", "osc~ 4", 2, 1, outlettype=["signal"]),
            ])),
        ])
        res = validate_patch(d, db=db)
        paths = [r.path for r in res]
        first_nested = next(i for i, p in enumerate(paths) if p)
        assert all(p == "" for p in paths[:first_nested])
        seen = []
        for p in paths[first_nested:]:
            assert p != ""
            if not seen or seen[-1] != p:
                seen.append(p)
        assert seen == ["obj-1", "obj-1/obj-2", "obj-3"]
        deep = [r for r in _osc_hits(res) if r.path == "obj-1/obj-2"]
        assert deep[0].message.startswith("[p a > p b] ")

    def test_external_not_loaded(self, db, monkeypatch):
        import builtins

        opened = []
        real_open = builtins.open

        def spy(file, *a, **kw):
            opened.append(str(file))
            return real_open(file, *a, **kw)

        d = _patch([
            _box("obj-1", None, 1, 1, maxclass="bpatcher", name="nowhere-x.maxpat"),
            _box("obj-2", "poly~ nowhere-voice 8", 1, 1),
        ])
        monkeypatch.setattr(builtins, "open", spy)
        res = validate_patch(d, db=db)
        monkeypatch.undo()
        assert not any("nowhere" in f for f in opened)
        assert all(r.path == "" for r in res)

    def test_deep_chain(self, db):
        cur = _inner([_box("obj-x", "osc~ 1", 2, 1, outlettype=["signal"])])
        for i in range(1500, 0, -1):
            cur = _inner([_container(f"obj-{i}", "p d", cur)])
        res = validate_patch({"patcher": cur}, db=db)
        hits = _osc_hits(res)
        assert len(hits) == 1
        assert hits[0].path.count("/") == 1499
        assert hits[0].path.startswith("obj-1/obj-2/")


# ---------------------------------------------------------------------------
# apply_fixes: nested proposals are removed in their own scope only
# ---------------------------------------------------------------------------


def _nested_oor_with_twin():
    """Top-level cord with the SAME 4-tuple as the nested OOR cord."""
    boxes, lines = _a7_content()
    top_boxes = [
        _container("obj-1", "p synth", _inner(boxes, lines)),
        _box("obj-3", "cycle~ 440", 2, 3, outlettype=["signal", "", ""]),
        _box("obj-2", "*~ 0.5", 2, 1, outlettype=["signal"]),
    ]
    return _patch(top_boxes, [_line("obj-3", 2, "obj-2", 0)])


class TestApplyFixesNested:
    def test_dict_removes_inner_only(self, db):
        d = _nested_oor_with_twin()
        res = validate_patch(d, db=db)
        assert [r.proposed_removal for r in res if r.proposed_removal] == [("obj-3", 2, "obj-2", 0)]
        inner_lines = d["patcher"]["boxes"][0]["box"]["patcher"]["lines"]
        top_lines = d["patcher"]["lines"]
        removed = apply_fixes(d, res)
        assert removed == [("obj-1", "obj-3", 2, "obj-2", 0)]
        assert d["patcher"]["boxes"][0]["box"]["patcher"]["lines"] is inner_lines
        assert inner_lines == []
        assert d["patcher"]["lines"] is top_lines
        assert len(top_lines) == 1
        assert [r for r in validate_patch(d, db=db) if r.proposed_removal] == []

    def test_patcher_removes_inner_only(self, db):
        d = _nested_oor_with_twin()
        p = Patcher.from_dict(copy.deepcopy(d), db=db)
        res = validate_patch(p, db=db)
        removed = apply_fixes(p, res)
        assert removed == [("obj-1", "obj-3", 2, "obj-2", 0)]
        inner = p.boxes[0]._inner_patcher
        assert inner.lines == []
        assert len(p.lines) == 1
        assert [r for r in validate_patch(p, db=db) if r.proposed_removal] == []

    def _mcgen(self):
        inner = _inner(
            [
                _box("obj-11", "in 1", 0, 1, outlettype=[""]),
                _box("obj-12", "out 1", 1, 0, outlettype=[]),
            ],
            [_line("obj-11", 3, "obj-12", 0)],
            classnamespace="dsp.gen",
        )
        top = _box("obj-1", "mc.gen~ @chans 2", 1, 1, outlettype=["multichannelsignal"],
                   data={"patcher": inner})
        return _patch([top])

    def test_mcgen_data_patcher_dict(self, db):
        d = self._mcgen()
        res = validate_patch(d, db=db)
        props = [r for r in res if r.proposed_removal]
        assert len(props) == 1 and props[0].path == "obj-1"
        assert props[0].message.startswith("[mc.gen~] ")
        removed = apply_fixes(d, res)
        assert removed == [("obj-1", "obj-11", 3, "obj-12", 0)]
        assert d["patcher"]["boxes"][0]["box"]["data"]["patcher"]["lines"] == []
        assert [r for r in validate_patch(d, db=db) if r.proposed_removal] == []

    def test_mcgen_data_patcher_patcher(self, db):
        p = Patcher.from_dict(self._mcgen(), db=db)
        res = validate_patch(p, db=db)
        removed = apply_fixes(p, res)
        assert removed == [("obj-1", "obj-11", 3, "obj-12", 0)]
        out = p.to_dict()
        assert out["patcher"]["boxes"][0]["box"]["data"]["patcher"]["lines"] == []
        assert [r for r in validate_patch(p, db=db) if r.proposed_removal] == []

    def test_mixed_top_and_nested_result_order(self, db):
        boxes, lines = _a7_content()
        d = _patch(
            [
                _box("obj-5", "number", 1, 2, maxclass="number", outlettype=["", "bang"]),
                _box("obj-6", "print", 1, 0, outlettype=[]),
                _container("obj-1", "p synth", _inner(boxes, lines)),
            ],
            [_line("obj-5", 0, "obj-6", 7)],
        )
        res = validate_patch(d, db=db)
        removed = apply_fixes(d, res)
        assert removed == [("obj-5", 0, "obj-6", 7), ("obj-1", "obj-3", 2, "obj-2", 0)]
        assert d["patcher"]["lines"] == []
        assert d["patcher"]["boxes"][2]["box"]["patcher"]["lines"] == []
        assert [r for r in validate_patch(d, db=db) if r.proposed_removal] == []

    def test_top_level_unchanged_return_shape(self, db):
        boxes, lines = _a7_content()
        d = _patch(boxes, lines)
        res = validate_patch(d, db=db)
        assert apply_fixes(d, res) == [("obj-3", 2, "obj-2", 0)]


# ---------------------------------------------------------------------------
# Scope rules
# ---------------------------------------------------------------------------


def _unterminated(results):
    return [r for r in results if "Unterminated signal chain" in r.message]


class TestScopeRules:
    def _cyc(self):
        return _box("obj-10", "cycle~ 440", 2, 1, outlettype=["signal"])

    def test_gen_scope_skips_layer4(self, db):
        d = _patch([_container("obj-1", "gen~", _inner([self._cyc()]))])
        assert _unterminated(validate_patch(d, db=db)) == []

    def test_top_level_gen_skips_layer4(self, db):
        d = _patch([self._cyc()], classnamespace="dsp.gen")
        assert _unterminated(validate_patch(d, db=db)) == []

    def test_p_scope_runs_layer4(self, db):
        d = _patch([_container("obj-1", "p x", _inner([self._cyc()]))])
        hits = _unterminated(validate_patch(d, db=db))
        assert len(hits) == 1
        assert hits[0].path == "obj-1"
        assert hits[0].message.startswith("[p x] Unterminated signal chain")

    def test_layer1_error_prunes_scope(self, db):
        d = _patch([
            _container("obj-1", "p bad", _inner(
                [_container("obj-2", "p deeper", _inner([
                    _box("obj-20", "osc~ 1", 2, 1, outlettype=["signal"]),
                ]))],
                lines="x",
            )),
            _osc_p("obj-3", "p sib"),
        ])
        res = validate_patch(d, db=db)
        json_errs = [r for r in res if r.layer == "json"]
        assert len(json_errs) == 1
        assert json_errs[0].path == "obj-1"
        assert json_errs[0].message == "[p bad] Missing or invalid 'lines' array in patcher"
        osc = _osc_hits(res)
        assert [r.path for r in osc] == ["obj-3"]
        assert not any(r.path.startswith("obj-1") and r.layer != "json" for r in res)

    def test_community_warning_once_per_patch(self, db, monkeypatch):
        info = dict(db.get_package_info("FluCoMa") or {})
        info["extracted"] = False
        monkeypatch.setitem(db._package_info, "FluCoMa", info)
        fl = lambda i: _box(i, "fluid.ampfeature~", 1, 2, outlettype=["signal", ""])  # noqa: E731
        d = _patch([fl("obj-1"), _container("obj-2", "p f", _inner([fl("obj-20")]))])
        res = validate_patch(d, db=db)
        hits = [r for r in res if r.layer == "packages" and "not extracted" in r.message]
        assert len(hits) == 1
        assert hits[0].path == ""


# ---------------------------------------------------------------------------
# Purity
# ---------------------------------------------------------------------------


def _mixed_nested():
    boxes, lines = _a7_content()
    gen_inner = _inner([
        _box("obj-21", "in 1", 0, 1, outlettype=[""]),
        _box("obj-22", "codebox", 1, 1, maxclass="codebox", code="out1 = in1;"),
    ], [_line("obj-21", 0, "obj-22", 0)], classnamespace="dsp.gen")
    return _patch([
        _container("obj-1", "p synth", _inner(boxes, lines)),
        _container("obj-2", "gen~", gen_inner, outlettype=["signal"]),
        _box("obj-3", "mc.gen~", 1, 1, outlettype=["multichannelsignal"],
             data={"patcher": copy.deepcopy(gen_inner)}),
    ])


class TestPurity:
    def test_nested_dict_unchanged(self, db):
        d = _mixed_nested()
        before = copy.deepcopy(d)
        validate_patch(d, db=db)
        assert d == before

    def test_patcher_unchanged_and_parity(self, db):
        d = _mixed_nested()
        p = Patcher.from_dict(copy.deepcopy(d), db=db)
        before = p.to_dict()
        res_p = validate_patch(p, db=db)
        assert p.to_dict() == before
        assert _sig(res_p) == _sig(validate_patch(d, db=db))
        assert any(r.path == "obj-1" for r in res_p)


# ---------------------------------------------------------------------------
# Save gate: a nested blocker refuses a new file
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
    """Create a throwaway git repo at tmp_path/repo and return its resolved root."""
    root = tmp_path / "repo"
    root.mkdir()
    hooks = tmp_path / "empty-hooks"
    hooks.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Save Gate Test")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "config", "core.hooksPath", str(hooks))
    return root.resolve()


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
class TestSaveGateNested:
    def test_new_file_with_nested_osc_refused(self, tmp_path):
        from src.maxpat.hooks import PatchValidationError, save_patch_roundtrip

        root = _repo(tmp_path)
        P = root / "patches" / "demo" / "generated" / "demo.maxpat"
        d = Patcher().to_dict()
        d["patcher"]["boxes"].append(_osc_p())

        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(d, P)

        vfind = [
            f for f in excinfo.value.findings
            if isinstance(f, ValidationResult) and f.path == "obj-1"
        ]
        assert vfind, excinfo.value.findings
        assert vfind[0].message.startswith("[p synth] ")
        assert "'osc~' is a Pure Data object" in vfind[0].message
        assert not P.exists()


# ---------------------------------------------------------------------------
# Layer 5: codeboxes in every gen scope (Task 2)
# ---------------------------------------------------------------------------

_DELAY_CODE = "out1 = delay(in1, 100);"


def _codebox(box_id="obj-90", code=_DELAY_CODE):
    return _box(box_id, None, 1, 1, maxclass="codebox", code=code)


def _gen_inner(boxes, **keys):
    keys.setdefault("classnamespace", "dsp.gen")
    return _inner(boxes, **keys)


def _delay_hits(results):
    return [r for r in results if "delay()" in r.message]


class TestLayer5EveryScope:
    def test_p_gen_codebox_reported_once_at_parent(self, db):
        d = _patch([
            _container("obj-1", "p synth", _inner([
                _container("obj-2", "gen~", _gen_inner([_codebox()]), outlettype=["signal"]),
            ])),
        ])
        res = validate_patch(d, db=db)
        hits = _delay_hits(res)
        assert len(hits) == 1, [r.message for r in res]
        assert hits[0].level == "error"
        assert hits[0].path == "obj-1"
        assert hits[0].message.startswith("[p synth] gen~ 'obj-2' codebox: ")
        assert not any("codebox" in r.message for r in res if r.path == "obj-1/obj-2")

    def test_top_level_mcgen_data_patcher(self, db):
        d = _patch([
            _box("obj-1", "mc.gen~ @chans 2", 1, 1, outlettype=["multichannelsignal"],
                 data={"patcher": _gen_inner([_codebox()])}),
        ])
        res = validate_patch(d, db=db)
        hits = _delay_hits(res)
        assert len(hits) == 1, [r.message for r in res]
        assert hits[0].level == "error"
        assert hits[0].path == ""
        assert hits[0].message.startswith("mc.gen~ 'obj-1' codebox: ")

    @pytest.mark.parametrize("name", ["jit.gen", "jit.pix", "jit.gl.pix", "gen", "mcs.gen~"])
    def test_gen_family_containers(self, db, name):
        d = _patch([
            _container("obj-1", name, _gen_inner([_codebox()], classnamespace="jit.gen")),
        ])
        res = validate_patch(d, db=db)
        hits = _delay_hits(res)
        assert len(hits) == 1, [r.message for r in res]
        assert hits[0].path == ""
        assert hits[0].message.startswith(f"{name} 'obj-1' codebox: ")

    def test_p_inside_gen_codebox(self, db):
        d = _patch([
            _container("obj-1", "gen~", _gen_inner([
                _container("obj-2", "p sub", _inner([_codebox()])),
            ]), outlettype=["signal"]),
        ])
        res = validate_patch(d, db=db)
        hits = _delay_hits(res)
        assert len(hits) == 1, [r.message for r in res]
        assert hits[0].path == "obj-1"
        assert hits[0].message.startswith("[gen~] p 'obj-2' codebox: ")

    def test_top_level_gen_file_codebox_unchecked(self, db):
        d = _patch([_codebox("obj-1")], classnamespace="dsp.gen")
        assert _delay_hits(validate_patch(d, db=db)) == []

    def test_top_level_gen_tilde_form_unchanged(self, db):
        d = _patch([_container("g1", "gen~", _gen_inner([_codebox()]), outlettype=["signal"])])
        hits = _delay_hits(validate_patch(d, db=db))
        assert len(hits) == 1
        assert hits[0].path == ""
        assert hits[0].message.startswith("gen~ 'g1' codebox: ")


# ---------------------------------------------------------------------------
# Nested RNBO scopes (Task 2)
# ---------------------------------------------------------------------------


def _rnbo(boxes, lines=None, box_id="obj-1"):
    return _container(box_id, "rnbo~", _inner(boxes, lines, classnamespace="rnbo"))


def _rnbo_compat(results):
    return [r for r in results if r.layer == "rnbo-objects"]


class TestNestedRnbo:
    def test_incompatible_object_warns(self, db):
        res = validate_patch(_patch([_rnbo([_box("obj-10", "coll", 1, 4)])]), db=db)
        hits = _rnbo_compat(res)
        assert len(hits) == 1, [r.message for r in res]
        assert hits[0].level == "warning"
        assert hits[0].path == "obj-1"
        assert hits[0].message == (
            "[rnbo~] Object 'coll' is not RNBO-compatible -- cannot be used in RNBO patches"
        )
        assert not has_blocking_errors(res)

    def test_alias_resolution(self, db):
        res = validate_patch(_patch([_rnbo([
            _box("obj-10", "t b b", 1, 2),
            _box("obj-11", "sel 1", 2, 2),
            _box("obj-12", "f", 2, 1),
        ])]), db=db)
        assert _rnbo_compat(res) == []

    def _line_print(self):
        boxes = [
            _box("obj-10", "line~", 2, 2, outlettype=["signal", ""]),
            _box("obj-11", "print", 1, 0, outlettype=[]),
        ]
        return boxes, [_line("obj-10", 0, "obj-11", 0)]

    def test_type_checks_skipped_in_rnbo(self, db):
        boxes, lines = self._line_print()
        res = validate_patch(_patch([_rnbo(boxes, lines)]), db=db)
        assert [r for r in res if r.proposed_removal] == []
        boxes, lines = self._line_print()
        res = validate_patch(_patch([_container("obj-1", "p x", _inner(boxes, lines))]), db=db)
        props = [r for r in res if r.proposed_removal]
        assert [(r.path, r.proposed_removal) for r in props] == [("obj-1", ("obj-10", 0, "obj-11", 0))]

    def test_bounds_still_checked_in_rnbo(self, db):
        boxes, _ = self._line_print()
        res = validate_patch(_patch([_rnbo(boxes, [_line("obj-10", 5, "obj-11", 0)])]), db=db)
        props = [r for r in res if r.proposed_removal]
        assert [(r.path, r.proposed_removal) for r in props] == [("obj-1", ("obj-10", 5, "obj-11", 0))]

    def test_top_level_rnbo_unchanged(self, db):
        d = _patch([_box("obj-1", "coll", 1, 4)], classnamespace="rnbo")
        assert _rnbo_compat(validate_patch(d, db=db)) == []


# ---------------------------------------------------------------------------
# Robustness, duplicate ids, malformed entries (Task 3; review G8 part)
# ---------------------------------------------------------------------------


def _place(entries, nested, lines=None):
    if nested:
        return _patch([_container("obj-100", "p wrap", _inner(entries, lines))])
    return _patch(entries, lines)


class TestRobustness:
    @pytest.mark.parametrize("nested", [False, True])
    @pytest.mark.parametrize("maxclass", ["newobj", "message", "comment"])
    @pytest.mark.parametrize("text", ["", "   ", None, 5, ["a"]])
    def test_bad_text_never_raises(self, db, text, maxclass, nested):
        entry = _box("obj-1", None, 1, 1, maxclass=maxclass)
        entry["box"]["text"] = text
        other = _box("obj-2", "print", 1, 0, outlettype=[])
        res = validate_patch(_place([entry, other], nested, [_line("obj-1", 0, "obj-2", 0)]), db=db)
        assert isinstance(res, list)

    def test_empty_newobj_next_to_umenu(self, db):
        """The G8 IndexError: `_check_umenu_items_format` split empty text."""
        d = _patch([
            _box("obj-1", "", 1, 1),
            _box("obj-2", None, 1, 3, maxclass="umenu", items=["a", ",", "b"]),
        ])
        assert isinstance(validate_patch(d, db=db), list)

    def test_duplicate_ids_top_level(self, db):
        d = _patch([
            _box("obj-1", "osc~ 1", 2, 1, outlettype=["signal"]),
            _box("obj-1", "cycle~ 440", 2, 1, outlettype=["signal"]),
        ], [_line("obj-1", 0, "obj-1", 0)])
        res = validate_patch(d, db=db)
        assert [(r.layer, r.level, r.message, r.path) for r in res] == [
            ("json", "error", "Duplicate box id 'obj-1' (2 boxes)", ""),
        ]

    def test_duplicate_ids_nested_prunes(self, db):
        d = _patch([
            _container("obj-1", "p dup", _inner([
                _box("obj-5", "print", 1, 0, outlettype=[]),
                _box("obj-5", "print", 1, 0, outlettype=[]),
                _box("obj-6", "osc~ 1", 2, 1, outlettype=["signal"]),
            ])),
            _osc_p("obj-2", "p sib"),
        ])
        res = validate_patch(d, db=db)
        errs = [r for r in res if r.layer == "json"]
        assert [(r.path, r.message) for r in errs] == [
            ("obj-1", "[p dup] Duplicate box id 'obj-5' (2 boxes)"),
        ]
        assert [r.path for r in _osc_hits(res)] == ["obj-2"]

    @pytest.mark.parametrize("nested", [False, True])
    @pytest.mark.parametrize("kind", ["box_entry", "box_value", "line_entry", "patchline_value"])
    def test_malformed_entries_layer1(self, db, kind, nested):
        boxes = [_box("obj-1", "print", 1, 0, outlettype=[])]
        lines = []
        if kind == "box_entry":
            boxes.append(5)
            want = 'Malformed box entry at index 1: expected {"box": {...}}'
        elif kind == "box_value":
            boxes.append({"box": "nope"})
            want = 'Malformed box entry at index 1: expected {"box": {...}}'
        elif kind == "line_entry":
            lines.append("x")
            want = 'Malformed line entry at index 0: expected {"patchline": {...}}'
        else:
            lines.append({"patchline": 3})
            want = 'Malformed line entry at index 0: expected {"patchline": {...}}'
        res = validate_patch(_place(boxes, nested, lines), db=db)
        errs = [r for r in res if r.layer == "json" and r.level == "error"]
        assert len(errs) == 1, [r.message for r in res]
        if nested:
            assert errs[0].path == "obj-100"
            assert errs[0].message == "[p wrap] " + want
        else:
            assert errs[0].path == ""
            assert errs[0].message == want

    def test_dict_entry_without_box_key_tolerated(self, db):
        d = _patch([_box("obj-1", "print", 1, 0, outlettype=[]), {"other": 1}], [{"other": 2}])
        assert [r for r in validate_patch(d, db=db) if r.layer == "json"] == []

    @pytest.mark.requires_max
    def test_bundle_sweep_never_raises(self, db):
        import json
        import warnings

        from tests.conftest import MAX_APP_PATH
        from src.maxpat.db_lookup import SCOPE_BY_SUFFIX

        root = MAX_APP_PATH / "Contents" / "Resources" / "C74"
        files = sorted(list(root.rglob("*.maxpat")) + list(root.rglob("*.maxhelp")))
        assert files
        raised = []
        for f in files:
            try:
                d = json.loads(f.read_text(errors="replace"))
            except (ValueError, OSError):
                continue
            if not isinstance(d, dict) or not isinstance(d.get("patcher"), dict):
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    validate_patch(d, db=db, scope=SCOPE_BY_SUFFIX.get(f.suffix))
            except Exception as exc:  # noqa: BLE001 -- collect every crash
                raised.append((str(f.relative_to(root)), repr(exc)))
        assert raised == []
