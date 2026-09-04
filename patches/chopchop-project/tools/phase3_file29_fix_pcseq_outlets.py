"""v6_212 -- Phase 5 file 11: fix pc_seq -- 6-outlet trigger driving outlet 6.

Base v6_211.  Logic-only, ONE box text edit.

ROOT CAUSE (present since v6_203 / file 20): `pc_seq` was built with text
`t b b b b b b` (6 args -> Max gives it 6 outlets, 0..5) but `numoutlets: 7` in
the JSON, and it drives outlet index **6** for the o6 latch step
(`pc_seq[6] -> pc_endf / pc_szf / pc_bmf / pc_ruf`).  Max drops the invalid
outlet-6 cords on load -> `end` / `size` are NEVER latched at Commit ->
`pc_startx` (`end - size`) and `pc_rmsx` (`size / 8`) never fire -> `pc_pk`
emits `[0, 0, 0]` -> `---commitGo` renderMs = 0 -> `record` + `delay 0` +
`play` in one tick -> karma can never close its record pass.  Every "loop
playing" so far has been the groove~ bridge; every karma stuck-record was this.
`validate.py` missed it -- it trusts the stored `numoutlets` (7) instead of
counting the trigger args (6).

  pc_seq : `t b b b b b b`  ->  `t b b b b b b b`   (7 outlets, matches the
                                                     wiring which uses 0,2,3,4,5,6)

Nothing else changes.

    python phase3_file29_fix_pcseq_outlets.py   # -> ../generated/ChopChop_v6_212.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_211.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_212.amxd"


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
    sq = next(b.get("box", b) for b in pc["boxes"] if b.get("box", b)["id"] == "pc_seq")
    assert sq["text"] == "t b b b b b b", sq["text"]
    outs = sorted({l.get("patchline", l)["source"][1]
                   for l in pc["lines"] if l.get("patchline", l)["source"][0] == "pc_seq"})
    assert max(outs) == 6, outs
    sq["text"] = "t b b b b b b b"          # 7 outlets
    sq["numoutlets"] = 7
    sq["outlettype"] = ["bang"] * 7

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_211 {btot})  problems {nprob}")
    chk = find(find_scope(load(OUT).patcher, "/").patcher,
               lambda x: x.get("text") == "p PrerollCapture")["patcher"]
    s2 = next(b.get("box", b) for b in chk["boxes"] if b.get("box", b)["id"] == "pc_seq")
    print(f"  pc_seq now: {s2['text']!r}  ({s2['text'].split().count('b')} outlets)")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
