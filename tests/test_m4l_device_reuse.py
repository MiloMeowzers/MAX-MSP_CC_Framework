"""add_m4l_device on a patcher that already holds device content (quick 261022-ud6 WP4).

Review findings covered (review-codegen.md):
- BL-01: an existing plugin~ / plugout~ / midiin / midiout / live.thisdevice
  is reused, never doubled; a second pass-through is never added.
- WR-01: a param longname (or explicit short name) already used in the
  patcher is refused before any box is created.
- Q40 duplicated device I/O check (find_duplicate_device_io /
  duplicate_device_io_results).
- IN-06: builder output carries info text and does not overlap the caller's
  chain.
- Q40 REVIEW IN-01 (export kind cross-check), IN-02 (explicit type /
  short-name consistency), IN-04 (build_amxd meta range).

EXPERIMENTAL like the builder itself (not yet confirmed in Live).
"""

from __future__ import annotations

import warnings

import pytest

from src.maxpat.m4l_constants import ParamType
from src.maxpat.m4l_device import (
    build_amxd,
    duplicate_device_io_results,
    export_amxd,
    find_duplicate_device_io,
    resolve_param_specs,
)
from src.maxpat.patcher import Patcher

pytestmark = pytest.mark.filterwarnings("ignore:.*not auto-committed:UserWarning")


def _spec(name, mn, mx, default=None, **kw):
    d = {"name": name, "min": mn, "max": mx, "default": mn if default is None else default}
    d.update(kw)
    return d


def _count(p, name):
    return sum(1 for b in p.boxes if b.name == name)


def _cords(p):
    by_id = {b.id: b for b in p.boxes}
    return [
        (by_id[l.source_id].name, l.source_outlet, by_id[l.dest_id].name, l.dest_inlet)
        for l in p.lines
    ]


def _into(p, box):
    return sorted((l.source_id, l.source_outlet, l.dest_inlet) for l in p.lines if l.dest_id == box.id)


def _from(p, box, outlet=None):
    return sorted((l.source_outlet, l.dest_id, l.dest_inlet) for l in p.lines
                  if l.source_id == box.id and (outlet is None or l.source_outlet == outlet))


def _quiet(fn, *a, **kw):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fn(*a, **kw)


# ---------------------------------------------------------------------------
# BL-01: reuse, never double
# ---------------------------------------------------------------------------


def test_second_audio_effect_call_reuses_the_whole_chain():
    """The review repro: two calls keep one pass-through and one live.thisdevice."""
    p = Patcher()
    first = _quiet(p.add_m4l_device, "audio_effect",
                   [_spec("Mix", 0.0, 1.0, 0.5, varname="mix_a")])
    second = _quiet(p.add_m4l_device, "audio_effect", [_spec("Wet", 0.0, 1.0, 0.5)])
    for name in ("plugin~", "plugout~", "live.thisdevice", "live.banks"):
        assert _count(p, name) == 1, name
    assert second.plugin is first.plugin and second.plugout is first.plugout
    assert second.thisdevice is first.thisdevice
    passthrough = [c for c in _cords(p) if c[0] == "plugin~" and c[2] == "plugout~"]
    assert sorted(passthrough) == [("plugin~", 0, "plugout~", 0), ("plugin~", 1, "plugout~", 1)]
    # Every inlet of plugout~ has exactly one feed: no doubled dry path.
    assert len(_into(p, first.plugout)) == 2


def test_second_call_banks_both_unbound_dials_through_one_trigger():
    """The first call's direct live.thisdevice -> dial cord becomes a t b b."""
    p = Patcher()
    first = _quiet(p.add_m4l_device, "audio_effect", [_spec("Mix", 0.0, 1.0, 0.5)])
    second = _quiet(p.add_m4l_device, "audio_effect", [_spec("Wet", 0.0, 1.0, 0.5)])
    dev = first.thisdevice
    outs = _from(p, dev, 0)
    assert len(outs) == 1, "live.thisdevice outlet 0 must not fan out"
    trig = next(b for b in p.boxes if b.id == outs[0][1])
    assert trig.name in ("t", "trigger") and trig.numoutlets == 2
    assert second.init_trigger is trig
    banged = {d for _o, d, _i in _from(p, trig)}
    assert banged == {first.dials[0].id, second.dials[0].id}


def test_existing_all_bang_trigger_is_extended():
    p = Patcher()
    first = _quiet(p.add_m4l_device, "audio_effect",
                   [_spec("Mix", 0.0, 1.0, 0.5), _spec("Tone", 0.0, 1.0, 0.5)])
    trig = first.init_trigger
    assert trig is not None and trig.numoutlets == 2
    second = _quiet(p.add_m4l_device, "audio_effect", [_spec("Wet", 0.0, 1.0, 0.5)])
    trigs = [b for b in p.boxes if b.name in ("t", "trigger")]
    assert len(trigs) == 1 and trigs[0].numoutlets == 3
    assert second.init_trigger is trigs[0]
    banged = {d for _o, d, _i in _from(p, trigs[0])}
    assert banged == {first.dials[0].id, first.dials[1].id, second.dials[0].id}
    assert _from(p, first.thisdevice, 0) == [(0, trigs[0].id, 0)]


def test_existing_chain_from_live_template_is_reused():
    """A patch built like Live's audio-effect template keeps its one pass-through."""
    p = Patcher()
    pin = p.add_box("plugin~", x=20.0, y=300.0)
    pout = p.add_box("plugout~", x=20.0, y=400.0)
    p.add_connection(pin, 0, pout, 0)
    p.add_connection(pin, 1, pout, 1)
    dev = _quiet(p.add_m4l_device, "audio_effect", [_spec("Mix", 0.0, 1.0, 0.5)])
    assert dev.plugin is pin and dev.plugout is pout
    assert _count(p, "plugin~") == 1 and _count(p, "plugout~") == 1
    assert len(_into(p, pout)) == 2


def test_user_chain_into_plugout_gets_no_dry_passthrough():
    """plugin~ -> fx -> plugout~: the builder must not add plugin~ -> plugout~."""
    p = Patcher()
    pin = p.add_box("plugin~", x=20.0, y=300.0)
    fx = p.add_box("*~", ["0.5"], x=20.0, y=350.0)
    pout = p.add_box("plugout~", x=20.0, y=400.0)
    p.add_connection(pin, 0, fx, 0)
    p.add_connection(fx, 0, pout, 0)
    p.add_connection(fx, 0, pout, 1)
    _quiet(p.add_m4l_device, "audio_effect", [_spec("Mix", 0.0, 1.0, 0.5)])
    assert not [c for c in _cords(p) if c[0] == "plugin~" and c[2] == "plugout~"]
    assert _into(p, pout) == [(fx.id, 0, 0), (fx.id, 0, 1)]


def test_source_into_an_already_fed_plugout_is_refused():
    p = Patcher()
    pin = p.add_box("plugin~", x=20.0, y=300.0)
    pout = p.add_box("plugout~", x=20.0, y=400.0)
    p.add_connection(pin, 0, pout, 0)
    p.add_connection(pin, 1, pout, 1)
    osc = p.add_box("cycle~", ["220"], x=200.0, y=300.0)
    p.add_connection(pin, 0, osc, 0)
    boxes, lines = len(p.boxes), len(p.lines)
    with pytest.raises(ValueError, match="already fed"):
        p.add_m4l_device("audio_effect", [_spec("Mix", 0.0, 1.0, 0.5)], audio_source=(osc, 0))
    assert (len(p.boxes), len(p.lines)) == (boxes, lines)


def test_same_source_again_is_idempotent():
    p = Patcher()
    osc = p.add_box("cycle~", ["220"], x=400.0, y=200.0)
    _quiet(p.add_m4l_device, "instrument", audio_source=(osc, 0))
    _quiet(p.add_m4l_device, "instrument", [_spec("Amp", 0.0, 1.0, 0.5)], audio_source=(osc, 0))
    assert _count(p, "plugout~") == 1 and _count(p, "midiin") == 1
    pout = next(b for b in p.boxes if b.name == "plugout~")
    assert _into(p, pout) == [(osc.id, 0, 0), (osc.id, 0, 1)]


def test_second_midi_effect_call_reuses_midiin_and_midiout():
    p = Patcher()
    _quiet(p.add_m4l_device, "midi_effect", [_spec("Vel", 0, 127, 100)])
    _quiet(p.add_m4l_device, "midi_effect", [_spec("Chan", 1, 16, 1)])
    assert _count(p, "midiin") == 1 and _count(p, "midiout") == 1
    assert _count(p, "live.thisdevice") == 1
    assert [c for c in _cords(p) if c[2] == "midiout"] == [("midiin", 0, "midiout", 0)]


def test_existing_duplicates_are_refused_before_building():
    p = Patcher()
    p.add_box("plugout~", x=20.0, y=400.0)
    p.add_box("plugout~", x=120.0, y=400.0)
    before = len(p.boxes)
    with pytest.raises(ValueError, match="plugout~"):
        p.add_m4l_device("instrument", [_spec("Amp", 0.0, 1.0, 0.5)])
    assert len(p.boxes) == before


# ---------------------------------------------------------------------------
# Duplicated device I/O check (Q40 critic hook)
# ---------------------------------------------------------------------------


def _patch(texts):
    boxes = [{"box": {"id": "obj-%d" % (i + 1), "maxclass": "newobj", "text": t,
                      "numinlets": 1, "numoutlets": 0, "outlettype": [],
                      "patching_rect": [10.0 * i, 10.0, 60.0, 22.0]}}
             for i, t in enumerate(texts)]
    return {"patcher": {"boxes": boxes, "lines": []}}


def test_find_duplicate_device_io():
    d = _patch(["plugin~", "plugout~", "plugin~", "live.thisdevice", "live.thisdevice",
                "midiin", "midiin", "plugout~ 1 2"])
    found = find_duplicate_device_io(d)
    assert found == {
        "plugin~": ["obj-1", "obj-3"],
        "plugout~": ["obj-2", "obj-8"],
        "live.thisdevice": ["obj-4", "obj-5"],
    }
    assert find_duplicate_device_io(_patch(["plugin~", "plugout~", "live.thisdevice"])) == {}
    assert find_duplicate_device_io({"patcher": {"boxes": "junk"}}) == {}
    assert find_duplicate_device_io(None) == {}


def test_duplicate_device_io_results_are_warnings():
    results = duplicate_device_io_results(_patch(["plugout~", "plugout~"]))
    assert len(results) == 1
    r = results[0]
    assert r.severity == "warning" and r.rule == "duplicate_device_io"
    assert "plugout~" in r.finding and "obj-1" in r.finding and "obj-2" in r.finding


def test_builder_output_never_has_duplicate_io():
    p = Patcher()
    for spec in (_spec("Mix", 0.0, 1.0, 0.5), _spec("Wet", 0.0, 1.0, 0.5), _spec("Dry", 0.0, 1.0)):
        _quiet(p.add_m4l_device, "audio_effect", [spec])
    assert find_duplicate_device_io(p.to_dict()) == {}


# ---------------------------------------------------------------------------
# WR-01: existing longnames / short names
# ---------------------------------------------------------------------------


def test_existing_longname_is_refused_before_building():
    p = Patcher()
    _quiet(p.add_m4l_device, "audio_effect", [_spec("Mix", 0.0, 1.0, 0.5, varname="mix_a")])
    boxes, lines = len(p.boxes), len(p.lines)
    with pytest.raises(ValueError, match="Mix"):
        p.add_m4l_device("audio_effect", [_spec("Mix", 0.0, 1.0, 0.5, varname="mix_b")])
    assert (len(p.boxes), len(p.lines)) == (boxes, lines)


def test_existing_explicit_shortname_is_refused():
    p = Patcher()
    _quiet(p.add_m4l_device, "audio_effect", [_spec("Dry Wet", 0.0, 1.0, 0.5, short_name="Mix")])
    with pytest.raises(ValueError, match="short"):
        p.add_m4l_device("audio_effect", [_spec("Blend", 0.0, 1.0, 0.5, short_name="Mix")])


def test_auto_shortname_avoids_existing_shortnames():
    from src.maxpat.critics import review_patch

    p = Patcher()
    _quiet(p.add_m4l_device, "audio_effect", [_spec("Filter Amount", 0.0, 1.0, 0.5)])
    dev = _quiet(p.add_m4l_device, "audio_effect", [_spec("Pitch Amount", 0.0, 1.0, 0.5)])
    short = dev.dials[0].extra_attrs["saved_attribute_attributes"]["valueof"]["parameter_shortname"]
    assert short == "Amount2"
    rules = {r.rule for r in _quiet(review_patch, p.to_dict())}
    assert "shortname_unique" not in rules and "parameter_uniqueness" not in rules


# ---------------------------------------------------------------------------
# Q40 REVIEW IN-02: explicit type / short-name consistency
# ---------------------------------------------------------------------------


def test_duplicate_explicit_shortnames_raise():
    with pytest.raises(ValueError, match="short name"):
        resolve_param_specs([_spec("a", 0.0, 1.0, short_name="X"),
                             _spec("b", 0.0, 1.0, short_name="X")])


@pytest.mark.parametrize("spec", [
    _spec("a", 0.0, 1.5, type=ParamType.INT),
    _spec("a", 0, 1000, 10, type="int"),
    _spec("a", 0, 10, 2.5, type=ParamType.INT),
], ids=["int-float-bound", "int-wide-span", "int-float-default"])
def test_inconsistent_explicit_int_type_warns_and_is_kept(spec):
    with pytest.warns(UserWarning, match="type Int"):
        r = resolve_param_specs([spec])
    assert r[0]["type"] == int(ParamType.INT)


def test_int_type_with_integral_floats_is_accepted():
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        r = resolve_param_specs([_spec("a", 0.0, 10.0, 2.0, type=ParamType.INT)])
    assert r[0]["type"] == int(ParamType.INT)


# ---------------------------------------------------------------------------
# Q40 REVIEW IN-01 and IN-04 (meta)
# ---------------------------------------------------------------------------


def test_export_warns_when_explicit_kind_disagrees_with_contents(tmp_path):
    p = Patcher()
    _quiet(p.add_m4l_device, "audio_effect")
    with pytest.warns(UserWarning, match="audio_effect"):
        export_amxd(p.to_dict(), tmp_path / "x.amxd", "instrument")


def test_export_matching_kind_does_not_warn(tmp_path):
    p = Patcher()
    _quiet(p.add_m4l_device, "audio_effect")
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        warnings.filterwarnings("ignore", ".*not auto-committed", UserWarning)
        export_amxd(p.to_dict(), tmp_path / "x.amxd", "audio_effect")


@pytest.mark.parametrize("meta", [-1, 2 ** 32, 1.5, True])
def test_build_amxd_meta_range(meta):
    with pytest.raises(ValueError, match="meta"):
        build_amxd("audio_effect", b"{}", meta)


def test_build_amxd_meta_bounds_ok():
    assert build_amxd("audio_effect", b"{}", 2 ** 32 - 1)
    assert build_amxd("audio_effect", b"{}", None)


# ---------------------------------------------------------------------------
# IN-06: info text and no overlap with the caller's chain
# ---------------------------------------------------------------------------


def test_builder_dials_carry_info_text():
    from src.maxpat.critics.m4l_critic import review_m4l

    p = Patcher()
    dev = _quiet(p.add_m4l_device, "audio_effect", [_spec("Mix", 0.0, 1.0, 0.5)])
    assert dev.dials[0].extra_attrs.get("annotation")
    assert dev.dials[0].extra_attrs.get("annotation_name") == "Mix"
    assert not [r for r in review_m4l(p.to_dict(), "audio_effect") if r.rule == "missing_info_text"]


def _overlaps(p):
    from src.maxpat.critics.layout_critic import review_layout

    return [r for r in _quiet(review_layout, p.to_dict()) if "verlap" in r.finding]


def test_builder_does_not_overlap_callers_chain():
    p = Patcher()
    mi = p.add_box("midiin", x=50.0, y=20.0)
    mk = p.add_box("makenote", ["100", "500"], x=50.0, y=60.0)
    p.add_connection(mi, 0, mk, 0)
    knob = p.add_box("live.dial", x=50.0, y=100.0)
    knob.extra_attrs["varname"] = "own"
    _quiet(p.add_m4l_device, "midi_effect",
           [_spec("Vel", 0, 127, 100), _spec("Len", 10, 2000, 500)], midi_source=(mk, 0))
    assert _overlaps(p) == []
