"""Bassoon v0.4.1 regression test: simulator must catch the in-loop
high-Q failure-mode family before it ships.

Per CONTEXT.md D-06 the v0.4.1 mirror (correct phase-delay compensation,
bell biquad at Q~2.5 inside the loop) must not pass the bell_bright sweep.

Q25 (planner decision 3) changed the expected verdict, and the change makes
the test stronger. Under the fixed pitch detector (Q25 / H1) the mirror is
DC-only for bell_bright below ~0.7: its AC std is only 1e-4..2e-4 and it has
no detectable fundamental. The old detector read that DC as 4009 Hz
(+5022 cents), so the old `mode_competition` at step 0 was the H1 artifact.
After Q25 / H4 a step with no detectable fundamental is `no_oscillation`,
which wins the D-09 priority cascade at step 0. The in-loop high-Q failure
itself is still visible: once the loop starts (step 22) the fundamental
jumps to ~1028 Hz (+2643 cents), the mode jump this test also asserts.
"""

from __future__ import annotations

from src.maxpat.dsp_sim import run_simulation

from tests.dsp_sim.fixtures.bassoon_v041_mirror import build_v041_mirror


def test_v041_high_q_in_loop_is_caught():
    """v0.4.1 (bell-in-loop, Q=2.5) never passes: no oscillation at low bell_bright, then a mode jump."""
    r = run_simulation(
        patch_path="<v041-mirror>",
        mirror=build_v041_mirror,
        params={
            "freq": 220.0,
            "breath": 0.6,
            "bore_damp": 0.3,
            "bell_bright": 0.5,
            "reed_stiff": 0.5,
            "reed_aper": 0.0,
            "cone_loss": 0.85,
            "bell_q": 2.5,
        },
        sweep_param="bell_bright",
        sweep=(0.0, 1.0, 32),
    )
    assert r.verdict == "no_oscillation", r.reason
    assert r.worst_step == 0
    assert r.measurements[0].measured_hz == 0.0
    assert any(m.cents_offset > 50.0 for m in r.measurements[1:]), (
        "expected the in-loop high-Q mode jump (> 50 cents) once the loop starts"
    )
    assert "Loop dissipation" in (r.suggested_fix or "")
