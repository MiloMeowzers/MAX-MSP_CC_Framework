"""v6_215 -- Phase 5 file 14: one shared, isolated sig~ 8. for BOTH sides.

Base v6_214.  Logic-only, `p Playback` only.

v6_214 test (5 runs): every genuine 8x render (SPD == 1714.25) came out
degraded ("hollow, no bass, no top" -- a continuous resampling artifact, not a
transient glitch) AND the final loop length (FRC) drifted run to run at the
IDENTICAL nominal renderMs.  The one flawless, dead-on-length capture (test 1,
SPD == 0) never actually ran the fast-render -- it fell through to the
untouched real-time record path.

Never-yet-tried combination: v6_213 made karma's speed an isolated `sig~ 8.`
(via `selector~`) but still read through `play~`; v6_214 switched the reader to
`groove~` but reverted karma's speed to `obj-7 + 7` (`obj-7` = is_playing x
pitchMod x the glitch engine's rate output -- a live signal, not guaranteed
rock-stable at 1.0).  A continuously wobbling `obj-7` explains BOTH symptoms at
once: karma's actual record rate drifts a hair off groove~'s exact 8x read
rate for the whole render (-> the uniform "hollow" artifact), and karma's
final loop length is `renderMs * actual_speed`, which drifts run to run with
whatever `obj-7` happened to be doing (-> the FRC drift).  The user's bench
probe was clean because BOTH sides there were driven by isolated constants,
with nothing derived from a live signal chain.

Fix: bypass `obj-7` for BOTH sides during the render, driven from the SAME
`sig~ 8.` box (not two separate ones):

  fr_s8b (sig~ 8.) already feeds fr_g2r[2] (gv2's rate selector) -- fan its
  output to a NEW fr_spd (selector~ 2) too: [1] = obj-7, [2] = fr_s8b, ctl =
  fr_ract.  Out -> obj-20[2] (karma-A speed).  Remove the `+~` boost chain
  (fr_add / fr_boost / fr_bsel / fr_b7 / fr_b0).

Both gv2's rate and karma's speed are now the identical `sig~ 8.` object during
the render -- no path through obj-7/pitchMod/glitch at all while rendering.

    python phase3_file32_shared_exact8.py   # -> ../generated/ChopChop_v6_215.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_214.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_215.amxd"
SIG = ["signal"]


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

    pb = find(root, lambda x: x.get("text") == "p Playback")["patcher"]

    BOOST = {"fr_add", "fr_boost", "fr_bsel", "fr_b7", "fr_b0"}
    drop(pb, lambda pl: pl["source"][0] in BOOST or pl["destination"][0] in BOOST)
    pb["boxes"] = [b for b in pb["boxes"] if b.get("box", b)["id"] not in BOOST]

    pb["boxes"].append(O("fr_spd", "selector~ 2", 40.0, 44.0, 90.0, nin=3, nout=1, ot=SIG))
    pb["lines"] += [
        Ln("obj-7", 0, "fr_spd", 1),
        Ln("fr_s8b", 0, "fr_spd", 2),      # SAME sig~ 8. box that already drives fr_g2r
        Ln("fr_ract", 0, "fr_spd", 0),
        Ln("fr_spd", 0, "obj-20", 2),
    ]

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_214 {btot})  problems {nprob}")
    for pth, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {pth}: {d}")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
