"""Emit the ChopChop scratch verification patchers.

Scope, after two bad batches: scratch patchers are used ONLY for pure
message/Max-object questions with no karma~ in them. Every karma~ question
(loop-definition-from-running-capture, jump attack, ramp seam, buffer
read/write) is deferred to a prototype inside a DUPLICATED copy of the real
device -- per doc 02 and the chopchop-max-testing skill, a from-scratch karma~
harness has failed this project every time it was tried.

Kept (no karma~, self-contained, self-filling buffer):
  voice.maxpat          play~ one-shot voice for poly~ (real done-bang -> frees)
  t2_poly_attack.maxpat pre-instantiated poly~ voice: is the trigger->sound
                        edge tight enough to replace karma~ jump for slicing?
  t3_poly_steal.maxpat  poly~ 4 voices: target routing + voice-stealing + choke
  t5_detonate_rhythm.maxpat  record a tapped rhythm to detonate, replay against
                        a metronome, write/read SMF -- detonate vs coll for the
                        MIDI-at-core sequencer store

Run:  python build_test_patchers.py     Out: ../test-patchers/*.maxpat
Open in Max 9 standalone, DSP on; step 1 is always "click ezdac".
"""
from pathlib import Path

from maxpat import Patch

OUT = Path(__file__).resolve().parents[1] / "test-patchers"
SR = 44100
BUFMS = 4000
STEP = int(BUFMS * SR / 1000 / 16)   # samples between the 16 fill clicks


def fill_block(p, bufname, x, y):
    """Button writing 16 evenly-spaced one-sample clicks into `bufname`."""
    b = p.ui("button", at=(x, y))
    p.comment("2) fill buffer (16 clicks)", at=(x + 40, y), w=190)
    u = p.obj("uzi 16 1", at=(x, y + 40), numinlets=2, numoutlets=3,
              outlettype=["bang", "bang", "int"])
    sub = p.obj("- 1", at=(x, y + 74))
    mul = p.obj(f"* {STEP}", at=(x, y + 108))
    tr = p.obj("t b i", at=(x, y + 142), numinlets=1, numoutlets=2, outlettype=["bang", "int"])
    one = p.msg("1.", at=(x, y + 176))
    pk = p.obj(f"poke~ {bufname}", at=(x, y + 210), numinlets=3, numoutlets=0)
    p.connect(b, 0, u, 0)
    p.connect(u, 2, sub, 0)
    p.connect(sub, 0, mul, 0)
    p.connect(mul, 0, tr, 0)
    p.connect(tr, 1, pk, 1)
    p.connect(tr, 0, one, 0)
    p.connect(one, 0, pk, 0)
    return b


def voice():
    """poly~ voice: bang -> play~ a fixed ms slice of tbuf once, free on done."""
    p = Patch("voice")
    p.comment("poly~ voice -- bang plays 1000..1250 ms of tbuf once, frees on line~ done",
              at=(40, 10), w=600)
    inn = p.obj("in 1", at=(40, 50), numinlets=1, numoutlets=1)
    idx = p.obj("thispoly~", at=(340, 50), numinlets=1, numoutlets=2,
                outlettype=["signal", "signal"])
    trig = p.obj("t b b", at=(40, 90), numinlets=1, numoutlets=2, outlettype=["bang", "bang"])
    busy = p.msg("1", at=(210, 90))
    seg = p.msg("1000, 1250 250", at=(40, 130), w=150)
    ln = p.obj("line~", at=(40, 170), numinlets=2, numoutlets=2, outlettype=["signal", "bang"])
    pl = p.obj("play~ tbuf 2", at=(40, 210), numinlets=1, numoutlets=3,
               outlettype=["signal", "signal", "bang"])
    free = p.msg("0", at=(210, 250))
    rep = p.obj("out 3", at=(340, 130), numinlets=1, numoutlets=0)
    o1 = p.obj("out~ 1", at=(40, 260), numinlets=1, numoutlets=0)
    o2 = p.obj("out~ 2", at=(150, 260), numinlets=1, numoutlets=0)
    p.connect(inn, 0, trig, 0)
    p.connect(trig, 0, seg, 0)
    p.connect(trig, 1, busy, 0)
    p.connect(busy, 0, idx, 0)
    p.connect(idx, 0, rep, 0)
    p.connect(seg, 0, ln, 0)
    p.connect(ln, 0, pl, 0)
    p.connect(ln, 1, free, 0)
    p.connect(free, 0, idx, 0)
    p.connect(pl, 0, o1, 0)
    p.connect(pl, 1, o2, 0)
    return p


def t2():
    p = Patch("T2 poly~ voice attack")
    p.comment("T2  --  does a pre-instantiated poly~/play~ voice fire tight enough to "
              "replace karma~ jump for slice triggering?  Fire repeatedly, watch the "
              "scope~ attack, judge by ear against the metronome.", at=(40, 10), w=940)
    p.obj("buffer~ tbuf 4000 2", at=(40, 46))
    fill_block(p, "tbuf", 720, 40)
    p.comment("1) click ezdac", at=(40, 44), w=140)

    met = p.obj("metro 8n", at=(300, 80), numinlets=2, numoutlets=1, outlettype=["bang"])
    mtog = p.ui("toggle", at=(300, 116))
    tr = p.obj("transport", at=(430, 80), numinlets=2, numoutlets=9)
    tst = p.msg("1", at=(430, 116))
    mclk = p.obj("click~", at=(300, 156), numinlets=1, numoutlets=1, outlettype=["signal"])
    p.comment("3) transport 1, metro toggle ON (reference grid)", at=(300, 46), w=420)

    fire = p.ui("button", at=(40, 100))
    poly = p.obj("poly~ voice.maxpat 4", at=(40, 140), numinlets=1, numoutlets=3,
                 outlettype=["signal", "signal", ""])
    note = p.msg("midinote 60 110", at=(160, 100))
    p.comment("4) hammer 'fire' -- attack should be instant, no lag vs the metro click",
              at=(40, 240), w=560)

    sc = p.ui("scope~", at=(40, 270), ins=2, outs=0, w=300, h=150)
    out = p.obj("*~ 0.5", at=(40, 440))
    dac = p.obj("ezdac~", at=(40, 490), numinlets=2, numoutlets=0)

    p.connect(mtog, 0, met, 0)
    p.connect(tst, 0, tr, 0)
    p.connect(met, 0, mclk, 0)
    p.connect(fire, 0, note, 0)
    p.connect(note, 0, poly, 0)
    p.connect(poly, 0, sc, 0)
    p.connect(poly, 0, out, 0)
    p.connect(mclk, 0, out, 0)
    p.connect(out, 0, dac, 0)
    p.connect(out, 0, dac, 1)
    return p


def t3():
    p = Patch("T3 poly~ stealing + target")
    p.comment("T3  --  poly~ voice.maxpat 4.  Machine-gun the 6 notes -> only 4 sound at "
              "once (stealing).  'target 2, 1' then a note -> VOICE print reads 2.",
              at=(40, 10), w=940)
    p.obj("buffer~ tbuf 4000 2", at=(40, 46))
    fill_block(p, "tbuf", 760, 40)
    p.comment("1) click ezdac", at=(40, 44), w=140)

    poly = p.obj("poly~ voice.maxpat 4", at=(40, 110), numinlets=1, numoutlets=3,
                 outlettype=["signal", "signal", ""])
    notes = []
    for i, pit in enumerate((60, 62, 64, 65, 67, 69)):
        notes.append(p.msg(f"midinote {pit} 110", at=(40 + (i % 3) * 160, 160 + (i // 3) * 34)))
    p.comment("3) machine-gun these six", at=(40, 232), w=320)

    tgt = p.msg("target 2, 1", at=(40, 270), w=120)
    tn = p.msg("midinote 72 110", at=(180, 270))
    p.comment("4) 'target 2, 1' then this -> VOICE = 2", at=(40, 300), w=420)
    pr = p.obj("print VOICE", at=(340, 270), numinlets=1, numoutlets=0)

    out = p.obj("*~ 0.4", at=(40, 340))
    dac = p.obj("ezdac~", at=(40, 390), numinlets=2, numoutlets=0)
    for m in notes + [tgt, tn]:
        p.connect(m, 0, poly, 0)
    p.connect(poly, 2, pr, 0)
    p.connect(poly, 0, out, 0)
    p.connect(out, 0, dac, 0)
    p.connect(out, 0, dac, 1)
    return p


def t5():
    p = Patch("T5 detonate rhythm round-trip")
    p.comment("T5  --  4n metronome = the grid.  Tap a rhythm on the 4 pads (each tap clicks "
              "AND records to detonate).  'start' replays -> replayed clicks should sit where "
              "you tapped, against the same metro.  Then 'write t5.mid' / 'read' / 'start'.",
              at=(40, 10), w=980)

    tr = p.obj("transport", at=(40, 55), numinlets=2, numoutlets=9)
    tst = p.msg("1", at=(40, 92))
    tsp = p.msg("0", at=(78, 92))
    grid = p.obj("metro 4n", at=(150, 92), numinlets=2, numoutlets=1, outlettype=["bang"])
    gtog = p.ui("toggle", at=(150, 128))
    gclk = p.obj("click~", at=(150, 168), numinlets=1, numoutlets=1, outlettype=["signal"])
    p.comment("1) ezdac   2) transport 1   3) metro toggle ON", at=(40, 128), w=400)

    pads = [p.msg(f"{pit}", at=(40 + i * 70, 214)) for i, pit in enumerate((60, 62, 64, 65))]
    p.comment("4) 'record'  5) tap a rhythm  6) 'start' replays", at=(40, 246), w=460)
    pclk = p.obj("click~", at=(40, 278), numinlets=1, numoutlets=1, outlettype=["signal"])

    det = p.obj("detonate", at=(260, 278), numinlets=8, numoutlets=8,
                outlettype=["", "", "", "", "", "", "", ""])
    drec = p.msg("record", at=(260, 244))
    dgo = p.msg("start", at=(322, 244))
    dclr = p.msg("clear", at=(374, 244))
    dwr = p.msg("write t5.mid", at=(444, 244))
    drd = p.msg("read", at=(548, 244))
    ms = p.ui("multislider", at=(260, 320), ins=1, outs=1, w=380, h=90)
    dpr = p.obj("print DET", at=(660, 278), numinlets=1, numoutlets=0)

    out = p.obj("*~ 0.5", at=(40, 340))
    dac = p.obj("ezdac~", at=(40, 390), numinlets=2, numoutlets=0)

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
