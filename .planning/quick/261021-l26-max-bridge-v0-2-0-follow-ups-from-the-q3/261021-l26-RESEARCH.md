# Quick 261021-l26: max-bridge v0.2.0 follow-ups - Research

**Researched:** 2026-10-21
**Domain:** MAX 9.2 bridge patch (UDP/OSC) and the stdlib Python client `tools/max_bridge.py`
**Confidence:** HIGH for the object/message choices (refpages, help files and the DB were all read). MEDIUM for the runtime details that only a MAX run can confirm (listed under Open Questions).

<user_constraints>
## User Constraints (locked, from the task and open-questions.md N1/N4/Findings)

1. **Kill switch:** a toggle in the bridge patch, OFF by default, that gates ALL incoming commands. The client must report a clear error when the bridge is gated.
2. **Restore the prior DSP state** after a check instead of forcing it off ("Leave DSP on if it was on before the check, off if it was off", N4).
3. **Sample-rate guard:** read MAX's own rate. When it disagrees with the wav header, analyze at MAX's rate and add the warning `sr_header_mismatch`.
4. **Tap placement:** each `send~` tap goes directly below its `dac~`/`ezdac~`, with `presentation` 0 and no overlaps.
5. **Distinct error count:** dedupe the same error across the `error`, `console` and `console_write` channels, and keep the raw occurrences.
6. **Note stimulus**, so that synths like simple-fm sound during `--record`. CLI: `--note 60 100 --note-ms 2000`.
7. A short v0.2.0 manual checklist.

All CLAUDE.md MAX rules apply. Rule #5: edit the bridge patch, never regenerate it. Rule #7: save through `save_patch_roundtrip`, which auto-commits. Rule #8: `replace_box_safe`. Rule #3: hot/cold order.
</user_constraints>

## Summary

All six changes fit the v0.1.0 design: the bridge stays a dumb pass-through and Python does the sequencing. The bridge patch needs four small additions:
- a `toggle` and a `gate 1 0` between `udpreceive` and `deferlow` (the kill switch);
- two new route addresses, appended at the END so that existing outlet indices 0-8 and their cords do not move: `/query` and `/note`;
- a `/query` branch: `t b b b` -> `adstatus switch`, `adstatus sr` and `dspstate~`, each through a `prepend` -> the existing `udpsend`;
- a `/note` branch -> `send __maxbridge_note`.

Everything else is client-side: DSP restore, the sample-rate guard, error dedupe, tap placement and note injection in `instrument()`.

**Primary recommendation:**
- Query DSP state **before `/open`**: the patch under test may switch DSP on itself at load.
- Use `dspstate~` outlet 1 as MAX's authoritative rate. It is the rate the oscillators run at: 478.9/440 = 48000/44100 proves the samples were made at the DSP rate, not the header rate.
- Inject the note by **mirroring every `notein`'s outgoing cords** from a `receive __maxbridge_note` -> `unpack 0 0 0`. Fall back to driving `kslider` inlets (velocity, then pitch) only when no `notein` exists.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary | Rationale |
|---|---|---|---|
| Kill switch | Bridge patch (MAX) | Client hint text | Only MAX can drop packets before `route` |
| DSP state + rate query | Bridge patch (`adstatus`, `dspstate~`) | Client (decision, restore) | MAX owns the audio state; Python decides |
| DSP restore | Client (`_execute`) | Bridge `/dsp` (exists) | Sequencing lives in Python by design |
| SR guard | Client (`analyze`) | Bridge `/query` | Pure analysis once the rate is known |
| Tap placement, note injection | Client (`instrument()`, temp copy) | — | The copy is the only patch we may change |
| Error dedupe | Client (`_error_lines`) | — | Post-processing of collected events |

## Standard Stack

No new packages. The existing stdlib, numpy 2.4.0 and scipy 1.17.0 are enough [VERIFIED: `python3 -c "import numpy, scipy"`]. MAX objects, all checked in the DB this session [VERIFIED: `ObjectDatabase().lookup()`, domain/IO printed]:

| Object | DB domain | Inlets / outlets | Use |
|---|---|---|---|
| `toggle` | Max | 1 / 1 | kill-switch control (UI maxclass) |
| `gate` | Max | `compute_io_counts('gate',[])` = (2, 1) | in 0 = control (hot), in 1 = data (cold) |
| `adstatus` | MSP | (2, 2); override outlets both `control` | `adstatus switch`, `adstatus sr` |
| `dspstate~` | MSP | 1 / 4; override `signal_role: "status"` (projects to `signal: False`, so a control cord validates) | outlet 1 = sample rate (float) |
| `trigger` | Max | `t b b b` | bang fan-out for `/query` |
| `send` | Max | 1 / 0 | `/note` -> `__maxbridge_note` |
| `notein` | Max | (1, 3) no args; `notein 1` -> (1, 2) | stimulus target |
| `kslider` | Max | in 0 hot, in 1 cold / out 0 pitch, out 1 velocity | stimulus fallback |
| `unpack` | Max | `unpack 0 0 0` -> (1, 3) | note list splitter in the copy |

The barnett-dbap help-style form `dspstate~` outlet 1 -> `prepend sr` exists in a user-confirmed patch [VERIFIED: patches/barnett-dbap/generated/barnett-dbap.maxpat, the `dspstate~` box `outlettype ['int', 'float', 'int', 'int']`, cord outlet 1 -> `prepend sr` inlet 0].

## Package Legitimacy Audit

None. This phase installs no external packages.

## Architecture Patterns

### Bridge patch data flow (v0.2.0)

```
udpreceive 7400 ──► gate 1 0 (in 1) ──► deferlow ──► route /ping … /closefile /query /note
toggle ─► t i i ─(out 1)► select 0 ─(bang)► t i i i i   (disable also stops listening)
               └(out 0)► gate (in 0)
route /query ─► t b b b ─(2)► adstatus switch ─(right out)► prepend /state/dsp  ─► udpsend 127.0.0.1 7401
                        ─(1)► adstatus sr     ─(right out)► prepend /state/adsr ─► udpsend
                        ─(0)► dspstate~       ─(out 1)────► prepend /state/sr   ─► udpsend
route /note  ─► send __maxbridge_note
```

### 1. Kill switch (bridge patch)

- **Gate:** `gate 1 0`. Per the gate refpage, "Initial state — Specifies which outlet is initially open. The default is 0 (none)", and "If the number in the left inlet is 0, or if no outlet number has been received yet, all messages are ignored" [CITED: refpages/max-ref/gate.maxref.xml]. The explicit `0` arg documents closed-at-load.
- **Toggle init:** a non-parameter `toggle` loads at 0 and does not save its value. **Do not add a second `loadmess`**: `test_listen_fanout_closed_at_load` calls `self._one(p, "loadmess")`, which asserts exactly one [VERIFIED: tests/test_max_bridge.py:341-354]. Pin the toggle's state in a test instead: no `parameter_enable`, gate args `["1", "0"]`.
- **Wiring:**
  - `udpreceive` outlet 0 -> `gate` **inlet 1** (data); `gate` outlet 0 -> `deferlow`.
  - `toggle` -> `t i i`: outlet 1 -> `select 0` -> `t i i i i` inlet 0 (the existing listen fan-out); outlet 0 -> `gate` inlet 0.
  - Per the trigger refpage, "A symbol, list, or bang received in the inlet will be converted to integer 0 by an i outlet" [CITED: refpages/max-ref/trigger.maxref.xml]. So the bang from `select 0` closes `error` and the three console gates. Turning the switch off makes the bridge deaf **and** mute.
- **Gate `/ping` too (recommended).** A fully deaf bridge cannot be fingerprinted. The client cannot tell "gated" from "not open", so its hint names both causes.
  - Alternative, only if the user wants it: `gate 2` with a disabled path replying `/disabled` lets the client say "disabled" exactly. It costs extra boxes and a reply on every LAN packet.
- **Presentation:** Rule #9 applies only "If the target patch uses presentation mode". The bridge has none, and `test_no_print_no_presentation` pins that [VERIFIED: tests/test_max_bridge.py:356-359]. Keep presentation off.
  - Place the toggle top-left, where it is seen first, with a label comment carrying `textcolor [0.8, 0.8, 0.82, 1.0]` (the existing header comments use exactly this [VERIFIED: max-bridge.maxpat obj-1 `'textcolor': [0.8, 0.8, 0.82, 1.0]`]).
  - Update context.md's "Presentation mode" note: the patch now has one user control, still with no presentation.
- **Layout:** udpreceive is at `[20.0, 100.0, 129.5, 22.0]`, deferlow at `[20.0, 140.0, 72.0, 22.0]` and route at `[20.0, 180.0, 513.0, 22.0]` [VERIFIED: bridge patch dump].
  - There is no vertical room for the gate, so move deferlow and its comment obj-7 down 40 and route to y 220. The route's branch boxes start at y 260, leaving an 18 px gap.
  - Put toggle + `t i i` + `select 0` left of / above the gate so its left inlet is fed without crossing the udpreceive cord. One way is to move udpreceive right to about x 110 and put the toggle at x 20.
  - Check with `rendered_rect`: 0 overlaps, as in v0.1.0.

### 2. DSP state + rate query

- **adstatus:**
  - The refpage's right-outlet table says `switch`: "Reports the current on/off setting of the DSP" and `sr`: "Reports the current sampling rate" [CITED: refpages/msp-ref/adstatus.maxref.xml, Output section].
  - The `bang` method: "Reports the current state of the setting … the numerical value of the setting is sent out the adstatus object's right outlet".
  - The help patch wires `adstatus sr` right outlet -> number box. `adstatus switch` is wired only on its LEFT outlet (to a umenu) [VERIFIED: msp/adstatus.maxhelp dump]. So the switch right outlet is MEDIUM until MAX confirms it.
- **dspstate~:**
  - It "outputs state information automatically whenever the audio is turned on or off". Also: "**Note that dspstate~ will not output anything if the audio is not turned on in its window.**" [CITED: refpages/msp-ref/dspstate~.maxref.xml].
  - So it is useless for reading "off". Use it for the rate while DSP is on, and as a fallback signal for "on".
- **Safety:** `t b b b` converts any `/query <args>` to bangs, so a remote `/query 0` can never reach adstatus's `int` method ("Change a setting").
- **Load-time packets:** adstatus has a `loadbang` method ("reports the state of the setting upon loading"). Opening the bridge will therefore send `/state/*` packets to 127.0.0.1:7401. That is harmless, but document it.

**Client sequence** (the existing `plan_messages` with these changes):

```
/ping                     (existence check, fails fast)
/query                    ← BEFORE /open: the patch under test may start DSP itself
/console write before.txt, /listen 1, /open <copy>, /ping (load barrier + settle)
[record]  /dsp 1, /sf samptype float32, /sf open, /sf record <ms>, /query  ← DSP surely on: dspstate~ gives sr
          [/note p v … wait note_ms … /note p 0]  … /sf 0, /ping
/dsp 0   ← sent only when dsp_before != 1 (and not --leave-dsp-on)
/console write after.txt, /listen 0, /close, /ping
```

**`dsp_before` resolution**, from events received before `/open` was sent:
1. the first `/state/dsp` value, if present;
2. else 1 if a `/state/sr` arrived (dspstate~ is silent when off);
3. else `None`: switch DSP off as in v0.1.0 and add the warning `dsp_state_unknown` (an old bridge patch ignores `/query`, because `route`'s unmatched outlet is unconnected).

This makes the restore correct even if adstatus's switch right outlet turns out silent. Restore with DSP state 0 also applies when there is no `--record`: `dsp stop` is idempotent, and N4 says restore regardless.

### 3. Sample-rate guard (`analyze`)

- Signature: `analyze(wav, channels=None, max_sr=None)`. Take `max_sr` as the last `/state/sr` (dspstate~) seen during the run, else the last `/state/adsr`.
- When `max_sr` and `abs(max_sr - header_sr) >= 1`:
  - analyze with `sr = max_sr`;
  - set `header_sample_rate`;
  - append the warning `"sr_header_mismatch: header {h} Hz, MAX DSP {m} Hz; analyzed at {m} Hz"`.
- Keep it a **warning, not a flag**: the corrected analysis is valid, so it should not change the exit code.
- Add `analyze OUT.wav --sr N` for manual reruns.
- Why dspstate~ wins: cycle~ 440 measured 478.9 Hz under a 48000 header. 48000/478.9 = 100.23 samples per cycle, which equals 44100/440. So the DSP ran at 44.1 k [VERIFIED: arithmetic on the open-questions.md Findings numbers]. dspstate~ outlet 1 is "Sampling rate of the connected signal or the global sampling rate" [CITED: dspstate~ refpage]. adstatus sr may report the driver's rate instead; that is unconfirmed.

### 4. Tap placement (`_instrument_patcher`)

- Today there is one `send~` per side per patcher at `x=right` (the far right) [VERIFIED: tools/max_bridge.py:360-382, `right = max(b.right_edge for b in p.boxes) + 30.0`].
- Change the key to `(dst.id, side)`. Place L at `(dac.x, dac.y + dac.h + 20)` and R at `(L.right + 15, same y)`.
- Use `add_box(..., skip_overlap_check=False)` inside `warnings.catch_warnings()` + `simplefilter("ignore", BoxMovedWarning)`. It moves the box down in 15 px steps only on a real overlap [VERIFIED: src/maxpat/builders.py:42-115 docstring].
- Several `send~` objects with one name are fine: "When two or more send~ objects are aimed at the same receive~ object, the signals add together" [CITED: refpages/msp-ref/send~.maxref.xml]. The recorded sum is identical to v0.1.0's.

### 5. Distinct errors (`_error_lines` + new `_distinct_errors`)

- Observed forms:
  - `console_write` line: `osc~: osc~: No such object` [VERIFIED: $TMPDIR/maxbridge-*/after.txt, 13 lines, verbatim];
  - `send: bad arguments creating object` and `codebox: can't assign to parameter g` [same files];
  - the `error` stream gave `osc~: osc~: No such object` (open-questions.md commit 760137be).
- Canonical key: build `"{obj}: {msg}"` for console entries (`msg` alone for the others), collapse whitespace, then repeatedly collapse `^(\S+): \1: ` -> `\1: `.
  - All three channels of the osc~ error then map to `osc~: No such object`.
  - Merge rule for the unconfirmed gen~ case: if key A equals key B with one leading `\S+: ` removed, merge them.
- Report `errors_distinct: [{key, sources: {error: n, console: n, console_write: n}, occurrences: max(n), first_t}]`.
  - `occurrences = max` over sources, because every channel sees every posting. The gen~ double-post then counts as 1 distinct, 2 occurrences.
  - Keep `errors` raw and unchanged. The test assertions on `rep["errors"][0]["source"]` still hold.
- Summary line: `N distinct error(s) (M occurrence(s))`.

### 6. Note stimulus (temp copy + bridge `/note`)

- simple-fm wiring [VERIFIED: patches/simple-fm/generated/simple-fm.maxpat dump]:
  - notein `obj-2`: outlet 0 -> `stripnote` in 0; outlet 1 -> `trigger f f` (-> `select 0` and `stripnote` in 1).
  - `select 0` -> `1. 10` / `0. 200` -> `line~ 0.` -> `*~` inlet 1. That is the envelope.
  - kslider `obj-1` (`'mode': 2`, touchscreen): out 0 -> `makenote 100` in 0; out 1 -> `select 0` and `makenote` in 1.
- **Recommended: mirror notein.** A real MIDI note reaches every no-argument `notein` ("If there is no argument, notein receives from all channels on all ports" [CITED: notein refpage]).
  - In each patcher containing a `notein`, add `receive __maxbridge_note` -> `unpack 0 0 0`.
  - For every cord from notein outlet k (k = 0 pitch, 1 velocity, 2 channel; only 0-1 when notein has a channel arg), add the same cord from unpack outlet k.
  - unpack fires right to left: channel, velocity, then pitch, the same order as notein. Cold-before-hot (Rule #3) holds by construction.
  - Velocity 0 is a note-off ("0 for a note-off message" [CITED: notein refpage]), so `--note-ms` releases the envelope.
- **Fallback (no notein anywhere): kslider.** Wire unpack out 1 -> kslider **in 1** (cold: "sets the output key velocity without triggering output") and out 0 -> kslider **in 0** (hot: "The current velocity value … is sent out its right outlet, followed by the received number out the left outlet") [CITED: refpages/max-ref/kslider.maxref.xml].
  - kslider has **no `list` method** (its methods are bang, int, float, chord, clear, flush, ft1, in1, set, size), so never send it the raw list.
  - Mode 1/2: "A key is turned off by sending … a velocity of 0". Mode 0 (monophonic) may not emit a note-off; confirm in MAX.
- **None of either:** `report["warnings"]` gets `"--note: no notein or kslider to drive"`, and `report["note_target"] = None`.
- **Bridge:** route `/note` -> `send __maxbridge_note`. The route remainder list `60 100 1` reaches the receive; A3 confirms remainder lists pass.
  - Client constant `NOTE_RECEIVE = "__maxbridge_note"`, pinned by a test like `CLOSE_RECEIVE`.
  - The client always sends 3 ints `(pitch, vel, 1)`.
- **CLI:**
  - `--note PITCH VEL` (`nargs=2, type=int`), which requires `--record`.
  - `--note-ms` defaults to `round(record*1000*0.75)` and is clamped to the record length.
  - Timing in `_execute`: after `/sf record`, send `/note p v`, `collect(note_ms/1000)`, `/note p 0`, `collect(record - note_ms/1000 + 0.5)`, then `/sf 0`. That replaces today's single `collect(args.record + 0.5)` before `/sf 0` [VERIFIED: tools/max_bridge.py:825-826].
- Deferred: a generic `/send <name> <msg>` via `forward` would let any LAN host message any `receive` in MAX. `/note` only reaches `__maxbridge_note`, which exists only in temp copies.

### Anti-Patterns to Avoid
- **`insert_into_connection` for the gate.** It wires `source -> new_box inlet i` with i = 0 [VERIFIED: src/maxpat/patcher.py:1538-1546], which would feed udpreceive into gate's CONTROL inlet. Use `remove_connection(udp,0,deferlow,0)` + `add_connection(udp,0,gate,1)` + `add_connection(gate,0,deferlow,0)` instead.
- **Inserting `/query`/`/note` mid-route.** That shifts outlet indices 1-8 and orphans their cords. Append them, then use `replace_box_safe(route, "route", args=[...])`, which keeps every cord whose index still exists.
- **Injecting into both notein and kslider.** simple-fm would get two note-ons per stimulus, and a poly synth would allocate two voices.
- **Reading DSP state from dspstate~ alone.** It is silent when DSP is off.
- **Querying DSP state after `/open`.** A patch with `loadbang -> ; dsp start` would make `dsp_before` read 1.

## Don't Hand-Roll

| Problem | Don't build | Use |
|---|---|---|
| DSP on/off + rate | parsing `adstatus` left-outlet `set N` menu indices | right outlets (numeric) + dspstate~ outlet 1 |
| Box placement off overlaps | custom collision code | `add_box(skip_overlap_check=False)` (`_nudge_off_overlap`) |
| Version label | editing the `v0.1.0` comment by hand | `project.update_version_comment(p, "0.2.0")` + `bump_version(dir, "minor", ...)` |
| Route arg change | delete + re-add the route | `replace_box_safe` (Rule #8) |

## Common Pitfalls

1. **Save gate on the bridge edit.** Use `read_patch(BRIDGE_PATCH)` -> edit -> `save_patch_roundtrip(p.to_dict(), path, original_text)`; it auto-commits. Removing `udpreceive -> deferlow` emits a `SaveGateWarning`; that removal is intended. `StaleFileError` means the user saved it in MAX: re-read. There are no subpatcher ports, so the x-rank rule does not apply.
2. **Pinned tests that must change** [VERIFIED: tests/test_max_bridge.py]:
   - `test_route_order` (270-274) pins the 9-tuple;
   - `test_udpreceive_deferlow_route` (276-282) asserts udpreceive's single successor is `deferlow`; it now goes through `gate`;
   - `test_clean_run_and_order` (725-737) asserts `planned[:2] == ["/ping", "/console"]` and `("/dsp", [0]) in fb.received`. FakeBridge must answer `/query` (configurable dsp state and sr), and the restore case asserts that **no** `/dsp 0` is sent when `dsp_before == 1`.
   - Current `ROUTE_ADDRESSES` [VERIFIED: tools/max_bridge.py:72-75]: `"/ping", "/open", "/sf", "/console", "/dsp", "/listen", "/close", "/openfile", "/closefile",`
3. **Open-questions count test.** `test_every_question_cites_a_checklist_step` asserts `len(entries) == 10 + 6 + 5` and reads `CHECKLIST = .../v0.1.0-bridge-checklist.md` [VERIFIED: tests/test_max_bridge.py:825, 876-887]. Put v0.2.0 questions in the new checklist (or a new file) with a separate test. Do not append numbered/A/N entries to open-questions.md.
4. **`route` numinlets.** The saved route shows `numinlets 10` [VERIFIED: dump], and `compute_io_counts('route', 11 args)` returns `(12, 12)`. Let the Patcher compute it, and do not hand-edit counts. MAX loaded the v0.1.0 value fine.
5. **Float from dspstate~.** The help patch shows outlettype `'float'` for outlet 1, and A2 found float encoding "not exercised yet". The decoder handles `f`/`d`, so `int(round())` the value.
6. **Kill switch UX.** Update `_bridge_hint()` [VERIFIED: tools/max_bridge.py:945-948] to append: "and turn on its enable toggle (the kill switch is off whenever the bridge patch opens)". Every checklist step starts by turning it on.
7. **Taps in a dense patch.** "Directly below" may nudge into far-below space when the dac~ sits above other boxes. That is acceptable; report the final rects in a test.

## Code Examples

```python
# instrument(): note-injection target selection (pseudo, house API)
def _note_sources(p):                      # per patcher, recursing p/patcher like taps
    return [b for b in p.boxes if b.name == "notein"]

# per patcher with noteins:
rcv = p.add_box("receive", [NOTE_RECEIVE], x=nx, y=ny)          # NOTE_RECEIVE = "__maxbridge_note"
up = p.add_box("unpack", ["0", "0", "0"], x=nx, y=ny + 40)
p.add_connection(rcv, 0, up, 0)
for line in list(p.lines):
    if line.source_id in notein_ids and line.source_outlet < 3:
        p.add_connection(up, line.source_outlet, by_id[line.dest_id], line.dest_inlet)
# fallback (no notein in the whole tree): up out 1 -> kslider in 1, up out 0 -> kslider in 0
```

```python
# client: DSP-before resolution from events received before /open was sent
def _dsp_before(events, t_open):
    pre = [(a, args) for t, a, args in events if t <= t_open]
    for a, args in pre:
        if a == "/state/dsp" and args:
            return int(args[0])
    return 1 if any(a == "/state/sr" for a, _ in pre) else None
```

## State of the Art
v0.1.0 protocol baseline: open-questions.md Q1-Q10/A1-A6 answers (2026-10-21) are confirmed facts. Unchanged: deferlow ordering, the `/pong` barrier, console type 1 = error, absolute POSIX paths, `record <ms>` auto-stop, offscreen-window filtering (f00883c6).

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | `adstatus switch` emits 0/1 from its RIGHT outlet on bang (the help patch only wires the left) | §2 | `dsp_before` falls back to the dspstate~ presence inference, which is still correct |
| A2 | dspstate~ outlet 1 reports 44100 in the 44.1 k-MAX / 48 k-interface setup | §3 | the guard picks the wrong rate; adstatus sr is the other candidate |
| A3 | dspstate~ auto-reports synchronously after `; dsp start` (the second `/query` covers it anyway) | §2 | none if the post-record `/query` is kept |
| A4 | console `/con/obj` for the gen~ error equals `codebox` (else the one-prefix merge rule is needed) | §5 | an over-count of 1 for gen~ errors |
| A5 | kslider mode 0 cannot emit velocity 0 (the refpage says "from 1 to 127") | §6 | the kslider fallback never releases; this is irrelevant to the recording |
| A6 | `unpack 0 0 0` ignores nothing and outputs right to left (standard Max) | §6 | wrong hot/cold order |
| A7 | toggle-off -> bang -> `t i i i i` closes listening as intended | §1 | the bridge stays "mute-able" only via `/listen 0` |

## Open Questions (MAX run only)
1. A1, A2, A4 and A5 above.
2. Does `notein` mirroring make simple-fm sound, and does `/note 60 0 1` release it (audible tail, `silent` not flagged)?
3. Toggle off: does `ping` exit 2 with the toggle hint? Toggle on: `PONG`. Does disabling mid-run stop `/err` traffic?
4. Do taps under `dac~` show in a patching-mode screenshot without overlapping (simple-fm's dac~ is at `[405.0, 945.0, 44.0, 22.0]`)?

## Environment Availability

| Dependency | Available | Version |
|---|---|---|
| MAX | ✓ | 9.2.0 (e9c80e453de) [VERIFIED: Info.plist] |
| Python numpy / scipy | ✓ | 2.4.0 / 1.17.0 |
| pytest suite | ✓ | `tests/test_max_bridge.py`: 82 passed in 6.84 s |

## Validation Architecture

| Property | Value |
|---|---|
| Framework | pytest (house) |
| Quick run | `python3 -m pytest tests/test_max_bridge.py -q` (~7 s) |
| Full suite | `python3 -m pytest -q` (baseline: the 2 known pre-existing failures) |

New hermetic tests (all FakeBridge or tmp_path):
- **Bridge patch:**
  - gate between udpreceive (into inlet 1) and deferlow;
  - gate args `1 0`;
  - toggle -> `t i i` -> gate inlet 0 and `select 0` -> listen trigger;
  - the `/query` branch reaches udpsend via 3 prepends;
  - `/note` -> `send` + `NOTE_RECEIVE`;
  - route order is the 11-tuple;
  - `validate_patch` errors are `[]` and `_blocking_findings` is `[]`.
- **DSP restore:** FakeBridge `dsp_on=1` -> no `/dsp 0`; `dsp_on=0` -> `/dsp 0`; no reply -> `/dsp 0` + `dsp_state_unknown`; `/query` precedes `/open`.
- **SR guard:** FakeBridge writes a 44100 header and replies `/state/sr 48000.`; the analysis then uses 48000 and warns `sr_header_mismatch`. Also cover `analyze --sr`.
- **Distinct errors:** the 3-channel osc~ case gives 1 distinct; the doubled codebox gives 1 distinct with 2 occurrences.
- **Taps:** each send~ y > its dac~ bottom, x within the dac~ column; no rendered overlap; two dac~s give two L sends.
- **Note:** the notein mirror reproduces simple-fm's cords from unpack; kslider-only fallback wires in 1 and in 0; neither present -> warning; `--note` without `--record` -> argparse error.
- **Hint:** `ping` against a closed port names the toggle.

## Security Domain

| Item | Control |
|---|---|
| LAN exposure (udpreceive on all interfaces, unchanged) | kill switch closed at every load; gate sits before `deferlow`, so nothing is queued |
| `/query` cannot change audio settings | `t b b b` converts any args to bang before adstatus |
| `/note` scope | fixed name `__maxbridge_note`, which exists only in gitignored temp copies; no generic `/send`/`forward` |
| Output leakage when disabled | toggle-off also closes `error` + console gates; replies only ever go to 127.0.0.1:7401 |

## v0.2.0 Manual Checklist (draft for `test-results/v0.2.0-bridge-checklist.md`)

0. Open the bridge. Confirm the toggle shows OFF. Run `ping`: expect exit 2 and a message naming the toggle. Turn the toggle ON and `ping` again: expect `PONG`.
1. Turn DSP OFF in MAX, then run `check fixtures/fx-clean.maxpat --record 2`. Expect `dsp_before: 0`, and DSP OFF afterwards.
2. Turn DSP ON, then run the same check. Expect `dsp_before: 1`, DSP still ON afterwards, and no `/dsp 0` in `events_raw`/plan.
3. Set MAX to 44.1 k with the interface at 48 k. Run fx-clean `--record 3`. Expect `pitch_hz` ~440, `seconds` ~3.0 and the warning `sr_header_mismatch`. Note the `/state/sr` and `/state/adsr` values (A2).
4. Run `check fixtures/fx-nosuchobj.maxpat`. The summary should say `1 distinct error(s)`. For fx-genfail: 1 distinct, 2 occurrences. Paste the `/con/obj` value (A4).
5. Run `check patches/simple-fm/generated/simple-fm.maxpat --record 3 --note 60 100 --note-ms 2000 --shot`. Expect it to be audible, `silent` not flagged, a release tail after 2 s, and taps under dac~ (inspect in patching mode). Afterwards, `git status --porcelain patches/simple-fm` and `find patches -name '__maxbridge_*'` must both print nothing.
6. Toggle OFF during an idle period, then `check` -> exit 2 with the hint.

## Sources

### Primary (HIGH)
- MAX 9.2 refpages: `msp-ref/adstatus`, `msp-ref/dspstate~`, `msp-ref/send~`, `msp-ref/receive~`, `msp-ref/sfrecord~` (no sample-rate control; only `resample`), `max-ref/gate`, `max-ref/trigger`, `max-ref/kslider`, `max-ref/notein`, `max-ref/error`, `max-ref/console`.
- Help: `help/msp/adstatus.maxhelp`, `help/msp/dspstate~.maxhelp` (wiring and outlettypes dumped).
- Repo: `tools/max_bridge.py`, `tests/test_max_bridge.py`, `patches/max-bridge/{open-questions,context}.md`, the bridge and simple-fm `.maxpat` dumps, `src/maxpat/{builders,patcher,hooks,project}.py`, and `ObjectDatabase` lookups.

### Tertiary
- `$TMPDIR/maxbridge-*/after.txt` (real MAX console-write lines from the 2026-10-21 run).

## Metadata
- Standard stack: HIGH (no new deps; every object is in the DB with the Max/MSP domain and no restrictions).
- Architecture: HIGH for the wiring; MEDIUM for adstatus switch right outlet and which reported rate is right (MAX run).
- Pitfalls: HIGH (read from the tests and API source).
- Valid until: the next Max update (re-check adstatus/dspstate~ refpages).
