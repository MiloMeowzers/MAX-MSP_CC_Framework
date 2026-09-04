"""v6_204 -- Phase 5 file 3: Record-only Commit + proper karma handover.

Base v6_203.  Logic-only; NO presentation / position / openrect change.

v6_203 test (user): the auto-first Commit undermines the preroll (it is just a
delayed record + a pointless second press), its defer/retry latch mis-fires
(half-bar dropouts, and eventually karma stuck stopped), and the committed
master had no chase overlay / position reporting because the fast-render path
skipped the `reinit` (`report 20` / `snramp 16` / `ramp 16`) that a normal
Record sends to karma via `---recordOn`.

This build:
  1. REMOVES the auto-first Commit entirely.  The Record button is the ONLY
     Commit trigger.  The device is silent until the user presses Record; the
     ring fills bar-aligned in the background and the FUL LED reports "a full
     LoopLength is captured" (unchanged).  `rc_gate` already routes a
     Record-when-FUL to `---prerollCapture`.
  2. REMOVES the wrap defer/retry latch.  A grab that would cross the ring seam
     (only the first `sizeBars` bars of each `ringBars` cycle) is clamped to
     `start = 0` -> Commit `[0, end]` (shorter that once, contiguous, valid).
     No `gate`, no retry -> the `/PrerollCapture/` message cycle is gone.
  3. FIXES the handover.  `p FastRender` now sends `report 20`, `snramp 16`,
     `ramp 16` to karma (via `s ---karmaMsg` -> obj-20) right after `play`,
     exactly like the `---recordOn` reinit -- so the chase overlay and the
     position/window displays come back.

Untouched: the bar-locked substrate (`p RollCapture`), the groove~ bridge, the
karma-A speed boost + record-source `selector~`s in `p Playback`.

Not addressed here (pre-existing base issue): `---enableA` / `---enableB` /
`---enableKeys` have no senders -- the A/B mute toggles feed `gate 1 1`
(default open) and do nothing.  The A/B-as-master-vs-ring rework is a separate
piece.

    python phase3_file21_no_autocommit_handover.py   # -> ../generated/ChopChop_v6_204.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_203.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_204.amxd"


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def O(bid, text, x, y, w=90.0, nin=1, nout=1, ot=None):
    b = {"id": bid, "maxclass": "newobj", "text": text, "numinlets": nin,
         "numoutlets": nout, "patching_rect": [float(x), float(y), float(w), 22.0]}
    if ot is not None:
        b["outlettype"] = ot
    return {"box": b}


def M(bid, text, x, y, w=60.0):
    return {"box": {"id": bid, "maxclass": "message", "text": text, "numinlets": 2,
                    "numoutlets": 1, "outlettype": [""],
                    "patching_rect": [float(x), float(y), float(w), 20.0]}}


def drop(pat, pred):
    pat["lines"] = [e for e in pat["lines"] if not pred(e.get("patchline", e))]


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher

    def find(pat, pred):
        for b in pat.get("boxes", []):
            bx = b.get("box", b)
            if pred(bx):
                return bx
            if isinstance(bx.get("patcher"), dict):
                r = find(bx["patcher"], pred)
                if r:
                    return r

    pc = find(root, lambda x: x.get("text") == "p PrerollCapture")["patcher"]
    fr = find(root, lambda x: x.get("text") == "p FastRender")["patcher"]

    # ================================================= p PrerollCapture: rebuild
    # keep only pc_trig; drop everything file-20 added.
    pc["boxes"] = [b for b in pc["boxes"] if b.get("box", b)["id"] == "pc_trig"]
    pc["lines"] = []

    pc["boxes"] += [
        O("pc_seq", "t b b b b b b", 20.0, 60.0, 130.0, nin=1, nout=7, ot=["bang"] * 7),
        O("pc_end", "r ---rollEndMs", 20.0, 96.0, 110.0, nin=0, ot=[""]),
        O("pc_endf", "f", 20.0, 124.0, 40.0, nin=2, ot=[""]),
        O("pc_bmr", "r ---barMs", 150.0, 96.0, 90.0, nin=0, ot=[""]),
        O("pc_bmf", "f 2000.", 150.0, 124.0, 60.0, nin=2, ot=[""]),
        O("pc_szr", "r ---size", 260.0, 96.0, 80.0, nin=0, ot=[""]),
        O("pc_szf", "f", 260.0, 124.0, 40.0, nin=2, ot=[""]),
        # sizeMs snapped to an integer-bar multiple
        O("pc_szsnap", "expr round($f2/$f1)*$f1", 150.0, 160.0, 190.0, nin=2, ot=[""]),
        # start = max(end - sizeMs, 0)   -- clamp instead of defer on a seam-crossing grab
        O("pc_startx", "expr ($f1-$f2<0.)?0.:($f1-$f2)", 20.0, 190.0, 200.0, nin=2, ot=[""]),
        # renderMs = (end - start) / 8   -- $f1 = start (hot), $f2 = end (cold)
        O("pc_spanx", "expr ($f2-$f1)/8.", 260.0, 218.0, 140.0, nin=2, ot=[""]),
        # bridge
        M("pc_gset", "set ---rollBuf", 420.0, 300.0, 110.0),
        M("pc_gl1", "loop 1", 420.0, 328.0, 60.0),
        M("pc_gsl", "startloop", 420.0, 356.0, 70.0),
        O("pc_gvs", "s ---gvMsg", 420.0, 384.0, 90.0, nout=0),
        O("pc_les", "s ---gvLoopEnd", 300.0, 300.0, 110.0, nout=0),
        O("pc_lss", "s ---gvLoopStart", 150.0, 300.0, 110.0, nout=0),
        M("pc_pl1", "1", 540.0, 328.0, 26.0),
        O("pc_pls", "s ---prerollLoop", 540.0, 356.0, 110.0, nout=0),
        # commit list  [start end renderMs]  -- one clean emit on o0
        O("pc_sthold", "f", 200.0, 250.0, 40.0, nin=2, ot=[""]),
        O("pc_pk", "pack f f f", 20.0, 360.0, 120.0, nin=3, ot=[""]),
        O("pc_go", "s ---commitGo", 20.0, 392.0, 100.0, nout=0),
    ]
    pc["lines"] += [
        Ln("pc_trig", 0, "pc_seq", 0),
        # o6: latch end / barMs / size
        Ln("pc_end", 0, "pc_endf", 1), Ln("pc_seq", 6, "pc_endf", 0),
        Ln("pc_bmr", 0, "pc_bmf", 1), Ln("pc_seq", 6, "pc_bmf", 0),
        Ln("pc_szr", 0, "pc_szf", 1), Ln("pc_seq", 6, "pc_szf", 0),
        # compute: bmf drives szsnap (szf already set). pc_endf cords below are
        # created startx-first so, firing in reverse, pc_endf sets spanx[1]/pk[1]/
        # les BEFORE it triggers startx -- then startx -> spanx[0] (hot) sees a
        # settled end, and pk has end already stored for the o0 emit.
        Ln("pc_bmf", 0, "pc_szsnap", 0), Ln("pc_szf", 0, "pc_szsnap", 1),
        Ln("pc_szsnap", 0, "pc_startx", 1),
        Ln("pc_startx", 0, "pc_spanx", 0),
        Ln("pc_endf", 0, "pc_startx", 0),
        Ln("pc_endf", 0, "pc_spanx", 1),
        Ln("pc_endf", 0, "pc_les", 0),
        Ln("pc_endf", 0, "pc_pk", 1),
        # groove~ bridge, o5..o2  (loop points settle on o6, then set/loop/startloop)
        Ln("pc_startx", 0, "pc_lss", 0),
        Ln("pc_seq", 5, "pc_gset", 0), Ln("pc_gset", 0, "pc_gvs", 0),
        Ln("pc_seq", 4, "pc_gl1", 0), Ln("pc_gl1", 0, "pc_gvs", 0),
        Ln("pc_seq", 3, "pc_gsl", 0), Ln("pc_gsl", 0, "pc_gvs", 0),
        Ln("pc_seq", 2, "pc_pl1", 0), Ln("pc_pl1", 0, "pc_pls", 0),
        # list: end (pk[1]) already stored above; span cold; start held silently; emit on o0
        Ln("pc_spanx", 0, "pc_pk", 2),
        Ln("pc_startx", 0, "pc_sthold", 1),
        Ln("pc_seq", 0, "pc_sthold", 0),
        Ln("pc_sthold", 0, "pc_pk", 0),
        Ln("pc_pk", 0, "pc_go", 0),
    ]

    # ================================================= p FastRender: add the reinit
    # after `play`, wake karma exactly like the ---recordOn reinit does.
    fr["boxes"] += [
        M("fr_rep", "report 20", 560.0, 340.0, 70.0),
        M("fr_snr", "snramp 16", 640.0, 340.0, 80.0),
        M("fr_rmp", "ramp 16", 720.0, 340.0, 70.0),
        O("fr_reit", "t b b b", 560.0, 312.0, 80.0, nin=1, nout=3, ot=["bang"] * 3),
    ]
    # fr_cl outlet 2 currently -> fr_rgb ("bang" -> s ---regrid).  Add the reinit
    # on the same close step, ahead of regrid, into s ---karmaMsg (-> obj-20).
    fr["lines"] += [
        Ln("fr_cl", 2, "fr_reit", 0),
        Ln("fr_reit", 2, "fr_rep", 0),
        Ln("fr_reit", 1, "fr_snr", 0),
        Ln("fr_reit", 0, "fr_rmp", 0),
        Ln("fr_rep", 0, "fr_km", 0),
        Ln("fr_snr", 0, "fr_km", 0),
        Ln("fr_rmp", 0, "fr_km", 0),
    ]

    # -------------------------------------------------------------- save + check
    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_203 {btot})  problems {nprob}")
    for pth, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {pth}: {d}")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
