"""v6_181 -- default the A/B mute gains to unity on load.

v6_180 (and v6_177-179) have no audio on a fresh load: the mute chain's
`vA_l` / `vB_l` (`line~ 1.`) do not reliably present 1.0 at instantiation, and a
`parameter_enable` `live.toggle` does not guarantee an outlet bang on device
load (Live restores parameter values AFTER loadbang -- the reason this device
has explicit INIT chains). So `vA_x = xf_a * vA_l = 1 * 0 = 0` -> karma A muted,
with nothing to correct it until the toggle is touched. In v6_177 the toggles
WERE clicked during testing, which is why it seemed fine.

Fix: one `loadbang -> [1 15( -> vA_l / vB_l` in p Playback so both mute line~
ramp to unity at load. When a toggle is moved it still drives its line~
normally; a saved "off" state that re-fires on restore still wins.

    python phase1_file6_mute_loadinit.py   # -> ../generated/ChopChop_v6_181.amxd
"""
from pathlib import Path

from ccamxd import load, find_scope
import validate

BASE = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_180.amxd"
OUT = Path(__file__).resolve().parents[1] / "generated" / "ChopChop_v6_181.amxd"


def main():
    amx = load(BASE)
    pb = find_scope(amx.patcher, "p Playback").patcher
    ids = {b.get("box", b)["id"] for b in pb["boxes"]}
    for n in ("vA_l", "vB_l"):
        assert n in ids, n
    for n in ("vmute_lb", "vmute_lbm"):
        assert n not in ids, f"id collision {n}"

    pb["boxes"] += [
        {"box": {"id": "vmute_lb", "maxclass": "newobj", "numinlets": 1, "numoutlets": 1,
                 "outlettype": ["bang"], "patching_rect": [400.0, 570.0, 60.0, 20.0],
                 "text": "loadbang"}},
        {"box": {"id": "vmute_lbm", "maxclass": "message", "numinlets": 2, "numoutlets": 1,
                 "outlettype": [""], "patching_rect": [400.0, 594.0, 40.0, 20.0],
                 "text": "1 15"}},
    ]
    pb["lines"] += [
        {"patchline": {"source": ["vmute_lb", 0], "destination": ["vmute_lbm", 0]}},
        {"patchline": {"source": ["vmute_lbm", 0], "destination": ["vA_l", 0]}},
        {"patchline": {"source": ["vmute_lbm", 0], "destination": ["vB_l", 0]}},
    ]

    amx.save(OUT)
    e = find_scope(load(OUT).patcher, "p Playback")
    for tgt in ("vA_l", "vB_l"):
        feed = sorted(s for (s, so, d, di) in e.lines() if d == tgt and di == 0)
        print(f"{tgt} inlet0 feeders: {feed}")
    per, total, probs = validate.sweep(load(OUT))
    _, btot, _ = validate.sweep(load(BASE))
    nprob = sum(len(v) for v in probs.values())
    ok = (total == btot and nprob == 0 and OUT.stat().st_size == BASE.stat().st_size)
    print(f"size {OUT.stat().st_size}  cycles {total} (base {btot})  problems {nprob}")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
