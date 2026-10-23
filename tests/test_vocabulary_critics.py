"""Q23 vocabulary checks -- critic side (fix-plan Q23; review §4.4 R7 / R10;
quick 261022-ud6 WP7b, review-docs-completion CR-01).

* Unmatched send/receive/value/buffer names across a CLOSED patch tree
  (planner decision D6) -- structure critic warning
* Int truncation: float source into arg-less ``+ - * /``, arg-less ``ftom``
  or int-input ``scale`` (D7) -- structure critic warning
* MC bare list into an MC wrapper (D9) -- structure critic note
* bach ``@out t`` -- already shipped by Q39 (package critic
  ``bach_out_mode``); only the physics-composition f4f096b0 probe is pinned
  here as a regression guard.
"""

from __future__ import annotations

import copy

import pytest

from src.maxpat.critics import review_patch
from src.maxpat.critics.package_critic import review_packages
from src.maxpat.critics.structure_critic import review_structure
from src.maxpat.db_lookup import ObjectDatabase
from tests.test_critic_precision import _box, _ln


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _patch(boxes, lines=(), **extra):
    patcher = {"boxes": [{"box": b} for b in boxes],
               "lines": [{"patchline": ln} for ln in lines]}
    patcher.update(extra)
    return {"patcher": patcher}


def _sub(box_id, boxes, lines=(), text="p x", **extra):
    box = _box(box_id, text, numinlets=0, numoutlets=0)
    box["patcher"] = _patch(boxes, lines)["patcher"]
    box.update(extra)
    return box


def _msg(box_id, text):
    return _box(box_id, text, maxclass="message", numinlets=2, numoutlets=1)


def _of(results, prefix):
    out = []
    for r in results:
        f = r.finding
        if f.startswith("[") and "] " in f:
            f = f.split("] ", 1)[1]
        if f.startswith(prefix):
            out.append(r)
    return out


def _unmatched(results):
    return _of(results, "Unmatched ")


# ---------------------------------------------------------------------------
# Unmatched names (D6)
# ---------------------------------------------------------------------------


class TestUnmatchedNames:

    def _run(self, db, boxes, lines=()):
        return _unmatched(review_structure(_patch(boxes, lines), db=db))

    def test_lone_send_and_receive(self, db):
        [r] = self._run(db, [_box("obj-1", "s foo", numoutlets=0)])
        assert r.finding.startswith("Unmatched send: 's foo' (obj-1)")
        assert r.severity == "warning" and r.rule == "unmatched_names"
        assert r.box_ids == ("obj-1",)
        assert "typo" in r.suggestion
        [r] = self._run(db, [_box("obj-1", "r foo", numinlets=0)])
        assert r.finding.startswith("Unmatched receive: 'r foo' (obj-1)")

    def test_matched_across_subpatcher(self, db):
        boxes = [_box("obj-1", "s foo", numoutlets=0),
                 _sub("obj-2", [_box("obj-3", "r foo", numinlets=0)])]
        assert self._run(db, boxes) == []

    def test_typo_gives_two_nested_tagged(self, db):
        boxes = [_box("obj-1", "s tsyn-cheby", numoutlets=0),
                 _sub("obj-2", [_box("obj-3", "r tsyn_cheby", numinlets=0)])]
        found = self._run(db, boxes)
        assert len(found) == 2
        nested = [r for r in found if r.path == "obj-2"]
        assert len(nested) == 1 and nested[0].finding.startswith("[p x] Unmatched receive: ")

    def test_signal_send(self, db):
        [r] = self._run(db, [_box("obj-1", "send~ a", numoutlets=0)])
        assert r.finding.startswith("Unmatched send: 'send~ a'")
        assert self._run(db, [_box("obj-1", "send~ a", numoutlets=0),
                              _box("obj-2", "receive~ a", numinlets=0)]) == []
        assert self._run(db, [_box("obj-1", "mc.send~ a", numoutlets=0),
                              _box("obj-2", "mc.receive~ a", numinlets=0)]) == []

    def test_remote_message_targets(self, db):
        assert self._run(db, [_msg("obj-1", "; foo 1"),
                              _box("obj-2", "r foo", numinlets=0)]) == []
        [r] = self._run(db, [_msg("obj-1", "; foo 1")])
        assert r.finding.startswith("Unmatched send: message '; foo 1' (obj-1) targets ';foo'")
        for text in ("; max refresh", ";\r\ndsp start", "; jitter glreadback fbo"):
            assert self._run(db, [_msg("obj-1", text)]) == [], text

    def test_remote_target_satisfied_by_named_buffer(self, db):
        assert self._run(db, [_msg("obj-1", "; buf clear"),
                              _box("obj-2", "buffer~ buf", numinlets=1, numoutlets=2)]) == []

    @pytest.mark.parametrize("text", ["s #1", "s $1x", "r #2-in", "s foo#1", "send 15",
                                      "s ---dev_gain", "r ---dev_tap"])
    def test_hash_and_dollar_names_ignored(self, db, text):
        assert self._run(db, [_box("obj-1", text, numoutlets=0)]) == []

    def test_values(self, db):
        [r] = self._run(db, [_box("obj-1", "v x")])
        assert r.finding.startswith("Unmatched value: 'v x' (obj-1) is the only value named 'x'")
        assert self._run(db, [_box("obj-1", "v x"), _box("obj-2", "value x")]) == []
        [r] = self._run(db, [_box("obj-1", "pv y")])
        assert "only pv named 'y'" in r.finding
        # value and pv are separate namespaces
        assert len(self._run(db, [_box("obj-1", "v z"), _box("obj-2", "pv z")])) == 2

    def test_buffers(self, db):
        [r] = self._run(db, [_box("obj-1", "play~ buf", numoutlets=2)])
        assert r.finding.startswith("Unmatched buffer: 'play~ buf' (obj-1) reads buffer~ 'buf'")
        assert self._run(db, [_box("obj-1", "play~ buf", numoutlets=2),
                              _box("obj-2", "buffer~ buf", numoutlets=2)]) == []
        assert self._run(db, [_box("obj-1", "play~ pb.1", numoutlets=2),
                              _box("obj-2", "polybuffer~ pb", numoutlets=2)]) == []
        assert self._run(db, [_box("obj-1", "groove~ g", numoutlets=2),
                              _box("obj-2", "jit.buffer~ g", numoutlets=2)]) == []
        assert len(self._run(db, [_box("obj-1", "cycle~ 440 wt", numinlets=2)])) == 1
        assert self._run(db, [_box("obj-1", "cycle~ 440", numinlets=2)]) == []
        # an unused buffer~ is normal (gen~ Buffer, waveform~ set, js ...)
        assert self._run(db, [_box("obj-1", "buffer~ lonely", numoutlets=2)]) == []

    def test_gen_and_rnbo_boxes_ignored(self, db):
        gen = _box("obj-1", "gen~", numinlets=1, numoutlets=1)
        gen["patcher"] = {"classnamespace": "dsp.gen", "boxes": [
            {"box": _box("obj-2", "buffer wt", numoutlets=2)}], "lines": []}
        rnbo = _box("obj-3", "rnbo~", numinlets=1, numoutlets=1)
        rnbo["patcher"] = {"classnamespace": "rnbo", "boxes": [
            {"box": _box("obj-4", "s inner", numoutlets=0)},
            {"box": _box("obj-5", "r other", numinlets=0)}], "lines": []}
        assert self._run(db, [gen, rnbo]) == []

    @pytest.mark.parametrize("opener", [
        _box("obj-9", "", maxclass="inlet", numinlets=0, numoutlets=1),
        _box("obj-9", "in 1", numinlets=0, numoutlets=1),
        _box("obj-9", "thispoly~", numinlets=1, numoutlets=2),
        {"id": "obj-9", "maxclass": "bpatcher", "name": "slot.maxpat",
         "numinlets": 1, "numoutlets": 1},
        _box("obj-9", "poly~ voice 4", numinlets=1, numoutlets=1),
        _box("obj-9", "js x.js", numinlets=1, numoutlets=1),
        _box("obj-9", "forward", numinlets=1, numoutlets=0),
        _box("obj-9", "zz_unknown_abstraction", numinlets=1, numoutlets=1),
        _box("obj-9", "s", numinlets=2, numoutlets=0),
        _box("obj-9", "jsui", maxclass="jsui", numinlets=1, numoutlets=1),
    ])
    def test_unmatched_names_skipped_on_open_tree(self, db, opener):
        """Invariant (assumption delta D6): a name's other end often lives
        in another file; an open tree (abstraction, file-loading container,
        script, forward, unknown external, nameless send) is never judged."""
        boxes = [_box("obj-1", "s foo", numoutlets=0), _box("obj-2", "r bar", numinlets=0), opener]
        assert self._run(db, boxes) == []

    def test_nested_inlet_does_not_open_tree(self, db):
        boxes = [_box("obj-1", "s foo", numoutlets=0),
                 _sub("obj-2", [_box("obj-3", "", maxclass="inlet", numinlets=0)])]
        assert len(self._run(db, boxes)) == 1

    def test_no_named_boxes_builds_no_db(self, monkeypatch):
        import src.maxpat.db_lookup as dbl

        built = []
        real = dbl.ObjectDatabase

        class Spy(real):
            def __init__(self, *a, **k):
                built.append(1)
                super().__init__(*a, **k)

        monkeypatch.setattr(dbl, "ObjectDatabase", Spy)
        review_structure(_patch([_box("obj-1", "cycle~ 440"), _box("obj-2", "zz_unknown")]))
        assert built == []


# ---------------------------------------------------------------------------
# Int truncation (D7)
# ---------------------------------------------------------------------------


def _flonum(box_id="obj-1"):
    return _box(box_id, "", maxclass="flonum", numinlets=1, numoutlets=2,
                outlettype=["", "bang"])


def _trunc(db, src, dst_text, outlet=0, inlet=0, dst_inlets=2, wrap=None):
    dst = _box("obj-2", dst_text, numinlets=dst_inlets, numoutlets=1)
    d = _patch([src, dst], [_ln(src["id"], outlet, "obj-2", inlet)])
    if wrap is not None:
        d = wrap(d)
    return _of(review_structure(d, db=db), "Int truncation: ")


class TestIntTruncation:

    def test_flonum_into_argless_minus_both_inlets(self, db):
        [r] = _trunc(db, _flonum(), "-")
        assert r.severity == "warning" and r.rule == "int_truncation"
        assert r.finding.startswith("Int truncation: '-' (obj-2) runs in int mode but inlet 0")
        assert "(obj-1) outlet 0" in r.finding and r.port == 0
        assert r.box_ids == ("obj-2", "obj-1")
        assert "'- 0.'" in r.suggestion
        assert len(_trunc(db, _flonum(), "-", inlet=1)) == 1

    def test_float_arg_is_fine(self, db):
        assert _trunc(db, _flonum(), "- 0.") == []

    def test_trigger_letters(self, db):
        t = _box("obj-1", "t f i", numinlets=1, numoutlets=2)
        assert len(_trunc(db, t, "*", outlet=0)) == 1
        assert _trunc(db, t, "*", outlet=1) == []

    def test_tci_probe(self, db):
        boxes = [_box("obj-1", "f", numinlets=2, numoutlets=1),
                 _box("obj-2", "+ 0.0025", numinlets=2, numoutlets=1),
                 _box("obj-3", "-", numinlets=2, numoutlets=1)]
        d = _patch(boxes, [_ln("obj-1", 0, "obj-2", 0), _ln("obj-2", 0, "obj-3", 0)])
        [r] = _of(review_structure(d, db=db), "Int truncation: ")
        assert "(obj-3)" in r.finding and "'+ 0.0025' (obj-2)" in r.finding

    def test_dial_and_scale(self, db):
        dial = _box("obj-1", "", maxclass="dial", numinlets=1, numoutlets=1,
                    outlettype=["float"])
        assert _trunc(db, dial, "scale 0 127 0. 1.", dst_inlets=6) == []
        dial_f = dict(dial, floatoutput=1)
        [r] = _trunc(db, dial_f, "scale 0 127 0. 1.", dst_inlets=6)
        assert "scale 0. 127. 0. 1." in r.suggestion
        assert _trunc(db, dial_f, "scale 0. 127. 0. 1.", dst_inlets=6) == []

    def test_ftom(self, db):
        [r] = _trunc(db, _flonum(), "ftom")
        assert "'ftom 0.'" in r.suggestion
        assert _trunc(db, _flonum(), "ftom 0.") == []
        assert _trunc(db, _flonum(), "ftom", inlet=1) == []

    def test_int_sources_fine(self, db):
        number = _box("obj-1", "", maxclass="number", numinlets=1, numoutlets=2,
                      outlettype=["", "bang"])
        assert _trunc(db, number, "+") == []

    def test_live_dial(self, db):
        ld = _box("obj-1", "", maxclass="live.dial", numinlets=1, numoutlets=2,
                  outlettype=["", "float"])
        assert len(_trunc(db, ld, "/")) == 1
        ld_int = dict(ld, saved_attribute_attributes={"valueof": {"parameter_type": 1}})
        assert _trunc(db, ld_int, "/") == []

    def test_db_float_outlet(self, db):
        snap = _box("obj-1", "snapshot~", numinlets=2, numoutlets=1)
        assert len(_trunc(db, snap, "+")) == 1

    def test_saved_float_outlettype(self, db):
        src = _box("obj-1", "zz_ext", numinlets=1, numoutlets=1, outlettype=["float"])
        assert len(_trunc(db, src, "*")) == 1

    def test_rnbo_scope_skipped(self, db):
        def wrap(d):
            rnbo = _box("obj-9", "rnbo~", numinlets=1, numoutlets=1)
            rnbo["patcher"] = dict(d["patcher"], classnamespace="rnbo")
            return _patch([rnbo])
        assert _trunc(db, _flonum(), "-", wrap=wrap) == []

    def test_nested_tagged(self, db):
        def wrap(d):
            return _patch([_sub("obj-9", [e["box"] for e in d["patcher"]["boxes"]],
                                [e["patchline"] for e in d["patcher"]["lines"]])])
        [r] = _trunc(db, _flonum(), "-", wrap=wrap)
        assert r.path == "obj-9" and r.finding.startswith("[p x] Int truncation: ")


# ---------------------------------------------------------------------------
# MC bare list (D9)
# ---------------------------------------------------------------------------


def _mc(db, src, dst_text, inlet=0):
    dst = _box("obj-2", dst_text, numinlets=2, numoutlets=1, outlettype=["multichannelsignal"])
    d = _patch([src, dst], [_ln(src["id"], 0, "obj-2", inlet)])
    return _of(review_structure(d, db=db), "MC bare list: ")


class TestMcBareList:

    def test_ji_harmonizer_probe(self, db):
        [r] = _mc(db, _msg("obj-1", "440 550 660"), "mc.cycle~")
        assert r.severity == "note" and r.rule == "mc_bare_list"
        assert r.finding.startswith(
            "MC bare list: '440 550 660' (obj-1) sends a bare list to MC wrapper "
            "'mc.cycle~' (obj-2) inlet 0")
        assert "applyvalues" in r.suggestion
        assert _mc(db, _msg("obj-1", "applyvalues 440 550 660"), "mc.cycle~") == []

    def test_pack_sources(self, db):
        assert len(_mc(db, _box("obj-1", "pack 0. 0. 0.", numinlets=3), "mc.sig~")) == 1
        assert len(_mc(db, _box("obj-1", "pack", numinlets=2), "mc.sig~")) == 1
        assert _mc(db, _box("obj-1", "pack setvalue 1 1", numinlets=3), "mc.sig~") == []

    def test_native_list_objects_and_ramps(self, db):
        assert _mc(db, _msg("obj-1", "0.5 100"), "mc.line~") == []
        assert _mc(db, _msg("obj-1", "3 4"), "mc.dac~") == []

    def test_dollar_list(self, db):
        assert len(_mc(db, _msg("obj-1", "$1 $2"), "mc.cycle~")) == 1

    def test_single_value_fine(self, db):
        assert _mc(db, _msg("obj-1", "440"), "mc.cycle~") == []
        assert _mc(db, _msg("obj-1", "set 1 2"), "mc.cycle~") == []


# ---------------------------------------------------------------------------
# bach @out t (Q39 regression guard)
# ---------------------------------------------------------------------------


def _physics_bach(fixed=False):
    suffix = " @out t" if fixed else ""
    inner = [
        _box("obj-5", "bach.keys position" + suffix, numinlets=1, numoutlets=2),
        _box("obj-6", "bach.nth 1" + suffix, numinlets=2, numoutlets=2),
        _box("obj-7", "bach.nth 2" + suffix, numinlets=2, numoutlets=2),
        _box("obj-8", "f 0.", numinlets=2, numoutlets=1, outlettype=["float"]),
        _box("obj-9", "f 0.", numinlets=2, numoutlets=1, outlettype=["float"]),
        _box("obj-15", "bach.keys ball" + suffix, numinlets=1, numoutlets=2),
        _box("obj-16", "bach.nth 1" + suffix, numinlets=2, numoutlets=2),
        _box("obj-17", "select 1", numinlets=2, numoutlets=2),
    ]
    lines = [_ln("obj-5", 0, "obj-6", 0), _ln("obj-5", 0, "obj-7", 0),
             _ln("obj-6", 0, "obj-8", 1), _ln("obj-7", 0, "obj-9", 1),
             _ln("obj-15", 0, "obj-16", 0), _ln("obj-16", 0, "obj-17", 0)]
    return _patch([_sub("obj-62", inner, lines)])


class TestBachNativeOutput:

    def test_physics_prefix_caught_fixed_clean(self, db):
        found = [r for r in review_packages(_physics_bach(), db=db) if r.rule == "bach_out_mode"]
        assert {r.box_ids[0] for r in found} == {"obj-6", "obj-7", "obj-16"}
        assert all(r.path == "obj-62" for r in found)
        assert [r for r in review_packages(_physics_bach(True), db=db)
                if r.rule == "bach_out_mode"] == []


# ---------------------------------------------------------------------------
# Purity
# ---------------------------------------------------------------------------


def _all_shapes():
    return _patch([
        _box("obj-1", "s foo", numoutlets=0),
        _flonum("obj-2"), _box("obj-3", "-", numinlets=2),
        _msg("obj-4", "440 550 660"),
        _box("obj-5", "mc.cycle~", numinlets=2, outlettype=["multichannelsignal"]),
        _box("obj-6", "play~ nobuf", numoutlets=2),
    ], [_ln("obj-2", 0, "obj-3", 0), _ln("obj-4", 0, "obj-5", 0)])


class TestQ23CriticPurity:

    def test_review_is_pure_and_never_blocks(self, db):
        d = _all_shapes()
        before = copy.deepcopy(d)
        results = review_patch(d, db=db)
        assert d == before
        q23 = [r for r in results if r.rule in ("unmatched_names", "int_truncation", "mc_bare_list")]
        assert {r.rule for r in q23} == {"unmatched_names", "int_truncation", "mc_bare_list"}
        assert all(r.severity != "blocker" for r in q23)

    def test_junk_never_raises(self, db):
        junk = _patch([
            {"id": "obj-1", "maxclass": "newobj", "text": None},
            {"id": "obj-2", "maxclass": "message", "text": 7},
            {"id": "obj-3", "maxclass": "newobj", "text": ["s", "x"]},
            {"maxclass": "newobj", "text": "s orphan"},
            {"id": "obj-4", "maxclass": "live.dial", "saved_attribute_attributes": "junk"},
            {"id": "obj-5", "maxclass": "newobj", "text": "t f", "numoutlets": "x"},
            {"id": "obj-6", "maxclass": "newobj", "text": "-"},
            {"id": "obj-7", "maxclass": "bpatcher", "patcher": "junk"},
        ], [_ln("obj-4", 0, "obj-6", 0), _ln("obj-5", "0", "obj-6", 1),
            _ln("obj-2", 0, "obj-1", 0), {"source": None, "destination": [1]}])
        assert isinstance(review_structure(junk, db=db), list)
        assert isinstance(review_patch(junk, db=db), list)
