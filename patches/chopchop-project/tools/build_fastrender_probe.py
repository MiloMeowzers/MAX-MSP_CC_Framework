"""fastrender_probe.maxpat -- standalone scratch patcher (NOT the device).

ONE question, per the chopchop-max-testing skill:

  Does karma~ `record` advance its write-head at the SPEED-INLET rate?

If yes, a high-speed (8x) speed signal + 8x-fast audio from groove~ produces a
REAL bounded karma loop of the correct LENGTH (8000 ms) that plays back at 1x
speed with correct pitch/duration -- the entire basis of the v6_203 fast-render
Commit. If no (record advance fixed at 1x/sample), the 8x pass writes only
~1000 ms of buffer, crammed with pitched-up audio, and only sounds right when
played back at 0.125x -- which the real-ms slice engine cannot use.

>>> karma~'s status outlet does NOT report in a bare editor patcher (documented,
    cost this project days). So this probe does NOT read karma state. It makes
    the loop LENGTH audible + measurable with pure Max objects:

  fill  src (8000 ms == 4 bars @ 120) with a phasor~ 0.125 ramp -- one clean
        0->1 sweep across the whole buffer (8 s period).
  B  RENDER 8x   groove~ reads src at rate 8, karma records dst at speed 8, for
                 ~1000 ms wall clock, then karma play + speeds -> 1x.
  measure  karma dst out -> delta~ -> <~ -0.5 -> edge~ -> timer  = ms between
           ramp wraps == the loop period karma actually established.
             ~8000  -> PASS  (record advance follows speed; fast-render viable)
             ~1000  -> FAIL  (record advance fixed at 1x; use the A/B swap)
  ear   PLAY 1x vs PLAY 0.125x: whichever restores the slow source ramp tells
        the same story (1x == PASS, 0.125x == FAIL).
  D  RENDER 1x   known-good real-time reference (8000 ms pass).

    python build_fastrender_probe.py   # -> ../test-patchers/fastrender_probe.maxpat
"""
from pathlib import Path

from maxpat import Patch

OUT = Path(__file__).resolve().parents[1] / "test-patchers" / "fastrender_probe.maxpat"


def main():
    p = Patch(title="fastrender_probe")

    # -- buffers (emitted first by the builder) ----------------------------------
    p.obj("buffer~ src 8000 2", at=(40, 40, 150), numinlets=1, numoutlets=2,
          outlettype=["float", "bang"])
    p.obj("buffer~ dst 8000 2", at=(210, 40, 150), numinlets=1, numoutlets=2,
          outlettype=["float", "bang"])

    # ===================================================================== A: fill
    p.comment("A.  FILL SRC -> writes one phasor~ 0.125 ramp (0->1 over 8 s) into src. "
              "Auto-stops after 8 s.", at=(40, 90, 620))
    fill_btn = p.ui("button", at=(40, 115, 24, 24), outlettype=["bang"])
    fill_t = p.obj("t b b", at=(40, 150, 60), numinlets=1, numoutlets=2,
                   outlettype=["bang", "bang"])
    fill_go = p.msg("1", at=(40, 185, 40))
    fill_dl = p.obj("delay 8000", at=(120, 150, 90), numinlets=2, numoutlets=1,
                    outlettype=["bang"])
    fill_stop = p.msg("0", at=(120, 185, 40))
    ramp = p.obj("phasor~ 0.125", at=(240, 150, 100), numinlets=1, numoutlets=1,
                 outlettype=["signal"])
    rec = p.obj("record~ src 2", at=(240, 220, 150), numinlets=2, numoutlets=1,
                outlettype=["signal"])
    p.connect(fill_btn, 0, fill_t, 0)
    p.connect(fill_t, 1, fill_go, 0)
    p.connect(fill_t, 0, fill_dl, 0)
    p.connect(fill_go, 0, rec, 0)
    p.connect(fill_dl, 0, fill_stop, 0)
    p.connect(fill_stop, 0, rec, 0)
    p.connect(ramp, 0, rec, 0)
    p.connect(ramp, 0, rec, 1)

    # ================================================================= B: render 8x
    p.comment("B.  RENDER 8x -> src -> dst through karma at 8x (~1 s), then karma play at 1x.",
              at=(40, 270, 640))
    r8 = p.ui("button", at=(40, 295, 24, 24), outlettype=["bang"])
    r8t = p.obj("t b b b b b b", at=(40, 330, 150), numinlets=1, numoutlets=6,
                outlettype=["bang"] * 6)
    m_loop = p.msg("loop 1", at=(40, 365, 60))          # o5 first
    m_sp8k = p.msg("8. 0", at=(110, 365, 50))           # o4 -> lk (karma speed)
    m_sp8g = p.msg("8. 0", at=(170, 365, 50))           # o4 -> lg (groove rate)
    m_kstop = p.msg("stop", at=(230, 365, 50))          # o3
    m_gstart = p.msg("0", at=(290, 365, 40))            # o2 -> groove~ in0 start from 0
    m_krec = p.msg("record", at=(340, 365, 60))         # o1
    close_dl = p.obj("delay 1000", at=(420, 365, 90), numinlets=2, numoutlets=1,
                     outlettype=["bang"])               # o0
    close_t = p.obj("t b b b", at=(420, 400, 90), numinlets=1, numoutlets=3,
                    outlettype=["bang", "bang", "bang"])
    m_kplay = p.msg("play", at=(420, 435, 50))
    m_sp1k = p.msg("1. 20", at=(480, 435, 50))
    m_sp0g = p.msg("0. 20", at=(540, 435, 50))
    p.connect(r8, 0, r8t, 0)
    p.connect(r8t, 5, m_loop, 0)
    p.connect(r8t, 4, m_sp8k, 0)
    p.connect(r8t, 4, m_sp8g, 0)
    p.connect(r8t, 3, m_kstop, 0)
    p.connect(r8t, 2, m_gstart, 0)
    p.connect(r8t, 1, m_krec, 0)
    p.connect(r8t, 0, close_dl, 0)
    p.connect(close_dl, 0, close_t, 0)
    p.connect(close_t, 2, m_kplay, 0)
    p.connect(close_t, 1, m_sp1k, 0)
    p.connect(close_t, 0, m_sp0g, 0)

    # ================================================================= D: render 1x
    p.comment("D.  RENDER 1x -> known-good real-time reference (8 s pass).", at=(40, 470, 640))
    r1 = p.ui("button", at=(40, 495, 24, 24), outlettype=["bang"])
    r1t = p.obj("t b b b b b", at=(40, 530, 150), numinlets=1, numoutlets=5,
                outlettype=["bang"] * 5)
    d_loop = p.msg("loop 1", at=(40, 565, 60))
    d_sp1k = p.msg("1. 0", at=(110, 565, 50))
    d_sp1g = p.msg("1. 0", at=(170, 565, 50))
    d_kstop = p.msg("stop", at=(230, 565, 50))
    d_gstart = p.msg("0", at=(290, 565, 40))
    d_krec = p.msg("record", at=(340, 565, 60))
    d_dl = p.obj("delay 8000", at=(410, 565, 90), numinlets=2, numoutlets=1,
                 outlettype=["bang"])
    d_kplay = p.msg("play", at=(410, 600, 50))
    p.connect(r1, 0, r1t, 0)
    p.connect(r1t, 4, d_loop, 0)
    p.connect(r1t, 3, d_sp1k, 0)
    p.connect(r1t, 3, d_sp1g, 0)
    p.connect(r1t, 2, d_kstop, 0)
    p.connect(r1t, 1, d_gstart, 0)
    p.connect(r1t, 0, d_krec, 0)
    p.connect(r1t, 0, d_dl, 0)
    p.connect(d_dl, 0, d_kplay, 0)

    # ======================================== signal graph: line~ / groove~ / karma~
    lk = p.obj("line~ 1.", at=(700, 300, 70), numinlets=2, numoutlets=2,
               outlettype=["signal", "bang"])       # karma speed
    lg = p.obj("line~ 1.", at=(780, 300, 70), numinlets=2, numoutlets=2,
               outlettype=["signal", "bang"])       # groove~ rate
    gr = p.obj("groove~ src 2", at=(700, 360, 150), numinlets=3, numoutlets=3,
               outlettype=["signal", "signal", "signal"])
    gmin = p.msg("0", at=(870, 330, 40))
    gmax = p.msg("8000", at=(920, 330, 50))
    ka = p.obj("karma~ dst 2", at=(700, 430, 150), numinlets=3, numoutlets=3,
               outlettype=["signal", "signal", ""])

    for m in (m_sp8k, m_sp1k, d_sp1k):
        p.connect(m, 0, lk, 0)
    for m in (m_sp8g, m_sp0g, d_sp1g):
        p.connect(m, 0, lg, 0)
    p.connect(lg, 0, gr, 0)
    p.connect(lk, 0, ka, 2)

    p.connect(gmin, 0, gr, 1)
    p.connect(gmax, 0, gr, 2)
    for m in (m_loop, m_gstart, d_loop, d_gstart):
        p.connect(m, 0, gr, 0)

    p.connect(gr, 0, ka, 0)
    p.connect(gr, 1, ka, 1)
    for m in (m_kstop, m_krec, m_kplay, d_kstop, d_krec, d_kplay):
        p.connect(m, 0, ka, 0)

    lb = p.obj("loadbang", at=(870, 290, 70), numinlets=1, numoutlets=1,
               outlettype=["bang"])
    lbt = p.obj("t b b", at=(870, 300, 60), numinlets=1, numoutlets=2,
                outlettype=["bang", "bang"])
    p.connect(lb, 0, lbt, 0)
    p.connect(lbt, 1, gmin, 0)
    p.connect(lbt, 0, gmax, 0)

    # =============================== MEASURE loop period with pure Max objects
    p.comment("C.  LOOP PERIOD (ms between ramp wraps in dst, at 1x playback):",
              at=(40, 640, 700))
    p.comment("      ~8000  = PASS  (karma record follows the speed inlet -> fast-render viable)",
              at=(60, 662, 700))
    p.comment("      ~1000  = FAIL  (record advance fixed at 1x -> A/B swap instead)",
              at=(60, 682, 700))
    dlt = p.obj("delta~", at=(700, 505, 60), numinlets=1, numoutlets=1,
                outlettype=["signal"])
    lt = p.obj("<~ -0.5", at=(700, 535, 60), numinlets=2, numoutlets=1,
               outlettype=["signal"])
    eg = p.obj("edge~", at=(700, 565, 60), numinlets=1, numoutlets=2,
               outlettype=["bang", "bang"])
    tmr = p.obj("timer", at=(700, 595, 60), numinlets=2, numoutlets=1,
                outlettype=["float"])
    per_n = p.ui("number", at=(770, 595, 100, 22), ins=1, outs=2, outlettype=["", "bang"])
    per_p = p.obj("print period", at=(880, 595, 90), numinlets=1, numoutlets=0)
    p.connect(ka, 0, dlt, 0)
    p.connect(dlt, 0, lt, 0)
    p.connect(lt, 0, eg, 0)
    p.connect(eg, 0, tmr, 0)
    p.connect(tmr, 0, per_n, 0)
    p.connect(tmr, 0, per_p, 0)

    # live value monitor + scope
    snp = p.obj("snapshot~ 150", at=(700, 660, 90), numinlets=1, numoutlets=1,
                outlettype=["float"])
    snp_n = p.ui("number", at=(800, 660, 100, 22), ins=1, outs=2, outlettype=["", "bang"])
    scope = p.obj("scope~", at=(910, 640, 140), numinlets=2, numoutlets=0)
    p.connect(ka, 0, snp, 0)
    p.connect(snp, 0, snp_n, 0)
    p.connect(ka, 0, scope, 0)
    p.comment("(snapshot: watch it sweep 0->1; time the sweep)", at=(700, 690, 340))

    # ================================ manual re-audition of dst at chosen speed
    p.comment("PLAY dst:", at=(560, 260, 70))
    pb1 = p.ui("button", at=(560, 285, 24, 24), outlettype=["bang"])
    pb8 = p.ui("button", at=(610, 285, 24, 24), outlettype=["bang"])
    pbs = p.ui("button", at=(660, 285, 24, 24), outlettype=["bang"])
    p.comment("1x / 0.125x / stop", at=(560, 312, 160))
    pm1 = p.msg("1. 0", at=(560, 230, 45))
    pm8 = p.msg("0.125 0", at=(610, 230, 60))
    pms = p.msg("stop", at=(670, 230, 45))
    pm1b = p.msg("play", at=(560, 200, 45))
    pm8b = p.msg("play", at=(620, 200, 45))
    p.connect(pb1, 0, pm1, 0)
    p.connect(pb1, 0, pm1b, 0)
    p.connect(pb8, 0, pm8, 0)
    p.connect(pb8, 0, pm8b, 0)
    p.connect(pbs, 0, pms, 0)
    p.connect(pm1, 0, lk, 0)
    p.connect(pm8, 0, lk, 0)
    p.connect(pm1b, 0, ka, 0)
    p.connect(pm8b, 0, ka, 0)
    p.connect(pms, 0, ka, 0)

    # ================================================================= DSP sink
    p.comment("E.  CLICK EZDAC ON FIRST (turn on audio).", at=(40, 810, 400))
    mul = p.obj("*~ 0.4", at=(700, 730, 60), numinlets=2, numoutlets=1, outlettype=["signal"])
    mur = p.obj("*~ 0.4", at=(770, 730, 60), numinlets=2, numoutlets=1, outlettype=["signal"])
    dac = p.obj("ezdac~", at=(700, 765, 90), numinlets=2, numoutlets=0)
    p.connect(ka, 0, mul, 0)
    p.connect(ka, 1, mur, 0)
    p.connect(mul, 0, dac, 0)
    p.connect(mur, 0, dac, 1)

    path = p.save(OUT)
    print(f"wrote {path}  ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
