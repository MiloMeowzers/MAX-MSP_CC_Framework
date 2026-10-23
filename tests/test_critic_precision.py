"""Q3 critic-precision regression tests (quick 261012-di7).

Covers `.planning/reviews/2026-10-11-fix-plan.md` Q3 and review findings:
  - E1: fan-out without trigger -- display-only sinks and preset membership
    outlets are skipped, signal-ness comes from outlettype (not the `~` name),
    trigger outlets are checked, and only reconvergent fan-out (two branches
    meeting one box at different inlets) is a blocker; everything else warns.
  - E4: Bach-llll -- command sources exempt, note severity.
  - E2: the control-rate-to-signal-rate check is removed (OQ2-A).
  - Comment `#N` (review §4.1 class 7 / §4.4 R3): comments fed by a
    `set ... #N` message box are not flagged.

Committed patches are opened read-only and every critic/validator call gets a
freshly loaded dict. No committed patch file is ever written.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from src.maxpat.critics.dsp_critic import review_dsp
from src.maxpat.critics.package_critic import review_packages
from src.maxpat.critics.structure_critic import review_structure
from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.validation import validate_patch
from tests.test_critics import _make_patch
from tests.test_validation import _make_box, _make_line, _make_patch_dict

_REPO_ROOT = Path(__file__).resolve().parent.parent

_FAN_PREFIX = "Fan-out without trigger"

# Fan-out finding-string format (moved verbatim from
# tests/test_integration_patches.py, whose allowlist now keys on the
# structured CriticResult fields; Q33):
#   "Fan-out without trigger: '<name>' (<source_id>) outlet <N> ..."
_FANOUT_RE = re.compile(
    r"Fan-out without trigger: '[^']*' \(([^)]+)\) outlet (\d+) "
    r"connected to \d+ destinations \((.*?)\) --"
)


@pytest.fixture(scope="module")
def db() -> ObjectDatabase:
    """Module-scoped ObjectDatabase (expensive to construct)."""
    return ObjectDatabase()


def _load(rel: str) -> dict:
    """Load a committed patch read-only (fresh dict on every call)."""
    with open(_REPO_ROOT / rel) as f:
        return json.load(f)


def _box(box_id, text="", maxclass="newobj", numinlets=1, numoutlets=1,
         outlettype=None, with_outlettype=True):
    box = {
        "id": box_id,
        "maxclass": maxclass,
        "text": text,
        "numinlets": numinlets,
        "numoutlets": numoutlets,
    }
    if with_outlettype:
        box["outlettype"] = outlettype if outlettype is not None else [""] * numoutlets
    return box


def _ln(src, outlet, dst, inlet):
    return {"source": [src, outlet], "destination": [dst, inlet]}


def _fan(results):
    """Fan-out findings, as (result, source_id, outlet)."""
    out = []
    for r in results:
        if r.finding.startswith(_FAN_PREFIX):
            m = _FANOUT_RE.search(r.finding)
            assert m, f"Fan-out finding breaks the prefix contract: {r.finding}"
            out.append((r, m.group(1), int(m.group(2))))
    return out


def _fan_for(results, src_id, outlet=None):
    return [
        r for r, sid, o in _fan(results)
        if sid == src_id and (outlet is None or o == outlet)
    ]


# Reusable boxes
def _number(box_id="obj-1"):
    return _box(box_id, maxclass="number", numinlets=1, numoutlets=2,
                outlettype=["", "bang"])


def _plus(box_id="obj-9"):
    return _box(box_id, text="+", numinlets=2, numoutlets=1, outlettype=["int"])


def _counter(box_id):
    return _box(box_id, text="counter 0 10", numinlets=5, numoutlets=4,
                outlettype=["", "", "", ""])


def _toggle(box_id):
    return _box(box_id, maxclass="toggle", numinlets=1, numoutlets=1,
                outlettype=["int"])


# ===========================================================================
# E1: fan-out unit fixtures
# ===========================================================================

class TestFanOutPrecision:

    def test_display_sink_flonum_skipped(self):
        """scale -> flonum (no outgoing cord) + send: no fan finding."""
        boxes = [
            _box("obj-1", text="scale 0 127 0. 1.", numinlets=6, numoutlets=1,
                 outlettype=[""]),
            _box("obj-2", maxclass="flonum", numinlets=1, numoutlets=2,
                 outlettype=["", "bang"]),
            _box("obj-3", text="s cutoff", numinlets=1, numoutlets=0,
                 outlettype=[]),
        ]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-1", 0, "obj-3", 0)]
        assert _fan(review_structure(_make_patch(boxes, lines))) == []

    def test_display_box_with_outgoing_cord_is_a_branch(self):
        """flonum that feeds *~ is a real branch: one fan warning."""
        boxes = [
            _box("obj-1", text="scale 0 127 0. 1.", numinlets=6, numoutlets=1,
                 outlettype=[""]),
            _box("obj-2", maxclass="flonum", numinlets=1, numoutlets=2,
                 outlettype=["", "bang"]),
            _box("obj-3", text="s cutoff", numinlets=1, numoutlets=0,
                 outlettype=[]),
            _box("obj-4", text="*~ 0.5", numinlets=2, numoutlets=1,
                 outlettype=["signal"]),
        ]
        lines = [
            _ln("obj-1", 0, "obj-2", 0),
            _ln("obj-1", 0, "obj-3", 0),
            _ln("obj-2", 0, "obj-4", 1),
        ]
        fans = _fan(review_structure(_make_patch(boxes, lines)))
        assert [r.severity for r, _, _ in fans] == ["warning"]

    def _preset_patch(self, outlet):
        boxes = [
            _box("obj-1", maxclass="preset", numinlets=1, numoutlets=5,
                 outlettype=["", "", "", "", ""]),
        ]
        lines = []
        for k in range(2):
            tid = f"obj-t{k}"
            boxes.append(_toggle(tid))
            lines.append(_ln("obj-1", outlet, tid, 0))
        return _make_patch(boxes, lines)

    def test_preset_membership_outlets_skipped(self):
        """preset outlets 0/2/4 are include/exclude/capture cords."""
        for outlet in (0, 2, 4):
            fans = _fan(review_structure(self._preset_patch(outlet)))
            assert fans == [], f"outlet {outlet}: {[r.finding for r, _, _ in fans]}"

    def test_preset_outlet1_still_checked(self):
        boxes = [
            _box("obj-1", maxclass="preset", numinlets=1, numoutlets=5,
                 outlettype=["", "", "", "", ""]),
            _counter("obj-2"),
            _toggle("obj-3"),
        ]
        lines = [_ln("obj-1", 1, "obj-2", 0), _ln("obj-1", 1, "obj-3", 0)]
        fans = _fan(review_structure(_make_patch(boxes, lines)))
        assert [r.severity for r, _, _ in fans] == ["warning"]

    def test_signal_outlettype_on_tildeless_name_skipped(self):
        """`p fx` with outlettype signal -> 2 *~: no fan finding."""
        boxes = [
            _box("obj-1", text="p fx", numinlets=1, numoutlets=1,
                 outlettype=["signal"]),
            _box("obj-2", text="*~ 0.5", numinlets=2, numoutlets=1,
                 outlettype=["signal"]),
            _box("obj-3", text="*~ 0.3", numinlets=2, numoutlets=1,
                 outlettype=["signal"]),
        ]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-1", 0, "obj-3", 0)]
        assert _fan(review_structure(_make_patch(boxes, lines))) == []

    def test_control_outlet_on_tilde_object_checked(self):
        """buffer~ outlet 1 (bang) -> 2 non-display boxes: fan finding."""
        boxes = [
            _box("obj-1", text="buffer~ snd", numinlets=1, numoutlets=2,
                 outlettype=["float", "bang"]),
            _counter("obj-2"),
            _toggle("obj-3"),
        ]
        lines = [_ln("obj-1", 1, "obj-2", 0), _ln("obj-1", 1, "obj-3", 0)]
        fans = _fan(review_structure(_make_patch(boxes, lines)))
        assert len(fans) == 1
        assert fans[0][1:] == ("obj-1", 1)

    def test_missing_outlettype_falls_back_to_tilde_name(self):
        boxes = [
            _box("obj-1", text="cycle~ 440", numinlets=2, numoutlets=1,
                 with_outlettype=False),
            _box("obj-2", text="*~ 0.5", numinlets=2, numoutlets=1,
                 outlettype=["signal"]),
            _box("obj-3", text="*~ 0.3", numinlets=2, numoutlets=1,
                 outlettype=["signal"]),
        ]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-1", 0, "obj-3", 0)]
        assert _fan(review_structure(_make_patch(boxes, lines))) == []

    def test_trigger_outlet_fan_out_warns(self):
        boxes = [
            _box("obj-1", text="t b b", numinlets=1, numoutlets=2,
                 outlettype=["bang", "bang"]),
            _counter("obj-2"),
            _toggle("obj-3"),
        ]
        lines = [_ln("obj-1", 0, "obj-2", 0), _ln("obj-1", 0, "obj-3", 0)]
        fans = _fan(review_structure(_make_patch(boxes, lines)))
        assert [r.severity for r, _, _ in fans] == ["warning"]

    def test_trigger_outlet_reconvergent_blocks(self):
        boxes = [
            _box("obj-1", text="t b b", numinlets=1, numoutlets=2,
                 outlettype=["bang", "bang"]),
            _plus("obj-9"),
        ]
        lines = [_ln("obj-1", 0, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)]
        fans = _fan(review_structure(_make_patch(boxes, lines)))
        assert [r.severity for r, _, _ in fans] == ["blocker"]

    def test_metro_counter_toggle_print_warns(self):
        from tests.test_critics import _fan_out_no_trigger_patch
        fans = _fan(review_structure(_fan_out_no_trigger_patch()))
        assert [r.severity for r, _, _ in fans] == ["warning"]

    def test_number_to_plus_both_inlets_blocks(self):
        boxes = [_number("obj-1"), _plus("obj-9")]
        lines = [_ln("obj-1", 0, "obj-9", 0), _ln("obj-1", 0, "obj-9", 1)]
        fans = _fan(review_structure(_make_patch(boxes, lines)))
        assert [r.severity for r, _, _ in fans] == ["blocker"]
        assert "'+' (obj-9)" in fans[0][0].finding.split("--", 1)[1]

    def test_two_hop_reconvergence_blocks(self):
        boxes = [
            _number("obj-1"),
            _box("obj-2", text="i", numinlets=2, numoutlets=1, outlettype=["int"]),
            _box("obj-3", maxclass="button", numinlets=1, numoutlets=1,
                 outlettype=["bang"]),
            _plus("obj-9"),
        ]
        lines = [
            _ln("obj-1", 0, "obj-2", 0),
            _ln("obj-1", 0, "obj-3", 0),
            _ln("obj-2", 0, "obj-9", 1),
            _ln("obj-3", 0, "obj-9", 0),
        ]
        fans = _fan_for(review_structure(_make_patch(boxes, lines)), "obj-1")
        assert [r.severity for r in fans] == ["blocker"]

    def test_same_inlet_meeting_warns(self):
        boxes = [
            _number("obj-1"),
            _box("obj-2", text="prepend a", numinlets=1, numoutlets=1),
            _box("obj-3", text="prepend b", numinlets=1, numoutlets=1),
            _box("obj-4", text="route a b", numinlets=1, numoutlets=3),
        ]
        lines = [
            _ln("obj-1", 0, "obj-2", 0),
            _ln("obj-1", 0, "obj-3", 0),
            _ln("obj-2", 0, "obj-4", 0),
            _ln("obj-3", 0, "obj-4", 0),
        ]
        fans = _fan_for(review_structure(_make_patch(boxes, lines)), "obj-1")
        assert [r.severity for r in fans] == ["warning"]

    def test_all_hot_meeting_warns(self):
        boxes = [
            _number("obj-1"),
            _box("obj-2", text="i", numinlets=2, numoutlets=1, outlettype=["int"]),
            _box("obj-5", text="js x.js", numinlets=2, numoutlets=1),
        ]
        lines = [
            _ln("obj-1", 0, "obj-5", 0),
            _ln("obj-1", 0, "obj-2", 0),
            _ln("obj-2", 0, "obj-5", 1),
        ]
        fans = _fan_for(review_structure(_make_patch(boxes, lines)), "obj-1")
        assert [r.severity for r in fans] == ["warning"]


# ===========================================================================
# E1: committed-patch repros (read-only)
# ===========================================================================

class TestFanOutCommittedPatches:

    def test_timestretch_preset_exclude_outlet(self):
        res = review_structure(_load("patches/timestretch/generated/timestretch.maxpat"))
        assert _fan_for(res, "obj-51", 2) == []

    def test_minitaur_zero_fan_blockers(self):
        res = review_structure(_load("patches/minitaur/generated/minitaur.maxpat"))
        blockers = [r for r, _, _ in _fan(res) if r.severity == "blocker"]
        assert blockers == [], [r.finding for r in blockers]

    def test_mixer_strip_plus_is_warning(self):
        res = review_structure(_load("patches/mixer/generated/mixer-strip.maxpat"))
        fans = _fan_for(res, "obj-14", 0)
        assert [r.severity for r in fans] == ["warning"]

    def test_slot_buffer_bang_does_not_reach_waveform_hot_and_cold(self):
        """``buffer~`` obj-1 outlet 1 feeds ``set #1`` -> waveform~ inlet 0 and
        ``setbuffer #1`` -> js obj-32, whose outputs enter the expr obj-150 only
        at its cold inlets 1/2 (the expr outputs when snapshot~ hits inlet 0).
        The bang never reaches waveform~ inlets 2/3, so the fan-out is a
        warning (quick 261022-ud6 CR-02; the Q3 allowlist entry was a false
        positive)."""
        res = review_structure(_load("patches/rhythmic-sampler/generated/slot.maxpat"))
        fans = _fan_for(res, "obj-1", 1)
        assert [r.severity for r in fans] == ["warning"]

    def test_calibration_shapes_are_warnings(self):
        cases = [
            ("patches/gong-model/generated/gong-model.maxpat", ["obj-335", "obj-349"]),
            ("patches/kicksynth/generated/kicksynth.maxpat", ["obj-129"]),
            ("patches/scala-synth/generated/scala-synth-voice.maxpat", ["obj-6"]),
            ("patches/scala-synth/generated/scala-synth.maxpat", ["obj-13", "obj-14"]),
        ]
        for rel, ids in cases:
            res = review_structure(_load(rel))
            for src_id in ids:
                fans = _fan_for(res, src_id)
                assert fans, f"{rel} {src_id}: expected a fan warning"
                assert all(r.severity == "warning" for r in fans), (
                    f"{rel} {src_id}: {[(r.severity, r.finding) for r in fans]}"
                )


# ===========================================================================
# E4: Bach-llll command sources
# ===========================================================================

def _llll(results):
    return [r for r in results if "llll" in r.finding.lower()]


_BACH_COMMAND_FIXTURES = [
    ("message", "addchord [ $1 [ $2 $3 $4 ] ]"),
    ("message", "domain $1 $2"),
    ("newobj", "receive roll-clear"),
    ("newobj", "r x"),
    ("attrui", ""),
    ("newobj", "loadmess 1"),
    ("newobj", "loadbang"),
    ("button", ""),
    ("newobj", "prepend addchord"),
]


class TestBachCommandSources:

    @pytest.mark.parametrize("dst", ["bach.roll", "bach.score"])
    @pytest.mark.parametrize(
        "maxclass,text", _BACH_COMMAND_FIXTURES,
        ids=[f"{m}:{t}" for m, t in _BACH_COMMAND_FIXTURES],
    )
    def test_command_source_exempt(self, db, maxclass, text, dst):
        boxes = [
            _box("obj-1", text=text, maxclass=maxclass, numinlets=1,
                 numoutlets=1),
            _box("obj-2", text=dst, numinlets=1, numoutlets=1),
        ]
        res = review_packages(_make_patch(boxes, [_ln("obj-1", 0, "obj-2", 0)]), db)
        assert _llll(res) == [], [(r.severity, r.finding) for r in res]

    def test_pack_into_bach_score_is_note(self, db):
        boxes = [
            _box("obj-1", text="pack 0 0", numinlets=2, numoutlets=1),
            _box("obj-2", text="bach.score", numinlets=1, numoutlets=1),
        ]
        res = _llll(review_packages(
            _make_patch(boxes, [_ln("obj-1", 0, "obj-2", 0)]), db))
        assert [r.severity for r in res] == ["note"]
        assert "bach.nth" in res[0].suggestion
        assert "list2llll" not in res[0].suggestion

    def test_physics_composition_command_sources(self, db):
        res = review_packages(
            _load("patches/physics-composition/generated/physics-composition.maxpat"),
            db,
        )
        hits = [
            r for r in _llll(res)
            if any(f"({i})" in r.finding for i in ("obj-107", "obj-109", "obj-73"))
        ]
        assert hits == [], [(r.severity, r.finding) for r in hits]


# ===========================================================================
# E2: control-rate-to-signal-rate check removed (OQ2-A)
# ===========================================================================

_CTRL_PREFIX = "Control-rate to signal-rate"


class TestControlToSignalRemoved:

    def _ctrl(self, results):
        return [r for r in results if r.finding.startswith(_CTRL_PREFIX)]

    def test_param_message_into_gen(self):
        boxes = [
            _box("obj-1", text="cutoff $1", maxclass="message", numinlets=2,
                 numoutlets=1),
            _box("obj-2", text="gen~", numinlets=1, numoutlets=1,
                 outlettype=["signal"]),
        ]
        res = review_dsp(_make_patch(boxes, [_ln("obj-1", 0, "obj-2", 0)]))
        assert self._ctrl(res) == []

    def test_number_into_sig(self):
        boxes = [
            _number("obj-1"),
            _box("obj-2", text="sig~", numinlets=1, numoutlets=1,
                 outlettype=["signal"]),
        ]
        res = review_dsp(_make_patch(boxes, [_ln("obj-1", 0, "obj-2", 0)]))
        assert self._ctrl(res) == []

    def test_number_into_times_tilde(self):
        boxes = [
            _number("obj-1"),
            _box("obj-2", text="*~ 1.", numinlets=2, numoutlets=1,
                 outlettype=["signal"]),
        ]
        res = review_dsp(_make_patch(boxes, [_ln("obj-1", 0, "obj-2", 0)]))
        assert self._ctrl(res) == []

    def test_corpus_has_no_control_rate_findings(self):
        hits = []
        for path in sorted(_REPO_ROOT.glob("patches/*/generated/*.maxpat")):
            rel = path.relative_to(_REPO_ROOT).as_posix()
            hits.extend((rel, r.finding) for r in self._ctrl(review_dsp(_load(rel))))
        assert hits == [], f"{len(hits)} control-rate finding(s), e.g. {hits[:3]}"


# ===========================================================================
# Comment #N: set-fed comments are not flagged
# ===========================================================================

_HASH_MSG = "Comment boxes don't support #N"


def _comment_hash_warnings(results):
    return [
        r for r in results
        if r.layer == "domain" and r.level == "warning" and _HASH_MSG in r.message
    ]


def _comment(box_id, text):
    return {"box": {"maxclass": "comment", "id": box_id, "text": text,
                    "numinlets": 1, "numoutlets": 0, "outlettype": [],
                    "patching_rect": [0, 40, 80, 22]}}


class TestCommentHashSetFed:

    def test_set_hash_message_feeds_comment(self, db):
        patch = _make_patch_dict(
            boxes=[
                _make_box("obj-1", maxclass="message", text="set Bus #1",
                          numinlets=2, numoutlets=1, outlettype=[""]),
                _comment("obj-2", "Bus #1"),
            ],
            lines=[_make_line("obj-1", 0, "obj-2", 0)],
        )
        assert _comment_hash_warnings(validate_patch(patch, db=db)) == []

    def test_set_without_hash_still_warns(self, db):
        patch = _make_patch_dict(
            boxes=[
                _make_box("obj-1", maxclass="message", text="set Label",
                          numinlets=2, numoutlets=1, outlettype=[""]),
                _comment("obj-2", "Label #1"),
            ],
            lines=[_make_line("obj-1", 0, "obj-2", 0)],
        )
        assert len(_comment_hash_warnings(validate_patch(patch, db=db))) == 1

    def test_unfed_comment_still_warns(self, db):
        patch = _make_patch_dict(boxes=[_comment("obj-1", "Freq: #1 Hz")])
        assert len(_comment_hash_warnings(validate_patch(patch, db=db))) == 1

    @pytest.mark.parametrize("rel,box_id", [
        ("patches/barnett-dbap/generated/dbap-motion.maxpat", "obj-3"),
        ("patches/barnett-dbap/generated/dbap-source.maxpat", "obj-1"),
        ("patches/mixer/generated/mixer-bus.maxpat", "obj-36"),
    ])
    def test_committed_set_fed_comments_clean(self, db, rel, box_id):
        res = validate_patch(copy.deepcopy(_load(rel)), db=db)
        hits = [r for r in _comment_hash_warnings(res) if f"({box_id})" in r.message]
        assert hits == []

    def test_committed_prose_comment_still_warns(self, db):
        rel = "patches/barnett-dbap/generated/barnett-dbap.maxpat"
        res = validate_patch(copy.deepcopy(_load(rel)), db=db)
        hits = [r for r in _comment_hash_warnings(res) if "(obj-27)" in r.message]
        assert len(hits) == 1
