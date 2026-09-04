"""v6_216 -- Phase 5 file 15: settle gap before the capture actually starts.

Base v6_215.  Logic-only, `p FastRender` only.

v6_215 test: renders range from flawless to degraded, and the number of clean
beats correlates with when FRC/SPD "lock in" (i.e. how much of the capture a
startup transient touches).  `fr_spd` / `fr_g2r` (the selectors that switch
karma's speed and groove~'s rate onto the shared `sig~ 8.`) only take effect on
the NEXT DSP vector after `---renderActive` arrives -- but karma's `record` and
gv2's position/start currently fire in the SAME instant as that control
message, with no guaranteed settle time.  The first sliver of every capture can
begin before both sides have actually locked onto exactly 8x.

Insert a `delay 5` between "renderActive on" (o1 of `fr_o`, which switches both
selectors) and the actual capture start (o0: gv2 position-float + karma
stop/record).  5 ms is comfortably more than one DSP vector at any common
buffer size, so by the time the capture starts, `fr_spd` and `fr_g2r` are
already outputting `sig~ 8.` -- both sides locked before anything is recorded.

  fr_o[0] (was -> fr_pos_f + fr_ks directly)
    -> fr_settle (delay 5) -> fr_o2 (t b b):
         o1 -> fr_pos_f (bang, gv2 plays)
         o0 -> fr_ks (bang, karma stop+record)

Total Commit-to-play wall clock grows by 5 ms; renderMs / SPD / the gv2<->karma
lock relationship are otherwise unchanged.

    python phase3_file33_settle_delay.py   # -> ../generated/ChopChop_v6_216.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_215.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_216.amxd"


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def O(bid, text, x, y, w=90.0, nin=1, nout=1, ot=None):
    b = {"id": bid, "maxclass": "newobj", "text": text, "numinlets": nin,
         "numoutlets": nout, "patching_rect": [float(x), float(y), float(w), 22.0]}
    if ot is not None:
        b["outlettype"] = ot
    return {"box": b}


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

    fr = find(root, lambda x: x.get("text") == "p FastRender")["patcher"]

    drop(fr, lambda pl: pl["source"] == ["fr_o", 0])
    fr["boxes"] += [
        O("fr_settle", "delay 5", 40.0, 240.0, 80.0, nin=2, nout=1, ot=["bang"]),
        O("fr_o2", "t b b", 40.0, 272.0, 60.0, nin=1, nout=2, ot=["bang", "bang"]),
    ]
    fr["lines"] += [
        Ln("fr_o", 0, "fr_settle", 0),
        Ln("fr_settle", 0, "fr_o2", 0),
        Ln("fr_o2", 1, "fr_pos_f", 0),
        Ln("fr_o2", 0, "fr_ks", 0),
    ]

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_215 {btot})  problems {nprob}")
    for pth, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {pth}: {d}")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
