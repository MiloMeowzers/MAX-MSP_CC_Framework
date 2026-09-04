"""v6_207 -- Phase 5 file 6: v6_204 + the expr fix ONLY (per user direction).

Base v6_204 (NOT v6_205/206 -- drop the groove~/selector~ rewrite).

User: "build from 203, it had a working fast render.  The issue was not wiring
it into everything else and the timer-driven auto-commit that killed it."

v6_204 already IS "v6_203 minus the auto-commit, plus the handover reinit"
(report 20 / snramp 16 / ramp 16 -> karma).  Its ONE remaining bug is the
`pc_startx` clamp: an arithmetic-in-condition `expr` ternary that emits nothing
in Max -> `start` stuck at 0 -> `renderMs = end/8` -> often huge -> the
whole-buffer loop that build produced.  v6_203's own render duration
(`pc_rmsx = expr $f1/8.` -> renderMs = sizeMs/8) was fine.

This build keeps v6_204 entirely -- `play~ ---rollBuf` render source, the
`+~` speed boost (obj-7 + 7), the record-source `selector~`s, the reinit --
and only rewrites the two clamp exprs as plain `max()`:

  pc_startx : ($f1-$f2<0.)?0.:($f1-$f2)  ->  expr max($f1-$f2,0.)
  pc_spanx  : ($f2-$f1)/8.               ->  expr max(($f2-$f1)/8.,60.)

  start    = max(end - sizeMs, 0)        (a seam-crossing grab clamps to [0,end])
  renderMs = max((end - start) / 8, 60)  (>= 60 ; <= sizeMs/8 by construction)

Nothing else changes.  Diag fields stay: SPD = ---karmaRep4 (loop END ms:
expect ~sizeMs, NOT 85 and NOT 120000), FRC = ---frRenderMs (~sizeMs/8).

    python phase3_file24_v204_expr_only.py   # -> ../generated/ChopChop_v6_207.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_204.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_207.amxd"


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

    fixes = {
        "pc_startx": "expr max($f1-$f2,0.)",
        "pc_spanx": "expr max(($f2-$f1)/8.,60.)",
    }
    seen = set()
    for b in pc["boxes"]:
        bx = b.get("box", b)
        if bx["id"] in fixes:
            bx["text"] = fixes[bx["id"]]
            seen.add(bx["id"])
    assert seen == set(fixes), f"missing: {set(fixes) - seen}"

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_204 {btot})  problems {nprob}")
    chk = find(find_scope(load(OUT).patcher, "/").patcher,
               lambda x: x.get("text") == "p PrerollCapture")["patcher"]
    for b in chk["boxes"]:
        bx = b.get("box", b)
        if bx["id"] in fixes:
            print(f"  {bx['id']}: {bx['text']!r}")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
