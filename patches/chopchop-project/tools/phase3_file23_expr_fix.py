"""v6_206 -- Phase 5 file 5: fix the two broken expr ternaries in p PrerollCapture.

Base v6_205.  Logic-only; NO presentation / position change.

v6_205 test (user): instant playback but "insanely quick", overlay whizzing.
Diag: FRC (---frRenderMs) = 0, SPD (---karmaRep4 = karma loop END ms) = static
85.33 ms  (== 4096 samples == karma's minimum-loop clamp).  cap/ful = 13714
(the intended 4-bar length -- so ---size is fine).

So `renderMs` reached FastRender as 0 -> `delay 0` -> `play` fired the same tick
as `record` -> karma's initial-loop `maxpos` ~= 0 -> loop clamped to 4096.

Root cause: the arithmetic-in-condition `expr` ternaries added in v6_204/v6_205
emit NOTHING in Max's `expr`, so `pc_pk`'s renderMs inlet kept its default 0.
(v6_204's `pc_startx` ternary broke the same way -- start stuck at 0 -> renderMs
= end/8 -> often huge -> that build's whole-buffer loop.)  Replace both with
plain `max(...)` (the CLAUDE.md-mandated form; `pc_swrap` in v6_202 only ever
used a single-var ternary, which does work).

  pc_startx : expr ($f1-$f2<0.)?0.:($f1-$f2)          -> expr max($f1-$f2,0.)
  pc_spanx  : expr ($f2-$f1<480.)?60.:(($f2-$f1)/8.)  -> expr max(($f2-$f1)/8.,60.)

start = max(end - sizeMs, 0)      (clamp a seam-crossing grab)
renderMs = max((end - start)/8, 60)    (>= 60; <= sizeMs/8 by construction)

Nothing else changes.  Diag fields stay: SPD = ---karmaRep4 (loop end ms:
now expect ~13712, NOT 85 and NOT 120000), FRC = ---frRenderMs (~1714).

    python phase3_file23_expr_fix.py   # -> ../generated/ChopChop_v6_206.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_205.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_206.amxd"


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
    assert seen == set(fixes), f"missing boxes: {set(fixes) - seen}"

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_205 {btot})  problems {nprob}")
    # confirm the new text landed on disk
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
