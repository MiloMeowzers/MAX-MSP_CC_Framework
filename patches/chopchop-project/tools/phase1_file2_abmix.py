"""Phase 1, file 2 -- wire ---abMix as an A/B crossfade.

v6_175 sums karma A + karmaB raw into bmixL/bmixR. This replaces the raw sum
with a linear crossfade driven by the existing AB_MIX dial:

    AB_MIX live.dial (0..100, initial 0)  ->  s ---abMix   [already in the file]

New, inside p Playback:

    r ---abMix -> / 100. -> [$1 20( -> line~ ---> (mix, 0..1) = B gain
                                            \-> !-~ 1.  --> (1-mix)   = A gain

    karma A L (obj-20[0]) -> *~ (xA) -> bmixL[0]
    karmaB   L            -> *~ (xB) -> bmixL[1]
    ... and R through bmixR

Removes the 4 direct cords added in file 1 and routes each through its `*~`.
Dial initial 0 (and nothing forces ---abMix on load) => line~ rests at 0 =>
A full, B silent = same as v6_174/v6_175-with-dial-at-0. Safe default.

    python phase1_file2_abmix.py     # -> ../generated/ChopChop_v6_176.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_175.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_176.amxd"


def L(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def obj(box_id, text, rect, nin=2, nout=1, otype=None):
    return {"box": {
        "id": box_id, "maxclass": "newobj", "numinlets": nin, "numoutlets": nout,
        "outlettype": otype if otype is not None else ["signal"],
        "patching_rect": [float(rect[0]), float(rect[1]), float(rect[2]), 22.0],
        "text": text,
    }}


def msg(box_id, text, rect):
    return {"box": {
        "id": box_id, "maxclass": "message", "numinlets": 2, "numoutlets": 1,
        "outlettype": [""],
        "patching_rect": [float(rect[0]), float(rect[1]), float(rect[2]), 22.0],
        "text": text,
    }}


def main():
    amx = load(BASE)
    pb = find_scope(amx.patcher, "p Playback").patcher
    ids = {(b.get("box", b)).get("id") for b in pb["boxes"]}
    for need in ("obj-20", "karmaB", "bmixL", "bmixR"):
        assert need in ids, need
    new_ids = ["xf_r", "xf_n", "xf_m", "xf_l", "xf_a", "mAL", "mBL", "mAR", "mBR"]
    for n in new_ids:
        assert n not in ids, f"id collision {n}"

    # control column tucked to the right of the mixers (obj-23 at x35, obj-25 at x143)
    pb["boxes"] += [
        obj("xf_r", "r ---abMix", [300.0, 590.0, 70.0], nin=0, nout=1, otype=[""]),
        obj("xf_n", "/ 100.", [300.0, 615.0, 40.0], otype=[""]),
        msg("xf_m", "$1 20", [300.0, 640.0, 44.0]),
        obj("xf_l", "line~", [300.0, 665.0, 40.0], nin=2, nout=2, otype=["signal", "bang"]),
        obj("xf_a", "!-~ 1.", [370.0, 690.0, 40.0]),
        obj("mAL", "*~", [35.0, 672.0, 32.0]),
        obj("mBL", "*~", [80.0, 672.0, 32.0]),
        obj("mAR", "*~", [143.5, 672.0, 32.0]),
        obj("mBR", "*~", [188.5, 672.0, 32.0]),
    ]

    def is_line(e, s, so, d, di):
        pl = e.get("patchline", e)
        return pl["source"] == [s, so] and pl["destination"] == [d, di]

    kill = [("obj-20", 0, "bmixL", 0), ("karmaB", 0, "bmixL", 1),
            ("obj-20", 1, "bmixR", 0), ("karmaB", 1, "bmixR", 1)]
    before = len(pb["lines"])
    pb["lines"] = [e for e in pb["lines"] if not any(is_line(e, *k) for k in kill)]
    assert before - len(pb["lines"]) == 4, f"removed {before - len(pb['lines'])}, expected 4"

    pb["lines"] += [
        L("xf_r", 0, "xf_n", 0),
        L("xf_n", 0, "xf_m", 0),
        L("xf_m", 0, "xf_l", 0),
        L("xf_l", 0, "xf_a", 0),
        L("xf_l", 0, "mBL", 1),
        L("xf_l", 0, "mBR", 1),
        L("xf_a", 0, "mAL", 1),
        L("xf_a", 0, "mAR", 1),
        L("obj-20", 0, "mAL", 0), L("mAL", 0, "bmixL", 0),
        L("karmaB", 0, "mBL", 0), L("mBL", 0, "bmixL", 1),
        L("obj-20", 1, "mAR", 0), L("mAR", 0, "bmixR", 0),
        L("karmaB", 1, "mBR", 0), L("mBR", 0, "bmixR", 1),
    ]

    print(f"minified {len(amx.minified())}  headroom {amx.slot - len(amx.minified())}")
    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    bper, btot, bprobs = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size})  cycles {total} (base {btot})  problems {nprob}")
    for p, c in per.items():
        if c != bper.get(p, 0):
            print(f"  cycle delta {p}: {bper.get(p,0)} -> {c}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
