"""Phase 1, file 1 -- make karmaB audible.

Inside `p Playback`, karma A (obj-20) audio outs go to the scope's outlets
obj-23 (L) / obj-25 (R); karmaB audio outs (karmaB[0]/[1]) go nowhere.

This edit inserts two `+~` objects so karma A and karmaB sum into the same
two outlets:

    obj-20[0] --> bmixL[0] --\
                              +~  --> obj-23   (L)
    karmaB[0] --> bmixL[1] --/

    obj-20[1] --> bmixR[0] --\
                              +~  --> obj-25   (R)
    karmaB[1] --> bmixR[1] --/

One coherent change (sum B into the main output). No `---abMix` yet -- file 2
replaces the raw sum with the crossfade. karmaB already records/plays in
lockstep with A (gB gate open, shared messages, bspeed sig~), so after a
capture you should hear the loop ~+6 dB / doubled = the wire proven.

    python phase1_karmab_audible.py           # writes ../generated/ChopChop_v6_175.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_174_BASE.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_175.amxd"


def line(src, so, dst, di):
    return {"patchline": {"source": [src, so], "destination": [dst, di]}}


def newobj(box_id, text, rect):
    return {"box": {
        "id": box_id,
        "maxclass": "newobj",
        "numinlets": 2,
        "numoutlets": 1,
        "outlettype": ["signal"],
        "patching_rect": [float(rect[0]), float(rect[1]), float(rect[2]), 22.0],
        "text": text,
    }}


def main():
    amx = load(BASE)
    pb = find_scope(amx.patcher, "p Playback").patcher

    ids = {(b.get("box", b)).get("id") for b in pb["boxes"]}
    assert "bmixL" not in ids and "bmixR" not in ids, "id collision"
    assert "obj-20" in ids and "obj-23" in ids and "obj-25" in ids and "karmaB" in ids

    # obj-23 rect [35,739], obj-25 rect [143.5,739] -- place the +~ just above each
    pb["boxes"].append(newobj("bmixL", "+~", [35.0, 700.0, 36.0]))
    pb["boxes"].append(newobj("bmixR", "+~", [143.5, 700.0, 36.0]))

    def is_line(entry, s, so, d, di):
        pl = entry.get("patchline", entry)
        return pl["source"] == [s, so] and pl["destination"] == [d, di]

    before = len(pb["lines"])
    pb["lines"] = [e for e in pb["lines"]
                   if not is_line(e, "obj-20", 0, "obj-23", 0)
                   and not is_line(e, "obj-20", 1, "obj-25", 0)]
    removed = before - len(pb["lines"])
    assert removed == 2, f"expected to remove 2 lines, removed {removed}"

    pb["lines"] += [
        line("obj-20", 0, "bmixL", 0),
        line("karmaB", 0, "bmixL", 1),
        line("bmixL", 0, "obj-23", 0),
        line("obj-20", 1, "bmixR", 0),
        line("karmaB", 1, "bmixR", 1),
        line("bmixR", 0, "obj-25", 0),
    ]

    body = amx.minified()
    print(f"minified size {len(body)}  slot {amx.slot}  headroom {amx.slot - len(body)}")
    amx.save(OUT)
    print(f"wrote {OUT}  ({OUT.stat().st_size} bytes; base is {BASE.stat().st_size})")

    # validate: structure clean + cycle total unchanged vs baseline
    per, total, probs = validate.sweep(load(OUT))
    bper, btot, bprobs = validate.sweep(load(BASE))
    print(f"cycles: edit={total} baseline={btot}   structural problems: "
          f"edit={sum(len(v) for v in probs.values())} baseline={sum(len(v) for v in bprobs.values())}")
    ok = (total == btot and not probs and OUT.stat().st_size == BASE.stat().st_size)
    print("PASS" if ok else "FAIL")
    for p, c in per.items():
        if c != bper.get(p, 0):
            print(f"  cycle delta {p}: {bper.get(p,0)} -> {c}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
