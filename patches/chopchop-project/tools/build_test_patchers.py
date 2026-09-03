"""Emit the T1-T6 scratch verification patchers from context.md Research R7.

Run:  python build_test_patchers.py
Out:  patches/chopchop-project/test-patchers/*.maxpat

These are throwaway. Open in Max 9 (standalone, DSP on), click the numbered
steps left-to-right, read the result, report back, delete. karma~ must be in
the Max search path (it is, since the device uses it).
"""
from pathlib import Path

from maxpat import Patch

OUT = Path(__file__).resolve().parents[1] / "test-patchers"


# --------------------------------------------------------------------------- T1
def t1():
    """Read a buffer with groove~ while record~ writes the same buffer."""
    p = Patch("T1 buffer read/write contention")
    p.comment("T1  --  does groove~ glitch while record~ writes the SAME buffer?  "
              "(rolling-karmaB contention)", at=(40, 10), w=760)
    p.obj("buffer~ tbuf 6000 2", at=(40, 50))

    # source to record: an audible tone so dropouts are obvious
    osc = p.obj("cycle~ 180", at=(40, 100), numinlets=2)
    srcm = p.obj("*~ 0.4", at=(40, 140))

    tgl = p.ui("toggle", at=(240, 100))
    rec = p.obj("record~ tbuf 2", at=(240, 140), numinlets=3, numoutlets=1, outlettype=["signal"])
    p.comment("2) record ON", at=(240, 80), w=120)

    rate = p.ui("flonum", at=(440, 100))
    ratesig = p.obj("sig~ 1.", at=(440, 140), numinlets=1)
    gr = p.obj("groove~ tbuf 2", at=(440, 190), numinlets=3, numoutlets=2,
               outlettype=["signal", "signal"])
    lp0 = p.msg("0", at=(600, 150))
    lp1 = p.msg("6000", at=(640, 150))
    startloop = p.msg("startloop", at=(560, 120))
    p.comment("3) rate 1.  then  4) startloop   5) listen for zipper/dropout while rec runs",
              at=(440, 90), w=420)

    outm = p.obj("*~ 0.5", at=(440, 240))
    mtr = p.ui("meter~", at=(620, 240), ins=1, outs=1)
    dac = p.obj("ezdac~", at=(440, 300), numinlets=2, numoutlets=0)
    p.comment("1) click ezdac (DSP on)", at=(440, 340), w=220)

    p.connect(osc, 0, srcm, 0)
    p.connect(srcm, 0, rec, 0)
    p.connect(tgl, 0, rec, 0)
    p.connect(rate, 0, ratesig, 0)
    p.connect(ratesig, 0, gr, 0)
    p.connect(lp0, 0, gr, 1)
    p.connect(lp1, 0, gr, 2)
    p.connect(startloop, 0, gr, 0)
    p.connect(gr, 0, outm, 0)
    p.connect(gr, 0, mtr, 0)
    p.connect(outm, 0, dac, 0)
    p.connect(outm, 0, dac, 1)
    return p


# --------------------------------------------------------------------------- T2
def t2_voice():
    """poly~ voice: bang inlet -> groove~ one-shot of a fixed slice."""
    p = Patch("T2 voice")
    p.comment("poly~ voice -- bang plays slice [start,end] ms of tbuf once", at=(40, 10), w=520)
    inn = p.obj("in 1", at=(40, 50), numinlets=1, numoutlets=1)
    tp = p.obj("thispoly~", at=(240, 50), numinlets=1, numoutlets=2, outlettype=["signal", "signal"])
    busy = p.msg("1", at=(240, 90))
    st = p.msg("startloop", at=(40, 90))
    slo = p.msg("500", at=(120, 90))
    shi = p.msg("875", at=(160, 90))
    rsig = p.obj("sig~ 1.", at=(40, 130), numinlets=1)
    gr = p.obj("groove~ tbuf 2", at=(40, 170), numinlets=3, numoutlets=2,
               outlettype=["signal", "signal"])
    o1 = p.obj("out~ 1", at=(40, 220), numinlets=1, numoutlets=0)
    o2 = p.obj("out~ 2", at=(160, 220), numinlets=1, numoutlets=0)
    p.connect(inn, 0, st, 0)
    p.connect(inn, 0, busy, 0)
    p.connect(busy, 0, tp, 0)
    p.connect(slo, 0, gr, 1)
    p.connect(shi, 0, gr, 2)
    p.connect(rsig, 0, gr, 0)
    p.connect(st, 0, gr, 0)
    p.connect(gr, 0, o1, 0)
    p.connect(gr, 1, o2, 0)
    return p


def t2():
    """poly~ note-on vs karma~ jump: trigger both, compare attack on two scope~."""
    p = Patch("T2 poly~ vs karma~ trigger")
    p.comment("T2  --  fire a poly~ voice and a karma~ jump from the same bang; "
              "compare attack tightness on the two scope~ / by ear", at=(40, 10), w=820)
    p.obj("buffer~ tbuf 6000 2", at=(40, 50))

    # prime tbuf with a click track so slice starts are audible transients
    fill = p.msg("fill tbuf 0.", at=(240, 50))  # placeholder; user records real audio first
    p.comment("0) record a few seconds into tbuf first (drop audio on the buffer~, or "
              "wire an input) -- slices need transients to judge attack", at=(40, 86), w=820)

    bng = p.ui("button", at=(40, 120))
    tb = p.obj("t b b", at=(40, 160), numinlets=1, numoutlets=2, outlettype=["bang", "bang"])
    p.comment("1) click ezdac   2) click this button to fire both", at=(40, 200), w=380)

    poly = p.obj("poly~ t2_voice.maxpat 4", at=(40, 240), numinlets=1, numoutlets=2,
                 outlettype=["signal", "signal"])
    polynote = p.msg("midinote 60 100", at=(160, 200))

    ksig = p.obj("sig~ 1.", at=(360, 120), numinlets=1)
    karma = p.obj("karma~ tbuf 2", at=(360, 200), numinlets=3, numoutlets=3,
                  outlettype=["signal", "signal", ""])
    kjump = p.msg("jump 0.5", at=(360, 160))
    krep = p.msg("report 200", at=(500, 160))

    scL = p.ui("scope~", at=(40, 320), ins=2, outs=0, w=200, h=120)
    scR = p.ui("scope~", at=(360, 320), ins=2, outs=0, w=200, h=120)
    mix = p.obj("*~ 0.5", at=(40, 470))
    kmix = p.obj("*~ 0.5", at=(360, 470))
    dac = p.obj("ezdac~", at=(200, 520), numinlets=2, numoutlets=0)

    p.connect(bng, 0, tb, 0)
    p.connect(tb, 1, polynote, 0)
    p.connect(tb, 0, kjump, 0)
    p.connect(polynote, 0, poly, 0)
    p.connect(kjump, 0, karma, 0)
    p.connect(krep, 0, karma, 0)
    p.connect(ksig, 0, karma, 2)
    p.connect(poly, 0, scL, 0)
    p.connect(poly, 0, mix, 0)
    p.connect(karma, 0, scR, 0)
    p.connect(karma, 0, kmix, 0)
    p.connect(mix, 0, dac, 0)
    p.connect(kmix, 0, dac, 1)
    return p


# --------------------------------------------------------------------------- T3
def t3():
    """poly~ voice-stealing + choke: 16 home voices, spill, per-pad choke group."""
    p = Patch("T3 poly~ stealing + choke")
    p.comment("T3  --  poly~ @voices 16: does `target N` give a stable home voice, "
              "does `midinote` steal sanely, does a shared note in a choke group cut group-mates?",
              at=(40, 10), w=880)
    p.obj("buffer~ tbuf 6000 2", at=(40, 50))
    poly = p.obj("poly~ t2_voice.maxpat 16", at=(40, 100), numinlets=1, numoutlets=2,
                 outlettype=["signal", "signal"])

    m_target = p.msg("target 3, 1", at=(40, 160))
    m_note = p.msg("midinote 60 100", at=(200, 160))
    m_note2 = p.msg("midinote 62 100", at=(360, 160))
    m_flood = p.msg("midinote 64 100", at=(520, 160))
    p.comment("1) target then note -> voice 3    2) spam midinote past 16 -> watch steal    "
              "3) two notes same pitch -> choke?", at=(40, 200), w=880)

    kb = p.ui("kslider", at=(40, 250), ins=2, outs=2, w=320, h=80)
    mk = p.obj("makenote 100 400", at=(40, 340), numinlets=3, numoutlets=2, outlettype=["", ""])
    fmt = p.obj("t l", at=(40, 380), numinlets=1, numoutlets=1)
    pre = p.obj("prepend midinote", at=(40, 420))

    mix = p.obj("*~ 0.4", at=(40, 470))
    dac = p.obj("ezdac~", at=(40, 520), numinlets=2, numoutlets=0)
    p.comment("0) click ezdac", at=(200, 520), w=140)

    for m in (m_target, m_note, m_note2, m_flood):
        p.connect(m, 0, poly, 0)
    p.connect(kb, 0, mk, 0)
    p.connect(kb, 1, mk, 1)
    p.connect(mk, 0, pre, 0)
    p.connect(pre, 0, poly, 0)
    p.connect(poly, 0, mix, 0)
    p.connect(mix, 0, dac, 0)
    p.connect(mix, 0, dac, 1)
    return p


# --------------------------------------------------------------------------- T4
def t4():
    """karma~ define-loop-from-running-capture: stop->bounds->play vs bare window; ramp seam."""
    p = Patch("T4 karma~ loop definition + ramp seam")
    p.comment("T4  --  a karma~ is recording a rolling capture. Define a shorter loop from it: "
              "compare  (a) window 0.5   vs   (b) stop -> position/window -> play.  "
              "Then sweep ramp/snramp 16 -> 200 and listen at the seam.", at=(40, 10), w=900)
    p.obj("buffer~ tbuf 12000 2", at=(40, 50))

    osc = p.obj("cycle~ 200", at=(40, 100), numinlets=2)
    src = p.obj("*~ 0.4", at=(40, 140))
    ksig = p.obj("sig~ 1.", at=(220, 100), numinlets=1)
    karma = p.obj("karma~ tbuf 2", at=(220, 200), numinlets=3, numoutlets=3,
                  outlettype=["signal", "signal", ""])

    m_rec = p.msg("record", at=(220, 140))
    m_rep = p.msg("report 300", at=(340, 140))
    m_ramp = p.msg("ramp 16, snramp 16", at=(460, 100))
    m_ramp2 = p.msg("ramp 200, snramp 200", at=(460, 140))
    m_win = p.msg("window 0.5", at=(220, 260))
    m_stopdef = p.msg("stop, position 0., window 0.5, play", at=(220, 300), w=260)
    p.comment("1) ezdac  2) record  3) let it roll a few s  "
              "4a) window 0.5   OR   4b) stop/position/window/play   5) toggle ramp msgs",
              at=(40, 340), w=900)

    rep = p.obj("unpack f i i f f f", at=(460, 240), numinlets=1, numoutlets=6,
                outlettype=["float", "int", "int", "float", "float", "float"])
    n_pos = p.ui("flonum", at=(460, 290), w=90)
    n_end = p.ui("flonum", at=(560, 290), w=90)
    n_win = p.ui("flonum", at=(660, 290), w=90)
    pr = p.obj("print KARMA", at=(460, 330), numinlets=1, numoutlets=0)

    mix = p.obj("*~ 0.5", at=(40, 300))
    dac = p.obj("ezdac~", at=(40, 360), numinlets=2, numoutlets=0)

    p.connect(osc, 0, src, 0)
    p.connect(src, 0, karma, 0)
    p.connect(src, 0, karma, 1)
    p.connect(ksig, 0, karma, 2)
    for m in (m_rec, m_rep, m_ramp, m_ramp2, m_win, m_stopdef):
        p.connect(m, 0, karma, 0)
    p.connect(karma, 2, rep, 0)
    p.connect(rep, 0, n_pos, 0)
    p.connect(rep, 4, n_end, 0)
    p.connect(rep, 5, n_win, 0)
    p.connect(rep, 0, pr, 0)
    p.connect(karma, 0, mix, 0)
    p.connect(mix, 0, dac, 0)
    p.connect(mix, 0, dac, 1)
    return p


# --------------------------------------------------------------------------- T5
def t5():
    """detonate round-trip: record (dt,pitch,vel,dur) vs transport, replay under tempo change."""
    p = Patch("T5 detonate MIDI round-trip")
    p.comment("T5  --  record pad events into detonate against the transport, play back, "
              "check timing faithful; then change tempo and replay; then write/read an SMF.",
              at=(40, 10), w=880)

    tp = p.obj("transport", at=(40, 50), numinlets=2, numoutlets=9)
    startm = p.msg("1", at=(40, 90))
    stopm = p.msg("0", at=(80, 90))
    tempo = p.ui("flonum", at=(140, 90), w=90)
    tempopre = p.obj("prepend tempo", at=(140, 130))

    kb = p.ui("kslider", at=(40, 170), ins=2, outs=2, w=300, h=80)
    mk = p.obj("makenote 100 300", at=(40, 260), numinlets=3, numoutlets=2, outlettype=["", ""])

    # detonate inlets: 0 pitch/bang, 1 delta-time, 2 duration, 3 velocity ...
    det = p.obj("detonate", at=(40, 320), numinlets=8, numoutlets=8,
                outlettype=["", "", "", "", "", "", "", ""])
    rec = p.msg("record", at=(240, 300))
    play = p.msg("start", at=(300, 300))
    clr = p.msg("clear", at=(360, 300))
    wr = p.msg("write t5.mid", at=(240, 260))
    rd = p.msg("read", at=(360, 260))
    p.comment("1) tempo 120, transport 1   2) 'record', play kslider   3) 'clear'? no -- "
              "'start' to replay   4) tempo 90, 'start' again   5) 'write', 'read'",
              at=(40, 380), w=880)

    mo = p.obj("noteout", at=(40, 430), numinlets=3, numoutlets=0)
    pr = p.obj("print DET", at=(240, 430), numinlets=1, numoutlets=0)

    p.connect(startm, 0, tp, 0)
    p.connect(stopm, 0, tp, 0)
    p.connect(tempo, 0, tempopre, 0)
    p.connect(tempopre, 0, tp, 0)
    p.connect(kb, 0, mk, 0)
    p.connect(kb, 1, mk, 1)
    p.connect(mk, 0, det, 0)
    p.connect(mk, 1, det, 3)
    for m in (rec, play, clr, wr, rd):
        p.connect(m, 0, det, 0)
    p.connect(det, 0, mo, 0)
    p.connect(det, 3, mo, 1)
    p.connect(det, 0, pr, 0)
    return p


# --------------------------------------------------------------------------- T6
def t6():
    """bar-edge-once: phasor~ @lock 1 -> delta~ -> <~ -0.5 -> edge~ -> onebang, re-armed."""
    p = Patch("T6 transport bar-edge once")
    p.comment("T6  --  exactly one bang per armed bar edge, transport-locked, no drift. "
              "Arm, watch the counter tick once per bar; leave running for minutes.",
              at=(40, 10), w=840)

    tp = p.obj("transport", at=(40, 50), numinlets=2, numoutlets=9)
    startm = p.msg("1", at=(40, 90))
    p.comment("1) transport 1", at=(40, 120), w=120)

    ph = p.obj("phasor~ @frequency 1n @lock 1", at=(220, 90), numinlets=2, numoutlets=1,
               outlettype=["signal"])
    dl = p.obj("delta~", at=(220, 130), numinlets=1, numoutlets=1, outlettype=["signal"])
    lt = p.obj("<~ -0.5", at=(220, 170), numinlets=2, numoutlets=1, outlettype=["signal"])
    eg = p.obj("edge~", at=(220, 210), numinlets=1, numoutlets=2, outlettype=["bang", "bang"])
    ob = p.obj("onebang", at=(220, 250), numinlets=2, numoutlets=2, outlettype=["bang", "bang"])

    arm = p.ui("button", at=(400, 210))
    p.comment("2) click to arm -- expect ONE tick on the next bar line", at=(400, 180), w=380)
    rearm = p.msg("bang", at=(400, 250))

    cnt = p.obj("counter", at=(220, 300), numinlets=5, numoutlets=4, outlettype=["int", "", "", ""])
    nb = p.ui("number", at=(220, 340), w=80)
    tsplit = p.obj("t b b", at=(360, 290), numinlets=1, numoutlets=2, outlettype=["bang", "bang"])
    tm = p.obj("timer", at=(360, 300), numinlets=2, numoutlets=1, outlettype=["float"])
    nt = p.ui("flonum", at=(360, 340), w=90)
    pr = p.obj("print BAR", at=(360, 380), numinlets=1, numoutlets=0)
    p.comment("timer between ticks should read the bar length in ms and stay constant",
              at=(360, 420), w=420)

    # keep DSP alive
    sink = p.obj("*~ 0.", at=(40, 300), numinlets=2)
    dac = p.obj("ezdac~", at=(40, 340), numinlets=2, numoutlets=0)
    p.comment("0) click ezdac (phasor~ @lock needs DSP + running transport)", at=(40, 380), w=420)

    p.connect(startm, 0, tp, 0)
    p.connect(ph, 0, dl, 0)
    p.connect(dl, 0, lt, 0)
    p.connect(lt, 0, eg, 0)
    p.connect(eg, 0, ob, 0)
    p.connect(arm, 0, ob, 1)
    p.connect(ob, 0, cnt, 0)
    p.connect(ob, 0, rearm, 0)
    p.connect(ob, 0, tsplit, 0)
    p.connect(tsplit, 1, tm, 1)    # report elapsed since last bar (fires first)
    p.connect(tsplit, 0, tm, 0)    # then restart
    p.connect(rearm, 0, ob, 1)     # self re-arm: one bang per bar, forever
    p.connect(cnt, 0, nb, 0)
    p.connect(tm, 0, nt, 0)
    p.connect(tm, 0, pr, 0)
    p.connect(ph, 0, sink, 0)
    p.connect(sink, 0, dac, 0)
    return p


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    built = [
        ("t1_buffer_contention.maxpat", t1()),
        ("t2_voice.maxpat", t2_voice()),
        ("t2_poly_vs_karma.maxpat", t2()),
        ("t3_poly_steal_choke.maxpat", t3()),
        ("t4_karma_loopdef_ramp.maxpat", t4()),
        ("t5_detonate_roundtrip.maxpat", t5()),
        ("t6_bar_edge_once.maxpat", t6()),
    ]
    for name, patch in built:
        path = patch.save(OUT / name)
        # sanity: reparse
        import json
        json.loads(path.read_text())
        print("wrote", path.relative_to(OUT.parents[1]))


if __name__ == "__main__":
    main()
