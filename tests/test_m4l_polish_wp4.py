"""ensure_m4l_prefixes rewrites `set <name>` only where it renames something (quick 261022-ud6 WP4, review IN-05).

A `set <name>` message segment is a handled (rewritable) position only when
the message box cords into a declarer (send/receive/value/pv/coll/dict/
buffer~ ...), a buffer user (play~/groove~/...) or a waveform~ -- the
objects whose `set` changes the name they refer to. Anywhere else (a
message box display, umenu, prepend, or no cord at all) the name is plain
text, so it counts as a reference and makes the name report-only.
"""

from __future__ import annotations

import warnings

from src.maxpat.m4l_polish import ensure_m4l_prefixes, plan_m4l_prefixes


def _nb(box_id, text):
    return {"id": box_id, "maxclass": "newobj", "text": text,
            "numinlets": 1, "numoutlets": 1, "outlettype": [""]}


def _msg(box_id, text):
    return {"id": box_id, "maxclass": "message", "text": text,
            "numinlets": 2, "numoutlets": 1, "outlettype": [""]}


def _line(src, dst, inlet=0):
    return {"patchline": {"source": [src, 0], "destination": [dst, inlet]}}


def _patch(boxes, lines=()):
    return {"patcher": {"boxes": [{"box": b} for b in boxes], "lines": list(lines)}}


def _texts(patch):
    return [e["box"].get("text") for e in patch["patcher"]["boxes"]]


def _run(patch):
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        ensure_m4l_prefixes(patch)
    return [str(w.message) for w in rec]


def test_set_into_a_display_is_not_rewritten_and_blocks_the_name():
    """The review repro: `set state, bang` beside `pv state`, feeding a message box."""
    patch = _patch(
        [_nb("obj-1", "pv state"), _msg("obj-2", "set state, bang"), _msg("obj-3", "")],
        [_line("obj-2", "obj-3")],
    )
    plan = plan_m4l_prefixes(patch)
    assert "state" in plan["report_only"] and plan["rename"] == []
    warned = _run(patch)
    assert _texts(patch) == ["pv state", "set state, bang", ""]
    assert any("state" in w for w in warned)


def test_unconnected_set_message_is_a_reference():
    patch = _patch([_nb("obj-1", "send level"), _nb("obj-2", "r level"), _msg("obj-3", "set level")])
    _run(patch)
    assert _texts(patch) == ["send level", "r level", "set level"]


def test_set_into_a_buffer_user_is_rewritten():
    patch = _patch(
        [_nb("obj-1", "buffer~ grains"), _nb("obj-2", "groove~ grains 2"),
         _msg("obj-3", "set grains, bang")],
        [_line("obj-3", "obj-2")],
    )
    _run(patch)
    assert _texts(patch) == ["buffer~ ---grains", "groove~ ---grains 2", "set ---grains, bang"]


def test_set_into_a_send_is_rewritten():
    patch = _patch(
        [_nb("obj-1", "s level"), _nb("obj-2", "r level"), _msg("obj-3", "set level")],
        [_line("obj-3", "obj-1")],
    )
    _run(patch)
    assert _texts(patch) == ["s ---level", "r ---level", "set ---level"]


def test_set_into_a_waveform_is_rewritten():
    wf = {"id": "obj-3", "maxclass": "waveform~", "buffername": "grains",
          "numinlets": 5, "numoutlets": 6}
    patch = _patch(
        [_nb("obj-1", "buffer~ grains"), _msg("obj-2", "set grains"), wf],
        [_line("obj-2", "obj-3")],
    )
    _run(patch)
    assert _texts(patch)[:2] == ["buffer~ ---grains", "set ---grains"]
    assert patch["patcher"]["boxes"][2]["box"]["buffername"] == "---grains"


def test_feeder_in_a_subpatcher_is_scoped_to_its_patcher():
    inner = {"boxes": [{"box": _msg("obj-1", "set grains")}, {"box": _nb("obj-2", "play~ grains")}],
             "lines": [_line("obj-1", "obj-2")]}
    sub = {"id": "obj-9", "maxclass": "newobj", "text": "p player", "numinlets": 0,
           "numoutlets": 0, "outlettype": [], "patcher": inner}
    patch = _patch([_nb("obj-1", "buffer~ grains"), sub])
    _run(patch)
    inner_texts = [e["box"]["text"] for e in patch["patcher"]["boxes"][1]["box"]["patcher"]["boxes"]]
    assert _texts(patch)[0] == "buffer~ ---grains"
    assert inner_texts == ["set ---grains", "play~ ---grains"]
