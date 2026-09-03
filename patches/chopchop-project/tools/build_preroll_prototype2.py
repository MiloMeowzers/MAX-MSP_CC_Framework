"""ChopChop_v6_183_PREROLL_TEST2.amxd -- prototype v2.

v1 result: `set + window + play` computes the window (rep5 correct) but does
NOT confine playback -- karma plays 0..window, goes silent, runs on to the
buffer end (rep4=119999) and wraps; ---karmaPos stuck at 0 => no real loop.

v2 tries the untested confinement paths on a record~-filled buffer:

  A  set ---thisBuffer, window 0.033, jump 0., play
  B  set ---thisBuffer, jump 0., window 0.033, play
  C  set ---thisBuffer, loop 1, window 0.033, jump 0., play
  D  set ---thisBuffer, window 0.033, play      then a self-retriggering
     [delay 3959] -> jump 0. every 3959 ms  (manual re-jump loop)
     E button starts D's clock, F stops it.

Same fill rig as v1 (record~ ---thisBuffer 2 @loop 1 <- ingain_L/R,
buttons 1 start / 0 stop). Same number boxes: ---karmaPos / Rep4 / Rep5 /
Playing. Watch whether pos now sweeps 0..~0.033 and audio loops cleanly.

    python build_preroll_prototype2.py
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_183.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_183_PREROLL_TEST2.amxd"

X, Y = 2600.0, 180.0


def bx(d):
    return {"box": d}


def obj(i, text, dx, dy, w=150, nin=2, nout=1, ot=None):
    return bx({"id": i, "maxclass": "newobj", "text": text, "numinlets": nin,
              "numoutlets": nout, "outlettype": ot if ot is not None else [""],
              "patching_rect": [X + dx, Y + dy, w, 22.0]})


def msg(i, text, dx, dy, w=300):
    return bx({"id": i, "maxclass": "message", "text": text, "numinlets": 2, "numoutlets": 1,
              "outlettype": [""], "patching_rect": [X + dx, Y + dy, w, 22.0]})


def btn(i, dx, dy):
    return bx({"id": i, "maxclass": "button", "numinlets": 1, "numoutlets": 1,
              "outlettype": ["bang"], "patching_rect": [X + dx, Y + dy, 22.0, 22.0]})


def num(i, dx, dy, w=100):
    return bx({"id": i, "maxclass": "number", "numinlets": 1, "numoutlets": 2,
              "outlettype": ["", "bang"], "patching_rect": [X + dx, Y + dy, w, 22.0]})


def cmt(i, text, dx, dy, w=520):
    return bx({"id": i, "maxclass": "comment", "text": text, "numinlets": 1, "numoutlets": 0,
              "patching_rect": [X + dx, Y + dy, w, 20.0]})


def L(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    ids = {b.get("box", b)["id"] for b in root["boxes"]}
    assert "ingain_L" in ids and "ingain_R" in ids

    B = [
        cmt("p2_lbl", "PREROLL TEST 2  -- fill: [1] start, play >6s in, [0] stop.  Then try A/B/C, or D+E (E starts re-jump clock, F stops).", 0, -28, 760),
        obj("p2_rec", "record~ ---thisBuffer 2 @loop 1", 0, 20, 210, nin=3, nout=1, ot=["signal"]),
        btn("p2_b1", 0, 50), msg("p2_m1", "1", 28, 50, 26),
        btn("p2_b0", 70, 50), msg("p2_m0", "0", 98, 50, 26),

        btn("p2_bA", 0, 84), msg("p2_mA", "set ---thisBuffer, window 0.033, jump 0., play", 28, 84),
        btn("p2_bB", 0, 108), msg("p2_mB", "set ---thisBuffer, jump 0., window 0.033, play", 28, 108),
        btn("p2_bC", 0, 132), msg("p2_mC", "set ---thisBuffer, loop 1, window 0.033, jump 0., play", 28, 132),
        btn("p2_bD", 0, 156), msg("p2_mD", "set ---thisBuffer, window 0.033, play", 28, 156),

        obj("p2_s", "s ---karmaMsg", 340, 84, 110, nin=1, nout=0),

        btn("p2_bE", 0, 190), cmt("p2_eL", "E: start re-jump clock", 28, 192, 160),
        btn("p2_bF", 200, 190), cmt("p2_fL", "F: stop clock", 228, 192, 120),
        obj("p2_dl", "delay 3959", 0, 214, 90, nin=2, nout=1, ot=["bang"]),
        msg("p2_jm", "jump 0.", 100, 214, 70),
        obj("p2_js", "s ---karmaMsg", 180, 214, 110, nin=1, nout=0),
        msg("p2_stopm", "stop", 260, 190, 50),

        obj("p2_r0", "r ---karmaPos", 0, 250, 110, nin=0, nout=1), num("p2_n0", 120, 250),
        obj("p2_r4", "r ---karmaRep4", 0, 274, 110, nin=0, nout=1), num("p2_n4", 120, 274, 110),
        obj("p2_r5", "r ---karmaRep5", 0, 298, 110, nin=0, nout=1), num("p2_n5", 120, 298, 110),
        obj("p2_rp", "r ---karmaPlaying", 0, 322, 120, nin=0, nout=1), num("p2_np", 130, 322),
    ]
    root["boxes"] += B
    root["lines"] += [
        L("ingain_L", 0, "p2_rec", 0), L("ingain_R", 0, "p2_rec", 1),
        L("p2_b1", 0, "p2_m1", 0), L("p2_m1", 0, "p2_rec", 0),
        L("p2_b0", 0, "p2_m0", 0), L("p2_m0", 0, "p2_rec", 0),
        L("p2_bA", 0, "p2_mA", 0), L("p2_mA", 0, "p2_s", 0),
        L("p2_bB", 0, "p2_mB", 0), L("p2_mB", 0, "p2_s", 0),
        L("p2_bC", 0, "p2_mC", 0), L("p2_mC", 0, "p2_s", 0),
        L("p2_bD", 0, "p2_mD", 0), L("p2_mD", 0, "p2_s", 0),
        # re-jump clock: E -> delay -> jump -> s ---karmaMsg -> delay (self retrigger)
        L("p2_bE", 0, "p2_dl", 0),
        L("p2_dl", 0, "p2_jm", 0),
        L("p2_jm", 0, "p2_js", 0),
        L("p2_jm", 0, "p2_dl", 0),
        L("p2_bF", 0, "p2_stopm", 0), L("p2_stopm", 0, "p2_dl", 0),
        L("p2_r0", 0, "p2_n0", 0), L("p2_r4", 0, "p2_n4", 0),
        L("p2_r5", 0, "p2_n5", 0), L("p2_rp", 0, "p2_np", 0),
    ]

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    # the self-retriggering delay IS a message cycle -- expected +1
    ok = (nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size}  cycles {total} (base {btot}; +1 expected from the re-jump delay loop)  problems {nprob}")
    for p, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {p} {d}")
    print("OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
