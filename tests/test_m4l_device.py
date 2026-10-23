"""Tests for src.maxpat.m4l_device and Patcher.add_m4l_device (quick 261022-pqu, Q40).

EXPERIMENTAL feature (not yet confirmed in Live): the .amxd codec and
export, parameter inference, unique short names and the three-kind device
skeleton. The byte layout is checked against real devices: the framework's
own kicksynth-m4l.amxd (vendored from 494c2e64, loaded by Live 12.3.6),
Max.app's fourin_fourout.amxd (requires_max) and Live 12's three
"Max Devices" templates (skipped when Live is absent).
"""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import warnings
from pathlib import Path

import pytest

from src.maxpat.m4l_constants import (
    AMXD_HEADER_FORMAT,
    AMXD_MAGIC,
    AMXD_META_MARKER,
    AMXD_META_VERSION,
    AMXD_PATCH_MARKER,
    AMXD_VERSION,
    ModMode,
    ParamType,
    UnitStyle,
)
from src.maxpat.m4l_device import (
    KIND_CODES,
    AmxdFile,
    M4LDevice,
    build_amxd,
    decode_payload,
    encode_payload,
    export_amxd,
    infer_type_unit,
    name_tokens,
    parse_amxd,
    resolve_param_specs,
    unique_shortnames,
)
from src.maxpat.patcher import BoxMovedWarning, Patcher

pytestmark = [
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
    # Exports to tmp_path outside a repository: the auto-commit warns.
    pytest.mark.filterwarnings("ignore:.*not auto-committed:UserWarning"),
]

FIXTURES = Path(__file__).parent / "fixtures"
KICKSYNTH = FIXTURES / "kicksynth-m4l.amxd"
FOURIN = Path("/Applications/Max.app/Contents/Resources/Examples/resources/fourin_fourout.amxd")
LIVE_DIR = Path("/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices")
LIVE_TEMPLATES = {
    "instrument": LIVE_DIR / "Max Instrument.amxd",
    "audio_effect": LIVE_DIR / "Max Audio Effect.amxd",
    "midi_effect": LIVE_DIR / "Max MIDI Effect.amxd",
}
needs_live = pytest.mark.skipif(not LIVE_DIR.is_dir(), reason="Ableton Live 12 Suite not installed")

KINDS = ("instrument", "audio_effect", "midi_effect")


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return struct.pack("<4sI", tag, len(payload)) + payload


def _cords(p: Patcher) -> set:
    """(src name, outlet, dst name, inlet) for every cord."""
    by_id = {b.id: b for b in p.boxes}
    return {
        (by_id[l.source_id].name, l.source_outlet, by_id[l.dest_id].name, l.dest_inlet)
        for l in p.lines
    }


def _names(p: Patcher) -> list:
    return [b.name for b in p.boxes]


def _spec(name, mn, mx, default=None, **kw):
    d = {"name": name, "min": mn, "max": mx, "default": mn if default is None else default}
    d.update(kw)
    return d


def _tu(spec):
    r = resolve_param_specs([spec])[0]
    return (r["type"], r["unit"])


# ---------------------------------------------------------------------------
# Codec: real files
# ---------------------------------------------------------------------------


def test_kicksynth_byte_roundtrip():
    data = KICKSYNTH.read_bytes()
    assert len(data) == 103996
    f = parse_amxd(data)
    assert isinstance(f, AmxdFile)
    assert f.code == b"iiii"
    assert f.kind == "instrument"
    assert f.meta == 0
    assert build_amxd(f.code, f.payload, f.meta) == data
    d = decode_payload(f.payload)
    assert isinstance(d["patcher"]["boxes"], list) and d["patcher"]["boxes"]


@pytest.mark.requires_max
def test_fourin_fourout_byte_roundtrip():
    if not FOURIN.exists():
        pytest.skip("fourin_fourout.amxd not in this Max build")
    data = FOURIN.read_bytes()
    f = parse_amxd(data)
    assert f.code == b"aaaa" and f.meta == 0
    assert f.payload.endswith(b"\n\x00")
    assert build_amxd(f.code, f.payload, f.meta) == data
    assert "patcher" in decode_payload(f.payload)


@needs_live
@pytest.mark.parametrize("kind", KINDS)
def test_live_template_byte_roundtrip(kind):
    data = LIVE_TEMPLATES[kind].read_bytes()
    f = parse_amxd(data)
    assert f.code == KIND_CODES[kind]
    assert f.kind == kind
    assert f.meta == 0
    assert build_amxd(f.code, f.payload, f.meta) == data


def test_no_meta_chunk_parses_and_rebuilds():
    payload = b'{"patcher": {"boxes": []}}\n\x00'
    data = _chunk(b"ampf", b"aaaa") + _chunk(b"ptch", payload)
    f = parse_amxd(data)
    assert f.meta is None
    assert f.payload == payload
    assert build_amxd(f.code, f.payload, f.meta) == data


def test_build_amxd_accepts_kind_name():
    payload = b"{}\n\x00"
    assert build_amxd("midi_effect", payload) == build_amxd(b"mmmm", payload, 0)


# ---------------------------------------------------------------------------
# Codec: refusals
# ---------------------------------------------------------------------------

_JSON = b'{"patcher": {}}\n\x00'


@pytest.mark.parametrize(
    "data, needle",
    [
        (_chunk(b"ampf", b"iiii") + _chunk(b"meta", b"\0\0\0\0") + _chunk(b"ciph", b"xxxx")
         + _chunk(b"ptch", _JSON), "frozen"),
        (_chunk(b"ampf", b"iiii") + _chunk(b"meta", b"\x07\0\0\0") + _chunk(b"ptch", b"mx@c" + b"\0" * 12),
         "frozen"),
        (_chunk(b"ampf", b"iiii") + struct.pack("<4sI", b"ptch", 999) + b"{}", "past the end"),
        (_chunk(b"ampf", b"iiii") + _chunk(b"ptch", _JSON) + b"junk", "trailing"),
        (_chunk(b"xxxx", b"iiii") + _chunk(b"ptch", _JSON), "ampf"),
        (_chunk(b"ampf", b"iiii") + _chunk(b"meta", b"\0\0\0\0"), "ptch"),
        (_chunk(b"ampf", b"natt") + _chunk(b"ptch", _JSON), "kind"),
        (b"amp", "truncated"),
    ],
    ids=["ciph", "mx@c", "length-past-end", "trailing", "not-ampf", "no-ptch", "natt", "truncated"],
)
def test_parse_refusals(data, needle):
    with pytest.raises(ValueError, match=needle):
        parse_amxd(data)


def test_decode_payload_rejects_invalid_utf8():
    with pytest.raises(ValueError):
        decode_payload(b'{"a": "\xff"}\n\x00')


def test_decode_payload_strips_exactly_one_nul():
    assert decode_payload(b'{"patcher": {}}\n\x00') == {"patcher": {}}
    with pytest.raises(ValueError):
        decode_payload(b'{"patcher": {}}\x00\x00')


def test_encode_payload_requires_patcher_dict():
    with pytest.raises(ValueError):
        encode_payload({"boxes": []})
    assert encode_payload({"patcher": {}}).endswith(b"\n\x00")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def _device_dict(kind: str) -> dict:
    p = Patcher()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        p.add_m4l_device(kind, [_spec("freq", 20.0, 2000.0, 220.0)])
    return p.to_dict()


@pytest.mark.parametrize("kind", KINDS)
def test_export_header_and_payload(tmp_path, kind):
    d = _device_dict(kind)
    out = export_amxd(d, tmp_path / "x.amxd", kind)
    assert out == tmp_path / "x.amxd"
    data = out.read_bytes()
    n = len(data) - 32
    assert data[:32] == struct.pack(
        AMXD_HEADER_FORMAT, AMXD_MAGIC, AMXD_VERSION, KIND_CODES[kind],
        AMXD_META_MARKER, AMXD_META_VERSION, AMXD_PATCH_MARKER, n,
    )
    f = parse_amxd(data)
    assert f.payload.endswith(b"\n\x00")
    assert decode_payload(f.payload) == d


@needs_live
@pytest.mark.parametrize("kind", KINDS)
def test_export_header_matches_live_template(tmp_path, kind):
    data = export_amxd(_device_dict(kind), tmp_path / "x.amxd", kind).read_bytes()
    assert data[:28] == LIVE_TEMPLATES[kind].read_bytes()[:28]


def test_export_from_path_leaves_maxpat_untouched(tmp_path):
    src = tmp_path / "dev.maxpat"
    src.write_text(json.dumps(_device_dict("instrument"), indent=2), encoding="utf-8")
    before = src.read_bytes()
    out = export_amxd(src, kind="instrument")
    assert out == tmp_path / "dev.amxd"
    assert out.exists()
    assert src.read_bytes() == before
    assert decode_payload(parse_amxd(out.read_bytes()).payload) == json.loads(before)


def test_export_from_patcher_object(tmp_path):
    p = Patcher()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        p.add_m4l_device("audio_effect")
    out = export_amxd(p, tmp_path / "fx.amxd")
    assert parse_amxd(out.read_bytes()).code == b"aaaa"


def test_export_refuses_non_amxd_suffix(tmp_path):
    with pytest.raises(ValueError, match=".amxd"):
        export_amxd(_device_dict("instrument"), tmp_path / "x.maxpat", "instrument")
    assert not (tmp_path / "x.maxpat").exists()


def test_export_refuses_amxdtype_mismatch(tmp_path):
    d = _device_dict("instrument")
    d["patcher"]["project"] = {"amxdtype": 1633771873}  # aaaa
    with pytest.raises(ValueError, match="amxdtype"):
        export_amxd(d, tmp_path / "x.amxd", "instrument")
    assert not (tmp_path / "x.amxd").exists()


def test_export_accepts_matching_amxdtype(tmp_path):
    d = _device_dict("instrument")
    d["patcher"]["project"] = {"amxdtype": 1768515945}  # iiii
    out = export_amxd(d, tmp_path / "x.amxd", "instrument")
    assert parse_amxd(out.read_bytes()).code == b"iiii"


def test_export_refuses_undetectable_kind(tmp_path):
    with pytest.raises(ValueError):
        export_amxd(Patcher().to_dict(), tmp_path / "x.amxd")
    assert not (tmp_path / "x.amxd").exists()


def test_export_refuses_unknown_kind(tmp_path):
    with pytest.raises(ValueError):
        export_amxd(_device_dict("instrument"), tmp_path / "x.amxd", "midi_tool")


def test_export_requires_out_path_for_dict():
    with pytest.raises(ValueError):
        export_amxd(_device_dict("instrument"), None, "instrument")


# --- git auto-commit (temp repo) -------------------------------------------


@pytest.fixture
def _isolate_git_env(monkeypatch):
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(root), capture_output=True, text=True, check=True,
    ).stdout


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    hooks = tmp_path / "empty-hooks"
    hooks.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "M4L Device Test")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "config", "core.hooksPath", str(hooks))
    return root.resolve()


def test_export_auto_commits_only_the_amxd(tmp_path, _isolate_git_env):
    root = _repo(tmp_path)
    proj = root / "patches" / "demo"
    proj.mkdir(parents=True)
    src = proj / "dev.maxpat"
    src.write_text(json.dumps(_device_dict("instrument"), indent=2), encoding="utf-8")
    _git(root, "add", "--", "patches/demo/dev.maxpat")
    _git(root, "commit", "-q", "-m", "init")
    before = _git(root, "rev-parse", "HEAD").strip()
    export_amxd(src)
    assert _git(root, "rev-parse", "HEAD").strip() != before
    files = [l for l in _git(root, "show", "--name-only", "--format=", "HEAD").splitlines() if l]
    assert files == ["patches/demo/dev.amxd"]


# ---------------------------------------------------------------------------
# Parameter inference
# ---------------------------------------------------------------------------


def test_name_tokens():
    assert name_tokens("cutoffHz") == ["cutoff", "hz"]
    assert name_tokens("freq1") == ["freq", "1"]
    assert name_tokens("Filter Cutoff") == ["filter", "cutoff"]
    assert name_tokens("delay_ms") == ["delay", "ms"]
    assert name_tokens("gain_dB") == ["gain", "db"]
    assert name_tokens("harmonics") == ["harmonics"]


@pytest.mark.parametrize(
    "spec, expected",
    [
        (_spec("freq", 20.0, 2000.0), (0, 3)),
        (_spec("Filter Cutoff", 20.0, 20000.0), (0, 3)),
        (_spec("cutoffHz", 0.0, 1.0), (0, 3)),
        (_spec("cutoff", 0.0, 1.0), (0, 1)),
        (_spec("attack", 1.0, 500.0), (0, 2)),
        (_spec("delay_ms", 0.0, 1.0), (0, 2)),
        (_spec("harmonics", 1.0, 16.0), (0, 1)),
        (_spec("gain", 0.0, 1.0), (0, 1)),
        (_spec("Out Gain", -70.0, 0.0), (0, 4)),
        (_spec("gain_dB", 0.0, 6.0), (0, 4)),
        (_spec("volume", 0.0, 2.0), (0, 1)),
        (_spec("pan", -50.0, 50.0), (0, 6)),
        (_spec("transpose", -24, 24, 0), (1, 7)),
        (_spec("Octave", -2, 2, 0), (1, 0)),
        (_spec("steps", 1, 16, 1), (1, 0)),
        (_spec("Delay Time", 0, 5000, 100), (0, 2)),
        (_spec("notes", 0, 1000, 0), (0, 0)),
        (_spec("freq", 20.0, 2000.0, type="int", unit="ms"), (1, 2)),
    ],
    ids=lambda v: v["name"] if isinstance(v, dict) else None,
)
def test_inference_table(spec, expected):
    assert _tu(spec) == expected


def test_infer_type_unit_direct():
    assert infer_type_unit("freq", 20.0, 2000.0, 220.0) == (ParamType.FLOAT, UnitStyle.HERTZ)
    assert infer_type_unit("Octave", -2, 2, 0) == (ParamType.INT, UnitStyle.INT)


def test_steps_on_float_range_keeps_type():
    r = resolve_param_specs([_spec("cutoff", 0.0, 1.0, steps=5)])[0]
    assert r["steps"] == 5
    assert r["type"] == int(ParamType.FLOAT)


def test_explicit_enum_members_and_names_accepted():
    r = resolve_param_specs([_spec("x", 0.0, 1.0, type=ParamType.INT, unit=UnitStyle.PERCENT,
                                   modmode="absolute")])[0]
    assert (r["type"], r["unit"], r["modmode"]) == (1, 5, 4)
    r = resolve_param_specs([_spec("y", 0.0, 1.0, unit="%", modmode=ModMode.BIPOLAR)])[0]
    assert (r["unit"], r["modmode"]) == (5, 2)
    r = resolve_param_specs([_spec("z", 0.0, 1.0, unit="hertz", type=0)])[0]
    assert (r["type"], r["unit"]) == (0, 3)


def test_modmode_default_none_and_override():
    assert resolve_param_specs([_spec("x", 0.0, 1.0)])[0]["modmode"] == 0
    assert resolve_param_specs([_spec("x", 0.0, 1.0)], modmode=ModMode.ABSOLUTE)[0]["modmode"] == 4


def test_varname_derivation():
    r = resolve_param_specs([_spec("freq", 0.0, 1.0), _spec("Out Gain", -70.0, 0.0)])
    assert r[0]["varname"] == "freq"
    assert r[1]["varname"] == "out_gain"
    r = resolve_param_specs([_spec("Out Gain", -70.0, 0.0, varname="og")])
    assert r[0]["varname"] == "og"


# ---------------------------------------------------------------------------
# Short names
# ---------------------------------------------------------------------------


def test_shortnames_dedupe():
    assert unique_shortnames(
        ["Filter Envelope Amount", "Pitch Envelope Amount"], [None, None]
    ) == ["Amount", "Amount2"]


def test_shortnames_explicit_reserved_and_kept():
    names = unique_shortnames(
        ["First", "Filter Envelope Amount", "Pitch Envelope Amount"], ["Amount", None, None]
    )
    assert names == ["Amount", "Amount2", "Amount3"]


def test_explicit_shortname_never_altered():
    assert unique_shortnames(["Frequency Long Name"], ["A Very Long Short Name"]) == [
        "A Very Long Short Name"
    ]


def test_auto_shortnames_at_most_8_chars():
    longnames = ["Filter Envelope Amount", "Pitch Envelope Amount", "Amplitude Release Time",
                 "Amplitude Release Times", "Oscillator Frequency", "freq", "Out Gain"]
    out = unique_shortnames(longnames, [None] * len(longnames))
    assert len(set(out)) == len(out)
    assert all(len(s) <= 8 for s in out)


def test_resolve_keeps_longname_verbatim():
    r = resolve_param_specs([_spec("Filter Envelope Amount", 0.0, 1.0),
                             _spec("Pitch Envelope Amount", 0.0, 1.0)])
    assert [x["name"] for x in r] == ["Filter Envelope Amount", "Pitch Envelope Amount"]
    assert [x["short_name"] for x in r] == ["Amount", "Amount2"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    [
        [_spec("a", 0.0, 1.0), _spec("a", 0.0, 1.0)],
        [_spec("a", 0.0, 1.0, colour="red")],
        [{"name": "a", "min": 0.0, "max": 1.0}],
        [_spec("a", False, True, False)],
        [_spec("a", 1.0, 1.0)],
        [_spec("a", 2.0, 1.0, 1.5)],
        [_spec("a", 0.0, 1.0, 2.0)],
        [_spec("a", 0.0, 1.0, steps=1)],
        [_spec("a", 0.0, 1.0, type=ParamType.ENUM)],
        [_spec("a", 0.0, 1.0, type="blob")],
        [_spec("a", 0.0, 1.0, unit=UnitStyle.CUSTOM)],
        [_spec("a", 0.0, 1.0, unit="custom")],
        [_spec("a", "0", 1.0)],
        [_spec("", 0.0, 1.0)],
        [_spec("A b", 0.0, 1.0), _spec("a_b", 0.0, 1.0)],
    ],
    ids=["dup-name", "unknown-key", "missing-default", "bool-bounds", "min-eq-max",
         "min-gt-max", "default-outside", "steps-lt-2", "enum", "blob", "custom-enum",
         "custom-name", "string-bound", "empty-name", "dup-varname"],
)
def test_validation_errors(params):
    with pytest.raises(ValueError):
        resolve_param_specs(params)


# ---------------------------------------------------------------------------
# Builder wiring
# ---------------------------------------------------------------------------


def _build(kind, params=None, **kw):
    p = Patcher()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dev = p.add_m4l_device(kind, params, **kw)
    return p, dev


_IO = {"plugin~", "plugout~", "midiin", "midiout"}


def _io_cords(p):
    return {c for c in _cords(p) if c[0] in _IO and c[2] in _IO}


def test_audio_effect_wiring():
    p, dev = _build("audio_effect")
    assert isinstance(dev, M4LDevice)
    assert _io_cords(p) == {("plugin~", 0, "plugout~", 0), ("plugin~", 1, "plugout~", 1)}
    assert dev.plugin is not None and dev.plugout is not None
    assert dev.midiin is None and dev.midiout is None


def test_midi_effect_wiring():
    p, dev = _build("midi_effect")
    assert _io_cords(p) == {("midiin", 0, "midiout", 0)}
    assert "plugin~" not in _names(p) and "plugout~" not in _names(p)


def test_instrument_wiring():
    p, dev = _build("instrument")
    assert "midiin" in _names(p) and "plugout~" in _names(p)
    assert _io_cords(p) == set()
    assert not [c for c in _cords(p) if c[2] == "plugout~"]
    p2, dev2 = _build("instrument", midi_in=False)
    assert "midiin" not in _names(p2)
    assert dev2.midiin is None


def test_instrument_mono_source_feeds_both_inlets():
    p = Patcher()
    osc = p.add_box("cycle~", ["220"], x=400.0, y=200.0)
    p.add_m4l_device("instrument", audio_source=(osc, 0))
    assert {("cycle~", 0, "plugout~", 0), ("cycle~", 0, "plugout~", 1)} <= _cords(p)


def test_instrument_stereo_source_pair():
    p = Patcher()
    left = p.add_box("cycle~", ["220"], x=400.0, y=200.0)
    right = p.add_box("cycle~", ["330"], x=500.0, y=200.0)
    p.add_m4l_device("instrument", audio_source=((left, 0), (right, 0)))
    by_id = {b.id: b for b in p.boxes}
    into = {(l.source_id, l.dest_inlet) for l in p.lines if by_id[l.dest_id].name == "plugout~"}
    assert into == {(left.id, 0), (right.id, 1)}


def test_audio_effect_with_source_has_no_passthrough():
    p = Patcher()
    pin = p.add_box("plugin~", x=400.0, y=150.0)
    osc = p.add_box("cycle~", ["220"], x=400.0, y=200.0)
    p.add_connection(pin, 0, osc, 0)
    dev = p.add_m4l_device("audio_effect", audio_source=(osc, 0))
    cords = _cords(p)
    assert dev.plugin is pin
    assert [b.name for b in p.boxes].count("plugin~") == 1
    assert not [c for c in cords if c[0] == "plugin~" and c[2] == "plugout~"]
    assert ("cycle~", 0, "plugout~", 0) in cords and ("cycle~", 0, "plugout~", 1) in cords


def test_midi_effect_with_source():
    p = Patcher()
    mi = p.add_box("midiin", x=400.0, y=150.0)
    mk = p.add_box("makenote", ["100", "500"], x=400.0, y=200.0)
    dev = p.add_m4l_device("midi_effect", midi_source=(mk, 0))
    cords = _cords(p)
    assert dev.midiin is mi
    assert [b.name for b in p.boxes].count("midiin") == 1
    assert ("midiin", 0, "midiout", 0) not in cords
    assert ("makenote", 0, "midiout", 0) in cords


def test_source_without_device_input_raises_before_building():
    """WR-01: a source chain with no plugin~/midiin would leave a dangling input."""
    for kind, key, name, args in (
        ("audio_effect", "audio_source", "cycle~", ["220"]),
        ("midi_effect", "midi_source", "makenote", ["100", "500"]),
    ):
        p = Patcher()
        src = p.add_box(name, args, x=400.0, y=200.0)
        before = len(p.boxes)
        with pytest.raises(ValueError, match="first"):
            p.add_m4l_device(kind, **{key: (src, 0)})
        assert len(p.boxes) == before


def test_midi_source_output_passes_midi_passthrough():
    """WR-01: the builder's own output no longer trips its own critic."""
    from src.maxpat.critics.m4l_critic import review_m4l

    p = Patcher()
    mi = p.add_box("midiin", x=400.0, y=150.0)
    mk = p.add_box("makenote", ["100", "500"], x=400.0, y=200.0)
    p.add_connection(mi, 0, mk, 0)
    p.add_m4l_device("midi_effect", midi_source=(mk, 0))
    rules = {r.rule for r in review_m4l(p.to_dict(), "midi_effect")}
    assert "midi_passthrough" not in rules


def test_varname_collision_raises_before_building():
    """WR-02: a dial varname equal to an existing box varname is refused."""
    p = Patcher()
    gen = p.add_box("cycle~", ["220"], x=400.0, y=200.0)
    gen.extra_attrs["varname"] = "synth"
    before = len(p.boxes)
    with pytest.raises(ValueError, match="varname"):
        p.add_m4l_device("instrument", [{"name": "synth", "min": 0, "max": 1, "default": 0.5}])
    assert len(p.boxes) == before


def test_gen_synth_param_named_like_gen_varname_raises():
    """WR-02: add_m4l_gen_synth refuses a param equal to gen_varname, before gen~ exists."""
    p = Patcher()
    with pytest.raises(ValueError, match="gen_varname"):
        p.add_m4l_gen_synth([("synth", 0.0, 1.0)])
    assert p.boxes == []


def test_presentation_grid_keeps_existing_ui():
    """WR-03: dials go right of existing presentation UI; devicewidth only grows."""
    p = Patcher()
    old = p.add_box("live.dial", x=10.0, y=10.0)
    p.add_to_presentation(old, [8.0, 8.0, 120.0, 48.0])
    p.props["devicewidth"] = 400.0
    p.props["openrect"] = [0.0, 0.0, 300.0, 169.0]
    dev = p.add_m4l_device("audio_effect", [{"name": "Mix", "min": 0, "max": 1, "default": 0.5}])
    rect = dev.dials[0].presentation_rect
    assert rect[0] >= 128.0
    assert p.props["devicewidth"] == 400.0
    assert p.props["openrect"] == [0.0, 0.0, 300.0, 169.0]


def test_banks_include_existing_parameters():
    """WR-04: planned banks cover parameters already in the patcher."""
    p = Patcher()
    p.add_m4l_device("audio_effect", [{"name": "Cutoff Freq", "min": 20, "max": 20000, "default": 1000}],
                     banks=False)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", BoxMovedWarning)  # second skeleton's I/O boxes
        p.add_m4l_device("instrument", [{"name": "Out Gain", "min": -70, "max": 6, "default": 0}],
                         midi_in=False)
    banked = {n for bank in p.props["parameters"]["parameterbanks"].values()
              for n in bank["parameters"] if n != "-"}
    assert banked == {"Cutoff Freq", "Out Gain"}


def test_bad_sources_raise_before_building():
    p = Patcher()
    osc = p.add_box("cycle~", ["220"], x=400.0, y=200.0)
    with pytest.raises(ValueError):
        p.add_m4l_device("midi_effect", audio_source=(osc, 0))
    with pytest.raises(ValueError):
        p.add_m4l_device("instrument", midi_source=(osc, 0))
    with pytest.raises(ValueError):
        p.add_m4l_device("instrument", audio_source=(osc, 5))
    with pytest.raises(ValueError):
        p.add_m4l_device("instrument", audio_source=("obj-1", 0))
    with pytest.raises(ValueError):
        p.add_m4l_device("midi_tool")
    with pytest.raises(ValueError):
        p.add_m4l_device("instrument", [_spec("a", 0.0, 1.0), _spec("a", 0.0, 1.0)])
    assert _names(p) == ["cycle~"]


@pytest.mark.parametrize("kind", ["instrument", "audio_effect"])
def test_plugin_plugout_bare(kind):
    p, _ = _build(kind)
    io = [b for b in p.boxes if b.name in ("plugin~", "plugout~")]
    assert io
    for b in io:
        assert not b.args
    texts = {e["box"].get("text") for e in p.to_dict()["patcher"]["boxes"]}
    io_texts = {t for t in texts if t and t.split()[0] in ("plugin~", "plugout~")}
    assert io_texts <= {"plugin~", "plugout~"}


# ---------------------------------------------------------------------------
# Dials
# ---------------------------------------------------------------------------

_LEGACY_EXTRA_ORDER_BOUND = ["varname", "param_connect", "parameter_enable", "saved_attribute_attributes"]
_VALUEOF_ORDER = [
    "parameter_initial", "parameter_initial_enable", "parameter_longname", "parameter_shortname",
    "parameter_mmin", "parameter_mmax", "parameter_modmode", "parameter_type", "parameter_unitstyle",
]


def test_dial_attribute_order_and_values():
    params = [
        _spec("freq", 20.0, 2000.0, 220.0, param_connect="synth::freq"),
        _spec("Octave", -2, 2, 0, steps=5),
    ]
    p, dev = _build("instrument", params, presentation=False)
    d0, d1 = dev.dials
    assert list(d0.extra_attrs) == _LEGACY_EXTRA_ORDER_BOUND
    assert list(d1.extra_attrs) == ["varname", "parameter_enable", "saved_attribute_attributes"]
    v0 = d0.extra_attrs["saved_attribute_attributes"]["valueof"]
    v1 = d1.extra_attrs["saved_attribute_attributes"]["valueof"]
    assert list(v0) == _VALUEOF_ORDER
    assert list(v1) == _VALUEOF_ORDER + ["parameter_steps"]
    assert v0["parameter_initial"] == [220.0]
    assert v0["parameter_mmin"] == 20.0 and v0["parameter_mmax"] == 2000.0
    assert (v0["parameter_type"], v0["parameter_unitstyle"], v0["parameter_modmode"]) == (0, 3, 0)
    assert v1["parameter_initial"] == [0] and type(v1["parameter_mmin"]) is int
    assert (v1["parameter_type"], v1["parameter_unitstyle"], v1["parameter_steps"]) == (1, 0, 5)
    assert d0.extra_attrs["param_connect"] == "synth::freq"
    assert d0.extra_attrs["parameter_enable"] == 1
    assert d1.extra_attrs["varname"] == "Octave"


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", [1, 8, 9, 24, 25, 40])
def test_presentation_grid(n):
    params = [_spec("p%d" % i, 0.0, 1.0) for i in range(n)]
    p = Patcher()
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        dev = p.add_m4l_device("audio_effect", params)
    assert not [w for w in rec if issubclass(w.category, BoxMovedWarning)]
    ncols = min(n, 8) if n <= 24 else -(-n // 3)
    for i, d in enumerate(dev.dials):
        row, col = divmod(i, ncols)
        assert d.presentation
        assert list(d.presentation_rect) == [8 + 52 * col, 8 + 56 * row, 44, 48]
        assert d.presentation_rect[1] + d.presentation_rect[3] <= 169
    assert p.props["openinpresentation"] == 1
    assert p.props["devicewidth"] == 8 + 52 * ncols
    assert p.props["openrect"] == [0.0, 0.0, 0.0, 169.0]
    assert p.props["latency"] == 0


def test_presentation_false_leaves_props():
    before = Patcher().props
    p, dev = _build("audio_effect", [_spec("a", 0.0, 1.0)], presentation=False)
    assert p.props["openinpresentation"] == before["openinpresentation"]
    assert p.props["devicewidth"] == before["devicewidth"]
    assert "openrect" not in p.props and "latency" not in p.props
    assert not dev.dials[0].presentation


# ---------------------------------------------------------------------------
# Tracer end to end
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kind", KINDS)
def test_review_has_no_blockers(kind):
    from src.maxpat.critics import review_patch

    p, _ = _build(kind, [_spec("freq", 20.0, 2000.0, 220.0), _spec("Octave", -2, 2, 0)])
    blockers = [r for r in review_patch(p.to_dict()) if r.severity == "blocker"]
    assert blockers == []


def test_tracer_instrument_export_roundtrip(tmp_path):
    p = Patcher()
    osc = p.add_box("cycle~", ["220"], x=400.0, y=200.0)
    p.add_m4l_device("instrument", [_spec("freq", 20.0, 2000.0, 220.0)], audio_source=(osc, 0))
    d = p.to_dict()
    f = parse_amxd(export_amxd(d, tmp_path / "inst.amxd", "instrument").read_bytes())
    assert f.code == b"iiii"
    assert decode_payload(f.payload) == d


# ===========================================================================
# Task 2: live.thisdevice init chain, Push banks, add_m4l_gen_synth delegation
# ===========================================================================


def _num(box_id: str) -> int:
    return int(box_id.split("-")[1])


def _from(p, box):
    return [(l.source_outlet, l.dest_id, l.dest_inlet) for l in p.lines if l.source_id == box.id]


def _mixed_params():
    return [
        _spec("freq", 20.0, 2000.0, 220.0, param_connect="synth::freq"),
        _spec("Out Gain", -70.0, 0.0, -12.0),
        _spec("Octave", -2, 2, 0),
        _spec("Attack", 1.0, 500.0, 10.0),
    ]


def test_init_chain_all_bound():
    p, dev = _build("instrument", [_spec("freq", 20.0, 2000.0, 220.0, param_connect="s::freq"),
                                   _spec("amp", 0.0, 1.0, 0.5, param_connect="s::amp")])
    assert dev.thisdevice is not None and dev.thisdevice.name == "live.thisdevice"
    assert dev.init_trigger is None
    assert "trigger" not in _names(p) and "t" not in _names(p)
    assert _from(p, dev.thisdevice) == []


def test_init_chain_one_unbound_cords_directly():
    p, dev = _build("instrument", [_spec("freq", 20.0, 2000.0, 220.0, param_connect="s::freq"),
                                   _spec("Out Gain", -70.0, 0.0, -12.0)])
    assert dev.init_trigger is None
    assert _from(p, dev.thisdevice) == [(0, dev.dials[1].id, 0)]


def test_init_chain_trigger_bangs_unbound_dials_in_order():
    p, dev = _build("instrument", _mixed_params())
    t = dev.init_trigger
    assert t is not None
    assert p.to_dict()["patcher"]["boxes"][[b.id for b in p.boxes].index(t.id)]["box"]["text"] == "t b b b"
    assert t.numoutlets == 3
    assert _from(p, dev.thisdevice) == [(0, t.id, 0)]
    unbound = dev.dials[1:]
    assert sorted(_from(p, t)) == [(j, unbound[j].id, 0) for j in range(3)]
    assert not [l for l in p.lines if l.dest_id == dev.dials[0].id]
    last_dial = max(_num(x.id) for x in dev.dials)
    assert _num(dev.thisdevice.id) > last_dial and _num(t.id) > last_dial


def test_init_chain_false():
    p, dev = _build("instrument", _mixed_params(), init_chain=False)
    assert "live.thisdevice" not in _names(p)
    assert dev.thisdevice is None and dev.init_trigger is None


@pytest.mark.parametrize("kind", KINDS)
def test_detect_kind_and_export_kind_none(tmp_path, kind):
    from src.maxpat.critics.m4l_critic import detect_m4l_device_type

    p, _ = _build(kind)
    d = p.to_dict()
    assert detect_m4l_device_type(d) == kind
    assert parse_amxd(export_amxd(d, tmp_path / "k.amxd").read_bytes()).code == KIND_CODES[kind]


def _polish_patch(longnames):
    boxes = []
    for i, ln in enumerate(longnames):
        boxes.append({"box": {
            "id": "obj-%d" % (i + 1), "maxclass": "live.dial", "numinlets": 1, "numoutlets": 2,
            "outlettype": ["", "float"], "patching_rect": [10.0 + 60 * i, 10.0, 44.0, 48.0],
            "parameter_enable": 1, "varname": "v%d" % i,
            "saved_attribute_attributes": {"valueof": {"parameter_longname": ln,
                                                       "parameter_shortname": ln[:8]}},
        }})
    return {"patcher": {"boxes": boxes, "lines": []}}


def test_plan_push_banks_matches_organize_push_banks():
    from src.maxpat.m4l_polish import organize_push_banks, plan_push_banks

    names = ["freq", "amp", "Attack", "Octave"]
    patch = organize_push_banks(_polish_patch(names))
    assert plan_push_banks(names) == patch["patcher"]["parameters"]["parameterbanks"]
    assert plan_push_banks([]) == {}


def test_plan_push_banks_chunks_and_pads():
    from src.maxpat.m4l_polish import plan_push_banks

    names = ["Filter %d" % i for i in range(10)]
    banks = plan_push_banks(names)
    assert [b["name"] for b in banks.values()] == ["Filter", "Filter 2"]
    assert banks["1"]["parameters"] == ["Filter 8", "Filter 9"] + ["-"] * 6
    assert banks["0"]["index"] == 0 and banks["1"]["index"] == 1


def test_builder_writes_banks_and_one_live_banks():
    from src.maxpat.m4l_polish import plan_push_banks

    p, dev = _build("audio_effect", _mixed_params())
    longnames = ["freq", "Out Gain", "Octave", "Attack"]
    assert p.props["parameters"]["parameterbanks"] == plan_push_banks(longnames)
    banks_boxes = [b for b in p.boxes if b.name == "live.banks"]
    assert len(banks_boxes) == 1 and banks_boxes[0] is dev.banks
    box = p.to_dict()["patcher"]["boxes"][[b.id for b in p.boxes].index(dev.banks.id)]["box"]
    assert box["maxclass"] == "newobj" and box["text"] == "live.banks"


def test_builder_keeps_user_banks_with_warning():
    user = {"0": {"index": 0, "name": "Mine", "parameters": ["freq"] + ["-"] * 7}}
    p = Patcher()
    p.props["parameters"] = {"parameterbanks": json.loads(json.dumps(user))}
    with pytest.warns(UserWarning, match="parameterbanks"):
        p.add_m4l_device("audio_effect", _mixed_params())
    assert p.props["parameters"]["parameterbanks"] == user


def test_builder_replaces_placeholder_banks():
    from src.maxpat.m4l_polish import plan_push_banks

    p = Patcher()
    p.props["parameters"] = {"parameterbanks": {"0": {"index": 0, "name": "", "parameters": ["-"] * 8}}}
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        p.add_m4l_device("audio_effect", [_spec("freq", 20.0, 2000.0, 220.0)])
    assert p.props["parameters"]["parameterbanks"] == plan_push_banks(["freq"])


def test_builder_reuses_existing_live_banks():
    p = Patcher()
    existing = p.add_box("live.banks", x=600.0, y=20.0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        dev = p.add_m4l_device("audio_effect", _mixed_params())
    assert dev.banks is existing
    assert [b.name for b in p.boxes].count("live.banks") == 1


@pytest.mark.parametrize("kw, params", [({"banks": False}, "mixed"), ({}, None)])
def test_no_banks(kw, params):
    p, dev = _build("audio_effect", _mixed_params() if params else None, **kw)
    assert "parameters" not in p.props
    assert "live.banks" not in _names(p)
    assert dev.banks is None


def test_polish_keeps_builder_output():
    import copy

    from src.maxpat.m4l_polish import polish_m4l_device

    p, dev = _build("instrument", _mixed_params() + [
        _spec("Filter Envelope Amount", 0.0, 1.0, 0.0),
        _spec("Pitch Envelope Amount", 0.0, 1.0, 0.0),
    ])
    d = p.to_dict()
    before = copy.deepcopy(d)
    polish_m4l_device(d)
    assert d["patcher"]["parameters"]["parameterbanks"] == before["patcher"]["parameters"]["parameterbanks"]

    def dial_info(dd):
        out = {}
        for e in dd["patcher"]["boxes"]:
            b = e["box"]
            if b.get("maxclass") == "live.dial":
                out[b["id"]] = (b["saved_attribute_attributes"]["valueof"]["parameter_shortname"],
                                b.get("presentation_rect"))
        return out

    assert dial_info(d) == dial_info(before)
    assert sum(1 for e in d["patcher"]["boxes"] if e["box"].get("text") == "live.banks") == 1
    assert all(e["box"].get("annotation") for e in d["patcher"]["boxes"]
               if e["box"].get("maxclass") == "live.dial")


@pytest.mark.parametrize("kind", KINDS)
def test_review_mixed_params_clean(kind):
    from src.maxpat.critics import review_patch

    p, dev = _build(kind, _mixed_params())
    results = review_patch(p.to_dict())
    assert [r for r in results if r.severity == "blocker"] == []
    assert not [r for r in results if r.rule == "fan_out_without_trigger"]
    dial_ids = {d.id for d in dev.dials}
    assert not [r for r in results if r.rule == "uninitialized_state"
                and set(getattr(r, "box_ids", ()) or ()) & dial_ids]


def test_gen_synth_delegates_to_add_m4l_device():
    """Behaviour, not source text (Q40 review IN-04): one delegate call, the
    instrument kind with the legacy flags, and gen~-bound param_connect."""
    from unittest import mock

    p = Patcher()
    with mock.patch.object(Patcher, "add_m4l_device", autospec=True,
                           side_effect=Patcher.add_m4l_device) as spy:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            gen, dials, plugout = p.add_m4l_gen_synth(
                [("freq", 20.0, 2000.0), ("amp", 0.0, 1.0)], gen_varname="osc")
    assert spy.call_count == 1
    args, kwargs = spy.call_args
    assert args[0] is p and args[1] == "instrument"
    assert [s["param_connect"] for s in args[2]] == ["osc::freq", "osc::amp"]
    assert kwargs == {"audio_source": (gen, 0), "midi_in": False, "init_chain": False,
                      "banks": False, "presentation": False}
    assert [d.extra_attrs["param_connect"] for d in dials] == ["osc::freq", "osc::amp"]
    assert plugout.name == "plugout~"


def test_gen_synth_duplicate_name_now_raises():
    p = Patcher()
    with pytest.raises(ValueError):
        p.add_m4l_gen_synth([("freq", 20.0, 2000.0), ("freq", 0.0, 1.0)])
    assert p.boxes == [] and p.lines == []
    with pytest.raises(ValueError):
        p.add_m4l_gen_synth([("freq", 20.0, 20.0)])
    assert p.boxes == []


# ===========================================================================
# Task 3: Q40 M4L critic rules (EXPERIMENTAL; all non-blocking)
# ===========================================================================

from src.maxpat.critics.m4l_critic import review_m4l  # noqa: E402

Q40_RULES = (
    "stereo_out", "midi_passthrough", "shortname_length", "int_param_range", "param_range",
    "shortname_unique", "bank_refs", "device_height",
)


# --- dict helpers (copied from tests/test_critics_recursive.py, not imported) ---


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


def _plugout(box_id="obj-90", text="plugout~"):
    return _box(box_id, text, 2, 2, outlettype=["signal", "signal"])


def _osc(box_id="obj-80"):
    return _box(box_id, "cycle~ 220", 2, 1, outlettype=["signal"])


def _pdial(box_id, longname="Cutoff", **valueof):
    v = {"parameter_longname": longname}
    v.update(valueof)
    return _box(box_id, None, 1, 2, maxclass="live.dial", outlettype=["", "float"],
                parameter_enable=1, annotation="x", saved_attribute_attributes={"valueof": v})


def _rules(results, rule):
    return [r for r in results if r.rule == rule]


def _m4l(d, kind="instrument"):
    return review_m4l(d, device_type=kind)


# --- stereo_out ---------------------------------------------------------------


@pytest.mark.parametrize("inlet", [0, 1])
def test_stereo_out_one_inlet(inlet):
    d = _patch([_osc(), _plugout()], [_line("obj-80", 0, "obj-90", inlet)])
    hits = _rules(_m4l(d), "stereo_out")
    assert len(hits) == 1
    assert hits[0].severity == "warning"
    assert hits[0].finding.startswith("plugout~ (obj-90)")
    assert "inlet %d only" % inlet in hits[0].finding
    assert hits[0].box_ids == ("obj-90",)


def test_stereo_out_both_or_none_or_args():
    both = _patch([_osc(), _plugout()], [_line("obj-80", 0, "obj-90", 0), _line("obj-80", 0, "obj-90", 1)])
    assert not _rules(_m4l(both), "stereo_out")
    unwired = _patch([_plugout()])
    assert not _rules(_m4l(unwired), "stereo_out")
    args = _patch([_osc(), _plugout(text="plugout~ 1")], [_line("obj-80", 0, "obj-90", 0)])
    assert not _rules(_m4l(args), "stereo_out")


# --- midi_passthrough -----------------------------------------------------------


def _midiin(box_id="obj-70"):
    return _box(box_id, "midiin", 1, 1, outlettype=["int"])


def _midiout(box_id="obj-71"):
    return _box(box_id, "midiout", 1, 0, outlettype=[])


def test_midi_passthrough_cut():
    d = _patch([_midiin(), _box("obj-72", "live.thisdevice", 1, 3, outlettype=["bang", "int", "int"])])
    hits = _rules(_m4l(d, "midi_effect"), "midi_passthrough")
    assert len(hits) == 1 and hits[0].severity == "warning" and "midiin (obj-70)" in hits[0].finding
    d = _patch([_midiout()])
    hits = _rules(_m4l(d, "midi_effect"), "midi_passthrough")
    assert len(hits) == 1 and "midiout (obj-71)" in hits[0].finding


def test_midi_passthrough_ok_and_instrument_ignored():
    d = _patch([_midiin(), _midiout()], [_line("obj-70", 0, "obj-71", 0)])
    assert not _rules(_m4l(d, "midi_effect"), "midi_passthrough")
    lone = _patch([_midiin(), _plugout()])
    assert not _rules(_m4l(lone, "instrument"), "midi_passthrough")


# --- shortname_length / int_param_range / param_range ----------------------------


def test_shortname_length():
    hits = _rules(_m4l(_patch([_plugout(), _pdial("obj-3", parameter_shortname="Frequency")])),
                  "shortname_length")
    assert len(hits) == 1 and hits[0].severity == "note" and hits[0].box_ids == ("obj-3",)
    assert not _rules(_m4l(_patch([_plugout(), _pdial("obj-3", parameter_shortname="Freqency")])),
                      "shortname_length")
    assert not _rules(_m4l(_patch([_plugout(), _pdial("obj-3")])), "shortname_length")


def test_int_param_range():
    def run(t, mx):
        return _rules(_m4l(_patch([_plugout(), _pdial("obj-3", parameter_type=t, parameter_mmin=0,
                                                      parameter_mmax=mx)])), "int_param_range")
    hits = run(1, 1000)
    assert len(hits) == 1 and hits[0].severity == "warning"
    assert not run(1, 255)
    assert not run(0, 1000)


def test_param_range():
    def run(**v):
        return _rules(_m4l(_patch([_plugout(), _pdial("obj-3", **v)])), "param_range")
    assert len(run(parameter_mmin=10, parameter_mmax=10)) == 1
    hits = run(parameter_mmin=0, parameter_mmax=100, parameter_initial=[500])
    assert len(hits) == 1 and hits[0].severity == "warning"
    assert not run(parameter_mmin=0, parameter_mmax=100, parameter_initial=[50])
    assert not run(parameter_mmin="0", parameter_mmax=100, parameter_initial=[500])
    assert not run(parameter_mmax=100, parameter_initial=[500])
    assert not run(parameter_mmin=0, parameter_mmax=100, parameter_initial=500)


# --- device-level rules ------------------------------------------------------------


def test_shortname_unique_top_and_nested():
    d = _patch([
        _plugout(),
        _pdial("obj-3", "Filter Env Amount", parameter_shortname="Amount"),
        _container("obj-1", "p synth", _inner([_pdial("obj-3", "Pitch Env Amount",
                                                      parameter_shortname="Amount")])),
    ])
    hits = _rules(_m4l(d), "shortname_unique")
    assert len(hits) == 1 and hits[0].severity == "warning" and hits[0].path == ""
    assert "'obj-3' and 'obj-1/obj-3'" in hits[0].finding


def test_shortname_unique_distinct():
    d = _patch([_plugout(), _pdial("obj-3", "A", parameter_shortname="Amount"),
                _pdial("obj-4", "B", parameter_shortname="Amount2")])
    assert not _rules(_m4l(d), "shortname_unique")


def _banks(*slots):
    return {"parameterbanks": {"0": {"index": 0, "name": "Main",
                                     "parameters": list(slots) + ["-"] * (8 - len(slots))}}}


def test_bank_refs():
    d = _patch([_plugout(), _pdial("obj-3", "Cutoff")], parameters=_banks("Cutoff", "Ghost"))
    hits = _rules(_m4l(d), "bank_refs")
    assert len(hits) == 1 and hits[0].severity == "warning" and "Ghost" in hits[0].finding
    assert "Cutoff" not in hits[0].finding
    ok = _patch([_plugout(), _pdial("obj-3", "Cutoff")], parameters=_banks("Cutoff"))
    assert not _rules(_m4l(ok), "bank_refs")
    for junk in ({"parameterbanks": 5}, {"parameterbanks": {"0": 3}},
                 {"parameterbanks": {"0": {"parameters": "Ghost"}}}, 7):
        assert not _rules(_m4l(_patch([_plugout(), _pdial("obj-3")], parameters=junk)), "bank_refs")


def test_device_height():
    def dev(openinp, y, h=48.0):
        dial = _pdial("obj-3")
        dial["box"]["presentation"] = 1
        dial["box"]["presentation_rect"] = [8.0, y, 44.0, h]
        return _patch([_plugout(), dial], openinpresentation=openinp)
    hits = _rules(_m4l(dev(1, 150.0)), "device_height")
    assert len(hits) == 1 and hits[0].severity == "warning" and hits[0].box_ids == ("obj-3",)
    assert not _rules(_m4l(dev(1, 121.0)), "device_height")
    assert not _rules(_m4l(dev(0, 150.0)), "device_height")


# --- nested parity for the per-scope rules ------------------------------------------


_PER_SCOPE = {
    "stereo_out": ("instrument", lambda: ([_osc(), _plugout()], [_line("obj-80", 0, "obj-90", 0)])),
    "midi_passthrough": ("midi_effect", lambda: ([_midiin()], [])),
    "shortname_length": ("instrument",
                         lambda: ([_pdial("obj-3", parameter_shortname="Frequency")], [])),
    "int_param_range": ("instrument", lambda: ([_pdial("obj-3", parameter_type=1, parameter_mmin=0,
                                                       parameter_mmax=1000)], [])),
    "param_range": ("instrument", lambda: ([_pdial("obj-3", parameter_mmin=5, parameter_mmax=1)], [])),
}


@pytest.mark.parametrize("rule", sorted(_PER_SCOPE))
def test_per_scope_rule_nested_parity(rule):
    kind, content = _PER_SCOPE[rule]
    boxes, lines = content()
    marker = [_box("obj-99", "live.thisdevice", 1, 3, outlettype=["bang", "int", "int"])]
    top = _rules(review_m4l(_patch(marker + boxes, lines), device_type=kind), rule)
    assert top and all(r.path == "" for r in top)
    boxes, lines = content()
    nested_d = _patch(marker + [_container("obj-1", "p synth", _inner(boxes, lines))])
    nested = [r for r in _rules(review_m4l(nested_d, device_type=kind), rule) if r.path == "obj-1"]
    assert [(r.severity, r.finding, r.suggestion, r.path) for r in nested] == [
        (r.severity, "[p synth] " + r.finding, r.suggestion, "obj-1") for r in top
    ]


# --- builder cleanliness and junk safety ---------------------------------------------


def _nine_params():
    return _mixed_params() + [
        _spec("amp", 0.0, 1.0, 0.5, param_connect="synth::amp"),
        _spec("Filter Envelope Amount", 0.0, 1.0, 0.0),
        _spec("Pitch Envelope Amount", 0.0, 1.0, 0.0),
        _spec("Delay Time", 0, 5000, 100),
        _spec("transpose", -24, 24, 0),
    ]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("params", ["none", "nine"])
def test_builder_output_has_no_q40_findings(kind, params):
    from src.maxpat.critics.m4l_critic import detect_m4l_device_type

    p, _ = _build(kind, _nine_params() if params == "nine" else None)
    d = p.to_dict()
    results = review_m4l(d, device_type=detect_m4l_device_type(d))
    assert not [r for r in results if r.rule in Q40_RULES], [r.finding for r in results]


def test_gen_synth_output_has_no_q40_findings():
    p = Patcher()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        p.add_m4l_gen_synth([("freq", 20.0, 2000.0), ("amp", 0.0, 1.0), ("cutoff", 20.0, 20000.0)])
    results = review_m4l(p.to_dict(), device_type="instrument")
    assert not [r for r in results if r.rule in Q40_RULES]


def test_junk_never_raises():
    junk = _inner(
        [
            "junk", None, {"box": "x"},
            {"box": {"id": "obj-5", "maxclass": "live.dial", "parameter_enable": 1,
                     "saved_attribute_attributes": {"valueof": 3}}},
            {"box": {"id": "obj-6", "maxclass": "live.dial", "parameter_enable": 1,
                     "saved_attribute_attributes": {"valueof": {
                         "parameter_shortname": 7, "parameter_type": "1", "parameter_mmin": None,
                         "parameter_mmax": [1], "parameter_initial": ["a"]}}}},
            {"box": {"id": "obj-7", "maxclass": "newobj", "text": "plugout~", "numinlets": "2",
                     "presentation": 1, "presentation_rect": ["a", 1, 2]}},
            {"box": {"id": "obj-8", "maxclass": "newobj", "text": "midiin"}},
        ],
        ["junk", {"patchline": {"source": ["obj-8", 0], "destination": ["obj-7", "0"]}}],
    )
    d = _patch([_plugout(), _container("obj-1", "p junk", junk)],
               parameters={"parameterbanks": {"0": {"parameters": [None, 3, "-"]}, "1": "x"}},
               openinpresentation=1)
    for kind in KINDS:
        review_m4l(d, device_type=kind)
    d2 = _patch(junk["boxes"], junk["lines"], parameters=[1], openinpresentation="yes")
    for kind in KINDS:
        review_m4l(d2, device_type=kind)
