"""Direct tests for src/maxpat/maxclass_map.py.

Pins the CLAUDE.md rule that UI_MAXCLASSES (not the database's maxclass
field) is the authoritative source for which objects use their own name
as maxclass vs. "newobj" with the name in the text field.
"""

from src.maxpat.maxclass_map import UI_MAXCLASSES, is_ui_object, resolve_maxclass
from src.maxpat.patcher import Patcher

# Representative UI widgets that must resolve to their own name
UI_OBJECTS = [
    "toggle", "dial", "flonum", "multislider", "meter~", "gain~",
    "ezdac~", "live.dial", "comment", "message", "inlet", "outlet",
    # Jitter pair added by fc3aa27 (shipped with no test coverage)
    "jit.pwindow", "jit.cellblock",
    # gen~/RNBO embedded code editor, added for SF-03
    "codebox",
]

# Representative non-UI objects that must resolve to "newobj"
NEWOBJ_OBJECTS = [
    "cycle~", "pack", "route", "expr", "gen~", "click~", "trigger",
]


class TestResolveMaxclass:
    """resolve_maxclass() both branches."""

    def test_ui_objects_resolve_to_own_name(self):
        for name in UI_OBJECTS:
            assert resolve_maxclass(name) == name, name

    def test_non_ui_objects_resolve_to_newobj(self):
        for name in NEWOBJ_OBJECTS:
            assert resolve_maxclass(name) == "newobj", name


class TestIsUiObject:
    """is_ui_object() mirrors UI_MAXCLASSES membership."""

    def test_true_for_ui_widgets(self):
        for name in UI_OBJECTS:
            assert is_ui_object(name) is True, name

    def test_false_for_newobj_objects(self):
        for name in NEWOBJ_OBJECTS:
            assert is_ui_object(name) is False, name

    def test_mirrors_set_membership(self):
        assert is_ui_object("toggle") == ("toggle" in UI_MAXCLASSES)
        assert is_ui_object("cycle~") == ("cycle~" in UI_MAXCLASSES)


class TestUIMaxclassesInvariants:
    """Structural invariants of the UI_MAXCLASSES constant."""

    def test_is_frozenset(self):
        assert isinstance(UI_MAXCLASSES, frozenset)

    def test_newobj_not_a_member(self):
        assert "newobj" not in UI_MAXCLASSES

    def test_entries_are_clean_lowercase_strings(self):
        for entry in UI_MAXCLASSES:
            assert isinstance(entry, str)
            assert entry, "empty entry in UI_MAXCLASSES"
            assert entry == entry.strip(), f"whitespace in entry: {entry!r}"
            assert entry == entry.lower(), f"non-lowercase entry: {entry!r}"


class TestCommittedPatchProvenance:
    """Entries admitted on committed-patch evidence, with that evidence named.

    UI_MAXCLASSES entries are normally derived from 02-RESEARCH.md Pattern 7.
    These entries were instead admitted because a committed patch that MAX
    itself wrote carries the object's own name in the maxclass field. The
    discriminator is ``patcher.appversion.revision``: this repo's generator
    hardcodes ``0`` (src/maxpat/defaults.py), so a non-zero revision means
    MAX wrote or re-saved the file. Each claim below names the confirming
    patch, its appversion, and the commit that introduced it, so a future
    audit can re-derive the claim without re-running the investigation.
    """

    def test_codebox_is_a_ui_maxclass(self):
        """SF-03: ``codebox`` carries its own maxclass in the MAX-saved form.

        Confirming evidence (review finding SF-03, quick task 260921-ima):

        - ``patches/kicksynth/generated/kicksynth.maxpat`` at commit
          ``02c9917`` ("MAX-side envelope + preset edits"),
          ``appversion`` 9.1.5 (revision 5, therefore MAX-written).
          Inside its gen~ patcher the codebox box is
          ``{"maxclass": "codebox", ...}`` with **no** ``text`` field,
          while its ``in 1`` / ``out 1`` siblings in the same patcher use
          ``maxclass: "newobj"`` with the name in ``text``.
        - ``patches/terrain-synth/generated/terrain-synth.maxpat`` at commit
          ``55757e0`` ("MAX re-save of v0.9.0"), ``appversion`` 9.1.5,
          carries four codebox boxes in the same form.

        19 of the 26 committed codebox-bearing ``.maxpat`` files satisfy the
        non-zero-revision discriminator; all 26 agree on the form.
        """
        assert resolve_maxclass("codebox") == "codebox"
        assert is_ui_object("codebox") is True
        assert "codebox" in UI_MAXCLASSES

    def test_jitter_pair_is_a_ui_maxclass(self):
        """The ``fc3aa27`` pair, which shipped with no test at all.

        ``fc3aa27`` ("fix(maxclass): jit.pwindow / jit.cellblock are UI
        maxclasses (MAX re-save form); terrain-synth window rect restored")
        added both entries to ``UI_MAXCLASSES`` and nothing else -- no test
        and no recorded provenance, which is the same gap that let SF-03
        stay open. Confirming evidence is the terrain-synth v0.3-v0.4 MAX
        re-saves cited in the source comment (e.g. commit ``174840c``,
        "user's MAX re-save, v0.4.1 confirmed working").
        """
        for name in ("jit.pwindow", "jit.cellblock"):
            assert resolve_maxclass(name) == name, name
            assert is_ui_object(name) is True, name
            assert name in UI_MAXCLASSES, name

    def test_gen_container_still_resolves_to_newobj(self):
        """The codebox entry must not perturb its gen~ container.

        A codebox only ever appears inside a gen~/rnbo~ embedded patcher.
        ``gen~`` itself is a newobj and is pinned by
        tests/test_codegen.py::test_gen_box_is_newobj; assert it here too so
        a future UI_MAXCLASSES edit that overreaches fails in this file.
        """
        assert resolve_maxclass("gen~") == "newobj"
        assert is_ui_object("gen~") is False
        assert resolve_maxclass("rnbo~") == "newobj"


class TestPatcherConsistency:
    """Patcher.add_box honors UI_MAXCLASSES for maxclass resolution."""

    def test_ui_object_uses_own_maxclass(self):
        """A UI widget box serializes with maxclass == its own name."""
        p = Patcher()
        box = p.add_box("toggle")
        assert box.maxclass == "toggle"
        d = box.to_dict()["box"]
        assert d["maxclass"] == "toggle"
        # UI widgets carry no object-name text field
        assert "text" not in d

    def test_non_ui_object_uses_newobj_with_text(self):
        """A non-UI object serializes as newobj with the name in text."""
        p = Patcher()
        box = p.add_box("cycle~", args=["440"])
        assert box.maxclass == "newobj"
        d = box.to_dict()["box"]
        assert d["maxclass"] == "newobj"
        assert d["text"].split()[0] == "cycle~"


# ---------------------------------------------------------------------------
# Review C4 / fix-plan Q13: non-UI live.* objects and patcher are newobj
# ---------------------------------------------------------------------------

import copy  # noqa: E402
import json  # noqa: E402
import warnings  # noqa: E402

import pytest  # noqa: E402

from src.maxpat.db_lookup import ObjectDatabase  # noqa: E402
from src.maxpat.sizing import UI_SIZES, calculate_box_size  # noqa: E402
from src.maxpat.validation import (  # noqa: E402
    _validate_maxclass_usage,
    has_blocking_errors,
    validate_patch,
)

# Max 9.2.0 saves each of these only as newobj with the name in ``text``
# (never as its own maxclass in 3,139 bundle .maxpat/.maxhelp files).
REMOVED_NON_UI = [
    "live.observer", "live.thisdevice", "live.path", "live.object",
    "live.map", "live.routing", "live.push",
    "live.miditool.in", "live.miditool.out",
    "live.remote~", "live.param~", "live.modulate~",
    "live.banks", "live.colors",
    "patcher",
]
REMOVED_LIVE = [n for n in REMOVED_NON_UI if n.startswith("live.")]

# live.* widgets MAX does save with their own maxclass; they must stay.
LIVE_UI_WIDGETS = [
    "live.arrows", "live.button", "live.comment", "live.dial", "live.drop",
    "live.gain~", "live.grid", "live.line", "live.menu", "live.meter~",
    "live.numbox", "live.scope~", "live.slider", "live.step", "live.tab",
    "live.text", "live.toggle",
]


@pytest.fixture(scope="module")
def db():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ObjectDatabase()


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch):
    """Make sure no inherited git env var can redirect git to another repo."""
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)


def _box_dicts(p: Patcher) -> list[dict]:
    """Serialize through Patcher.to_dict() (never Box.to_dict())."""
    return [entry["box"] for entry in p.to_dict()["patcher"]["boxes"]]


def _own_maxclass_patch() -> dict:
    """A hand-written patch carrying own-maxclass live.thisdevice / patcher boxes.

    midiin -> midiout (built through the API) makes it a valid MIDI-effect
    shape, so the M4L critic adds no blocker of its own.
    """
    p = Patcher()
    mi = p.add_box("midiin", x=260, y=50)
    mo = p.add_box("midiout", x=260, y=100)
    p.add_connection(mi, 0, mo, 0)
    d = p.to_dict()
    d["patcher"]["boxes"].extend([
        {"box": {"id": "obj-90", "maxclass": "live.thisdevice",
                 "numinlets": 1, "numoutlets": 3,
                 "outlettype": ["", "", ""],
                 "patching_rect": [40.0, 50.0, 90.0, 22.0]}},
        {"box": {"id": "obj-91", "maxclass": "patcher",
                 "numinlets": 1, "numoutlets": 1, "outlettype": [""],
                 "patching_rect": [40.0, 100.0, 60.0, 22.0]}},
    ])
    return d


def _wrong_maxclass(results) -> list[str]:
    return [
        r.message for r in results
        if r.layer == "objects" and r.level == "error"
        and r.message.startswith("Wrong maxclass")
    ]


class TestNonUiNamesAreNewobj:
    """C4: the 14 non-UI live.* objects and ``patcher`` are not UI maxclasses."""

    @pytest.mark.parametrize("name", REMOVED_NON_UI)
    def test_removed_from_ui_set_and_sizes(self, name):
        assert name not in UI_MAXCLASSES
        assert name not in UI_SIZES
        assert resolve_maxclass(name) == "newobj"
        assert is_ui_object(name) is False

    def test_live_ui_widgets_kept(self):
        for name in LIVE_UI_WIDGETS:
            assert name in UI_MAXCLASSES, name

    def test_set_sizes(self):
        """90 -> 75 names after C4 (T1); 93 after the C5 additions (T3)."""
        assert len(UI_MAXCLASSES) == 75
        assert len(UI_SIZES) == 66

    @pytest.mark.parametrize("name", REMOVED_LIVE)
    def test_add_box_serializes_as_newobj_with_text(self, name, db):
        p = Patcher(db=db)
        p.add_box(name)
        box = _box_dicts(p)[0]
        assert box["maxclass"] == "newobj"
        assert box["text"] == name
        assert "fontname" in box and "fontsize" in box
        assert (box["numinlets"], box["numoutlets"]) == db.compute_io_counts(name, [])
        assert box["patching_rect"][2:] == list(calculate_box_size(name, "newobj"))

    def test_live_thisdevice_io(self, db):
        p = Patcher(db=db)
        p.add_box("live.thisdevice")
        box = _box_dicts(p)[0]
        assert (box["numinlets"], box["numoutlets"]) == (1, 3)


class TestMaxclassUsageCheck:
    """C4, validator half: own-maxclass live.*/patcher boxes are flagged."""

    def test_own_maxclass_boxes_flagged(self, db):
        results = validate_patch(_own_maxclass_patch(), db=db)
        wrong = _wrong_maxclass(results)
        assert len(wrong) == 2, wrong
        assert any("'live.thisdevice'" in m for m in wrong), wrong
        assert any("'patcher'" in m for m in wrong), wrong
        assert has_blocking_errors(results) is True

    def test_legitimate_boxes_not_flagged(self, db):
        d = Patcher().to_dict()
        d["patcher"]["boxes"] = [
            {"box": {"id": "obj-1", "maxclass": "newobj", "text": "p foo",
                     "numinlets": 0, "numoutlets": 0,
                     "patching_rect": [10.0, 10.0, 50.0, 22.0],
                     "patcher": copy.deepcopy(Patcher().to_dict()["patcher"])}},
            {"box": {"id": "obj-2", "maxclass": "bpatcher",
                     "numinlets": 0, "numoutlets": 0,
                     "patching_rect": [10.0, 50.0, 200.0, 100.0]}},
            {"box": {"id": "obj-3", "maxclass": "inlet", "numinlets": 0,
                     "numoutlets": 1, "outlettype": [""],
                     "patching_rect": [300.0, 10.0, 30.0, 30.0]}},
            {"box": {"id": "obj-4", "maxclass": "outlet", "numinlets": 1,
                     "numoutlets": 0,
                     "patching_rect": [300.0, 200.0, 30.0, 30.0]}},
            {"box": {"id": "obj-5", "maxclass": "toggle", "numinlets": 1,
                     "numoutlets": 1, "outlettype": ["int"],
                     "patching_rect": [400.0, 10.0, 24.0, 24.0]}},
        ]
        assert _validate_maxclass_usage(d) == []
        assert _wrong_maxclass(validate_patch(d, db=db)) == []


class TestSaveGateEndToEnd:
    """Tracer: generated live.thisdevice saves; own-maxclass forms are refused."""

    def test_generated_live_thisdevice_saves(self, tmp_path, db):
        from src.maxpat.hooks import save_patch_roundtrip

        p = Patcher(db=db)
        td = p.add_box("live.thisdevice", x=40, y=50)
        pr = p.add_box("print", ["thisdevice"], x=40, y=100)
        p.add_connection(td, 0, pr, 0)
        mi = p.add_box("midiin", x=260, y=50)
        mo = p.add_box("midiout", x=260, y=100)
        p.add_connection(mi, 0, mo, 0)
        target = tmp_path / "ok.maxpat"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            save_patch_roundtrip(p.to_dict(), target)
        assert target.exists()
        saved = json.loads(target.read_text(encoding="utf-8"))
        boxes = [b["box"] for b in saved["patcher"]["boxes"]
                 if b["box"].get("text") == "live.thisdevice"]
        assert len(boxes) == 1
        assert boxes[0]["maxclass"] == "newobj"

    def test_own_maxclass_form_refused(self, tmp_path):
        from src.maxpat.hooks import PatchValidationError, save_patch_roundtrip

        target = tmp_path / "bad.maxpat"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with pytest.raises(PatchValidationError) as exc:
                save_patch_roundtrip(_own_maxclass_patch(), target)
        texts = [
            str(getattr(f, "message", None) or getattr(f, "finding", "") or f)
            for f in exc.value.findings
        ]
        assert any("Wrong maxclass" in t and "live.thisdevice" in t
                   for t in texts), texts
        assert not target.exists()
