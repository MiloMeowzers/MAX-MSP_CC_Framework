# max-bridge -- open questions (Q34 spike)

Only MAX can answer these. Each one names the checklist step in `test-results/v0.1.0-bridge-checklist.md` that answers it. Fill in "Answer:" after running the checklist.

## From the research

1. Does `error` see load-time errors (a "No such object" posted at instantiation), and gen~ compile errors raised in another top-level patcher? The refpage says "any object in any patch".
   - Answered by: checklist step 4 (and steps 5 and 6)
   - Answer:

2. What do `console`'s three outlets fire, and in what order? What do the Message Type ints mean? Is "No such object" an error type, so that it passes `@showonlyerrors 1`?
   - Answered by: checklist step 4
   - Answer:

3. What is the `console write` file format (plain lines, or with the object-name column?), and does it accept an absolute POSIX path?
   - Answered by: checklist step 4 (`console_write.status` and `new_lines`)
   - Answer:

4. Do `pcontrol load` and `sfrecord~ open` accept absolute POSIX paths?
   - Answered by: checklist step 3
   - Answer:

5. Must `samptype float32` come before `open`? Does a float32 wav keep NaN?
   - Answered by: checklist step 7 (header dtype)
   - Answer:

6. Does `record <ms>` close the file when it finishes, or is `0` still required? Does `0` after an auto-stop post an error?
   - Answered by: checklist step 7
   - Answer:

7. Does `clean, wclose` free a top-level patcher loaded by pcontrol, so that its DSP chain and its `send~` are gone?
   - Answered by: checklist step 9
   - Answer:

8. Does `max openfile` show the window (variant B), and does `max closefile` close it?
   - Answered by: checklist step 8
   - Answer:

9. How long after load does gen~ compile? This sets the `--settle` default (3 s today).
   - Answered by: checklist step 6
   - Answer:

10. Out of spike scope, but needed for `--live`: how should a patch that needs stimulus (MIDI or note messages) be driven? A possible route is a `/send <name> <msg>` via `forward`; it is deferred.
    - Answered by: checklist step 9 (note what simple-fm needed in order to sound)
    - Answer:

## Assumptions to verify

A1. verify: absolute POSIX paths work in `pcontrol load`, `sfrecord~ open` and `console write`. If they do not, fall back to `open -a Max`, or to Max-style paths via `conformpath`.
   - Answered by: checklist step 3 (pcontrol, sfrecord~) and step 4 (console write)
   - Answer:

A2. verify: `udpsend` encodes Max floats as OSC `f` or `d`. The decoder accepts both either way.
   - Answered by: checklist step 4 (the `/con/type` args in `events_raw`)
   - Answer:

A3. verify: a `route` remainder such as `open /x.wav` reaches sfrecord~ as the `open` selector. The same goes for the single-symbol remainder `/open <path>` -> `prepend load`, and for `/openfile <path>` -> `$1` in the message box.
   - Answered by: checklist step 3 (record works) and step 8 (openfile)
   - Answer:

A4. verify: signal fan-out to `send~` in the copy adds no audible change.
   - Answered by: checklist step 3 (listen)
   - Answer:

A5. verify: 0.01 is a sensible `dc_offset` threshold.
   - Answered by: checklist step 3 (fx-clean `dc`) and step 7 (fx-dc)
   - Answer:

A6. verify: is an ephemeral, gitignored sibling copy written without `save_patch_roundtrip` acceptable? The alternative is copies in `$TMPDIR`, which breaks relative lookups.
   - Answered by: checklist step 9 (git status clean, no leftovers)
   - Answer:

## New questions for the user

N1. The bridge listens on UDP 7400 on all interfaces. Do you want a host filter (drop packets not from 127.0.0.1, if MAX exposes the sender) or a kill switch (a toggle that gates the route) before any `/max-verify --live` work?
   - Answered by: checklist step 1 (decide after seeing the firewall behaviour)
   - Answer:

N2. Does macOS show a firewall prompt for MAX when the bridge opens?
   - Answered by: checklist step 1
   - Answer:

N3. `check` refuses patches outside the repo and the temp dir. Should it accept other project roots, e.g. `~/Projects/Ambire`?
   - Answered by: checklist step 9 (decide after a real-project run)
   - Answer:

N4. Should the DSP state be restored to what it was before the check, rather than forced off at the end? (`--leave-dsp-on` is the only escape today.)
   - Answered by: checklist step 7
   - Answer:

N5. How is a presentation-mode window titled and captured (`<stem> (presentation)`)? Is the as-shown capture what you want?
   - Answered by: checklist step 9 (simple-fm, if it opens in presentation)
   - Answer:
