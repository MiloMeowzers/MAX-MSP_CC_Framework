"""v6_182 -- actually mirror karma A's message stream to karmaB.

Discovery: karmaB never received karma A's transport messages. karma A (obj-20)
inlet 0 is fed DIRECTLY by ~11 sources (record/play, window, INIT, reloop
palette, report/ramp config). The `gB` gate only carries the
p glitching / p transport / directJump side-stream via `kmsg_gate` -- NOT
record/play/stop/window. `p RollingB` was the sole thing sending `record` to
karmaB; v6_180 removed it, so karmaB has had no capture path at all -> silent,
and the A/B mix / mutes have nothing on B to act on.

Fix: for every obj-20 inlet-0 feeder that isn't already mirrored (obj-34 audio
and gA both are), add the same cord to karmaB[0]. No new objects -- 11 cords.
karmaB then records, windows, INITs and reloops exactly when karma A does.

    python phase1_file7_mirror_karmaB.py   # -> ../generated/ChopChop_v6_182.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_181.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_182.amxd"

# (source-id, outlet) pairs currently feeding obj-20 inlet 0 that karmaB lacks
MIRROR = [
    ("obj-13", 2),        # p MessagesToKarma  -> record/play/overdub/jump/position
    ("obj-18", 1),        # t l l  <- p Recording  -> record/play
    ("obj-28", 0),        # p INIT -> stop / window 1 / position 0
    ("obj-31", 0),        # window 0.25  (reloop palette)
    ("obj-38", 0),        # window 1
    ("obj-43", 0),        # window 0.75
    ("obj-45", 0),        # r ---karmaMsg -> window calc + main stream
    ("obj-46", 0),        # loadmess report 150
    ("reinit_ramp", 0),   # ramp 16
    ("reinit_report", 0), # report 20
    ("reinit_snramp", 0), # snramp 16
]


def main():
    amx = load(BASE)
    pb = find_scope(amx.patcher, "p Playback").patcher
    ids = {b.get("box", b)["id"] for b in pb["boxes"]}
    assert "karmaB" in ids

    have = {(s, so) for (s, so, d, di) in
            ((l.get("patchline", l)["source"][0], l.get("patchline", l)["source"][1],
              l.get("patchline", l)["destination"][0], l.get("patchline", l)["destination"][1])
             for l in pb["lines"])
            if d == "obj-20" and di == 0}
    # sanity: every MIRROR pair really does feed obj-20[0] in this file
    for (s, so) in MIRROR:
        assert s in ids, f"missing box {s}"
        assert (s, so) in have, f"{s}[{so}] does not feed obj-20[0] -- refusing to guess"

    kb_have = {(s, so) for (s, so, d, di) in
               ((l.get("patchline", l)["source"][0], l.get("patchline", l)["source"][1],
                 l.get("patchline", l)["destination"][0], l.get("patchline", l)["destination"][1])
                for l in pb["lines"])
               if d == "karmaB" and di == 0}

    added = 0
    for (s, so) in MIRROR:
        if (s, so) in kb_have:
            continue
        pb["lines"].append({"patchline": {"source": [s, so], "destination": ["karmaB", 0]}})
        added += 1
    print(f"added {added} mirror cords to karmaB[0]")

    amx.save(OUT)
    e = find_scope(load(OUT).patcher, "p Playback")
    kb = sorted({(s, so) for (s, so, d, di) in e.lines() if d == "karmaB" and di == 0})
    a20 = sorted({(s, so) for (s, so, d, di) in e.lines() if d == "obj-20" and di == 0})
    print("karmaB[0] feeders:", [x[0] for x in kb])
    missing = [x for x in a20 if x not in kb and x[0] != "gA"]
    print("still only on A (excl. gA):", missing or "none")

    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size}  cycles {total} (base {btot})  problems {nprob}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
