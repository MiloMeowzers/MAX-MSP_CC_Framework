"""v6_211 -- Phase 5 file 10: drop pc_szsnap (a 2-op expr that silently fails).

Base v6_210.  Logic-only.

v6_210 test: SPD (`---frRenderMs`) STILL 0 -- so reverting `pc_rmsx` did not
help.  The dead link is one further upstream: `pc_szsnap` =
`expr round($f2/$f1)*$f1` -- `round()` AND `*`, two operations -> emits NOTHING
in this device's Max (see the confirmed-broken list).  So `pc_szsnap` never
outputs -> `pc_rmsx` (fed by it) never fires -> `pc_pk[2]` stays at pack's
default 0 -> `renderMs` = 0 -> `record` then `delay 0` then `play` in one tick
-> karma cannot close the pass -> stuck recording, whole-buffer loop.
This link has been dead since v6_203; every "loop playing" so far has been the
groove~ bridge, with karma A stuck.

`pc_szsnap` only re-quantised `---size` to an integer bar count -- and `---size`
is ALREADY bar-quantised in `p TempoTranslate` upstream.  So delete it and feed
`---size` straight through:

  drop box pc_szsnap and its 4 lines
  + pc_szf[0] -> pc_startx[1]   (start = end - ---size)
  + pc_szf[0] -> pc_rmsx[0]     (renderMs = ---size / 8)

pc_szf fires on pc_seq[6] before pc_endf (fan order), so pc_startx sees a
settled size and renderMs is computed on the same o6 pass.  pc_bmf (r ---barMs)
is left dangling -- harmless.  Nothing else changes.

    python phase3_file28_drop_szsnap.py   # -> ../generated/ChopChop_v6_211.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_210.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_211.amxd"


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

    # sanity: the box is what we think it is
    szsnap = next(b.get("box", b) for b in pc["boxes"] if b.get("box", b)["id"] == "pc_szsnap")
    assert szsnap["text"] == "expr round($f2/$f1)*$f1", szsnap["text"]

    pc["boxes"] = [b for b in pc["boxes"] if b.get("box", b)["id"] != "pc_szsnap"]
    pc["lines"] = [e for e in pc["lines"]
                   if e.get("patchline", e)["source"][0] != "pc_szsnap"
                   and e.get("patchline", e)["destination"][0] != "pc_szsnap"]
    pc["lines"] += [
        Ln("pc_szf", 0, "pc_startx", 1),
        Ln("pc_szf", 0, "pc_rmsx", 0),
    ]

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_210 {btot})  problems {nprob}")
    for pth, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {pth}: {d}")
    # show the resulting compute chain
    chk = find(find_scope(load(OUT).patcher, "/").patcher,
               lambda x: x.get("text") == "p PrerollCapture")["patcher"]
    t = {b.get("box", b)["id"]: (b.get("box", b).get("text") or "") for b in chk["boxes"]}
    for l in chk["lines"]:
        pl = l.get("patchline", l)
        s, d = pl["source"], pl["destination"]
        if d[0] in ("pc_startx", "pc_rmsx", "pc_pk") or s[0] in ("pc_rmsx", "pc_startx"):
            print(f"    {t.get(s[0], s[0])[:24]:26}[{s[1]}] -> [{d[1]}] {t.get(d[0], d[0])[:24]}")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
