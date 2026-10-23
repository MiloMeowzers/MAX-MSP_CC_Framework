---
scope: validation core (validation.py, graph.py, io_resolvers.py, db_lookup.py, walk.py, quickfix.py, critics/fixes.py, audit/*, overrides.json, groups.json, idioms.json, version_io.json)
range: 0f96a6f1..HEAD (8ddcdc49)
reviewed: 2026-10-22
depth: deep
findings:
  blocker: 2
  warning: 4
  info: 4
  total: 10
status: issues_found
---

# Validation core regression review (Q1-Q40)

## Method

- Baseline: the full suite is green on HEAD (`6287 passed, 5 xfailed, 1 xpassed`).
- Old vs new behaviour: I extracted `src/` and `.claude/max-objects/` at 0f96a6f1 into a scratch dir with `git archive`. I ran `validate_patch` on all 77 committed `.maxpat`, `.maxhelp` and `.gendsp` files with both trees and diffed the findings.
- Targeted probes: each finding below was checked with a python3 snippet on HEAD.
  - DB-writing probes (the audit merger) ran on a scratch copy of `.claude/max-objects`.
  - Max.app 9.2.0 is installed, so the refpage and help-patch evidence was read directly from the bundle.
- No source, test or patch file was edited.

The committed patches produce no new validation errors, apart from the deliberately broken `max-bridge` fixtures and the allowlisted `tape-wobble` `pi`/`twopi` assignment. The regressions below therefore show up only on **new** builds and on the DB tooling paths. The calibration suite does not exercise either of them.

---

## BLOCKER

### CR-01: The save gate refuses valid new patches because DB inlets are wrongly marked control-only

These DB entries mark signal inlets as control-only, so Layer 3 flags valid signal cords into them. Q1 and Q7 turned that from a silent strip into a hard block.

**Where**
- Data: `.claude/max-objects/overrides.json`, for example `"mc.sum~"` at line 7070, the `mc.tapout~` / `mcs.tapout~` / `mc.selector~` entries, and the `record~` rule at line 17073.
- Code that acts on it: `src/maxpat/validation.py:1252-1275` (legacy signal → control-only check) and `src/maxpat/validation.py:526-554` (`has_blocking_errors`).

**Defect**
- At 0f96a6f1 these cords were auto-removed and did not block.
- Q1 made a proposed removal block new patches (`has_blocking_errors(is_new=True)`).
- Q7 made a new file refuse every blocker.
- Q2 was supposed to repair the data, but it repaired only inlets that sit inside the base array. Q11 then lengthened some arrays with placeholder control inlets (`{"type": "", "signal": false, "digest": ""}`).

**Failure scenario.** Build the canonical MC mixdown with the Patcher API and save it. The save is refused and nothing is written:

```python
p = Patcher()
osc = p.add_box("mc.cycle~", ["440"]); g = p.add_box("mc.*~", ["0.2"])
s = p.add_box("mc.sum~", []);         d = p.add_box("dac~", [])
p.add_connection(osc,0,g,0); p.add_connection(g,0,s,0); p.add_connection(s,0,d,0); p.add_connection(s,0,d,1)
save_patch_roundtrip(p.to_dict(), "<scratch>/mcsum-test.maxpat")
# PatchValidationError ... (baseline: new file: every blocker refuses):
#   [connections:error] Signal outlet to control-only inlet: 'obj-2' outlet 0 -> 'obj-3' inlet 0 -- proposed removal
```

**Other cords that are valid in MAX but blocked on HEAD.** The old tree only stripped these silently; HEAD blocks them.

| Cord | Evidence that MAX accepts it |
|---|---|
| `cycle~ → mc.selector~ 2` inlet 2 | refpage: inlets 1..N are `signal` |
| `cycle~ → mc.tapout~ 100 200` / `mcs.tapout~` inlet 1 | help: `sig~ → mc.tapout~ 1` |
| `click~` or `cycle~` → `phasor~` inlet 1 | refpage digest "Trigger Reset (signal)"; help: `<~ → phasor~ 1` |
| `cycle~ → sig~` inlet 0 | help: `begin~ → sig~ 0` |
| `cycle~ → record~ buf 2` inlet 1 | channel 2. MAX's own `C74/media/legacy-tutorials/msp-tut/mypvoc2~.maxpat` ships `phasewrap~ → record~ this 2` inlet 1, and validating that bundle file on HEAD proposes removing the cord |

**Contributing causes**
1. 22 placeholder control-only inlets remain on `~` objects past their base arrays. Among them: `mc.sum~ 0`, `mc.bands~ 0`, `live.remote~ 0`, `windowed-fft~ 0`, `mc.tapout~ 1-2`, `mcs.tapout~ 1-2` and `mc.selector~ 2`.
   - Q2's guard (`tests/test_db_signal_ports.py::_inlet_flips`) compares only indices inside the base array, so it never sees them.
2. `record~ buf N`: Q10 fixed the count (`second_arg+2`) but left the inlet layout unmodelled ("deferred to S6/Q33"). Q33 did not do it. `_inlet_accepts_signal` indexes the DB array without args, so inlet 1 resolves to "Recording Start Point".
3. Q38 already mined the evidence: `idioms.json` contains 25 shipped signal cords into DB control-only inlets. But the exemption is keyed by source name.
   - `<~ → phasor~ 1` passes.
   - `click~ → phasor~ 1` blocks.
   - So the DB error is masked for one source and enforced for every other.
4. `ObjectDatabase.get_outlet_types` never returns `multichannelsignal`: it tests `"multichannel" in type`, but the DB types are `signal` / `mc_signal`.
   - MAX-saved MC boxes (`multichannelsignal`) therefore skip the legacy check.
   - Patcher-built ones (`signal`) do not.
   - That is why no committed patch shows the problem.

**Fix**
- Correct the inlets from the evidence. For every `(dst, inlet)` in `idioms.json` with class `signal` whose DB inlet is control-only, set `signal: true` and a `signal/...` type in `overrides.json`. Do the same for the 22 placeholder extensions.
- Extend the guard test to fail on any `~`-object inlet with `type == ""`, `digest == ""` and `signal: false` that has no reviewed reason.
- Model the `record~` layout. Add `trailing_inlets: 2` (mirroring `trailing_outlets`) and resolve the inlet through it in `_inlet_accepts_signal` / `_classify_dst_inlet`, passing `walk.box_args(dst_box)`.
- Make `get_outlet_types` emit `multichannelsignal` for `mc_signal` / `mc.*` signal outlets, so built boxes match what MAX saves.

### CR-02: The audit merger writes `overrides.json` entries that make `ObjectDatabase()` fail to load (Q30 vs Q11)

**Where:** `src/maxpat/audit/merger.py:177-187`, `merger.py:116-127`

**Defect**
- `merge()` still adds a proposal for an object with no domain entry, tagged `_note: "override inactive until object added to domain JSON"`. Since Q11, `ObjectDatabase._apply_object_overrides` raises ValueError on such a key. Q11 also deleted every existing `_note` of this kind.
- New proposal keys are never canonicalized. An alias and its canonical name (`t` + `trigger`) are both written as new keys. Help patches use both spellings, and `parse_object_text` does not canonicalize.

**Repro** (scratch copy of the DB):

```python
db = ObjectDatabase(copy)
prop = {"objects": {"notarealobject~": {"inlets": [{"id": 0}]}}, "conflicts": {}}
m = OverrideMerger(prop_path, copy/"overrides.json", db); m.write(m.merge())
ObjectDatabase(copy)  # ValueError: overrides.json objects key 'notarealobject~' has no base domain entry
# with {"t": {...}, "trigger": {...}} and no live entry for either:
# ValueError: overrides.json objects keys 't' and 'trigger' both resolve to 'trigger' through aliases.json
```

**Impact.** One `audit_db --merge` run leaves every `ObjectDatabase()` constructor in the repo raising, until the file is reverted.

**Fix**
- In `merge()`, skip (and report) proposals whose canonical name is not in `db._objects`, instead of writing a `_note`.
- Key new entries by `self._canonical(name)`, merging same-canonical proposals or reporting them as conflicts.
- After building `merged`, rehearse a load: write to a temp dir, construct `ObjectDatabase`, and refuse to `write()` on ValueError. This mirrors what `--apply aliases` already does.

---

## WARNING

### WR-01: A non-int port index crashes `validate_patch` and the save gate; a negative index passes

**Where:** `src/maxpat/validation.py:1137-1187` (also `1435-1448` and `1464-1478` in Layer 4)

**Defect.** Q19 claims malformed-entry robustness, but only `len()` is checked. `src_outlet >= src_numoutlets` raises TypeError for `"0"` or None, and `outlettype[0.0]` raises for a float. A negative index (`-1`) passes the bounds check, and the role and type lookups then read the last outlet.

**Repro**
- `{"patchline": {"source": ["obj-1", "0"], "destination": ["obj-2", 0]}}` → `TypeError: '>=' not supported between instances of 'str' and 'int'`.
- `save_patch_roundtrip` on such a dict raises that raw TypeError instead of PatchValidationError.
- `review_patch` on the same dict does not crash, because `graph._parse_endpoint` skips the line.
- `["obj-1", -1] -> ["obj-2", -1]` gives no finding at all.

**Fix.** In the malformed-patchline check, also require `type(port) is int and port >= 0` on both ends and emit the existing "Malformed patchline" proposed-removal error. Apply the same guard in `_validate_domain_rules`' two line loops, and reject negatives in `graph._valid_port`.

### WR-02: The override generator still downgrades signal outlets to control (Q2 fixed only the inlet half)

**Where:** `src/maxpat/audit/overrides.py:199-202`, `:264-267`, `_build_outlet_array` at `:288-305`

**Defect**
- The io-count and empty-I/O proposal paths build outlets with `_build_outlet_array([""] * n)`, which gives every outlet `signal: False`.
- Under Q11's per-port merge, `signal: False` overrides a base signal outlet.
- Q2 made `_build_inlet_array` copy `signal`/`type` from the DB but left the outlet builder unchanged.

**Repro** (scratch DB):
- An `ObjectFindings` for `PI_OVER_2~` with `io_count_finding={"confidence": "HIGH", "help_outlets": 2}` → proposed outlets are both `('', False)`.
- After `OverrideMerger.write`, the reloaded DB gives `get_outlet_types("PI_OVER_2~") == ['', '']` (base: `['signal']`).
- Q11's `TestOutletDowngradeGuard` catches this only after the bad merge reaches CI.

**Fix.** Give `_build_outlet_array` the same DB-seeded behaviour as `_build_inlet_array`: copy `signal`/`type` by index, and use the control default only beyond the DB array or for unknown objects. Add a generator-level test next to `test_io_count_path_copies_signal_and_type`.

### WR-03: `sfrecord~ N` inlet count ignores its channel argument, so wiring channels 3+ is impossible

**Where:** `.claude/max-objects/overrides.json` (no `variable_io_rules` entry for `sfrecord~`); consumed by `src/maxpat/db_lookup.py:1411-1471`

**Defect.** `compute_io_counts("sfrecord~", ["4"]) == (2, 1)`, but the refpage (`msp-ref/sfrecord~.maxref.xml`, objarg `number-of-input-channels`) gives N signal inlets.

**Consequence.** The help-I/O oracle cannot see this because the bundle only ships `sfrecord~ 2`. A Patcher-built `sfrecord~ 4` gets 2 inlets: `add_connection` to inlet 2 fails, and validation of a MAX-saved 4-channel box proposes removal of the channel-3/4 cords. `jit.catch~ N` has the same defect (help `jit.catch~ 7` = 7 inlets, DB 1); that one is already listed in `tests/fixtures/help_io_baseline.json`.

**Fix.** Add `"sfrecord~": {"inlet_count": "first_arg", "default_inlets": 1, ...}` with the refpage as evidence. Add a matching `first_arg` inlet rule for `jit.catch~`.

### WR-04: The unterminated-chain rule flags the CLAUDE.md-sanctioned `*~ 0.` terminator, now inside every subpatcher

**Where:** `src/maxpat/validation.py:1689-1730`

**Defect.** CLAUDE.md (MSP): "Always terminate signal chains with `dac~` or `*~ 0.`". `_check_unterminated_chains` exempts only `dsp_roles.chain_terminal_names`, so `*~ 0.` (and `*~ 0`) with no downstream cord is reported as unterminated. Q19's recursion turned the top-level-only false positive into 4 new warnings on the user-confirmed `terrain-synth.maxpat`: `[p terrain-view-a]` obj-26 and obj-45, `[p terrain-view-b]` obj-26 and obj-48. Each is `terrain-osc → *~ 0.`, the documented mute sink.

**Fix.** Skip a `*~` box whose first positional arg parses to 0.0 and whose right inlet has no incoming cord. Alternatively, add "zero-gain `*~`" to the chain-terminal rule in `dsp_roles`.

---

## INFO

### IN-01: The quick-fix docstring claims the save gate uses the `(rule, box_ids, port, path)` identity, but it does not

**Where:** `src/maxpat/quickfix.py:16-18`

`hooks._finding_key` (hooks.py:563-599) still keys on a normalised text template plus regex-extracted `obj-N` ids. Q33's structured `rule` / `box_ids` fields are not used by the gate, so the two identities can diverge. A finding whose text changes without its rule changing (a reworded message) is new to the gate but not to the quick-fix selection. Either switch the gate to the structured key or fix the docstring.

### IN-02: Nested scopes now warn "Unknown object" for abstractions that sit beside the patch

**Where:** `src/maxpat/validation.py:883-890`

Q19 recursion added 7 warnings on `terrain-synth.maxpat` and `terrain-voice.maxpat` (`terrain-osc`, `terrain-osc-b`, `terrain-lfo`). All three are `.maxpat` files in `patches/terrain-synth/generated/`. Q23's planned abstraction lookup (`patch_path`) would have suppressed them; Q23 never landed (see Spec gaps).

### IN-03: The comment `#N` warning fires on documentation prose

**Where:** `src/maxpat/validation.py:1901-1936`

`looper.maxpat [p about]` obj-18 "A gen~ codebox records and plays buffer~ #1 ..." is newly reported through recursion. It is prose about the bpatcher argument, not an attempted substitution. Consider skipping comments in which `#N` follows an object name inside prose, or keep it at warning and ignore it.

### IN-04: `target_version` says a port "is lost" when the target sits inside the unknown interval

**Where:** `src/maxpat/validation.py:400-432`

`live.meter~` changed between 7.0.3 and 9.0.0. With `target_version="8.0"` the warning says "outlet 1 is lost on Max 8.0", but the evidence only brackets the change. For `after < target < by` the message should say "may be missing (changed between 7.0.3 and 9.0.0)".

---

## Spec gaps

| Q | Missing |
|---|---|
| **Q23** | **Not implemented at all.** `261015-fm1` has PLAN.md only: no SUMMARY, no commits, `validate_patch` has no `patch_path`. A probe on HEAD with each of these gives no finding from `validate_patch` or `review_patch`:<br>• `expr clip($f1, 0., 1.)`<br>• `s nowhere` / `r orphan`<br>• flonum → arg-less `-`<br>• bare list → `mc.cycle~`<br>• `frobnicate 3` → `cycle~`<br>• bpatcher `args: ["slot", "0"]`<br>• missing patcher `bgcolor`<br>A nonexistent abstraction is only a warning; `line~` comma segments are still the old warning, not the specified error. (Also reported as CR-01 in review-docs-completion.md.) |
| Q2 | "Repair signal inlets … and any others found" is incomplete. The listed `mc.tapout~` 1-2, `mcs.tapout~` 1-2 and `mc.selector~` 2 are still control-only, and placeholder inlets remain (`mc.sum~` 0, `mc.bands~` 0, `live.remote~` 0, `windowed-fft~` 0, …). "Fix the cause" covered `_build_inlet_array` only, not `_build_outlet_array` (WR-02). The guard ignores indices past the base array (CR-01). |
| Q10 | `record~ buf N` inlet layout was explicitly deferred to "S6/Q33" (overrides.json:17073, Q10 SUMMARY), and Q33 never did it. `sfrecord~ N` and `jit.catch~ N` are not argument-dependent (WR-03). |
| Q30 | The merger "recomputes conflicts" but still writes orphan `_note` entries and non-canonical alias keys, both of which Q11's loader rejects (CR-02). |
| Q7 / Q33 | Q7 asked for blocker matching "by rule + box ids rather than finding text". The gate still matches a normalised text template. Q33 added structured `rule` / `box_ids` to CriticResult, and the allowlist uses them, but `hooks._finding_key` was not switched (IN-01). |
| Q38 | Done as specified, but the mined idioms expose 25 shipped signal cords into DB control-only inlets that were never fed back into `overrides.json`. The allowlist hides them for one source name only (CR-01, cause 3). |

Q1, Q11, Q12, Q14, Q19, Q20, Q32 and Q39 were spot-checked against their specs and are implemented as written:
- Q1: proposed removals, `apply_fixes` per scope (dict and Patcher, including mc.gen~ `data.patcher`), containers, warning-only roles, known pairs.
- Q11: the corrected counts in the table, alias-canonical keys, fail-fast.
- Q12: implied restrictions with the MAX-equivalent hint.
- Q14: groups merged at lookup time.
- Q19: path-tagged recursion, duplicate ids.
- Q20: port-exact graph.
- Q32: the audit `ImportError` swallow is removed.
- Q39: payload contract, and an end-to-end insert_trigger produces correct cold-before-hot wiring.

The Q10 resolver counts match MAX-saved help boxes for every listed object.

_Reviewer: Claude (gsd-code-reviewer), deep_
