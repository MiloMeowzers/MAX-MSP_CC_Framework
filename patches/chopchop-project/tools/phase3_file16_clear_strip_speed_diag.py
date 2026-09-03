"""v6_199 -- clear the K_1-K_7 strip for the diag, add SPD (karma speed) + RON.

Process: the diag boxes at x1008 collided with the DEBUG panel (diagpr_*).
The K_1..K_7 probe flonums occupy the genuinely-reserved x1130 strip (doc 19
A8: remove before ship). Remove them, move the diag strip there.

Data the user asked for:
 - SPD: snapshot~ 120 on obj-7's output in p Playback (the shared speed signal
   into all three karma~ speed inlets) -> s ---dbgSpeed -> flonum. If this is 0
   after Record, karma can't play regardless of the `play` message.
 - RON: r ---recordOn number -- should stay 0 during a handoff (proves the
   normal record chain isn't fighting).

Removed: obj-4311..4314, obj-4411..4413 and their sole feeders pollrecv_0..3 /
reprecv_0..2 (+ 7 lines). Diag stack -> x1130 y14..; labels x1195. Handoff
unchanged (v6_197 bare).

    python phase3_file16_clear_strip_speed_diag.py   # -> ../generated/ChopChop_v6_199.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

ORANGE = [1.0, 0.709803921568627, 0.196078431372549, 1.0]


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_198.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_199.amxd"

KILL = {"obj-4311", "obj-4312", "obj-4313", "obj-4314", "obj-4411", "obj-4412", "obj-4413",
        "pollrecv_0", "pollrecv_1", "pollrecv_2", "pollrecv_3", "reprecv_0", "reprecv_1", "reprecv_2"}

# id-stem -> (presentation y, float?)
ROWS = [("dg_ply", "PLY", 14.0, False), ("dg_frc", "FRC", 36.0, True),
        ("dg_hc", "HC", 58.0, False), ("dg_ful", "FUL", 80.0, False),
        ("dg_siz", "SIZ", 102.0, False), ("dg_cap", "CAP", 124.0, True),
        ("dg_hnd", "HND", 146.0, False), ("dg_spd", "SPD", 168.0, True),
        ("dg_ron", "RON", 190.0, False)]


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher

    root["boxes"] = [b for b in root["boxes"] if b.get("box", b)["id"] not in KILL]
    root["lines"] = [e for e in root["lines"]
                     if e.get("patchline", e)["source"][0] not in KILL
                     and e.get("patchline", e)["destination"][0] not in KILL]

    bx = {b.get("box", b)["id"]: b.get("box", b) for b in root["boxes"]}

    # move existing diag boxes to the freed strip
    for stem, lbl, py, is_float in ROWS:
        n = bx.get(stem + "_n")
        if n:
            n["presentation_rect"] = [1130.0, py, 62.0, 20.0]
        el = bx.get(stem + "_l")
        if el:
            el["presentation_rect"] = [1196.0, py + 3.0, 26.0, 15.0]

    # SPD: snapshot~ on the speed signal in p Playback
    pb = next(b.get("box", b) for b in root["boxes"] if b.get("box", b)["id"] == "obj-118")["patcher"]
    pb["boxes"] += [
        {"box": {"id": "sp_snap", "maxclass": "newobj", "text": "snapshot~ 120", "numinlets": 1,
                 "numoutlets": 1, "outlettype": ["float"], "patching_rect": [40.0, 900.0, 90.0, 20.0]}},
        {"box": {"id": "sp_send", "maxclass": "newobj", "text": "s ---dbgSpeed", "numinlets": 1,
                 "numoutlets": 0, "patching_rect": [140.0, 900.0, 100.0, 20.0]}},
    ]
    pb["lines"] += [Ln("obj-7", 0, "sp_snap", 0), Ln("sp_snap", 0, "sp_send", 0)]

    # SPD + RON diag boxes at root (new)
    def diagbox(stem, ch, py, is_float, px=2600.0):
        return [
            {"box": {"id": stem + "_r", "maxclass": "newobj", "text": "r " + ch, "numinlets": 0,
                     "numoutlets": 1, "outlettype": [""], "patching_rect": [px, 460.0 + py, 110.0, 20.0]}},
            {"box": {"id": stem + "_n", "maxclass": "flonum" if is_float else "number",
                     "numinlets": 1, "numoutlets": 2, "outlettype": ["", "bang"],
                     "patching_rect": [px + 120.0, 460.0 + py, 70.0, 20.0],
                     "presentation": 1, "presentation_rect": [1130.0, py, 62.0, 20.0]}},
            {"box": {"id": stem + "_l", "maxclass": "comment", "text": stem[-3:].upper(),
                     "numinlets": 1, "numoutlets": 0, "patching_rect": [px + 200.0, 460.0 + py, 40.0, 18.0],
                     "presentation": 1, "presentation_rect": [1196.0, py + 3.0, 26.0, 15.0],
                     "textcolor": ORANGE, "fontsize": 7.0}},
        ]
    root["boxes"] += diagbox("dg_spd", "---dbgSpeed", 168.0, True)
    root["boxes"] += diagbox("dg_ron", "---recordOn", 190.0, False)
    root["lines"] += [Ln("dg_spd_r", 0, "dg_spd_n", 0), Ln("dg_ron_r", 0, "dg_ron_n", 0)]

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size}  cycles {total} (base {btot})  problems {nprob}")
    for p, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {p} {d}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
