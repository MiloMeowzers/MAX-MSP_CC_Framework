"""v6_213 -- Phase 5 file 12: exact-8 render speed + karma B out of the render.

Base v6_212.  Logic-only.

v6_212: fast-render WORKS (loop bounded to sizeMs, reverse/chase/overlay OK).
Two issues:

  - Buffer B loops `renderMs` (2 beats) not `sizeMs` -- karma B receives the
    render's `record`/`play` on `---karmaMsg` too, but at 1x (no 8x boost), so
    its initial loop closes at renderMs.  B must sit out the render.

  - Buffer A degrades after ~2 beats -- karma A records at `obj-7 + 7`, not
    exactly 8x; when `obj-7` != 1 the karma record rate and `play~`'s exact-8x
    read rate drift apart and the audio resamples badly.

Changes (p Playback only):

1. **karma-A render speed EXACTLY `sig~ 8.`**  Replace `fr_add (+~)` /
   `fr_boost (line~)` / `fr_bsel` / `fr_b7` / `fr_b0` with `fr_spd
   (selector~ 2)`:  [1] = `obj-7`, [2] = `fr_s8 (sig~ 8.)`, ctl =
   `fr_ract (+ 1)`.  renderActive 0 -> ctl 1 -> `obj-7`; renderActive 1 ->
   ctl 2 -> `sig~ 8.`.  Out -> `obj-20[2]`.

2. **karma B out of the render.**  `obj-45[0] -> karmaB[0]` gets a `gate 1 1`
   (`fr_bg`) whose control is `fr_bra (r ---renderActive) -> fr_bginv (== 0)` --
   open only when NOT rendering.  So B keeps its own live loop and its length
   is not clobbered.

    python phase3_file30_exact8_and_bgate.py   # -> ../generated/ChopChop_v6_213.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_212.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_213.amxd"

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

    # ---- 1. exact-8 render speed
    OLD = {"fr_add", "fr_boost", "fr_bsel", "fr_b7", "fr_b0"}
    drop(pb, lambda pl: pl["source"][0] in OLD or pl["destination"][0] in OLD)
    pb["boxes"] = [b for b in pb["boxes"] if b.get("box", b)["id"] not in OLD]
    pb["boxes"] += [
        O("fr_s8", "sig~ 8.", 40.0, 12.0, 50.0, nin=1, ot=SIG),
        O("fr_spd", "selector~ 2", 40.0, 44.0, 90.0, nin=3, nout=1, ot=SIG),
    ]
    pb["lines"] += [
        Ln("obj-7", 0, "fr_spd", 1),
        Ln("fr_s8", 0, "fr_spd", 2),
        Ln("fr_ract", 0, "fr_spd", 0),
        Ln("fr_spd", 0, "obj-20", 2),
    ]

    # ---- 2. karma B out of the render
    drop(pb, lambda pl: pl["source"] == ["obj-45", 0] and pl["destination"] == ["karmaB", 0])
    pb["boxes"] += [
        O("fr_bg", "gate 1 1", 300.0, 44.0, 60.0, nin=2, nout=1, ot=[""]),
        O("fr_bginv", "== 0", 300.0, 12.0, 44.0, nin=2, ot=[""]),
    ]
    pb["lines"] += [
        Ln("fr_bra", 0, "fr_bginv", 0),
        Ln("fr_bginv", 0, "fr_bg", 0),
        Ln("obj-45", 0, "fr_bg", 1),
        Ln("fr_bg", 0, "karmaB", 0),
    ]

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_212 {btot})  problems {nprob}")
    for pth, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {pth}: {d}")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
