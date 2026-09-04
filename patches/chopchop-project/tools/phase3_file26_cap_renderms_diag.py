"""v6_209 -- Phase 5 file 8: bypass the wrap gate + bound renderMs + diagnostics.

Base v6_208.  Logic-only.

v6_208 test: clean full loop plays (groove~ bridge) but `ply 0` / `ful 1` /
`cap 0` -- karma A never takes over.  `ful 1` == `---hasContent` never reached
1 == FastRender never ran.

Root cause: v6_203's `p PrerollCapture` routes the commit list through
`pc_pk -> pc_gate (gate 2) -> pc_go`.  `gate 2` has NO init arg -> control 0 ==
CLOSED by default, opened only by `pc_wrapx -> pc_wsel`.  The auto-commit fired
`pc_seq` many times so a later pass got the gate open; a single manual Commit
does not -> `---commitGo` never fires.  v6_204 -- the one build whose handover
worked (`ply 1`, overlay tracking) -- had wired `pc_pk -> pc_go` DIRECT with no
gate.  Do that.

Changes:

1. **Bypass the wrap gate.**  Delete `pc_gate` / `pc_wsel` / `pc_wrapx` and their
   lines; wire `pc_pk[0] -> pc_go` direct.  `---commitGo` now fires on every
   Commit.  A would-wrap grab (`start < 0`) sends a slightly-off list;
   FastRender's `line~`/`play~` clamps the position -- acceptable for now.
   `pc_gvlo` (clamps `---gvLoopStart` to >= 0) is kept.

2. **Bound renderMs.**  `pc_rmsx`:  `expr $f1/8.` -> `expr min(max($f1/8.,60.),4000.)`
   (>= 60, <= 4000 ms).  `min`/`max` are functions, not the arithmetic-condition
   ternaries that silently failed in v6_204/205.

3. **`s ---frRenderMs`** in `p FastRender` from `fr_unpk[2]`.

4. **Diag repoint** (logic only):
     dg_spd_r  r ---rollFold   -> r ---frRenderMs   (renderMs used)
     dg_frc_r  r ---rollEndMs  -> r ---karmaRep4    (karma loop END ms; ~---size
                                                     = the transfer worked)

Render mechanism still v6_203's verbatim.

    python phase3_file26_cap_renderms_diag.py   # -> ../generated/ChopChop_v6_209.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_208.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_209.amxd"


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


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

    # 1. bypass the wrap gate: drop pc_gate/pc_wsel/pc_wrapx, wire pc_pk -> pc_go direct
    GATE = {"pc_gate", "pc_wsel", "pc_wrapx"}
    n0 = len(pc["boxes"])
    pc["boxes"] = [b for b in pc["boxes"] if b.get("box", b)["id"] not in GATE]
    assert n0 - len(pc["boxes"]) == 3
    pc["lines"] = [e for e in pc["lines"]
                   if e.get("patchline", e)["source"][0] not in GATE
                   and e.get("patchline", e)["destination"][0] not in GATE]
    pc["lines"].append(Ln("pc_pk", 0, "pc_go", 0))

    # 2. bound renderMs
    hit = False
    for b in pc["boxes"]:
        bx = b.get("box", b)
        if bx["id"] == "pc_rmsx":
            assert bx["text"] == "expr $f1/8.", bx["text"]
            bx["text"] = "expr min(max($f1/8.,60.),4000.)"
            hit = True
    assert hit

    # 2. s ---frRenderMs from fr_unpk[2]
    fr["boxes"].append({"box": {
        "id": "fr_rms_s", "maxclass": "newobj", "text": "s ---frRenderMs",
        "numinlets": 1, "numoutlets": 0, "patching_rect": [40.0, 300.0, 110.0, 22.0]}})
    fr["lines"].append(Ln("fr_unpk", 2, "fr_rms_s", 0))

    # 3. diag repoint
    rb = {b.get("box", b)["id"]: b.get("box", b) for b in root["boxes"]}
    assert rb["dg_spd_r"]["text"] == "r ---rollFold"
    assert rb["dg_frc_r"]["text"] == "r ---rollEndMs"
    rb["dg_spd_r"]["text"] = "r ---frRenderMs"
    rb["dg_frc_r"]["text"] = "r ---karmaRep4"

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    same = OUT.stat().st_size == BASE.stat().st_size
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size}) same={same}  "
          f"cycles {total} (v6_208 {btot})  problems {nprob}")
    for pth, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {pth}: {d}")
    ok = same and nprob == 0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
