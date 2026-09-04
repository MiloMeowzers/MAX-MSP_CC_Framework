"""v6_214 -- Phase 5 file 13: render source play~ -> groove~ ; revert v6_213 selector~.

Base v6_213.  Logic-only.

v6_213 test: karma A degraded even sooner than v6_212 and the last 2 beats
(slices 15-16) came out silent.  The `selector~` on karma-A speed made it worse
than the `+~` boost; and `play~ ---rollBuf` driven by a `line~` position ramp is
the likely source of the "bit reduction" artifacts + the dropped tail (user's
own bench test used `groove~`, rate-driven).

Changes:

1. **Revert karma-A render speed to v6_212's `+~` boost.**  Drop `fr_spd
   (selector~ 2)` / `fr_s8`; restore `fr_add (+~)` + `fr_boost (line~)` +
   `fr_bsel (sel 1 0)` + `fr_b7 (7. 0)` + `fr_b0 (0. 0)` off `fr_bra`.
   `obj-7 + 7` -> `obj-20[2]` during render.

2. **Render source play~ -> groove~.**  In `p FastRender` drop
   `fr_stt / fr_fmt / fr_line / fr_play / fr_sL / fr_sR`.  In `p Playback` drop
   `fr_rvL / fr_rvR (receive~ ---renderL/R)`.
   New in `p Playback`:  `gv2 (groove~ ---rollBuf 2)` ; rate from
   `fr_g2r (selector~ 2)` -- [1] = `fr_z (sig~ 0.)`, [2] = `fr_s8b (sig~ 8.)`,
   ctl = `fr_ract` -- 0 idle / 8 during render.  Loop points via
   `r ---gv2Lo -> gv2[1]`, `r ---gv2Hi -> gv2[2]`; messages via
   `r ---gv2Msg -> gv2[0]`.  `gv2[0]/gv2[1]` -> `fr_recL[2] / fr_recR[2]` (the
   karma record-source selector, input 2).
   New in `p FastRender` (on `r ---commitGo` -> unpack f f f):
     end  (o1) -> `s ---gv2Hi`
     start(o0) -> `fr_lot (t f b)` : f -> `s ---gv2Lo` + store in `fr_pos_f (f)`;
       b -> `fr_o (t b b b)` :
         o2 -> "set ---rollBuf" -> s ---gv2Msg
         o1 -> "loop 1" -> s ---gv2Msg ; and "1" -> s ---renderActive (rate 8,
               rec source -> gv2)
         o0 -> `fr_pos_f` bang -> start float -> s ---gv2Msg (groove~ plays the
               slab at 8x) ; then `fr_ks (t b b)` -> reinit+stop, record+delay.
   renderMs (o2) still -> `fr_dl[1]` + `s ---frRenderMs`.

3. **Keep** the v6_213 karma-B gate (`fr_bg`) and the record-source selectors.

    python phase3_file31_groove_render_on_working_base.py   # -> ../generated/ChopChop_v6_214.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_213.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_214.amxd"
SIG = ["signal"]


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def O(bid, text, x, y, w=90.0, nin=1, nout=1, ot=None):
    b = {"id": bid, "maxclass": "newobj", "text": text, "numinlets": nin,
         "numoutlets": nout, "patching_rect": [float(x), float(y), float(w), 22.0]}
    if ot is not None:
        b["outlettype"] = ot
    return {"box": b}


def M(bid, text, x, y, w=70.0):
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

    pb = find(root, lambda x: x.get("text") == "p Playback")["patcher"]
    fr = find(root, lambda x: x.get("text") == "p FastRender")["patcher"]

    # ============================ 1. revert karma-A speed to +~ boost
    SPD = {"fr_spd", "fr_s8"}
    drop(pb, lambda pl: pl["source"][0] in SPD or pl["destination"][0] in SPD)
    pb["boxes"] = [b for b in pb["boxes"] if b.get("box", b)["id"] not in SPD]
    pb["boxes"] += [
        O("fr_add", "+~", 40.0, 40.0, 40.0, nin=2, ot=SIG),
        O("fr_boost", "line~", 40.0, 12.0, 60.0, nin=2, nout=2, ot=["signal", "bang"]),
        O("fr_bsel", "sel 1 0", 160.0, 12.0, 60.0, nin=2, nout=3, ot=["bang", "bang", ""]),
        M("fr_b7", "7. 0", 160.0, 40.0, 40.0),
        M("fr_b0", "0. 0", 208.0, 40.0, 40.0),
    ]
    pb["lines"] += [
        Ln("obj-7", 0, "fr_add", 0),
        Ln("fr_boost", 0, "fr_add", 1),
        Ln("fr_add", 0, "obj-20", 2),
        Ln("fr_bra", 0, "fr_bsel", 0),
        Ln("fr_bsel", 0, "fr_b7", 0),
        Ln("fr_bsel", 1, "fr_b0", 0),
        Ln("fr_b7", 0, "fr_boost", 0),
        Ln("fr_b0", 0, "fr_boost", 0),
    ]

    # ============================ 2a. p Playback: gv2 groove~ render reader
    drop(pb, lambda pl: pl["source"][0] in ("fr_rvL", "fr_rvR")
         or pl["destination"][0] in ("fr_rvL", "fr_rvR"))
    pb["boxes"] = [b for b in pb["boxes"] if b.get("box", b)["id"] not in ("fr_rvL", "fr_rvR")]
    pb["boxes"] += [
        O("fr_z", "sig~ 0.", 320.0, 12.0, 50.0, nin=1, ot=SIG),
        O("fr_s8b", "sig~ 8.", 380.0, 12.0, 50.0, nin=1, ot=SIG),
        O("fr_g2r", "selector~ 2", 320.0, 44.0, 90.0, nin=3, nout=1, ot=SIG),
        O("gv2", "groove~ ---rollBuf 2", 320.0, 100.0, 150.0, nin=3, nout=3,
          ot=["signal", "signal", "signal"]),
        O("fr_g2m", "r ---gv2Msg", 320.0, 72.0, 100.0, nin=0, ot=[""]),
        O("fr_g2lo", "r ---gv2Lo", 430.0, 72.0, 90.0, nin=0, ot=[""]),
        O("fr_g2hi", "r ---gv2Hi", 520.0, 72.0, 90.0, nin=0, ot=[""]),
    ]
    pb["lines"] += [
        Ln("fr_z", 0, "fr_g2r", 1),
        Ln("fr_s8b", 0, "fr_g2r", 2),
        Ln("fr_ract", 0, "fr_g2r", 0),
        Ln("fr_g2r", 0, "gv2", 0),
        Ln("fr_g2m", 0, "gv2", 0),
        Ln("fr_g2lo", 0, "gv2", 1),
        Ln("fr_g2hi", 0, "gv2", 2),
        Ln("gv2", 0, "fr_recL", 2),
        Ln("gv2", 1, "fr_recR", 2),
    ]

    # ============================ 2b. p FastRender: drop play~ chain, add groove~ drive
    DEAD = {"fr_stt", "fr_fmt", "fr_line", "fr_play", "fr_sL", "fr_sR"}
    drop(fr, lambda pl: pl["source"][0] in DEAD or pl["destination"][0] in DEAD)
    fr["boxes"] = [b for b in fr["boxes"] if b.get("box", b)["id"] not in DEAD]
    # fr_ks was `t b b b` (o2 renderActive, o1 stop, o0 record) driven by fr_stt[0].
    # renderActive moves to fr_o o1; fr_ks becomes `t b b`.
    ks = next(b.get("box", b) for b in fr["boxes"] if b.get("box", b)["id"] == "fr_ks")
    ks["text"] = "t b b"
    ks["numoutlets"] = 2
    ks["outlettype"] = ["bang", "bang"]
    drop(fr, lambda pl: pl["source"] == ["fr_ks", 2])          # old renderActive tap
    fr["boxes"] += [
        O("fr_lot", "t f b", 40.0, 90.0, 50.0, nin=1, nout=2, ot=["float", "bang"]),
        O("fr_los", "s ---gv2Lo", 40.0, 122.0, 90.0, nout=0),
        O("fr_his", "s ---gv2Hi", 150.0, 60.0, 90.0, nout=0),
        O("fr_pos_f", "f", 40.0, 200.0, 40.0, nin=2, ot=[""]),
        O("fr_o", "t b b b", 120.0, 122.0, 80.0, nin=1, nout=3, ot=["bang"] * 3),
        M("fr_g2set", "set ---rollBuf", 120.0, 158.0, 110.0),
        M("fr_g2l1", "loop 1", 240.0, 158.0, 50.0),
        O("fr_g2s", "s ---gv2Msg", 120.0, 260.0, 90.0, nout=0),
    ]
    fr["lines"] += [
        Ln("fr_unpk", 1, "fr_his", 0),
        Ln("fr_unpk", 0, "fr_lot", 0),
        Ln("fr_lot", 1, "fr_los", 0),
        Ln("fr_lot", 1, "fr_pos_f", 1),
        Ln("fr_lot", 0, "fr_o", 0),
        Ln("fr_o", 2, "fr_g2set", 0), Ln("fr_g2set", 0, "fr_g2s", 0),
        Ln("fr_o", 1, "fr_g2l1", 0), Ln("fr_g2l1", 0, "fr_g2s", 0),
        Ln("fr_o", 1, "fr_ra1", 0),                      # renderActive 1 (fr_ra1 -> fr_ras exists)
        Ln("fr_o", 0, "fr_ks", 0),
        Ln("fr_o", 0, "fr_pos_f", 0),                    # bang start float -> gv2 position
        Ln("fr_pos_f", 0, "fr_g2s", 0),
    ]

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_213 {btot})  problems {nprob}")
    for pth, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {pth}: {d}")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
