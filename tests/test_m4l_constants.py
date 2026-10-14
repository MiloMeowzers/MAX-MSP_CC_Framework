"""Smoke tests for src/maxpat/m4l_constants.py enums and AMXD format constants."""

import struct
import xml.etree.ElementTree as ET
from enum import IntEnum

import pytest

from src.maxpat.m4l_constants import (
    AMXD_HEADER_FORMAT,
    AMXD_HEADER_SIZE,
    AMXD_MAGIC,
    AMXD_TYPE_AUDIO_EFFECT,
    AMXD_TYPE_INSTRUMENT,
    AMXD_TYPE_MIDI_EFFECT,
    ModMode,
    ParamType,
    ParamVisibility,
    UnitStyle,
)


class TestEnums:
    def test_all_are_int_enums(self):
        for enum_cls in (ParamType, UnitStyle, ModMode, ParamVisibility):
            assert issubclass(enum_cls, IntEnum), enum_cls.__name__

    def test_param_type_members(self):
        # Order in docs/refpages/m4l-ref/parameters.maxref.xml (Max 9.2.0):
        # Float, Int, Enum, Blob. kicksynth-m4l.maxpat at 408cdf8 saves its
        # 0-1 / 50-1000 Hz float dials as type 0 (review D1).
        assert ParamType.FLOAT == 0
        assert ParamType.INT == 1
        assert ParamType.ENUM == 2
        assert ParamType.BLOB == 3

    def test_unit_style_representative_members(self):
        assert UnitStyle.INT == 0
        assert UnitStyle.HERTZ == 3
        assert UnitStyle.DECIBEL == 4
        assert UnitStyle.CUSTOM == 9

    def test_mod_mode_members(self):
        # parameters.maxref.xml order: None, Unipolar, Bipolar, Additive,
        # Absolute. kicksynth-m4l (408cdf8) dials save modmode 0 = None.
        assert ModMode.NONE == 0
        assert ModMode.UNIPOLAR == 1
        assert ModMode.BIPOLAR == 2
        assert ModMode.ADDITIVE == 3
        assert ModMode.ABSOLUTE == 4

    def test_param_visibility_members(self):
        assert ParamVisibility.AUTOMATED_AND_STORED == 0
        assert ParamVisibility.HIDDEN == 2


def _maxref_enum_items(entry, label_before_colon):
    """List items of a parameters.maxref.xml <description>, split on <br/>.

    The chunks are the description text and every <br/> tail. The list
    region starts at the first non-empty chunk after the "... are:" lead-in
    and ends at the next empty chunk (the blank <br/><br/> line).
    """
    desc = entry.find("description")
    chunks = [desc.text or ""] + [br.tail or "" for br in desc.findall("br")]
    items = []
    started = False
    for i, chunk in enumerate(chunks):
        text = " ".join(chunk.split())
        if i == 0:
            text = text.split("are:", 1)[1].strip() if "are:" in text else ""
        if not text:
            if started:
                break
            continue
        started = True
        items.append(text.split(":", 1)[0].strip() if label_before_colon
                     else text.split()[0])
    return items


@pytest.mark.requires_max
def test_enum_order_matches_parameters_maxref():
    """The enums are the 0-based positions of the bundle's documented lists."""
    from tests.conftest import MAX_APP_PATH

    path = (MAX_APP_PATH / "Contents" / "Resources" / "C74" / "docs"
            / "refpages" / "m4l-ref" / "parameters.maxref.xml")
    root = ET.parse(str(path)).getroot()
    entries = {e.get("anchor"): e for e in root.iter("entry")}

    types = _maxref_enum_items(entries["_parameter_type"], False)
    modes = _maxref_enum_items(entries["_parameter_modmode"], False)
    units = _maxref_enum_items(entries["_parameter_unitstyle"], True)

    assert types == ["Float", "Int", "Enum", "Blob"]
    assert modes == ["None", "Unipolar", "Bipolar", "Additive", "Absolute"]
    assert units[:10] == ["Int", "Float", "Time", "Hertz", "deciBel", "%",
                          "Pan", "Semitones", "MIDI", "Custom"]

    assert int(ParamType.FLOAT) == types.index("Float") == 0
    assert int(ParamType.INT) == types.index("Int") == 1
    assert int(ParamType.ENUM) == types.index("Enum") == 2
    assert int(ParamType.BLOB) == types.index("Blob") == 3

    assert int(ModMode.NONE) == modes.index("None") == 0
    assert int(ModMode.UNIPOLAR) == modes.index("Unipolar") == 1
    assert int(ModMode.BIPOLAR) == modes.index("Bipolar") == 2
    assert int(ModMode.ADDITIVE) == modes.index("Additive") == 3
    assert int(ModMode.ABSOLUTE) == modes.index("Absolute") == 4

    assert int(UnitStyle.INT) == units.index("Int") == 0
    assert int(UnitStyle.FLOAT) == units.index("Float") == 1
    assert int(UnitStyle.TIME) == units.index("Time") == 2
    assert int(UnitStyle.HERTZ) == units.index("Hertz") == 3
    assert int(UnitStyle.DECIBEL) == units.index("deciBel") == 4
    assert int(UnitStyle.PERCENT) == units.index("%") == 5
    assert int(UnitStyle.PAN) == units.index("Pan") == 6
    assert int(UnitStyle.SEMITONES) == units.index("Semitones") == 7
    assert int(UnitStyle.MIDI) == units.index("MIDI") == 8
    assert int(UnitStyle.CUSTOM) == units.index("Custom") == 9


class TestAmxdFormat:
    def test_header_format_packs_to_declared_size(self):
        assert struct.calcsize(AMXD_HEADER_FORMAT) == AMXD_HEADER_SIZE == 32

    def test_magic_bytes(self):
        assert AMXD_MAGIC == b"ampf"

    def test_device_type_markers_distinct_4_byte_values(self):
        markers = {AMXD_TYPE_AUDIO_EFFECT, AMXD_TYPE_INSTRUMENT,
                   AMXD_TYPE_MIDI_EFFECT}
        assert len(markers) == 3
        for marker in markers:
            assert isinstance(marker, bytes)
            assert len(marker) == 4
