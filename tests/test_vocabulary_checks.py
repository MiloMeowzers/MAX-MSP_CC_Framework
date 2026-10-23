"""Q23 vocabulary checks -- validator side (fix-plan Q23; review §4.4 R7 / R10;
quick 261022-ud6 WP7b, review-docs-completion CR-01).

Covers the validator rows of the Q23 table plus the builder / DB / save-gate
plumbing they need:

* ``expr clip()``            -- error (layer domain, max scope only)
* unknown object, load path  -- error via the save gate and ``validate_file``
  (validate_patch(patch_path=...) itself landed in WP1; see
  tests/test_validation_abstractions.py)
* line~ comma segments       -- error when a ramp segment is followed by
  another segment (planner decision D2: the jump-then-ramp idiom is fine)
* numeric bpatcher args      -- error; ``add_bpatcher`` coerces them
* message selector           -- warning (D4 guards)
* patcher ``bgcolor``        -- warning (D5)
* ``walk.message_segments`` / ``walk.message_remote_targets``
* ``ObjectDatabase.selectors`` on dict message entries (D10)

Probe shapes are rebuilt in memory from the git history quoted in the
261015-fm1 plan (physics-composition ab79ddbe, bassoon aac68ed).
"""

from __future__ import annotations

import copy
import json
import warnings
from pathlib import Path

import pytest

from src.maxpat import walk
from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.hooks import save_patch_roundtrip, validate_file
from src.maxpat.patcher import Patcher
from src.maxpat.validation import has_blocking_errors, validate_patch
from tests.test_validation import _make_box, _make_line, _make_patch_dict


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _msg(box_id, text):
    return _make_box(box_id, maxclass="message", text=text,
                     numinlets=2, numoutlets=1, outlettype=[""])


def _obj(box_id, text, numinlets=2, numoutlets=1, outlettype=None):
    return _make_box(box_id, text=text, numinlets=numinlets,
                     numoutlets=numoutlets, outlettype=outlettype or [""])


def _with(results, prefix, level=None):
    out = []
    for r in results:
        msg = r.message
        if msg.startswith("[") and "] " in msg:
            msg = msg.split("] ", 1)[1]
        if msg.startswith(prefix) and (level is None or r.level == level):
            out.append(r)
    return out


def _sub(box_id, inner_boxes, inner_lines=None, text="p x", **extra):
    box = {
        "id": box_id, "maxclass": "newobj", "text": text,
        "numinlets": 0, "numoutlets": 0, "patching_rect": [0, 0, 40, 22],
        "patcher": {"boxes": inner_boxes, "lines": inner_lines or []},
    }
    box.update(extra)
    return {"box": box}


def _gen_box(box_id, code):
    return {"box": {
        "id": box_id, "maxclass": "newobj", "text": "gen~",
        "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"],
        "patching_rect": [0, 0, 40, 22],
        "patcher": {
            "classnamespace": "dsp.gen",
            "boxes": [{"box": {
                "id": "obj-c", "maxclass": "codebox", "code": code,
                "numinlets": 1, "numoutlets": 1, "outlettype": [""],
                "patching_rect": [0, 0, 200, 100],
            }}],
            "lines": [],
        },
    }}


def _rnbo_box(box_id, inner_boxes, inner_lines=None):
    return {"box": {
        "id": box_id, "maxclass": "newobj", "text": "rnbo~",
        "numinlets": 1, "numoutlets": 1, "outlettype": ["signal"],
        "patching_rect": [0, 0, 40, 22],
        "patcher": {"classnamespace": "rnbo",
                    "boxes": inner_boxes, "lines": inner_lines or []},
    }}


# ---------------------------------------------------------------------------
# walk helpers
# ---------------------------------------------------------------------------


class TestMessageParts:

    @pytest.mark.parametrize("text, expected", [
        ("0, 1 500", [["0"], ["1", "500"]]),
        ("0., 0.9 15, 0.9 60, 0. 80",
         [["0."], ["0.9", "15"], ["0.9", "60"], ["0.", "80"]]),
        ("set 1 2; foo bar", [["set", "1", "2"]]),
        (";\rdsp start", []),
        ("a , b", [["a"], ["b"]]),
        ("a ,b", [["a"], ["b"]]),
        ("a\\, b", [["a\\,", "b"]]),
        ('"x, y" z', [['"x, y"', "z"]]),
        ("1 2 3", [["1", "2", "3"]]),
        (", , 1", [["1"]]),
    ])
    def test_message_segments(self, text, expected):
        assert walk.message_segments({"maxclass": "message", "text": text}) == expected

    def test_remote_targets(self):
        box = {"maxclass": "message", "text": "; foo 1, 2; bar"}
        assert walk.message_remote_targets(box) == ["foo", "bar"]
        assert walk.message_remote_targets(
            {"maxclass": "message", "text": ";\r\nwhrt pitch 7"}) == ["whrt"]
        assert walk.message_remote_targets(
            {"maxclass": "message", "text": "x 1;"}) == []

    @pytest.mark.parametrize("box", [
        {"maxclass": "newobj", "text": "0, 1 500"},
        {"maxclass": "message", "text": None},
        {"maxclass": "message", "text": 7},
        {"maxclass": "message", "text": '"unbalanced, 1'},
        None, 3, {},
    ])
    def test_junk_never_raises(self, box):
        segs = walk.message_segments(box)
        targets = walk.message_remote_targets(box)
        assert isinstance(segs, list) and isinstance(targets, list)
        if not (isinstance(box, dict) and box.get("maxclass") == "message"
                and isinstance(box.get("text"), str)):
            assert segs == [] and targets == []


# ---------------------------------------------------------------------------
# expr clip()
# ---------------------------------------------------------------------------


_CLIP_PROBE = "expr clip($f1/8., 0., 1.) * 127."  # physics-composition ab79ddbe


class TestExprClip:

    def _one(self, db, text, wrap=None):
        boxes = [_obj("obj-1", text, numinlets=1)]
        patch = _make_patch_dict(boxes=boxes)
        if wrap is not None:
            patch = wrap(patch)
        return _with(validate_patch(patch, db=db), "expr clip(): ")

    def test_physics_probe_is_one_error(self, db):
        [r] = self._one(db, _CLIP_PROBE)
        assert r.level == "error" and r.layer == "domain"
        assert "(obj-1)" in r.message and "min(max(" in r.message
        assert r.rule == "expr_clip" and r.box_ids == ("obj-1",)
        assert has_blocking_errors([r], is_new=True)

    @pytest.mark.parametrize("text", [
        "vexpr clip($f1, 0, 1)",
        "if clip($i1, 0, 1) > 0 then 1",
        "expr clip ($f1, 0, 1)",
    ])
    def test_vexpr_if_fire(self, db, text):
        assert len(self._one(db, text)) == 1

    @pytest.mark.parametrize("text", [
        "expr min(max($f1/8., 0.), 1.) * 127.",
        "expr fclip($f1)",
        "expr $f1 * 2",
        "clip 0. 1.",
        "pack clip(",
    ])
    def test_negatives(self, db, text):
        assert self._one(db, text) == []

    def test_gen_codebox_clip_not_flagged(self, db):
        patch = _make_patch_dict(boxes=[_gen_box("obj-1", "out1 = clip(in1, 0, 1);")])
        assert _with(validate_patch(patch, db=db), "expr clip(): ") == []

    def test_rnbo_scope_not_flagged(self, db):
        patch = _make_patch_dict(boxes=[_rnbo_box("obj-1", [_obj("obj-2", _CLIP_PROBE, 1)])])
        assert _with(validate_patch(patch, db=db), "expr clip(): ") == []

    def test_nested_is_prefixed(self, db):
        patch = _make_patch_dict(boxes=[_sub("obj-1", [_obj("obj-2", _CLIP_PROBE, 1)])])
        [r] = _with(validate_patch(patch, db=db), "expr clip(): ")
        assert r.path == "obj-1" and r.message.startswith("[p x] expr clip(): ")


# ---------------------------------------------------------------------------
# line~ comma segments (D2)
# ---------------------------------------------------------------------------


def _line_patch(text, dst="line~", inlet=0):
    boxes = [_msg("msg-1", text),
             _obj("line-1", dst, numinlets=2, numoutlets=2, outlettype=["signal", ""])]
    return _make_patch_dict(boxes=boxes, lines=[_make_line("msg-1", 0, "line-1", inlet)])


def _line_findings(db, patch):
    return [r for r in validate_patch(patch, db=db) if r.rule == "line_tilde_comma"]


class TestLineTildeSegments:

    def test_bassoon_probe_is_one_error(self, db):
        [r] = _line_findings(db, _line_patch("0., 0.9 15, 0.9 60, 0. 80"))  # aac68ed
        assert r.level == "error" and r.layer == "domain"
        assert r.message.startswith("line~ comma segments: ")
        assert "(msg-1)" in r.message and "(line-1)" in r.message
        assert r.box_ids == ("msg-1", "line-1")

    @pytest.mark.parametrize("text", ["1 10, 0 500", "0, 1 10, 0 500", "1 10, 0"])
    def test_ramp_followed_by_segment_fires(self, db, text):
        assert len(_line_findings(db, _line_patch(text))) == 1

    @pytest.mark.parametrize("text", [
        "0, 1 500", "100, 500 1000", "0, $1 $1", "stop, 0 100", "1 10", "0 1 500",
        "1 10; foo 0 500",
    ])
    def test_line_tilde_jump_then_ramp_idiom_not_flagged(self, db, text):
        """Invariant (assumption delta D2): a per-cord 'any comma' reading
        would flag Max's own jump-then-ramp idiom; only a ramp followed by
        another segment is the bug."""
        assert _line_findings(db, _line_patch(text)) == []

    def test_nested_carries_path(self, db):
        inner = _line_patch("1 10, 0 500")["patcher"]
        patch = _make_patch_dict(boxes=[_sub("obj-1", inner["boxes"], inner["lines"])])
        [r] = _line_findings(db, patch)
        assert r.level == "error" and r.path == "obj-1"
        assert r.message.startswith("[p x] line~ comma segments: ")

    def test_non_line_destination_none(self, db):
        assert _line_findings(db, _line_patch("1 10, 0 500", dst="line")) == []

    def test_one_error_per_cord(self, db):
        patch = _line_patch("1 10, 0 500")
        patch["patcher"]["boxes"].append(
            _obj("line-2", "line~", numinlets=2, numoutlets=2, outlettype=["signal", ""]))
        patch["patcher"]["lines"].append(_make_line("msg-1", 0, "line-2", 0))
        assert len(_line_findings(db, patch)) == 2


# ---------------------------------------------------------------------------
# numeric bpatcher args (D11)
# ---------------------------------------------------------------------------


def _bp_patch(args=None, has_args=True):
    box = {"id": "obj-1", "maxclass": "bpatcher", "name": "slot.maxpat",
           "numinlets": 1, "numoutlets": 1, "outlettype": [""],
           "patching_rect": [0, 0, 100, 100]}
    if has_args:
        box["args"] = args
    return _make_patch_dict(boxes=[{"box": box}])


class TestBpatcherArgs:

    @pytest.mark.parametrize("args", [["slot-1", "0"], ["-3"], ["1.5"], [".5"], ["+2"]])
    def test_numeric_strings_error(self, db, args):
        [r] = _with(validate_patch(_bp_patch(args), db=db), "bpatcher args: ")
        assert r.level == "error" and r.layer == "domain"
        assert "'slot.maxpat' (obj-1)" in r.message
        assert r.rule == "bpatcher_numeric_args" and r.box_ids == ("obj-1",)

    def test_values_listed(self, db):
        [r] = _with(validate_patch(_bp_patch(["a", "0", "-2.5"]), db=db), "bpatcher args: ")
        assert "'0', '-2.5'" in r.message

    @pytest.mark.parametrize("args", [
        ["slot-1", 0], ["slot-1", "slot-1-out"], ["1e3"], "0", None, [1.5, -2], ["", "-"],
    ])
    def test_negatives(self, db, args):
        assert _with(validate_patch(_bp_patch(args), db=db), "bpatcher args: ") == []

    def test_no_args_key(self, db):
        assert _with(validate_patch(_bp_patch(has_args=False), db=db), "bpatcher args: ") == []

    def test_nested_bpatcher(self, db):
        inner = _bp_patch(["0"])["patcher"]["boxes"]
        patch = _make_patch_dict(boxes=[_sub("obj-9", inner)])
        [r] = _with(validate_patch(patch, db=db), "bpatcher args: ")
        assert r.path == "obj-9"


class TestAddBpatcherCoercion:

    def test_numeric_strings_become_numbers(self):
        p = Patcher()
        args = ["slot-1", "0", "1.5", "-2", "1e3", 3, 0.5]
        before = list(args)
        p.add_bpatcher("x.maxpat", args=args)
        assert args == before  # caller's list untouched
        d = p.to_dict()
        [bp] = [e["box"] for e in d["patcher"]["boxes"] if e["box"].get("maxclass") == "bpatcher"]
        assert bp["args"] == ["slot-1", 0, 1.5, -2, "1e3", 3, 0.5]
        assert isinstance(bp["args"][1], int) and isinstance(bp["args"][2], float)
        assert _with(validate_patch(p), "bpatcher args: ") == []

    def test_round_trip_keeps_numbers(self):
        p = Patcher()
        p.add_bpatcher("x.maxpat", args=["slot-1", "0"])
        d = Patcher.from_dict(json.loads(json.dumps(p.to_dict()))).to_dict()
        [bp] = [e["box"] for e in d["patcher"]["boxes"] if e["box"].get("maxclass") == "bpatcher"]
        assert bp["args"] == ["slot-1", 0]


# ---------------------------------------------------------------------------
# DB selectors on dict messages (D10)
# ---------------------------------------------------------------------------


class TestDbSelectorsDictMessages:

    def test_bach_roll_and_dada(self, db):
        s = db.selectors("bach.roll")
        assert isinstance(s, set) and "addchord" in s
        assert all(isinstance(x, str) for x in s)
        if db.lookup("dada.bounce") is not None:
            assert isinstance(db.selectors("dada.bounce"), set)

    def test_cycle_unchanged_and_unknown(self, db):
        s = db.selectors("cycle~")
        assert {"frequency", "phase", "reset", "set"} <= s
        assert db.selectors("zz_nope") is None

    def test_messages_unchanged(self, db):
        assert any(isinstance(m, dict) for m in db.messages("bach.roll"))


# ---------------------------------------------------------------------------
# message selector (D4)
# ---------------------------------------------------------------------------


def _sel_patch(text, dst_text, dst_maxclass="newobj", inlet=0, numinlets=2):
    dst = _make_box("obj-2", maxclass=dst_maxclass, text=dst_text,
                    numinlets=numinlets, numoutlets=1, outlettype=[""])
    return _make_patch_dict(boxes=[_msg("obj-1", text), dst],
                            lines=[_make_line("obj-1", 0, "obj-2", inlet)])


def _sel(db, patch):
    return _with(validate_patch(patch, db=db), "Message selector: ")


class TestMessageSelector:

    def test_foo_into_cycle_warns(self, db):
        [r] = _sel(db, _sel_patch("foo", "cycle~ 440"))
        assert r.level == "warning" and r.layer == "domain"
        assert "'foo'" in r.message and "'cycle~' (obj-2)" in r.message and "(obj-1)" in r.message
        assert r.rule == "message_selector" and r.box_ids == ("obj-1", "obj-2")

    def test_bang_into_cycle_warns(self, db):
        assert len(_sel(db, _sel_patch("bang", "cycle~ 440"))) == 1

    def test_umenu_segments(self, db):
        [r] = _sel(db, _sel_patch("clear, foo", "umenu", dst_maxclass="umenu"))
        assert "'foo'" in r.message

    @pytest.mark.parametrize("text", [
        "frequency 440", "getfrequency", "set 1", "440", "$1 $2", "#1", "@min 0",
        '"foo bar"', "; rname foo", "-0.5 10",
    ])
    def test_accepted_into_cycle(self, db, text):
        assert _sel(db, _sel_patch(text, "cycle~ 440")) == []

    def test_jbox_common_attribute(self, db):
        assert _sel(db, _sel_patch("hidden 1", "live.text", dst_maxclass="live.text")) == []

    @pytest.mark.parametrize("dst_text, inlet", [
        ("gate 2", 1), ("print", 0), ("prepend foo", 0), ("js x.js", 0),
        ("zz_unknown_thing", 0), ("line~", 0),
    ])
    def test_guarded_destinations(self, db, dst_text, inlet):
        assert _sel(db, _sel_patch("foo", dst_text, inlet=inlet)) == []

    def test_container_and_outlet_and_gen(self, db):
        p = _sel_patch("foo", "p x")
        p["patcher"]["boxes"][1]["box"]["patcher"] = {"boxes": [], "lines": []}
        assert _sel(db, p) == []
        assert _sel(db, _sel_patch("foo", "", dst_maxclass="outlet")) == []
        assert _sel(db, _sel_patch("foo", "gen~")) == []

    def test_cold_inlet_of_cycle_not_checked(self, db):
        assert _sel(db, _sel_patch("foo", "cycle~ 440", inlet=1)) == []

    def test_nested_and_rnbo(self, db):
        inner = _sel_patch("foo", "cycle~ 440")["patcher"]
        patch = _make_patch_dict(boxes=[_sub("obj-9", inner["boxes"], inner["lines"])])
        [r] = _sel(db, patch)
        assert r.path == "obj-9" and r.message.startswith("[p x] Message selector: ")
        patch = _make_patch_dict(boxes=[_rnbo_box("obj-9", inner["boxes"], inner["lines"])])
        assert _sel(db, patch) == []


# ---------------------------------------------------------------------------
# patcher bgcolor (D5)
# ---------------------------------------------------------------------------


_GREY = [0.2, 0.2, 0.2, 1.0]


def _bg_patch(**keys):
    d = _make_patch_dict(boxes=[_obj("obj-1", "cycle~ 440")])
    d["patcher"].update(keys)
    return d


class TestPatcherBgcolor:

    @pytest.mark.parametrize("keys", [
        {"editing_bgcolor": _GREY}, {"locked_bgcolor": _GREY},
        {"editing_bgcolor": _GREY, "locked_bgcolor": _GREY},
    ])
    def test_missing_bgcolor_warns(self, db, keys):
        [r] = _with(validate_patch(_bg_patch(**keys), db=db), "Patcher bgcolor: ")
        assert r.level == "warning" and r.layer == "domain" and r.rule == "patcher_bgcolor"

    @pytest.mark.parametrize("keys", [
        {}, {"bgcolor": _GREY},
        {"bgcolor": _GREY, "editing_bgcolor": _GREY, "locked_bgcolor": _GREY},
    ])
    def test_no_warning(self, db, keys):
        assert _with(validate_patch(_bg_patch(**keys), db=db), "Patcher bgcolor: ") == []

    def test_nested_p_warns_gen_never(self, db):
        patch = _make_patch_dict(boxes=[_sub("obj-9", [_obj("obj-2", "cycle~")])])
        patch["patcher"]["boxes"][0]["box"]["patcher"]["editing_bgcolor"] = _GREY
        [r] = _with(validate_patch(patch, db=db), "Patcher bgcolor: ")
        assert r.path == "obj-9"
        gen = _gen_box("obj-9", "out1 = in1;")
        gen["box"]["patcher"]["editing_bgcolor"] = _GREY
        assert _with(validate_patch(_make_patch_dict(boxes=[gen]), db=db),
                     "Patcher bgcolor: ") == []

    def test_set_canvas_background_never_fires(self, db):
        p = Patcher()
        p.add_box("cycle~", args=["440"])
        from src.maxpat.aesthetics import set_canvas_background

        set_canvas_background(p, [0.2, 0.2, 0.2, 1.0])
        assert _with(validate_patch(p), "Patcher bgcolor: ") == []


# ---------------------------------------------------------------------------
# Purity and the save gate
# ---------------------------------------------------------------------------


def _all_shapes():
    boxes = [
        _obj("obj-1", _CLIP_PROBE, numinlets=1),
        _msg("obj-2", "1 10, 0 500"),
        _obj("obj-3", "line~", numinlets=2, numoutlets=2, outlettype=["signal", ""]),
        _bp_patch(["slot-1", "0"])["patcher"]["boxes"][0],
        _msg("obj-4", "foo"),
        _obj("obj-5", "cycle~ 440"),
    ]
    boxes[3]["box"]["id"] = "obj-6"
    d = _make_patch_dict(boxes=boxes, lines=[
        _make_line("obj-2", 0, "obj-3", 0), _make_line("obj-4", 0, "obj-5", 0)])
    d["patcher"]["editing_bgcolor"] = _GREY
    return d


class TestPurity:

    def test_validate_never_mutates(self, db):
        d = _all_shapes()
        before = copy.deepcopy(d)
        results = validate_patch(d, db=db)
        assert d == before
        for prefix in ("expr clip(): ", "line~ comma segments: ", "bpatcher args: ",
                       "Message selector: ", "Patcher bgcolor: "):
            assert _with(results, prefix), prefix

    def test_junk_boxes_never_raise(self, db):
        d = _make_patch_dict(boxes=[
            {"box": {"id": "obj-1", "maxclass": "newobj", "text": None}},
            {"box": {"id": "obj-2", "maxclass": "message", "text": 5}},
            {"box": {"id": "obj-3", "maxclass": "bpatcher", "args": [None, {"a": 1}, "0"],
                     "name": 7}},
            {"box": {"id": "obj-4", "maxclass": "newobj", "text": ["expr", "clip("]}},
            {"box": {"id": "obj-5", "maxclass": "message", "text": '"open, 1'}},
        ], lines=[_make_line("obj-2", 0, "obj-1", 0), _make_line("obj-5", 0, "obj-1", 0)])
        d["patcher"]["editing_bgcolor"] = "junk"
        results = validate_patch(d, db=db)
        [r] = _with(results, "bpatcher args: ")
        assert "'bpatcher' (obj-3)" in r.message


def _new_file_dict(*boxes, lines=()):
    return _make_patch_dict(boxes=list(boxes), lines=list(lines))


class TestSaveGateVocabulary:

    def test_new_file_with_unresolved_unknown_refused(self, tmp_path):
        from src.maxpat.hooks import PatchValidationError

        path = tmp_path / "a" / "top.maxpat"
        path.parent.mkdir(parents=True)
        d = _new_file_dict(_obj("obj-1", "zzabs", 1))
        with pytest.raises(PatchValidationError) as exc:
            save_patch_roundtrip(d, path)
        assert "zzabs" in str(exc.value)
        assert not path.exists()

    def test_new_file_with_abstraction_beside_saves(self, tmp_path):
        path = tmp_path / "a" / "top.maxpat"
        path.parent.mkdir(parents=True)
        (path.parent / "zzabs.maxpat").write_text("{}")
        d = _new_file_dict(_obj("obj-1", "zzabs", 1))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            save_patch_roundtrip(d, path)
        assert path.exists()

    def test_edit_keeps_preexisting_unknown_refuses_a_second(self, tmp_path):
        from src.maxpat.hooks import PatchValidationError

        path = tmp_path / "a" / "top.maxpat"
        path.parent.mkdir(parents=True)
        d = _new_file_dict(_obj("obj-1", "zzabs", 1))
        original = json.dumps(d, indent=4)
        path.write_text(original)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            save_patch_roundtrip(copy.deepcopy(d), path, original_text=original)
        text = path.read_text()
        d2 = copy.deepcopy(d)
        d2["patcher"]["boxes"].append(_obj("obj-2", "zzother", 1))
        with pytest.raises(PatchValidationError) as exc:
            save_patch_roundtrip(d2, path, original_text=text)
        assert "zzother" in str(exc.value)
        assert path.read_text() == text

    @pytest.mark.parametrize("which", ["clip", "line", "bpatcher"])
    def test_new_file_with_vocabulary_error_refused(self, tmp_path, which):
        from src.maxpat.hooks import PatchValidationError

        if which == "clip":
            d = _new_file_dict(_obj("obj-1", _CLIP_PROBE, 1))
        elif which == "line":
            d = _line_patch("1 10, 0 500")
        else:
            d = _bp_patch(["slot-1", "0"])
            (tmp_path / "slot.maxpat").write_text("{}")
        path = tmp_path / "top.maxpat"
        with pytest.raises(PatchValidationError):
            save_patch_roundtrip(d, path)
        assert not path.exists()

    def test_validate_file_reports_unknown_error(self, tmp_path):
        path = tmp_path / "a" / "top.maxpat"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(_new_file_dict(_obj("obj-1", "zzabs", 1))))
        [r] = [r for r in validate_file(path) if r.rule == "unknown_object"]
        assert r.level == "error" and "(obj-1)" in r.message
        (path.parent / "zzabs.js").write_text("")
        assert [r for r in validate_file(path) if r.rule == "unknown_object"] == []
