"""ChopChop scratch verification patchers -- minimal, no karma~, no buffer~.

Everything is a synthesised blip (cycle~ * line~ env). No buffer~, no poke~,
no play~, no file loading -- so the ONLY thing under test in t2/t3 is whether
poly~ routes a trigger to a voice that makes sound.

  t0_sanity.maxpat   the blip, inline, no poly~  -> proves audio path works
  voice.maxpat       the same blip as a poly~ voice
  t2_poly_attack     fire the poly~ voice against a metronome -> attack tight?
  t3_poly_steal      4 voices, 6 rapid notes -> stealing; target -> VOICE print
  t5_detonate_rhythm tap a rhythm to detonate, replay vs metro, SMF write/read

Run:  python build_test_patchers.py     Out: ../test-patchers/*.maxpat
Max 9 standalone, DSP on. Step 1 is always "click ezdac".
"""
from pathlib import Path

from maxpat import Patch

OUT = Path(__file__).resolve().parents[1] / "test-patchers"


def blip_inline(p, trig_out_id, x, y, freq=330, ms=400):
    """cycle~ freq * line~(1 -> 0 over ms), triggered by a bang from trig_out_id[0]."""
    env = p.msg(f"1, 0 {ms}", at=(x, y), w=110)
    ln = p.obj("line~", at=(x, y + 34), numinlets=2, numoutlets=2, outlettype=["signal", "bang"])
    osc = p.obj(f"cycle~ {freq}", at=(x + 130, y + 34), numinlets=2, numoutlets=1,
                outlettype=["signal"])
    amp = p.obj("*~", at=(x, y + 68), numinlets=2, numoutlets=1, outlettype=["signal"])
    p.connect(trig_out_id, 0, env, 0)
    p.connect(env, 0, ln, 0)
    p.connect(ln, 0, amp, 1)
    p.connect(osc, 0, amp, 0)
    return amp   # signal out


# --------------------------------------------------------------------------- T0
def t0():
    p = Patch("T0 audio-path sanity (no poly~)")
    p.comment("T0  --  no poly~. Click ezdac, then click 'blip' -- you should hear a short "
              "330 Hz tone every click. If this is silent, the problem is DSP / audio setup, "
              "not poly~.", at=(40, 10), w=940)
    b = p.ui("button", at=(40, 60))
    sig = blip_inline(p, b, 40, 100, freq=330, ms=400)
    out = p.obj("*~ 0.3", at=(40, 200))
    dac = p.obj("ezdac~", at=(40, 240), numinlets=2, numoutlets=0)
    p.comment("1) click ezdac", at=(200, 240), w=140)
    p.connect(sig, 0, out, 0)
    p.connect(out, 0, dac, 0)
    p.connect(out, 0, dac, 1)
    return p


# ------------------------------------------------------------------- voice.maxpat
def voice():
    p = Patch("voice")
    p.comment("poly~ voice -- ANY input to in 1 fires a 600 ms 300 Hz blip and reports the "
              "voice index out (out 3). thispoly~ busy on trigger, free on line~ done.",
              at=(40, 10), w=720)
    inn = p.obj("in 1", at=(40, 50), numinlets=0, numoutlets=1)
    tr = p.obj("t b b b", at=(40, 88), numinlets=1, numoutlets=3,
               outlettype=["bang", "bang", "bang"])
    mbusy = p.msg("1", at=(220, 88))
    tp = p.obj("thispoly~", at=(300, 128), numinlets=1, numoutlets=2,
               outlettype=["signal", "signal"])
    env = p.msg("1, 0 600", at=(40, 128), w=110)
    ln = p.obj("line~", at=(40, 162), numinlets=2, numoutlets=2, outlettype=["signal", "bang"])
    osc = p.obj("cycle~ 300", at=(180, 162), numinlets=2, numoutlets=1, outlettype=["signal"])
    amp = p.obj("*~", at=(40, 196), numinlets=2, numoutlets=1, outlettype=["signal"])
    mfree = p.msg("0", at=(220, 196))
    o1 = p.obj("out~ 1", at=(40, 234), numinlets=1, numoutlets=0)
    o2 = p.obj("out~ 2", at=(140, 234), numinlets=1, numoutlets=0)
    oidx = p.obj("out 3", at=(300, 200), numinlets=1, numoutlets=0)

    p.connect(inn, 0, tr, 0)
    p.connect(tr, 2, mbusy, 0)      # fires 1st: mark busy
    p.connect(mbusy, 0, tp, 0)
    p.connect(tr, 1, tp, 0)         # fires 2nd: bang -> report index
    p.connect(tr, 0, env, 0)        # fires 3rd: trigger envelope
    p.connect(env, 0, ln, 0)
    p.connect(ln, 0, amp, 1)
    p.connect(osc, 0, amp, 0)
    p.connect(ln, 1, mfree, 0)      # env done -> free
    p.connect(mfree, 0, tp, 0)
    p.connect(amp, 0, o1, 0)
    p.connect(amp, 0, o2, 0)
    p.connect(tp, 0, oidx, 0)
    return p


# --------------------------------------------------------------------------- T2
def t2():
    p = Patch("T2 poly~ voice attack")
    p.comment("T2  --  hammer 'fire'. Each click should give an instant blip, dead in time "
              "with the metronome click, no lag, clean attack on the scope~.", at=(40, 10), w=940)
    poly = p.obj("poly~ voice.maxpat 4", at=(40, 60), numinlets=1, numoutlets=3,
                 outlettype=["signal", "signal", ""])
    fire = p.ui("button", at=(40, 110))
    note = p.msg("midinote 60 110", at=(120, 110))
    plain = p.msg("bang", at=(260, 110))
    p.comment("2) click 'fire' (sends midinote).  If silent, try the 'bang' box instead "
              "and tell me which works.", at=(40, 140), w=760)

    tr = p.obj("transport", at=(460, 60), numinlets=2, numoutlets=9)
    tst = p.msg("1", at=(460, 96))
    met = p.obj("metro 8n", at=(560, 96), numinlets=2, numoutlets=1, outlettype=["bang"])
    mtog = p.ui("toggle", at=(560, 132))
    mclk = p.obj("click~", at=(560, 168), numinlets=1, numoutlets=1, outlettype=["signal"])
    p.comment("3) transport 1, metro toggle ON = reference grid", at=(460, 36), w=420)

    sc = p.ui("scope~", at=(40, 200), ins=2, outs=0, w=320, h=150)
    idxpr = p.obj("print FIRED", at=(400, 200), numinlets=1, numoutlets=0)
    out = p.obj("*~ 0.4", at=(40, 370))
    dac = p.obj("ezdac~", at=(40, 410), numinlets=2, numoutlets=0)
    p.comment("1) click ezdac", at=(200, 410), w=140)

    p.connect(fire, 0, note, 0)
    p.connect(note, 0, poly, 0)
    p.connect(plain, 0, poly, 0)
    p.connect(tst, 0, tr, 0)
    p.connect(mtog, 0, met, 0)
    p.connect(met, 0, mclk, 0)
    p.connect(poly, 0, sc, 0)
    p.connect(poly, 2, idxpr, 0)
    p.connect(poly, 0, out, 0)
    p.connect(mclk, 0, out, 0)
    p.connect(out, 0, dac, 0)
    p.connect(out, 0, dac, 1)
    return p


# --------------------------------------------------------------------------- T3
def t3():
    p = Patch("T3 poly~ stealing + target")
    p.comment("T3  --  poly~ voice.maxpat 4. Machine-gun the six 'midinote' boxes -> at most "
              "4 blips overlap (older ones cut). 'target 2, 1' then a note -> VOICE prints 2.",
              at=(40, 10), w=960)
    poly = p.obj("poly~ voice.maxpat 4", at=(40, 60), numinlets=1, numoutlets=3,
                 outlettype=["signal", "signal", ""])
    notes = [p.msg(f"midinote {pit} 110", at=(40 + (i % 3) * 170, 110 + (i // 3) * 34))
             for i, pit in enumerate((60, 62, 64, 65, 67, 69))]
    tgt = p.msg("target 2, 1", at=(40, 200), w=120)
    tn = p.msg("midinote 72 110", at=(180, 200))
    pr = p.obj("print VOICE", at=(340, 200), numinlets=1, numoutlets=0)
    p.comment("2) machine-gun the six    3) 'target 2, 1' then this note -> VOICE = 2",
              at=(40, 236), w=620)
    out = p.obj("*~ 0.35", at=(40, 280))
    dac = p.obj("ezdac~", at=(40, 320), numinlets=2, numoutlets=0)
    p.comment("1) click ezdac", at=(200, 320), w=140)
    for m in notes + [tgt, tn]:
        p.connect(m, 0, poly, 0)
    p.connect(poly, 2, pr, 0)
    p.connect(poly, 0, out, 0)
    p.connect(out, 0, dac, 0)
    p.connect(out, 0, dac, 1)
    return p


# --------------------------------------------------------------------------- T5
def t5():
    p = Patch("T5 detonate rhythm round-trip")
    p.comment("T5  --  4n metronome = the grid. Tap a rhythm on the 4 pads (tap = click + "
              "record to detonate). 'start' replays -> replayed clicks should land where you "
              "tapped, vs the same metro. Then 'write t5.mid' / 'read' / 'start'.",
              at=(40, 10), w=980)
    tr = p.obj("transport", at=(40, 55), numinlets=2, numoutlets=9)
    tst = p.msg("1", at=(40, 92))
    tsp = p.msg("0", at=(78, 92))
    grid = p.obj("metro 4n", at=(150, 92), numinlets=2, numoutlets=1, outlettype=["bang"])
    gtog = p.ui("toggle", at=(150, 128))
    gclk = p.obj("click~", at=(150, 168), numinlets=1, numoutlets=1, outlettype=["signal"])
    p.comment("1) ezdac   2) transport 1   3) metro toggle ON", at=(40, 128), w=400)

    pads = [p.msg(f"{pit}", at=(40 + i * 70, 214)) for i, pit in enumerate((60, 62, 64, 65))]
    pclk = p.obj("click~", at=(40, 278), numinlets=1, numoutlets=1, outlettype=["signal"])
    det = p.obj("detonate", at=(260, 278), numinlets=8, numoutlets=8,
                outlettype=["", "", "", "", "", "", "", ""])
    drec = p.msg("record", at=(260, 244))
    dgo = p.msg("start", at=(322, 244))
    dclr = p.msg("clear", at=(374, 244))
    dwr = p.msg("write t5.mid", at=(444, 244))
    drd = p.msg("read", at=(548, 244))
    p.comment("4) 'record'  5) tap a rhythm  6) 'start' replays  7) write / read / start",
              at=(40, 244), w=200)
    ms = p.ui("multislider", at=(260, 320), ins=1, outs=1, w=380, h=90)
    dpr = p.obj("print DET", at=(660, 278), numinlets=1, numoutlets=0)
    out = p.obj("*~ 0.5", at=(40, 340))
    dac = p.obj("ezdac~", at=(40, 380), numinlets=2, numoutlets=0)

    p.connect(tst, 0, tr, 0)
    p.connect(tsp, 0, tr, 0)
    p.connect(gtog, 0, grid, 0)
    p.connect(grid, 0, gclk, 0)
    for m in pads:
        p.connect(m, 0, pclk, 0)
        p.connect(m, 0, det, 0)
    for m in (drec, dgo, dclr, dwr, drd):
        p.connect(m, 0, det, 0)
    p.connect(det, 0, pclk, 0)
    p.connect(det, 1, ms, 0)
    p.connect(det, 0, dpr, 0)
    p.connect(gclk, 0, out, 0)
    p.connect(pclk, 0, out, 0)
    p.connect(out, 0, dac, 0)
    p.connect(out, 0, dac, 1)
    return p


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    import json
    for name, patch in [
        ("t0_sanity.maxpat", t0()),
        ("voice.maxpat", voice()),
        ("t2_poly_attack.maxpat", t2()),
        ("t3_poly_steal.maxpat", t3()),
        ("t5_detonate_rhythm.maxpat", t5()),
    ]:
        path = patch.save(OUT / name)
        json.loads(path.read_text())
        print("wrote", path.name)


if __name__ == "__main__":
    main()
