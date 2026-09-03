"""ChopChop_v6_183_PREROLL_TEST.amxd -- prototype rig for the preroll core question.

NOT a version bump. A throwaway test build: v6_183 + a small root-level rig to
answer one thing before Phase 3 is designed for real:

  Does `karma~ set <buffer> / position 0. / window <frac> / play` on a buffer
  filled by `record~` (NOT by karma A) produce a clean, bounded loop with no
  record pass?

Rig (root, unlocked patcher, near x=2600 y=180 -- look for the "PREROLL
PROTOTYPE" comment):

  record~ ---thisBuffer 2 @loop 1   <- ingain_L / ingain_R (device input)
  [1 fill start]  -> record~ inlet 0 = 1   (let it run >5 s of audio in)
  [2 fill stop]   -> record~ inlet 0 = 0
  [3 window .033] -> s ---karmaMsg : "set ---thisBuffer, position 0., window 0.033, play"
  [3b window .5 ] -> ...
  [3c window 1  ] -> ...
  number boxes: karma pos / loop-end ms (rep4) / window ms (rep5) / play state

Expected if the claim holds: after [2] then [3], karma A plays a ~4000 ms loop
(rep5 ~= 4000, rep4 ~= 120000, play state 1, pos sweeps 0..~0.033), audio =
the first 4 s of what record~ captured, no click, no wait.

    python build_preroll_prototype.py
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_183.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_183_PREROLL_TEST.amxd"

X, Y = 2600.0, 180.0


def box(d):
    return {"box": d}


def obj(i, text, dx, dy, w=150, nin=2, nout=1, ot=None, extra=None):
    d = {"id": i, "maxclass": "newobj", "text": text, "numinlets": nin, "numoutlets": nout,
         "outlettype": ot if ot is not None else [""],
         "patching_rect": [X + dx, Y + dy, w, 22.0]}
    if extra:
        d.update(extra)
    return box(d)


def msg(i, text, dx, dy, w=230):
    return box({"id": i, "maxclass": "message", "text": text, "numinlets": 2, "numoutlets": 1,
               "outlettype": [""], "patching_rect": [X + dx, Y + dy, w, 22.0]})


def btn(i, dx, dy):
    return box({"id": i, "maxclass": "button", "numinlets": 1, "numoutlets": 1,
               "outlettype": ["bang"], "patching_rect": [X + dx, Y + dy, 24.0, 24.0]})


def num(i, dx, dy, w=90):
    return box({"id": i, "maxclass": "number", "numinlets": 1, "numoutlets": 2,
               "outlettype": ["", "bang"], "patching_rect": [X + dx, Y + dy, w, 22.0]})


def comment(i, text, dx, dy, w=360):
    return box({"id": i, "maxclass": "comment", "text": text, "numinlets": 1, "numoutlets": 0,
               "patching_rect": [X + dx, Y + dy, w, 20.0]})


def L(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    ids = {b.get("box", b)["id"] for b in root["boxes"]}
    assert "ingain_L" in ids and "ingain_R" in ids
    new = [i for i in ("pt_rec", "pt_b1", "pt_m1", "pt_b2", "pt_m2", "pt_b3", "pt_m3",
                       "pt_b3b", "pt_m3b", "pt_b3c", "pt_m3c", "pt_s", "pt_r0", "pt_n0",
                       "pt_r4", "pt_n4", "pt_r5", "pt_n5", "pt_rp", "pt_np", "pt_lbl", "pt_lbl2")]
    for i in new:
        assert i not in ids, f"collision {i}"

    root["boxes"] += [
        comment("pt_lbl", "PREROLL PROTOTYPE  -- 1 fill start, play >5s in, 2 fill stop, 3/3b/3c window", 0, -28, 620),
        comment("pt_lbl2", "watch: pos sweeps in-window | rep4=loop end ms | rep5=window ms | play", 0, 150, 620),
        obj("pt_rec", "record~ ---thisBuffer 2 @loop 1", 0, 20, 210, nin=3, nout=1, ot=["signal"]),
        btn("pt_b1", 0, 52), msg("pt_m1", "1", 30, 52, 30),
        btn("pt_b2", 90, 52), msg("pt_m2", "0", 120, 52, 30),
        btn("pt_b3", 0, 90), msg("pt_m3", "set ---thisBuffer, position 0., window 0.033, play", 30, 90, 300),
        btn("pt_b3b", 0, 116), msg("pt_m3b", "set ---thisBuffer, position 0., window 0.5, play", 30, 116, 300),
        btn("pt_b3c", 0, 142), msg("pt_m3c", "set ---thisBuffer, position 0., window 1., play", 30, 142, 300),
        obj("pt_s", "s ---karmaMsg", 350, 90, 110, nin=1, nout=0),
        obj("pt_r0", "r ---karmaPos", 0, 178, 110, nin=0, nout=1), num("pt_n0", 120, 178),
        obj("pt_r4", "r ---karmaRep4", 0, 204, 110, nin=0, nout=1), num("pt_n4", 120, 204, 110),
        obj("pt_r5", "r ---karmaRep5", 0, 230, 110, nin=0, nout=1), num("pt_n5", 120, 230, 110),
        obj("pt_rp", "r ---karmaPlaying", 0, 256, 120, nin=0, nout=1), num("pt_np", 130, 256),
    ]
    root["lines"] += [
        L("ingain_L", 0, "pt_rec", 0), L("ingain_R", 0, "pt_rec", 1),
        L("pt_b1", 0, "pt_m1", 0), L("pt_m1", 0, "pt_rec", 0),
        L("pt_b2", 0, "pt_m2", 0), L("pt_m2", 0, "pt_rec", 0),
        L("pt_b3", 0, "pt_m3", 0), L("pt_m3", 0, "pt_s", 0),
        L("pt_b3b", 0, "pt_m3b", 0), L("pt_m3b", 0, "pt_s", 0),
        L("pt_b3c", 0, "pt_m3c", 0), L("pt_m3c", 0, "pt_s", 0),
        L("pt_r0", 0, "pt_n0", 0), L("pt_r4", 0, "pt_n4", 0),
        L("pt_r5", 0, "pt_n5", 0), L("pt_rp", 0, "pt_np", 0),
    ]

    amx.save(OUT)
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size} (base {BASE.stat().st_size})  cycles {total} (base {btot})  problems {nprob}")
    for p, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {p} {d}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
