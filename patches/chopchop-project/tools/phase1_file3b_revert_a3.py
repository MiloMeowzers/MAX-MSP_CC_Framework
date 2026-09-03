"""v6_178 -- revert the A3 region-overlay-under-reverse change, keep the mute toggles.

v6_177 bundled two changes. The A/B mute toggles work; the A3 overlay fix broke
the region overlay on Reloop (normal AND reverse) -- it relocates the whole
region outside the playing area. User: unusable, revert.

This rebuilds from v6_176 and re-applies ONLY the mute-toggle half, so the
`ovr_*` overlay is byte-identical to v6_176 (the pre-A3 behaviour: ~1 slice lag
under reverse, self-correcting on release -- acceptable).

    python phase1_file3b_revert_a3.py   # -> ../generated/ChopChop_v6_178.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_176.amxd"
REF177 = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_177.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_178.amxd"
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
                    "patching_rect": [1660.0, 780.0, 30.0, 18.0], "presentation": 1,
                    "presentation_rect": [float(prect[0]), float(prect[1]), float(prect[2]), float(prect[3])],
                    "text": text, "textcolor": ORANGE, "textjustification": 1, "fontsize": 9.0}}


def rm(lines, *keys):
    def hit(e):
        pl = e.get("patchline", e)
        return any(pl["source"] == [s, so] and pl["destination"] == [d, di] for (s, so, d, di) in keys)
    n0 = len(lines)
    kept = [e for e in lines if not hit(e)]
    return kept, n0 - len(kept)


def main():
    amx = load(BASE)
    root = find_scope(amx.patcher, "/").patcher
    pb = find_scope(amx.patcher, "p Playback").patcher

    # --- mute-toggle half only (identical to v6_177 part A) ---
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
    pb["lines"], nrem = rm(pb["lines"], ("xf_a", 0, "mAL", 1), ("xf_a", 0, "mAR", 1),
                           ("xf_l", 0, "mBL", 1), ("xf_l", 0, "mBR", 1))
    assert nrem == 4, nrem
    pb["lines"] += [
        Ln("vA_r", 0, "vA_m", 0), Ln("vA_m", 0, "vA_l", 0),
        Ln("xf_a", 0, "vA_x", 0), Ln("vA_l", 0, "vA_x", 1),
        Ln("vA_x", 0, "mAL", 1), Ln("vA_x", 0, "mAR", 1),
        Ln("vB_r", 0, "vB_m", 0), Ln("vB_m", 0, "vB_l", 0),
        Ln("xf_l", 0, "vB_x", 0), Ln("vB_l", 0, "vB_x", 1),
        Ln("vB_x", 0, "mBL", 1), Ln("vB_x", 0, "mBR", 1),
    ]

    amx.save(OUT)

    # verify: overlay section identical to v6_176; mute section identical to v6_177
    o176 = find_scope(load(BASE).patcher, "/")
    o178 = find_scope(load(OUT).patcher, "/")
    rev_ids = {b.get("box", b)["id"] for b in o178.patcher["boxes"]
               if b.get("box", b)["id"].startswith("ovr_rev")}
    assert not rev_ids, f"ovr_rev* leaked into v6_178: {rev_ids}"
    sub_dests_176 = sorted((d, di) for (s, so, d, di) in o176.lines() if s == "ovr_sub")
    sub_dests_178 = sorted((d, di) for (s, so, d, di) in o178.lines() if s == "ovr_sub")
    assert sub_dests_176 == sub_dests_178 == [("ovr_add", 0)], (sub_dests_176, sub_dests_178)

    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size}  cycles {total} (base {btot})  problems {nprob}")
    print(f"ovr_sub -> ovr_add restored, no ovr_rev* present")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
