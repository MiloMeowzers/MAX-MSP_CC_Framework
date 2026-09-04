# ChopChop — continuation prompt

Paste the block below into a new chat to hand over.

---

⚠️ **Work in the EXISTING worktree — do not create a new one.**

Path: `F:\CC Working\MAX Framework\rep\.claude\worktrees\chopchop-v6-203-fast-render-03e1c4`
Branch: `claude/chopchop-v6-203-fast-render-03e1c4`

This is the live head of the project. A prior handover from an earlier worktree
(`chopchop-project-max-new-e831de`, stopped at v6_202) was picked up by spinning up a *new*
worktree instead of continuing in the one that already existed — that forked the branch and
cost a day reconciling it (see context.md, "2026-09-04 — worktree fork incident"). If the tool
you're using would default to creating a fresh worktree for this task, point it at the path
above instead. If you're not sure how to do that in the current tool, **ask the user before
proceeding** rather than guessing — this is exactly the kind of decision that forks history
silently.

---

I'm continuing work on the **chopchop-project** in this repo, in the worktree above. Full
history and the agreed architecture are in `patches/chopchop-project/context.md` — **read the
"▶ CONTINUATION STATE" section at the very end first**, then the "Phase 5/6 design spec"
section above it (diagram: `reference/rolling_buffer_flow.svg`). `status.md` is the one-line
state.

## What the project is

Pick up an existing, working Max for Live device (**ChopChop** — a 16-slice loop chopper built
on the third-party **`karma~`** v1.0 external) and finish its unbuilt core functionality. It
targets MAX 9 / Live 12. `CLAUDE.md` at the repo root has the mandatory MAX rules (object DB is
the source of truth, verify before connect, etc.).

## Current state

- **Base file:** `patches/chopchop-project/generated/ChopChop_v6_216.amxd` (1,883,883 bytes).
- The **fast-render Commit** mechanism (grab the rolling ring, render into `karma~
  ---thisBuffer` at 8×) is implemented and has been through several rounds of real-device
  debugging: exact-integer-bar grab windows, a shared isolated `sig~ 8.` speed source for both
  render sides (karma record rate and the `groove~`/`play~` read rate had been drifting apart
  through a live signal chain), and a `delay 5` settle gap so both sides lock onto that shared
  speed before the capture actually starts (v6_216).
- **Waiting on:** the user's test of v6_216. Known open item: `RON` (`---recordOn`) reading 1
  even on a fresh INIT+Arm+single-press — confirmed NOT a repeat-press issue, lower priority,
  not yet root-caused.
- **Documented fallback** if capture quality/length is still inconsistent after v6_216: close
  the render on `gv2`'s own sync-outlet wrap (sample-accurate) instead of a scheduler
  `delay renderMs` — needs `groove~`'s loop-point sync behaviour verified first.

## Hard workflow constraints (the user is firm on these)

1. **Continue in this exact worktree. Never spin up a new one for this project** unless the
   user explicitly asks for a parallel/experimental branch — and even then, say so and name it
   clearly as a fork, don't let it become the de facto continuation.
2. **Logic-only edits.** Never change presentation, `openrect`, or any box position — the user
   re-laid the v6_199 layout by hand. Diagnostics go on existing (repointed) fields or not at
   all unless the user approves placement.
3. **No build that needs editing before it can be tested.** Ship it working.
4. **Ask / gather data before building on assumptions.** Several open karma behaviours must be
   verified in Max, not assumed — listed at the end of context.md.
5. Commit every `.amxd` save:
   `git -c user.email="sisericm@gmail.com" -c user.name="Claude" commit ...`
   (Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>). Never `git stash`.
6. Update the `context.md` build log every version, keep the `▶ CONTINUATION STATE` section at
   the end current, and refresh `status.md`. Send the `.amxd` with SendUserFile.

## Tooling (`patches/chopchop-project/tools/`)

- `ccamxd.py` — load / inspect / byte-preserving save of the `.amxd` main patcher JSON.
  `load(path)` → `.patcher` (dict), `.save(path)`. Re-minifies + re-pads into the fixed slot,
  so output stays the same byte size.
- `validate.py` — `sweep(amx)` → `(per_scope, total, problems)`. **Baseline is now 28** message
  cycles (was 27 through v6_202/203; +1 is the bar-synced-arm latch loop, expected), 0
  problems, byte-size preserved. A build that changes either needs justification.
- `cctrace.py` — channel/box graph tracer across send/receive + subpatcher walls.
- Build scripts: `phase3_fileNN_*.py`, one per version, in numbered sequence — check the
  highest-numbered file in `tools/` before naming the next one. Pattern: `load(BASE)` → mutate
  `patcher` dicts (`root["boxes"] += [...]`, `root["lines"] += [Ln(...)]`) → `amx.save(OUT)` →
  `validate.sweep` → assert cycles unchanged (28), 0 problems, size preserved.

## karma~ facts (v1.0 — from `C:\Users\Brown\Downloads\chopchop\karma1.0\...\karma~.c`)

Messages, complete: `position window jump stop play record append set overdub report ramp
snramp snrcurv interp`. No `loopstart`/`loopend`/`crop`/`resize`/`sync`. `set` on a buffer
karma didn't record → loop = whole allocation. `record` from a stopped state **zeroes the
entire buffer**. Speed inlet is signal-preferential; value 0 = frozen (no playback motion).
`record` clamps position advance to `loop/1024` per sample (~375× ceiling for a 4-bar loop) —
8× render speed is well inside it. `groove~` (Cycling '74) *does* have `@loopstart`/
`@loopend` (ms) and inlets 1/2 = loop min/max — it region-loops a pre-filled buffer with no
record pass. Reference patches the user supplied: `C:\Users\Brown\Downloads\chopchop\maxpat
samples\` (groovebasics, PlayPartOf..., livecaptureinbuffer, temporelativephasor).

## Phases after the fast-render Commit is solid

v6_205+ (renumber as needed) — wrapped-grab two-segment read; A/B-as-master-vs-ring rework
incl. wiring `---enableA/B` (currently dead); Snapshot clean/wet split; feedback gain into the
roll input; then the `poly~` voice layer (`target N` routing, not `midinote`) + `coll`
sequencer. Full order in the spec's "Build order".

---
