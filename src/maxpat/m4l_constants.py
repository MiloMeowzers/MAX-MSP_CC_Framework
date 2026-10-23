"""M4L constants for parameter types, unit styles, modulation modes, and AMXD format.

Pure data module -- IntEnum classes and named constants only.
Imported by scaffold (Phase 21), critic (Phase 22) and the Q40 device
builder / .amxd codec (src/maxpat/m4l_device.py).

Evidence for the parameter enums (review D1, Q15):
  - The list order in the bundle's ``docs/refpages/m4l-ref/parameters.maxref.xml``
    (Max 9.2.0): Type = Float, Int, Enum, Blob; Clip Modulation Mode = None,
    Unipolar, Bipolar, Additive, Absolute; Unit Style = Int, Float, Time,
    Hertz, deciBel, %, Pan, Semitones, MIDI, Custom, Native. Each value is the
    0-based position in that list. ``tests/test_m4l_constants.py``
    (``requires_max``) parses the refpage and pins every member.
  - kicksynth-m4l.maxpat at commit 408cdf8 (saved by MAX): its 23 float
    live.dials store ``parameter_type`` 0 and ``parameter_modmode`` 0, and
    its live.tab stores ``parameter_type`` 2.
Earlier values had INT and FLOAT swapped and ModMode off by one (no None),
so Float dials were written as Int and Absolute as Additive.
"""

from enum import IntEnum


class ParamType(IntEnum):
    """parameter_type values in saved_attribute_attributes.valueof.

    Controls how Ableton treats the parameter value. Order is the
    parameters.maxref.xml "Type" list (Float, Int, Enum, Blob); float dials
    in kicksynth-m4l (408cdf8) are type 0 and its live.tab is type 2.
    """
    FLOAT = 0      # Floating point (Live's native representation)
    INT = 1        # Integer values (256 values, 0-255 range default)
    ENUM = 2       # Enumerated list of items
    BLOB = 3       # Non-automatable, preset storage only


class UnitStyle(IntEnum):
    """parameter_unitstyle values -- controls display format in Ableton.

    Determines the unit label shown in automation lanes and device UI.
    Order is the parameters.maxref.xml "Unit Style" list (Int, Float, Time,
    Hertz, deciBel, %, Pan, Semitones, MIDI, Custom, Native); Native (10) is
    not modelled because nothing writes it.
    """
    INT = 0        # Integer display
    FLOAT = 1      # Float display
    TIME = 2       # Milliseconds (ms)
    HERTZ = 3      # Frequency (Hz)
    DECIBEL = 4    # Decibels (dB)
    PERCENT = 5    # Percentage (%)
    PAN = 6        # Left/Right pan
    SEMITONES = 7  # Semitones for tuning
    MIDI = 8       # MIDI note numbers (0-127)
    CUSTOM = 9     # User-definable label


class ModMode(IntEnum):
    """parameter_modmode values -- Clip Modulation Mode in Ableton.

    Controls how clip envelopes modulate the parameter. Order is the
    parameters.maxref.xml "Clip Modulation Mode" list (None, Unipolar,
    Bipolar, Additive, Absolute); kicksynth-m4l (408cdf8) dials store 0.
    ``parameter_modrange`` is used only with ABSOLUTE.
    """
    NONE = 0       # No clip modulation
    UNIPOLAR = 1   # Modulation between min and current value
    BIPOLAR = 2    # Modulation range = 2x distance to nearest boundary
    ADDITIVE = 3   # +/- half of total range
    ABSOLUTE = 4   # Current value as upper/lower bound (uses modrange)


class ParamVisibility(IntEnum):
    """parameter_visibility values.

    Controls whether the parameter appears in Ableton's automation system.
    """
    AUTOMATED_AND_STORED = 0  # Stored in Live Set/presets, available for automation
    STORED_ONLY = 1           # Stored but not visible to automation system
    HIDDEN = 2                # Neither stored nor automatable


# -----------------------------------------------------------------------
# AMXD Binary Format Constants
# -----------------------------------------------------------------------
# An .amxd file is a chunk stream: ``[4-byte tag][uint32 LE length][payload]``
# repeated, with nothing after the last chunk (quick 261022-pqu, Q40; survey
# of 309 real files: Live 12/11 bundles, Max.app fourin_fourout.amxd, user
# devices, and the framework's own kicksynth-m4l.amxd that Live 12.3.6 loaded).
# An editable device holds three chunks:
#   ampf  length 4   payload = device kind code (aaaa / iiii / mmmm)
#   meta  length 4   payload = uint32 LE flags: 0 for every editable
#                    Max-written device (all Live 12 templates); 1, 4 or 7
#                    seen in Max 8 saves and frozen files. Optional (a few
#                    files go straight from ampf to ptch).
#   ptch  length N   payload = UTF-8 patcher JSON; Max ends it with "\n\0"
#                    (counted in N). A frozen device's ptch starts "mx@c"
#                    and an encrypted one has a "ciph" chunk before ptch.
#
# So AMXD_VERSION and AMXD_META_VERSION are really the ampf and meta chunk
# LENGTHS (both 4), and the 4 zero bytes at offset 20 are the meta PAYLOAD.
# The names are kept (tests/test_m4l_constants.py pins them).
#
# Header bytes of an editable device (32 bytes):
#   Offset  Len  Content
#   0       4    b"ampf"          (chunk tag)
#   4       4    uint32 LE = 4    (ampf chunk length; AMXD_VERSION)
#   8       4    device type      (aaaa/iiii/mmmm; the ampf payload)
#   12      4    b"meta"          (chunk tag)
#   16      4    uint32 LE = 4    (meta chunk length; AMXD_META_VERSION)
#   20      4    uint32 LE = 0    (meta payload: flags)
#   24      4    b"ptch"          (chunk tag)
#   28      4    uint32 LE        (ptch payload length N; file size = 32 + N)
#
# AMXD_HEADER_FORMAT is for WRITING only: its ``4x`` discards the meta
# payload and it cannot describe a file without a meta chunk. Parse chunk by
# chunk with AMXD_CHUNK_HEADER (src/maxpat/m4l_device.py parse_amxd).

AMXD_MAGIC = b"ampf"
AMXD_VERSION = 4
AMXD_META_MARKER = b"meta"
AMXD_META_VERSION = 4
AMXD_PATCH_MARKER = b"ptch"

AMXD_TYPE_AUDIO_EFFECT = b"aaaa"
AMXD_TYPE_INSTRUMENT = b"iiii"
AMXD_TYPE_MIDI_EFFECT = b"mmmm"

# struct format string for packing the 32-byte header
# < = little-endian, 4s = 4-char bytes, I = uint32, 4x = 4 zero bytes
AMXD_HEADER_FORMAT = "<4sI4s4sI4x4sI"
AMXD_HEADER_SIZE = 32

# One chunk header: 4-byte tag + uint32 LE payload length (Q40).
AMXD_CHUNK_HEADER = "<4sI"

# Max ends every ptch JSON payload with a newline and a NUL byte (26 of 26
# Max-written JSON payloads in the survey); export_amxd writes the same.
AMXD_PAYLOAD_TERMINATOR = b"\n\x00"
