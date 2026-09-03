"""v6_177 -- two independent changes bundled at user request:

A) Hard mute toggles for karma A and karma B.
   Two live.toggle params (enableA / enableB, enum off/on, initial 1) in the
   OVERDUB presentation panel, sending ---voiceOnA / ---voiceOnB. In p Playback
   each drives a line~ (init 1.) into a new `*~` folded onto the file-2 gain
   signals: A gain = (1-mix) * voiceOnA, B gain = mix * voiceOnB. Toggle off ->
   line~ ramps to 0 -> that voice silenced (12 ms, click-free). Default 1 =
   unchanged on load.

B) Region overlay under reverse (roadmap A3).
   The per-slice test lights `((i - s + 16) % 16) < n` -- correct forward, wrong
   under reverse (region lies behind the playhead). Insert `gate 2 1` on
   ---effectiveReverse selecting `ovr_sub` (i-s, forward, outlet 0) or its
   negation `* -1` (= s-i, reverse, outlet 1) into `ovr_add`. A `change -> t b i`
   sets the gate control (+1 -> 1|2) then re-fires `ovr_fire3` so the overlay
   repaints when direction flips. `gate 2 1` defaults to forward so a load with
   no ---effectiveReverse still works.

    python phase1_file3_enables_reverse.py   # -> ../generated/ChopChop_v6_177.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_176.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_177.amxd"

ORANGE = [1.0, 0.709803921568627, 0.196078431372549, 1.0]


def Ln(s, so, d, di):
    return {"patchline": {"source": [s, so], "destination": [d, di]}}


def O(i, text, rect, nin=2, nout=1, ot=None):
    return {"box": {"id": i, "maxclass": "newobj", "numinlets": nin, "numoutlets": nout,
                    "outlettype": ot if ot is not None else [""],
                    "patching_rect": [float(rect[0]), float(rect[1]), float(rect[2]), 20.0],
                    "text": text}}


def M(i, text, rect):
    return {"box": {"id": i, "maxclass": "message", "numinlets": 2, "numoutlets": 1,
                    "outlettype": [""], "patching_rect": [float(rect[0]), float(rect[1]),
                    float(rect[2]), 20.0], "text": text}}


def toggle(i, longname, shortname, prect, patchrect):
    return {"box": {
        "id": i, "maxclass": "live.toggle", "numinlets": 1, "numoutlets": 1,
        "outlettype": [""], "parameter_enable": 1, "presentation": 1,
        "patching_rect": [float(patchrect[0]), float(patchrect[1]), 20.0, 20.0],
        "presentation_rect": [float(prect[0]), float(prect[1]), float(prect[2]), float(prect[3])],
        "varname": i,
        "saved_attribute_attributes": {"valueof": {
            "parameter_enum": ["off", "on"], "parameter_longname": longname,
            "parameter_shortname": shortname, "parameter_mmax": 1, "parameter_modmode": 0,
            "parameter_type": 2, "parameter_initial_enable": 1, "parameter_initial": [1]}}}}


def label(i, text, prect):
    return {"box": {"id": i, "maxclass": "comment", "numinlets": 1, "numoutlets": 0,
                    "patching_rect": [1660.0, 780.0, 30.0, 18.0],
                    "presentation": 1,
                    "presentation_rect": [float(prect[0]), float(prect[1]), float(prect[2]), float(prect[3])],
                    "text": text, "textcolor": ORANGE, "textjustification": 1, "fontsize": 9.0}}


def rm(lines, *keys):
    def hit(e):
        pl = e.get("patchline", e)
        return any(pl["source"] == [s, so] and pl["destination"] == [d, di]
                   for (s, so, d, di) in keys)
    n0 = len(lines)
    kept = [e for e in lines if not hit(e)]
    return kept, n0 - len(kept)


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    pb = find_scope(amx.patcher, "p Playback").patcher

    # ---- A: enable/mute toggles ------------------------------------------------
    root["boxes"] += [
        toggle("en_a", "enableA", "Enable A", [716, 118, 14, 14], [520, 440]),
        toggle("en_b", "enableB", "Enable B", [750, 118, 14, 14], [548, 440]),
        label("en_a_lbl", "A", [732, 119, 12, 13]),
        label("en_b_lbl", "B", [766, 119, 12, 13]),
        O("ena_s", "s ---voiceOnA", [520, 470, 90], nin=1, nout=0),
        O("enb_s", "s ---voiceOnB", [620, 470, 90], nin=1, nout=0),
    ]
    root["lines"] += [Ln("en_a", 0, "ena_s", 0), Ln("en_b", 0, "enb_s", 0)]

    pb["boxes"] += [
        O("vA_r", "r ---voiceOnA", [470, 600, 90], nin=0, nout=1),
        M("vA_m", "$1 12", [470, 624, 44]),
        O("vA_l", "line~ 1.", [470, 648, 44], nin=2, nout=2, ot=["signal", "bang"]),
        O("vA_x", "*~", [430, 690, 30], ot=["signal"]),
        O("vB_r", "r ---voiceOnB", [560, 600, 90], nin=0, nout=1),
        M("vB_m", "$1 12", [560, 624, 44]),
        O("vB_l", "line~ 1.", [560, 648, 44], nin=2, nout=2, ot=["signal", "bang"]),
        O("vB_x", "*~", [80, 690, 30], ot=["signal"]),
    ]
    pb["lines"], nrem_a = rm(pb["lines"],
                             ("xf_a", 0, "mAL", 1), ("xf_a", 0, "mAR", 1),
                             ("xf_l", 0, "mBL", 1), ("xf_l", 0, "mBR", 1))
    assert nrem_a == 4, nrem_a
    pb["lines"] += [
        Ln("vA_r", 0, "vA_m", 0), Ln("vA_m", 0, "vA_l", 0),
        Ln("xf_a", 0, "vA_x", 0), Ln("vA_l", 0, "vA_x", 1),
        Ln("vA_x", 0, "mAL", 1), Ln("vA_x", 0, "mAR", 1),
        Ln("vB_r", 0, "vB_m", 0), Ln("vB_m", 0, "vB_l", 0),
        Ln("xf_l", 0, "vB_x", 0), Ln("vB_l", 0, "vB_x", 1),
        Ln("vB_x", 0, "mBL", 1), Ln("vB_x", 0, "mBR", 1),
    ]

    # ---- B: region overlay under reverse ------------------------------------
    root["boxes"] += [
        O("ovr_revr", "r ---effectiveReverse", [1600, 2040, 130], nin=0, nout=1),
        O("ovr_revchg", "change", [1600, 2064, 50]),
        O("ovr_revt", "t b i", [1600, 2088, 44], nin=1, nout=2, ot=["bang", "int"]),
        O("ovr_revinc", "+ 1", [1600, 2112, 34]),
        O("ovr_revgate", "gate 2 1", [1500, 2058, 54], nin=2, nout=2, ot=["", ""]),
        O("ovr_revneg", "* -1", [1500, 2090, 40]),
    ]
    root["lines"], nrem_b = rm(root["lines"], ("ovr_sub", 0, "ovr_add", 0))
    assert nrem_b == 1, nrem_b
    root["lines"] += [
        Ln("ovr_sub", 0, "ovr_revgate", 1),
        Ln("ovr_revgate", 0, "ovr_add", 0),
        Ln("ovr_revgate", 1, "ovr_revneg", 0),
        Ln("ovr_revneg", 0, "ovr_add", 0),
        Ln("ovr_revr", 0, "ovr_revchg", 0),
        Ln("ovr_revchg", 0, "ovr_revt", 0),
        Ln("ovr_revt", 1, "ovr_revinc", 0),
        Ln("ovr_revinc", 0, "ovr_revgate", 0),
        Ln("ovr_revt", 0, "ovr_fire3", 0),
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
    for p, plist in probs.items():
        for k, d in plist:
            print(f"  [{k}] {p} {d}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
