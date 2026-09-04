# ChopChop — continuation prompt

Paste the block below into a new chat to hand over. It assumes the same repo/worktree.

---

I'm continuing work on the **chopchop-project** in this repo. Full history and the agreed
architecture are in `patches/chopchop-project/context.md` — **read the "▶ CONTINUATION STATE"
section at the very end first**, then the "Phase 5/6 design spec" section above it. `status.md`
in the same folder is the one-line state.

## What the project is

Pick up an existing, working Max for Live device (**ChopChop** — a 16-slice loop chopper built
on the third-party **`karma~`** v1.0 external) and finish its unbuilt core functionality. It
targets MAX 9 / Live 12. `CLAUDE.md` at the repo root has the mandatory MAX rules (object DB is
the source of truth, verify before connect, etc.).

## Current state

- **Base file:** `patches/chopchop-project/generated/ChopChop_v6_202.amxd` (1,883,883 bytes).
- **v6_202 (rolling substrate)** is built and with the user for testing. It adds a continuous
  `record~ @loop 1` ring (`---rollBuf`), a fixed 1-bar transport-locked cadence
  (`phasor~ @frequency 1n @lock 1`), bar counter → `s ---dbgBar`, ring write-pos →
  `s ---rollWritePos`, and repoints the v6_201 `groove~` preroll engine to grab
  `[writePos − LoopLength, writePos]` off the ring. Diagnostics: the visible **SPD** strip
  field now shows the bar counter, **FRC** shows ring write-pos in ms (repoint only, no layout
  change).
- **Waiting on:** the user's test report for v6_202 (does SPD tick per bar locked to
  transport, does the grabbed slab sound like the recent audio, does it glitch at the ring
  wrap).

## Immediate next task — v6_203, fast-render Commit

Render the grabbed ring slab into `karma~ ---thisBuffer` (= `karmaMaster`, box `obj-20` in
`p Playback`) as a **real bounded karma loop**: a `groove~` reads the slab at ~8× while
`karmaMaster` `record`s at the same rate, both driven off one shared high-speed ramp, closing
on the ramp end (`play`) so the loop length comes out correct. Crossfade the groove~ bridge
out / `karmaMaster` in. Lifecycle: **first Commit is automatic** on the first bar mark after
arm from a clean state (sets `---hasContent`, hands the existing slice/`jump`/`window`/overlay
engine onto `karmaMaster`, ends the groove~ bridge); every Commit after is the manual Record
button (preroll-full path). Do not rebuild the slice engine — it already works on a real karma
loop.

## Hard workflow constraints (the user is firm on these)

1. **Logic-only edits.** Never change presentation, `openrect`, or any box position — the user
   re-laid the v6_199 layout by hand. Diagnostics go on existing (repointed) fields or not at
   all unless the user approves placement.
2. **No build that needs editing before it can be tested.** Ship it working.
3. **Ask / gather data before building on assumptions.** Several open karma behaviours must be
   verified in Max, not assumed — listed at the end of context.md.
4. Commit every `.amxd` save:
   `git -c user.email="sisericm@gmail.com" -c user.name="Claude" commit ...`
   (Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>). Never `git stash`.
5. Update the `context.md` build log every version. Send the `.amxd` with SendUserFile.

## Tooling (`patches/chopchop-project/tools/`)

- `ccamxd.py` — load / inspect / byte-preserving save of the `.amxd` main patcher JSON.
  `load(path)` → `.patcher` (dict), `.save(path)`. Re-minifies + re-pads into the fixed slot,
  so output stays the same byte size (headroom ~1.3 MB).
- `validate.py` — `sweep(amx)` → `(per_scope, total, problems)`. **Baseline: 27 message
  cycles, 0 problems.** A build that changes either needs justification.
- `cctrace.py` — channel/box graph tracer across send/receive + subpatcher walls.
- Build scripts: `phase3_fileNN_*.py`, one per version. Model the next one on
  `phase3_file19_rolling_substrate.py`. Pattern: `load(BASE)` → mutate `patcher` dicts
  (`root["boxes"] += [...]`, `root["lines"] += [Ln(...)]`) → `amx.save(OUT)` → `validate.sweep`
  → assert cycles unchanged, 0 problems, size preserved.

## karma~ facts (v1.0 — from `C:\Users\Brown\Downloads\chopchop\karma1.0\...\karma~.c`)

Messages, complete: `position window jump stop play record append set overdub report ramp
snramp snrcurv interp`. No `loopstart`/`loopend`/`crop`/`resize`/`sync`. `set` on a buffer
karma didn't record → loop = whole allocation. `record` from a stopped state **zeroes the
entire buffer**. Speed inlet is signal-preferential; value 0 = frozen (no playback motion).
`record` clamps position advance to `loop/1024` per sample (~375× ceiling for a 4-bar loop).
`groove~` (Cycling '74) *does* have `@loopstart`/`@loopend` (ms) and inlets 1/2 = loop
min/max — it region-loops a pre-filled buffer with no record pass. Reference patches the user
supplied: `C:\Users\Brown\Downloads\chopchop\maxpat samples\` (groovebasics, PlayPartOf...,
livecaptureinbuffer, temporelativephasor).

## Phases after v6_203

v6_204 Snapshot clean/wet + feedback gain into the roll input · v6_205+ `poly~` voice layer
(`target N` routing, not `midinote`), `coll` sequencer, per-pad pitch/direction. Full order in
the "Build order" of the spec.

---
