"""v6_210 -- Phase 5 file 9: revert pc_rmsx to the plain expr that works.

Base v6_209.  Logic-only, ONE box text edit.

v6_209 test: gate bypass worked (ply 1, HC 1, hearing karma A, waveform draws)
BUT SPD (`---frRenderMs`) = 0 -> `record` then `delay 0` then `play` in one tick
-> `play` cannot close the record pass -> karma stuck recording / overdub, loop
= whole buffer (FRC `---karmaRep4` = 119999.98).

Cause: my v6_209 "bound", `pc_rmsx` = `expr min(max($f1/8.,60.),4000.)`, emits
NOTHING in this device's Max -- same silent failure as the earlier ternaries.
`min`/`max`/nested function calls are not safe here; only a single simple op is
(`expr $f1/8.` ran fine through every v6_203 test).

  pc_rmsx : expr min(max($f1/8.,60.),4000.)  ->  expr $f1/8.

renderMs is back to `sizeMs/8` (= 13714/8 ~= 1714 ms for the user's 4-bar loop),
so `fr_dl` gives karma a real ~1714 ms to record before `play` closes it at
`maxpos` ~= sizeMs.  `---size` is bar-quantised upstream, so renderMs cannot be
pathologically large in practice; if a huge `---size` ever shows up that is a
`p TempoTranslate` bug to fix at the source, not with a broken expr here.

Nothing else changes.  Gate bypass + diags from v6_209 stay.

    python phase3_file27_revert_rmsx.py   # -> ../generated/ChopChop_v6_210.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_209.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_210.amxd"


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
    hit = False
    for b in pc["boxes"]:
        bx = b.get("box", b)
        if bx["id"] == "pc_rmsx":
            assert bx["text"] == "expr min(max($f1/8.,60.),4000.)", bx["text"]
            bx["text"] = "expr $f1/8."
            hit = True
    assert hit

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_209 {btot})  problems {nprob}")
    chk = find(find_scope(load(OUT).patcher, "/").patcher,
               lambda x: x.get("text") == "p PrerollCapture")["patcher"]
    for b in chk["boxes"]:
        bx = b.get("box", b)
        if bx["id"] == "pc_rmsx":
            print(f"  pc_rmsx: {bx['text']!r}")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
