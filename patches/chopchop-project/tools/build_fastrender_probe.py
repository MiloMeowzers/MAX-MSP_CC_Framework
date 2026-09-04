"""fastrender_probe.maxpat -- standalone scratch patcher (NOT the device).

ONE question, per the chopchop-max-testing skill:

  Does karma~ `record` advance its write-head at the SPEED-INLET rate?

If yes, a high-speed (8x) speed signal + 8x-fast audio from groove~ produces a
REAL bounded karma loop of the correct LENGTH that plays back at correct 1x
PITCH -- which is the entire basis of the v6_203 fast-render Commit. Source
reading says the record advance follows speed, clamped to loop/1024 per sample
(~375x ceiling for an 8000 ms loop). It has never been run.

Rig
---
  buffer~ src 8000 2   stand-in "ring": 8000 ms == 4 bars @ 120 BPM
  buffer~ dst 8000 2   the karma~ target

  A  FILL SRC   -> record~ writes cycle~ 200 into `src` for one 8000 ms pass.
  B  RENDER 8x  -> lg,lk (line~) both jump to 8 ; karma stop ; groove~ starts
                  from 0 (plays `src` at rate 8) ; karma record (zeroes dst,
                  records groove~'s 8x tone at speed 8) ; after 1000 ms wall
                  clock: karma play (closes the loop), lk -> 1 (audition at
                  1x), lg -> 0 (stop groove~).
  C  read       karma~ outlet 2 -> unpack f i i f f f -> 6 number boxes
                (pos / play / rec / start ms / end ms / window ms) + `print k`.
  D  RENDER 1x  -> reference real-time pass (lk,lg stay at 1 ; 8000 ms delay).
                  Known-good loop to compare B against by ear + scope.
  E  ezdac~ (through *~ 0.4) + scope~ on karma out.  CLICK EZDAC ON FIRST.

PASS   end ms ~= 8000, window ms ~= 8000, play=1, rec=0 after B ; audio is a
       200 Hz sine looping every 8 s -- identical to D.
FAIL   end ms ~= 1000 (only 1000 ms of buffer written), OR the tone sounds an
       octave-plus high / loops every ~1 s -> record advance does NOT follow
       speed, fast-render as designed is dead, fall back to the A/B swap.

Note: this probe drives groove~ rate and karma speed off two SEPARATE line~
(lg, lk), not one shared ramp. It tests whether the mechanism works at all,
not sub-sample lock between the two -- that is a v6_203 build concern.

    python build_fastrender_probe.py   # -> ../test-patchers/fastrender_probe.maxpat
"""
from pathlib import Path

from maxpat import Patch

OUT = Path(__file__).resolve().parents[1] / "test-patchers" / "fastrender_probe.maxpat"


def main():
    p = Patch(title="fastrender_probe")

    # -- buffers (emitted first by the builder) ------------------------------
    src = p.obj("buffer~ src 8000 2", at=(40, 40, 150), numinlets=1, numoutlets=2,
                outlettype=["float", "bang"])
    dst = p.obj("buffer~ dst 8000 2", at=(210, 40, 150), numinlets=1, numoutlets=2,
                outlettype=["float", "bang"])

    # ================================================================= A: fill
    p.comment("A.  Click FILL SRC, wait ~8 s (auto-stops). Fills src with a 200 Hz sine.",
              at=(40, 90, 520))
    fill_btn = p.ui("button", at=(40, 115, 24, 24), outlettype=["bang"])
    fill_t = p.obj("t b b", at=(40, 150, 60), numinlets=1, numoutlets=2,
                   outlettype=["bang", "bang"])
    fill_go = p.msg("1", at=(40, 185, 40))
    fill_dl = p.obj("delay 8000", at=(120, 150, 90), numinlets=2, numoutlets=1,
                    outlettype=["bang"])
    fill_stop = p.msg("0", at=(120, 185, 40))
    tone = p.obj("cycle~ 200", at=(240, 150, 90), numinlets=2, numoutlets=1,
                 outlettype=["signal"])
    rec = p.obj("record~ src 2", at=(240, 220, 150), numinlets=2, numoutlets=1,
                outlettype=["signal"])
    p.connect(fill_btn, 0, fill_t, 0)
    p.connect(fill_t, 1, fill_go, 0)          # right outlet first: start
    p.connect(fill_t, 0, fill_dl, 0)          # then arm the auto-stop
    p.connect(fill_go, 0, rec, 0)
    p.connect(fill_dl, 0, fill_stop, 0)
    p.connect(fill_stop, 0, rec, 0)
    p.connect(tone, 0, rec, 0)
    p.connect(tone, 0, rec, 1)

    # ============================================================= B: render 8x
    p.comment("B.  Click RENDER 8x. Renders src -> dst through karma at 8x, then auditions at 1x.",
              at=(40, 270, 620))
    r8 = p.ui("button", at=(40, 295, 24, 24), outlettype=["bang"])
    # right-to-left fire order: o5 speeds=8 ... o0 arm the close
    r8t = p.obj("t b b b b b b", at=(40, 330, 150), numinlets=1, numoutlets=6,
                outlettype=["bang"] * 6)
    m_loop = p.msg("loop 1", at=(40, 365, 60))                 # o5
    m_sp8k = p.msg("8. 0", at=(110, 365, 50))                  # o4 -> lk
    m_sp8g = p.msg("8. 0", at=(170, 365, 50))                  # o4 -> lg
    m_kstop = p.msg("stop", at=(230, 365, 50))                 # o3
    m_gstart = p.msg("0", at=(290, 365, 40))                   # o2 -> groove~ in0 (start from 0)
    m_krec = p.msg("record", at=(340, 365, 60))                # o1
    m_krep = p.msg("report 400", at=(410, 365, 80))            # o0a
    close_dl = p.obj("delay 1000", at=(500, 365, 90), numinlets=2, numoutlets=1,
                     outlettype=["bang"])                       # o0b
    close_t = p.obj("t b b b", at=(500, 400, 90), numinlets=1, numoutlets=3,
                    outlettype=["bang", "bang", "bang"])
    m_kplay = p.msg("play", at=(500, 435, 50))
    m_sp1k = p.msg("1. 20", at=(560, 435, 50))
    m_sp0g = p.msg("0. 20", at=(620, 435, 50))

    p.connect(r8, 0, r8t, 0)
    p.connect(r8t, 5, m_loop, 0)
    p.connect(r8t, 4, m_sp8k, 0)
    p.connect(r8t, 4, m_sp8g, 0)
    p.connect(r8t, 3, m_kstop, 0)
    p.connect(r8t, 2, m_gstart, 0)
    p.connect(r8t, 1, m_krec, 0)
    p.connect(r8t, 0, m_krep, 0)
    p.connect(r8t, 0, close_dl, 0)
    p.connect(close_dl, 0, close_t, 0)
    p.connect(close_t, 2, m_kplay, 0)
    p.connect(close_t, 1, m_sp1k, 0)
    p.connect(close_t, 0, m_sp0g, 0)

    # ============================================================= D: render 1x
    p.comment("D.  Click RENDER 1x for the known-good real-time reference (8 s pass).",
              at=(40, 470, 620))
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

    # ============================================= signal graph: line~ / groove~ / karma~
    lk = p.obj("line~ 1.", at=(700, 300, 70), numinlets=2, numoutlets=2,
               outlettype=["signal", "bang"])          # karma speed
    lg = p.obj("line~ 1.", at=(780, 300, 70), numinlets=2, numoutlets=2,
               outlettype=["signal", "bang"])          # groove~ rate
    gr = p.obj("groove~ src 2", at=(700, 360, 150), numinlets=3, numoutlets=3,
               outlettype=["signal", "signal", "signal"])
    gmin = p.msg("0", at=(870, 330, 40))
    gmax = p.msg("8000", at=(920, 330, 50))
    ka = p.obj("karma~ dst 2", at=(700, 430, 150), numinlets=3, numoutlets=3,
               outlettype=["signal", "signal", ""])

    # line~ targets
    for m in (m_sp8k, m_sp1k, d_sp1k):
        p.connect(m, 0, lk, 0)
    for m in (m_sp8g, m_sp0g, d_sp1g):
        p.connect(m, 0, lg, 0)
    p.connect(lg, 0, gr, 0)          # groove~ rate signal
    p.connect(lk, 0, ka, 2)         # karma speed signal

    # groove~ loop points + start
    p.connect(gmin, 0, gr, 1)
    p.connect(gmax, 0, gr, 2)
    for m in (m_loop, m_gstart, d_loop, d_gstart):
        p.connect(m, 0, gr, 0)

    # groove~ audio -> karma record inlets
    p.connect(gr, 0, ka, 0)
    p.connect(gr, 1, ka, 1)

    # karma messages
    for m in (m_kstop, m_krec, m_krep, m_kplay, d_kstop, d_krec, d_kplay):
        p.connect(m, 0, ka, 0)

    # loadbang: set groove~ loop points once
    lb = p.obj("loadbang", at=(870, 295, 70), numinlets=1, numoutlets=1,
               outlettype=["bang"])
    lbt = p.obj("t b b", at=(870, 300, 60), numinlets=1, numoutlets=2,
                outlettype=["bang", "bang"])
    p.connect(lb, 0, lbt, 0)
    p.connect(lbt, 1, gmin, 0)
    p.connect(lbt, 0, gmax, 0)

    # ================================================================= C: read
    p.comment("C.  RESULT after B:  end ms ~= 8000  AND  window ms ~= 8000  AND  play=1, rec=0.",
              at=(40, 640, 700))
    p.comment("    Audio: 200 Hz sine, loops every 8 s -- must match D. "
              "FAIL if end ms ~= 1000 or tone is high / loops ~1 s.",
              at=(40, 660, 700))
    unp = p.obj("unpack f i i f f f", at=(700, 500, 150), numinlets=1, numoutlets=6,
                outlettype=["float", "int", "int", "float", "float", "float"])
    p.connect(ka, 2, unp, 0)
    labels = ["pos 0-1", "play", "rec", "start ms", "end ms", "window ms"]
    for i, lab in enumerate(labels):
        n = p.ui("number", at=(700 + 0, 530 + i * 26, 90, 22), ins=1, outs=2,
                 outlettype=["", "bang"])
        p.connect(unp, i, n, 0)
        p.comment(lab, at=(800, 532 + i * 26, 90))
    pr = p.obj("print k", at=(900, 500, 60), numinlets=1, numoutlets=0)
    p.connect(ka, 2, pr, 0)

    # ============================================================= E: DSP sink
    p.comment("E.  CLICK EZDAC ON FIRST (turn on audio).", at=(40, 810, 400))
    mul = p.obj("*~ 0.4", at=(700, 600, 60), numinlets=2, numoutlets=1,
                outlettype=["signal"])
    mur = p.obj("*~ 0.4", at=(770, 600, 60), numinlets=2, numoutlets=1,
                outlettype=["signal"])
    dac = p.obj("ezdac~", at=(700, 640, 90), numinlets=2, numoutlets=0)
    scope = p.obj("scope~", at=(820, 600, 130), numinlets=2, numoutlets=0)
    p.connect(ka, 0, mul, 0)
    p.connect(ka, 1, mur, 0)
    p.connect(mul, 0, dac, 0)
    p.connect(mur, 0, dac, 1)
    p.connect(ka, 0, scope, 0)

    # manual re-audition
    stopb = p.ui("button", at=(560, 295, 24, 24), outlettype=["bang"])
    stopm = p.msg("stop", at=(560, 260, 50))
    p.connect(stopb, 0, stopm, 0)
    p.connect(stopm, 0, ka, 0)
    p.comment("stop", at=(590, 297, 50))

    path = p.save(OUT)
    print(f"wrote {path}  ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
