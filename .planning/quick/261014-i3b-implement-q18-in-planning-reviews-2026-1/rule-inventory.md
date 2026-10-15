# Q18 rule inventory (base CLAUDE.md at 725f568f)

Units counted by the reference_data awk counter: 193. RULE: 182. INFO: 11.

Anchors: seed hits are the RULE_ANCHORS seed strings found verbatim in the unit; added anchors (EXTRA) are appended to RULE_ANCHORS.

| # | base line | section | kind | anchors | detail home | planned action | unit text (first 60 chars) |
|---|---|---|---|---|---|---|---|
| 1 | 3 | MAX Development Framework | RULE | Every rule here is mandatory | stays | keep | This file defines how Claude works with MAX/MSP patches and  |
| 2 | 7 | Object Database | RULE | .claude/max-objects/ | stays | keep | The object knowledge base lives at `.claude/max-objects/` wi |
| 3 | 21 | Object Database | INFO | variable_io; min_version | stays | keep | Each domain file is a JSON object keyed by object name. Ever |
| 4 | 25 | Supplementary Files | RULE | aliases.json; overrides.json | db-maintenance.md | one-line + move-detail | - **`overrides.json`** -- Expert corrections that take prece |
| 5 | 26 | Supplementary Files | RULE | aliases.json | stays | keep | - **`aliases.json`** -- Common shortcuts mapped to canonical |
| 6 | 27 | Supplementary Files | RULE | relationships.json | stays | keep | - **`relationships.json`** -- Common object pairings and com |
| 7 | 28 | Supplementary Files | RULE | pd-blocklist.json | stays | keep | - **`pd-blocklist.json`** -- Pure Data objects that do NOT e |
| 8 | 29 | Supplementary Files | INFO | extraction-log.json | stays | keep | - **`extraction-log.json`** -- Extraction metadata and stati |
| 9 | 30 | Supplementary Files | RULE | ObjectDatabase; groups.json; sync_max_bundle.py | db-maintenance.md | one-line + move-detail | - **`groups.json`** -- Inherited group names: MC wrapper met |
| 10 | 34 | How to Use the Database | RULE | ObjectDatabase; src.maxpat.db_lookup; .maxpat | stays | keep | **Primary method -- `ObjectDatabase`:** Use the `ObjectDatab |
| 11 | 48 | How to Use the Database | RULE | db.messages(name); db.selectors(name); groups.json | stays | keep | `lookup()` returns only an object's own messages/attributes. |
| 12 | 50 | How to Use the Database | RULE | .claude/max-objects/; ObjectDatabase | stays | keep | **Browse by domain:** The raw JSON files at `.claude/max-obj |
| 13 | 52 | How to Use the Database | RULE | relationships.json | stays | keep | **Check common companions:** Look up the object name in `rel |
| 14 | 54 | How to Use the Database | RULE | overrides.json; audit_empty_io(); audit_half_empty_io(); dac~; .maxpat | db-maintenance.md | one-line + move-detail | **Verify lookup results have non-empty I/O.** Some DB entrie |
| 15 | 56 | How to Use the Database | RULE | UI_MAXCLASSES; invalid attribute maxclass; dac~; meter~ | db-maintenance.md | one-line + move-detail | **The `maxclass` field in the DB is NOT authoritative.** Mos |
| 16 | 58 | How to Use the Database | RULE | <c74object name>; audit_db.py; v8 | db-maintenance.md | one-line + move-detail | **The authoritative object name is the refpage's `<c74object |
| 17 | 60 | How to Use the Database | RULE | overrides.json; help box wins | db-maintenance.md | one-line + move-detail | **Refpages are authoritative for I/O counts far more than fo |
| 18 | 62 | How to Use the Database | RULE | overrides.json; groups.json; audit_db.py; sync_max_bundle.py | db-maintenance.md | one-line + move-detail | **After a Max update, re-sync the DB from the installed bund |
| 19 | 68 | Rule #1: Never Guess Objects | RULE | UNKNOWN OBJECT; get_effective_restrictions; No such object; lookup()['domain']; rnbo~ | stays | keep | THE cardinal rule. If an object is not in the database, DO N |
| 20 | 70 | Rule #1: Never Guess Objects | RULE | single source of truth | stays | keep (compressed) | This applies to everything: object names, argument formats,  |
| 21 | 74 | Rule #2: Verify Before Connect | RULE | Before creating any connection | stays | keep (compressed) | Before creating any connection between objects, verify: |
| 22 | 75 | Rule #2: Verify Before Connect | RULE | variable_io | stays | keep (compressed) | - Source object outlet index is within bounds (check outlet  |
| 23 | 76 | Rule #2: Verify Before Connect | RULE | variable_io | stays | keep (compressed) | - Destination object inlet index is within bounds (check inl |
| 24 | 77 | Rule #2: Verify Before Connect | RULE | signal outlets connect to signal inlets | stays | keep (compressed) | - Signal type compatibility: signal outlets connect to signa |
| 25 | 78 | Rule #2: Verify Before Connect | RULE | signal/float inlets accept both signal and control connections | stays | keep (compressed) | - Exception: signal/float inlets accept both signal and cont |
| 26 | 80 | Rule #2: Verify Before Connect | RULE | Always count from the database | stays | keep (compressed) | Never connect outlet index 2 on an object that only has 2 ou |
| 27 | 82 | Rule #2: Verify Before Connect | RULE | severity-contract.md | stays | keep (compressed) | What validator and critic findings mean, and which ones bloc |
| 28 | 86 | Rule #3: Hot/Cold Inlet Ordering | INFO | - | stays | keep (compressed) | When sending multiple values to an object: |
| 29 | 87 | Rule #3: Hot/Cold Inlet Ordering | RULE | Send to cold inlets FIRST | stays | keep (compressed) | - Send to cold inlets FIRST (right to left) |
| 30 | 88 | Rule #3: Hot/Cold Inlet Ordering | RULE | Send to hot inlet LAST | stays | keep (compressed) | - Send to hot inlet LAST (leftmost, inlet 0) -- this trigger |
| 31 | 89 | Rule #3: Hot/Cold Inlet Ordering | RULE | Use `trigger` (t) | stays | keep (compressed) | - Use `trigger` (t) object for explicit fan-out ordering whe |
| 32 | 90 | Rule #3: Hot/Cold Inlet Ordering | RULE | ordering does not apply for MSP signal connections | stays | keep (compressed) | - Signal inlets are all "hot" in the audio domain -- orderin |
| 33 | 92 | Rule #3: Hot/Cold Inlet Ordering | RULE | Always use `trigger` for explicit ordering | stays | keep (compressed) | Getting this wrong causes silent bugs where objects compute  |
| 34 | 96 | Rule #4: Patch Style | RULE | Top-to-bottom signal flow | stays | keep (compressed) | - Top-to-bottom signal flow (audio flows down, control flows |
| 35 | 97 | Rule #4: Patch Style | RULE | Use explicit `trigger` objects for fan-out | stays | keep (compressed) | - Use explicit `trigger` objects for fan-out instead of conn |
| 36 | 98 | Rule #4: Patch Style | RULE | Add `comment` objects on non-obvious connections | stays | keep (compressed) | - Add `comment` objects on non-obvious connections |
| 37 | 99 | Rule #4: Patch Style | RULE | Prefer named `send`/`receive` | stays | keep (compressed) | - Prefer named `send`/`receive` (and `send~`/`receive~`) ove |
| 38 | 100 | Rule #4: Patch Style | RULE | Use `patcher` (subpatchers) | stays | keep (compressed) | - Use `patcher` (subpatchers) to organize complex logic into |
| 39 | 101 | Rule #4: Patch Style | RULE | ~20px vertical, ~15px horizontal gutter | stays | keep (compressed) | - Standard object spacing: ~20px vertical, ~15px horizontal  |
| 40 | 102 | Rule #4: Patch Style | RULE | ~5px horizontal gap; meter~ | stays | keep (compressed) | - Companion pairs (e.g. `meter~` beside `gain~`) sit side-by |
| 41 | 103 | Rule #4: Patch Style | RULE | len(text) * 8 + 25 | stays | keep (compressed) | - MAX renders message boxes wider than their stored `patchin |
| 42 | 107 | Text Contrast: Resolve Against the Displayed Surface | RULE | MIN_CONTRAST_RATIO; 4.5:1; luminance > 0.5 | ui-presets.md 'Text Contrast Resolution' | one-line + move-detail | Text color is NEVER chosen against the editing background al |
| 43 | 109 | Text Contrast: Resolve Against the Displayed Surface | INFO | - | ui-presets.md 'Text Contrast Resolution' | move-detail | Precedence when resolving the effective background: |
| 44 | 111 | Text Contrast: Resolve Against the Displayed Surface | RULE | `bgcolor` | ui-presets.md 'Text Contrast Resolution' | one-line + move-detail | 1. **A box's own `bgcolor` wins over any panel beneath it.** |
| 45 | 112 | Text Contrast: Resolve Against the Displayed Surface | RULE | presentation_rect | ui-presets.md 'Text Contrast Resolution' | one-line + move-detail | 2. **Presentation coordinates, when the box is in presentati |
| 46 | 113 | Text Contrast: Resolve Against the Displayed Surface | RULE | `patching_rect` | ui-presets.md 'Text Contrast Resolution' | one-line + move-detail | 3. **Patching coordinates** — `patching_rect` center against |
| 47 | 114 | Text Contrast: Resolve Against the Displayed Surface | RULE | as fallback | ui-presets.md 'Text Contrast Resolution' | one-line + move-detail | 4. **Patcher background** as fallback. |
| 48 | 116 | Text Contrast: Resolve Against the Displayed Surface | RULE | `bgcolor`; all three must be read | ui-presets.md 'Text Contrast Resolution' | one-line + move-detail | Panels encode their fill three different ways and all three  |
| 49 | 118 | Text Contrast: Resolve Against the Displayed Surface | RULE | ensure_text_contrast; repair_text_contrast; finalize_patch(is_new=True) | ui-presets.md 'Text Contrast Resolution' | one-line + move-detail | Use `ensure_text_contrast(patcher)` on new patches (it runs  |
| 50 | 124 | Multislider as Labeled Parameter Bank | INFO | - | builders.py add_labeled_param_bank docstring | move-detail | When multislider bars represent labeled parameters (with com |
| 51 | 125 | Multislider as Labeled Parameter Bank | RULE | orientation: 0 | builders.py add_labeled_param_bank docstring | one-line + move-detail | - Set `orientation: 0` (horizontal bars stacked vertically)  |
| 52 | 126 | Multislider as Labeled Parameter Bank | RULE | add_labeled_param_bank (covering seed anchor kept in the pointer one-liner) | builders.py add_labeled_param_bank docstring | one-line + move-detail | - Bar-to-label alignment formula: multislider height = `size |
| 53 | 127 | Multislider as Labeled Parameter Bank | RULE | add_labeled_param_bank (covering seed anchor kept in the pointer one-liner) | builders.py add_labeled_param_bank docstring | one-line + move-detail | - Comment labels start at the same Y as the multislider top, |
| 54 | 128 | Multislider as Labeled Parameter Bank | RULE | size * 24; add_labeled_param_bank (covering seed anchor kept in the pointer one-liner) | builders.py add_labeled_param_bank docstring | one-line + move-detail | - For fontsize=10 labels: use height=18, spacing=24px, so mu |
| 55 | 129 | Multislider as Labeled Parameter Bank | RULE | contdata: 1 | builders.py add_labeled_param_bank docstring | one-line + move-detail | - Always set `contdata: 1` for real-time feedback during dra |
| 56 | 130 | Multislider as Labeled Parameter Bank | RULE | setstyle: 1 | builders.py add_labeled_param_bank docstring | one-line + move-detail | - Always set `setstyle: 1` for bar display |
| 57 | 131 | Multislider as Labeled Parameter Bank | RULE | named subpatchers | builders.py add_labeled_param_bank docstring | one-line + move-detail | - When adding utility/routing objects (prepend chains, init  |
| 58 | 132 | Multislider as Labeled Parameter Bank | INFO | - | builders.py add_labeled_param_bank docstring | move-detail | - Example extra_attrs for a 14-param bank: `{"size": 14, "se |
| 59 | 134 | Multislider as Labeled Parameter Bank | RULE | Reading values by index; fetchindex; fetch $1; outlet 1 | stays | keep (compressed) | **Reading values by index:** send `fetch $1` (NOT `fetchinde |
| 60 | 138 | Rule #5: No Generator Scripts | RULE | generate.py; .maxpat | stays | keep (compressed) | Never create `generate.py` or similar intermediary Python sc |
| 61 | 140 | Rule #5: No Generator Scripts | INFO | - | - | drop-INFO | This rule exists because the generator pattern causes regene |
| 62 | 142 | Rule #5: No Generator Scripts | RULE | box._raw; Box.to_dict(); Patcher.to_dict(); git show A:file; .maxpat; silently dropped at serialize | stays | keep (compressed) | `Patcher.from_dict` -> `Patcher.to_dict()` round-trips are l |
| 63 | 148 | Rule #6: Z-Order Awareness | RULE | .maxpat; index 0 = topmost | builders.py add_overlay_readout docstring; shared-capabilities 'Z-Order Manipulation' | one-line + move-detail | In `.maxpat` files, z-order is implicit: objects **earlier** |
| 64 | 150 | Rule #6: Z-Order Awareness | RULE | background=1 | builders.py add_overlay_readout docstring; shared-capabilities 'Z-Order Manipulation' | one-line + move-detail | - Background elements (panels, step markers): use `add_panel |
| 65 | 151 | Rule #6: Z-Order Awareness | RULE | bring_to_front | builders.py add_overlay_readout docstring; shared-capabilities 'Z-Order Manipulation' | one-line + move-detail | - Overlay readouts (flonum on top of dial): use `bring_to_fr |
| 66 | 152 | Rule #6: Z-Order Awareness | RULE | ignoreclick=1 | builders.py add_overlay_readout docstring; shared-capabilities 'Z-Order Manipulation' | one-line + move-detail | - Overlay readouts must set `ignoreclick=1` so mouse events  |
| 67 | 153 | Rule #6: Z-Order Awareness | RULE | bring_to_front; send_to_back; set_z_index | builders.py add_overlay_readout docstring; shared-capabilities 'Z-Order Manipulation' | one-line + move-detail | - Use `bring_to_front(box)` (index 0 = top), `send_to_back(b |
| 68 | 155 | Rule #6: Z-Order Awareness | INFO | - | builders.py add_overlay_readout docstring; shared-capabilities 'Z-Order Manipulation' | move-detail | The overlay readout pattern (from gen-eq): |
| 69 | 156 | Rule #6: Z-Order Awareness | RULE | add_overlay_readout (covering seed anchor kept in the pointer one-liner) | builders.py add_overlay_readout docstring; shared-capabilities 'Z-Order Manipulation' | one-line + move-detail | 1. Create the interactive control (e.g., `dial`) |
| 70 | 157 | Rule #6: Z-Order Awareness | RULE | add_overlay_readout (covering seed anchor kept in the pointer one-liner) | builders.py add_overlay_readout docstring; shared-capabilities 'Z-Order Manipulation' | one-line + move-detail | 2. Create the readout display (e.g., `flonum`) |
| 71 | 158 | Rule #6: Z-Order Awareness | RULE | bring_to_front | builders.py add_overlay_readout docstring; shared-capabilities 'Z-Order Manipulation' | one-line + move-detail | 3. Call `bring_to_front(readout)` to move it to index 0 (ren |
| 72 | 159 | Rule #6: Z-Order Awareness | RULE | ignoreclick=1 | builders.py add_overlay_readout docstring; shared-capabilities 'Z-Order Manipulation' | one-line + move-detail | 4. Set `ignoreclick=1` on the readout so the dial remains in |
| 73 | 160 | Rule #6: Z-Order Awareness | RULE | overlapping the dial | builders.py add_overlay_readout docstring; shared-capabilities 'Z-Order Manipulation' | one-line + move-detail | 5. Position the readout overlapping the dial (same or overla |
| 74 | 164 | Rule #7: Commit After Every Save | RULE | auto_commit_patch() | severity-contract.md section 5 | one-line | Every patch save MUST be committed to git. The `save_patch_r |
| 75 | 166 | Rule #7: Commit After Every Save | RULE | StaleFileError; force=True; patches/<project>/; re-read after every save | severity-contract.md section 5 | one-line | Auto-commit is path-scoped: it runs `git commit -m msg -- <p |
| 76 | 168 | Rule #7: Commit After Every Save | RULE | PatchValidationError; SaveGateWarning; force=True | severity-contract.md section 5 | one-line | **Save gate:** before writing, `save_patch_roundtrip()` and  |
| 77 | 170 | Rule #7: Commit After Every Save | RULE | git stash; commit your current work first | severity-contract.md section 5 | one-line | **Prohibited:** `git stash` during any patch workflow. Three |
| 78 | 172 | Rule #7: Commit After Every Save | RULE | git stash; git stash list | severity-contract.md section 5 | one-line | To verify whether a change caused a failure, check out a pri |
| 79 | 174 | Rule #7: Commit After Every Save | RULE | git add -A | severity-contract.md section 5 | one-line | **Multi-instance safety:** When multiple Claude instances wo |
| 80 | 178 | Rule #8: `replace_box()` Orphans Connections — Always Rewire | RULE | does NOT preserve connections | stays | keep (compressed) | `Patcher.replace_box(old, new_name, args=...)` does NOT pres |
| 81 | 180 | Rule #8: `replace_box()` Orphans Connections — Always Rewire | RULE | result.orphaned | stays | keep (compressed) | After every `replace_box` call, iterate `result.orphaned` an |
| 82 | 182 | Rule #8: `replace_box()` Orphans Connections — Always Rewire | RULE | replace_box_safe; rewire="auto" | stays | keep (compressed) | **Prefer `Patcher.replace_box_safe(old, new_name, args=...,  |
| 83 | 186 | Rule #9: Presentation Mode Parity | RULE | add_to_presentation; presentation_rect; Presentation coverage; context.md; must-fix before save | stays | keep (compressed) | If the target patch uses presentation mode (any box has `pre |
| 84 | 188 | Rule #9: Presentation Mode Parity | RULE | ensure_text_contrast; Low contrast text | stays | keep (compressed) | **Presentation parity includes contrast parity.** A control  |
| 85 | 190 | Rule #9: Presentation Mode Parity | RULE | set_canvas_background(); `bgcolor` | stays | keep (compressed) | Set the patcher-level **`bgcolor`** key, not just `editing_b |
| 86 | 196 | MSP (Audio/Signal) | RULE | dac~; *~ 0. | stays | keep (compressed) | - Always terminate signal chains with `dac~` or `*~ 0.` (mul |
| 87 | 197 | MSP (Audio/Signal) | RULE | dac~; *~ 0.; line~; never connect raw oscillators to `dac~` at full volume | stays | keep (compressed) | - Use `*~ 0.5` or `*~` with `line~` for gain control -- neve |
| 88 | 198 | MSP (Audio/Signal) | RULE | scale 0 127 0. 1.; scale 0. 127. 0. 1.; line~ | stays | keep (compressed) | - Gain safety: values feeding the gain input of the `*~` mul |
| 89 | 199 | MSP (Audio/Signal) | RULE | slider position | stays | keep (compressed) | - `gain~` is different: its left inlet takes int slider posi |
| 90 | 200 | MSP (Audio/Signal) | RULE | process at audio rate | stays | keep (compressed) | - Signal objects (names ending in `~`) process at audio rate |
| 91 | 201 | MSP (Audio/Signal) | RULE | snapshot~ | stays | keep (compressed) | - Use `snapshot~` to convert signal values to control rate f |
| 92 | 202 | MSP (Audio/Signal) | RULE | meter~ | stays | keep (compressed) | - Use `meter~` or `levelmeter~` for audio level monitoring |
| 93 | 203 | MSP (Audio/Signal) | RULE | mc.pack~ | stays | keep (compressed) | - Multichannel: `mc.` prefix objects handle multiple channel |
| 94 | 204 | MSP (Audio/Signal) | RULE | line~; space-delimited list | stays | keep (compressed) | - `line~` (signal-rate) **replaces** the active ramp on ever |
| 95 | 205 | MSP (Audio/Signal) | RULE | fluid.buf2list; jit.buffer~; peek~; uzi | stays | keep (compressed) | - `buffer~` has no `info` query and bare attribute names (`s |
| 96 | 206 | MSP (Audio/Signal) | RULE | replacechannel; do not generate it | max-9.2-changes.md | one-line | - Max 9.2 adds to `buffer~` the messages `replacechannel` /  |
| 97 | 207 | MSP (Audio/Signal) | RULE | overrides.json; non-primary outlet | db-maintenance.md | one-line + move-detail | - If a control connection from an MSP object's non-primary o |
| 98 | 208 | MSP (Audio/Signal) | RULE | No such object; min(max(x, lo), hi); do NOT have a `clip()` function | stays | keep (compressed) | - `expr`, `vexpr` and `if` do NOT have a `clip()` function.  |
| 99 | 209 | MSP (Audio/Signal) | RULE | trunc~; floor~ | stays | keep (compressed) | - `floor~` is RNBO-only. In standard MSP use `trunc~` (equiv |
| 100 | 210 | MSP (Audio/Signal) | RULE | "items": ["LP", ","; .maxpat | stays | keep (compressed) | - `umenu` items in `.maxpat` JSON use a comma-as-element for |
| 101 | 214 | Gen~ (GenExpr DSP Code) | RULE | in1; out1 | genexpr-rules.md | one-line + move-detail | - GenExpr codebox uses C-style syntax with `in1`, `in2` for  |
| 102 | 215 | Gen~ (GenExpr DSP Code) | RULE | Param | genexpr-rules.md | one-line + move-detail | - Use `Param` for user-controllable parameters (maps to gen~ |
| 103 | 216 | Gen~ (GenExpr DSP Code) | RULE | History | genexpr-rules.md | one-line + move-detail | - Use `History` for single-sample delay (feedback loops, sta |
| 104 | 217 | Gen~ (GenExpr DSP Code) | RULE | Delay myDelay; delay(); Delay.read | genexpr-rules.md | one-line + move-detail | - For longer delay lines, declare `Delay myDelay(max_samples |
| 105 | 218 | Gen~ (GenExpr DSP Code) | RULE | `Buffer` and `Data` | genexpr-rules.md | one-line + move-detail | - `Buffer` and `Data` for sample data access |
| 106 | 219 | Gen~ (GenExpr DSP Code) | RULE | once per sample | genexpr-rules.md | one-line + move-detail | - Gen~ operates at sample rate -- every operation runs once  |
| 107 | 220 | Gen~ (GenExpr DSP Code) | RULE | both branches always execute | genexpr-rules.md | one-line + move-detail | - No conditional branching cost -- both branches always exec |
| 108 | 221 | Gen~ (GenExpr DSP Code) | RULE | initialized before | genexpr-rules.md | one-line + move-detail | - Variables used inside `if`/`else` blocks must be initializ |
| 109 | 222 | Gen~ (GenExpr DSP Code) | RULE | .maxpat; .gendsp | genexpr-rules.md | one-line + move-detail | - Codebox objects embed GenExpr in `.maxpat` patches; `.gend |
| 110 | 223 | Gen~ (GenExpr DSP Code) | RULE | Param; History; Declaration ordering | genexpr-rules.md | one-line + move-detail | - **Declaration ordering**: ALL declarations (`Param`, `Hist |
| 111 | 224 | Gen~ (GenExpr DSP Code) | RULE | Param; param_name $1; attrui | genexpr-rules.md | one-line + move-detail | - **Setting Param values from MAX:** send `param_name $1` me |
| 112 | 225 | Gen~ (GenExpr DSP Code) | RULE | Waveguide loop filters; POST-LOOP; phase delay; group delay | genexpr-rules.md | one-line + move-detail | - **Waveguide loop filters:** resonant filters (Q >= ~1.5) g |
| 113 | 226 | Gen~ (GenExpr DSP Code) | RULE | Param; mc.gen~; add_gen() | genexpr-rules.md | one-line + move-detail | - **mc.gen~ via `add_gen()` + rename** (confirmed working, j |
| 114 | 227 | Gen~ (GenExpr DSP Code) | RULE | Param; Pre-flight any new in-loop waveguide filter | genexpr-rules.md | one-line + move-detail | - **Pre-flight any new in-loop waveguide filter with a numpy |
| 115 | 228 | Gen~ (GenExpr DSP Code) | RULE | tanh(x*g)/g; 1/tanh(drive) | genexpr-rules.md | one-line + move-detail | - **In-loop saturation: normalize by the drive gain, never b |
| 116 | 229 | Gen~ (GenExpr DSP Code) | RULE | Param; No local aliases in Param-only expressions | genexpr-rules.md | one-line + move-detail | - **No local aliases in Param-only expressions.** gen~ hoist |
| 117 | 230 | Gen~ (GenExpr DSP Code) | RULE | Param; History; Hoisted temps can be emitted out of order; History one(1) | genexpr-rules.md | one-line + move-detail | - **Hoisted temps can be emitted out of order — de-hoist any |
| 118 | 231 | Gen~ (GenExpr DSP Code) | RULE | twopi; sqrt1_2; radtodeg; built-in constant names | genexpr-rules.md | one-line + move-detail | - **Never use GenExpr built-in constant names as variable na |
| 119 | 232 | Gen~ (GenExpr DSP Code) | RULE | Codebox safe-construct rules | genexpr-rules.md | one-line + move-detail | - **Codebox safe-construct rules** (learned from spectraldet |
| 120 | 233 | Gen~ (GenExpr DSP Code) | RULE | tab characters | genexpr-rules.md | one-line + move-detail | - **Spaces only, NEVER tab characters** in codebox code stri |
| 121 | 234 | Gen~ (GenExpr DSP Code) | RULE | else if | genexpr-rules.md | one-line + move-detail | - **No `else if` chains** — use nested `else { if ... }` or  |
| 122 | 235 | Gen~ (GenExpr DSP Code) | RULE | peek(buf, idx, 0); poke(buf, val, idx, 0) | genexpr-rules.md | one-line + move-detail | - **`peek`/`poke` always with explicit channel arg**: `peek( |
| 123 | 236 | Gen~ (GenExpr DSP Code) | RULE | CONSTANT bounds | genexpr-rules.md | one-line + move-detail | - **For loops: single, non-nested, CONSTANT bounds** (`for ( |
| 124 | 237 | Gen~ (GenExpr DSP Code) | RULE | History; Amortize | genexpr-rules.md | one-line + move-detail | - **Amortize heavy scans across samples** instead of burstin |
| 125 | 238 | Gen~ (GenExpr DSP Code) | RULE | proven-safe | genexpr-rules.md | one-line + move-detail | - Caveat: v0.2.0 fixed tabs + loops + else in one pass, so c |
| 126 | 239 | Gen~ (GenExpr DSP Code) | RULE | Param; History; History one(1); Max 9.2's Gen compiler fixes do NOT retire | genexpr-rules.md | one-line + move-detail | - **Max 9.2's Gen compiler fixes do NOT retire any rule abov |
| 127 | 243 | Subpatcher Inlet/Outlet Access | RULE | get_inlets(); get_outlets() | stays | keep (compressed) | When connecting to inlet/outlet objects inside a subpatcher  |
| 128 | 254 | Subpatcher Inlet/Outlet Access | RULE | No such object; inlet~ | stays | keep (compressed) | **No `inlet~` / `outlet~` objects exist in MAX.** Always use |
| 129 | 256 | Subpatcher Inlet/Outlet Access | RULE | extra_attrs={"comment": | stays | keep (compressed) | **Label inlets/outlets via the `comment` attribute** (MAX's  |
| 130 | 260 | RNBO (Export-Ready Patches) | RULE | rnbo_compatible: true | stays | keep (compressed) | - ONLY use objects with `rnbo_compatible: true` in the datab |
| 131 | 261 | RNBO (Export-Ready Patches) | RULE | rnbo~ | stays | keep (compressed) | - RNBO uses `rnbo~` as the container object (like `gen~` but |
| 132 | 262 | RNBO (Export-Ready Patches) | RULE | self-contained | stays | keep (compressed) | - RNBO patches must be self-contained -- no external file de |
| 133 | 263 | RNBO (Export-Ready Patches) | RULE | VST3/AU | stays | keep (compressed) | - Export targets: VST3/AU (plugin), Web Audio (browser), C++ |
| 134 | 264 | RNBO (Export-Ready Patches) | RULE | RNBO-specific definitions | stays | keep (compressed) | - Some RNBO objects have different behavior than their MAX c |
| 135 | 265 | RNBO (Export-Ready Patches) | RULE | `param` objects in RNBO | stays | keep (compressed) | - `param` objects in RNBO map to plugin parameters for VST3/ |
| 136 | 269 | Node for Max (N4M / node.script) | RULE | node.script; node.codebox; .maxpat | max-js-agent SKILL.md | one-line + move-detail | - **`node.script` and `node.codebox` are in the object datab |
| 137 | 270 | Node for Max (N4M / node.script) | RULE | node.script; max-api | max-js-agent SKILL.md | one-line + move-detail | - `node.script` objects run Node.js -- use `const maxAPI = r |
| 138 | 271 | Node for Max (N4M / node.script) | RULE | max-api (covering seed anchor kept in the pointer one-liner) | max-js-agent SKILL.md | one-line + move-detail | - `maxAPI.addHandler('message_name', callback)` to receive m |
| 139 | 272 | Node for Max (N4M / node.script) | RULE | maxAPI.outlet | max-js-agent SKILL.md | one-line + move-detail | - `maxAPI.outlet(value)` to send data back to MAX |
| 140 | 273 | Node for Max (N4M / node.script) | RULE | max-api (covering seed anchor kept in the pointer one-liner) | max-js-agent SKILL.md | one-line + move-detail | - `maxAPI.post('message')` for console output visible in MAX |
| 141 | 274 | Node for Max (N4M / node.script) | RULE | max-api (covering seed anchor kept in the pointer one-liner) | max-js-agent SKILL.md | one-line + move-detail | - `maxAPI.getDict('dict_name')` and `maxAPI.setDict('dict_na |
| 142 | 275 | Node for Max (N4M / node.script) | RULE | node.script; node.codebox; maxAPI.outlet; 1 inlet / 2 outlets | max-js-agent SKILL.md | one-line + move-detail | - `node.script` has a fixed 1 inlet / 2 outlets (not argumen |
| 143 | 276 | Node for Max (N4M / node.script) | RULE | network requests | max-js-agent SKILL.md | one-line + move-detail | - Use for: file I/O, network requests, complex data processi |
| 144 | 280 | js / v8 (JavaScript inside MAX) | RULE | Legacy Engine; ES5; v8; add_js() | max-js-agent SKILL.md; max-9.2-changes.md | one-line + move-detail | - `js` object runs JavaScript inline in MAX on the **Legacy  |
| 145 | 281 | js / v8 (JavaScript inside MAX) | RULE | ES5; v8; add_v8() | max-js-agent SKILL.md; max-9.2-changes.md | one-line + move-detail | - **Write ES5 only for `js` / `jsui`:** `var` and `function` |
| 146 | 282 | js / v8 (JavaScript inside MAX) | RULE | Legacy Engine (covering seed anchor kept in the pointer one-liner) | max-js-agent SKILL.md; max-9.2-changes.md | one-line + move-detail | - `inlets = N` and `outlets = N` to configure I/O count |
| 147 | 283 | js / v8 (JavaScript inside MAX) | RULE | ES5; messagename; arrayfromargs(arguments) | max-js-agent SKILL.md; max-9.2-changes.md | one-line + move-detail | - Handler functions: `bang()`, `msg_int(v)`, `msg_float(v)`, |
| 148 | 284 | js / v8 (JavaScript inside MAX) | RULE | Legacy Engine (covering seed anchor kept in the pointer one-liner) | max-js-agent SKILL.md; max-9.2-changes.md | one-line + move-detail | - `outlet(outlet_index, value)` to send data |
| 149 | 285 | js / v8 (JavaScript inside MAX) | RULE | Legacy Engine (covering seed anchor kept in the pointer one-liner) | max-js-agent SKILL.md; max-9.2-changes.md | one-line + move-detail | - `post('message')` for console output |
| 150 | 286 | js / v8 (JavaScript inside MAX) | RULE | Legacy Engine (covering seed anchor kept in the pointer one-liner) | max-js-agent SKILL.md; max-9.2-changes.md | one-line + move-detail | - Access patcher: `this.patcher.getnamed('object_name')` |
| 151 | 287 | js / v8 (JavaScript inside MAX) | RULE | Legacy Engine (covering seed anchor kept in the pointer one-liner) | max-js-agent SKILL.md; max-9.2-changes.md | one-line + move-detail | - Use for: UI logic, data transformation, algorithmic compos |
| 152 | 288 | js / v8 (JavaScript inside MAX) | RULE | Legacy Engine; v8 | max-js-agent SKILL.md; max-9.2-changes.md | one-line + move-detail | - **`js` vs `v8`:** the installed refpages describe `js` / ` |
| 153 | 289 | js / v8 (JavaScript inside MAX) | RULE | v8; Task; only when the task asks for them | max-js-agent SKILL.md; max-9.2-changes.md | one-line + move-detail | - **Max 9.2 `v8` additions (9.2-only, `v8` family, not `js`) |
| 154 | 295 | Max for Live (M4L / .amxd) | RULE | dac~; plugout~ | stays | keep (compressed) | - **No `gain~` / `live.gain~` / `ezdac~` before `plugout~`.* |
| 155 | 296 | Max for Live (M4L / .amxd) | RULE | Param; param_connect; parameter_enable: 1; saved_attribute_attributes.valueof | add_m4l_gen_synth docstring (valueof keys) | one-line | - **`live.dial` / `live.slider` bind to gen~ Params via `par |
| 156 | 297 | Max for Live (M4L / .amxd) | RULE | param_connect; not Live-automatable | stays | keep (compressed) | - Without `param_connect`, the dial passes values via messag |
| 157 | 298 | Max for Live (M4L / .amxd) | RULE | line~; Param; param_connect; parameter_enable: 1; saved_attribute_attributes.valueof; signal-rate exception | stays | keep (compressed) | - **Slider -> line~ -> gen~ signal-rate exception:** when a  |
| 158 | 302 | bach (package) | RULE | No such object; bach.llll2list; bach.nth; @unwrap 1 | stays | keep (compressed) | - `bach.llll2list` and `bach.list2llll` do NOT exist in the  |
| 159 | 303 | bach (package) | RULE | @out t | stays | keep (compressed) | - Every bach object's `@out` attribute defaults to `n` (nati |
| 160 | 307 | PD Confusion Guard | RULE | .claude/max-objects/; pd-blocklist.json | stays | keep (compressed) | Check `.claude/max-objects/pd-blocklist.json` before using a |
| 161 | 308 | PD Confusion Guard | RULE | osc~ | stays | keep (compressed) | - `osc~` is PD -- use `cycle~` in MAX |
| 162 | 309 | PD Confusion Guard | RULE | lop~ | stays | keep (compressed) | - `lop~` is PD -- use `onepole~` in MAX |
| 163 | 310 | PD Confusion Guard | RULE | hip~ | stays | keep (compressed) | - `hip~` is PD -- use `onepole~` (with inversion) in MAX |
| 164 | 311 | PD Confusion Guard | RULE | bp~ | stays | keep (compressed) | - `bp~` is PD -- use `reson~` in MAX |
| 165 | 312 | PD Confusion Guard | RULE | tabread~ | stays | keep (compressed) | - `tabread~` is PD -- use `index~`, `play~`, or `wave~` in M |
| 166 | 313 | PD Confusion Guard | RULE | throw~ | stays | keep (compressed) | - `throw~`/`catch~` is PD -- use `send~`/`receive~` in MAX |
| 167 | 315 | PD Confusion Guard | RULE | check the PD blocklist | stays | keep (compressed) | If you are about to use an object with `~` that is not in th |
| 168 | 319 | Version Compatibility | RULE | MAX 9; do not ask users to choose a version | stays | keep (compressed) | All patches target MAX 9. This is the required version for a |
| 169 | 321 | Version Compatibility | RULE | min_version | stays | keep (compressed) | - Check `min_version` field before using objects |
| 170 | 322 | Version Compatibility | RULE | MAX 9 | stays | keep (compressed) | - MAX 9 objects (`array.*`, `string.*`, `abl.*`): only avail |
| 171 | 323 | Version Compatibility | RULE | MAX 8.1+ | stays | keep (compressed) | - MC objects (`mc.*`): available from MAX 8.1+ |
| 172 | 324 | Version Compatibility | RULE | MAX 9; min_version | max-9.2-changes.md | one-line | - MAX 9.2 objects (`min_version: 9.2`): `dspstress~`, `jit.w |
| 173 | 325 | Version Compatibility | RULE | NOT version-tagged | max-9.2-changes.md | one-line | - Messages and attributes added in 9.2 (e.g. `buffer~` `trim |
| 174 | 329 | Bpatcher and Abstraction Arguments (`#N` Substitution) | RULE | .maxpat; `args` attribute | stays | keep (compressed) | When a `.maxpat` file is loaded as a bpatcher (or abstractio |
| 175 | 331 | Bpatcher and Abstraction Arguments (`#N` Substitution) | RULE | standalone token | stays | keep (compressed) | **Critical rule: `#N` must be a standalone token in the obje |
| 176 | 341 | Bpatcher and Abstraction Arguments (`#N` Substitution) | RULE | standalone token; separate argument | stays | keep (compressed) | When a bpatcher instance needs multiple distinct names (e.g. |
| 177 | 347 | Bpatcher and Abstraction Arguments (`#N` Substitution) | INFO | - | stays (inline example) | one-line | Inside the subpatch, use `#1` and `#2` directly: |
| 178 | 348 | Bpatcher and Abstraction Arguments (`#N` Substitution) | INFO | - | stays (inline example) | one-line | - `buffer~ #1` becomes `buffer~ slot-1` |
| 179 | 349 | Bpatcher and Abstraction Arguments (`#N` Substitution) | INFO | - | stays (inline example) | one-line | - `send~ #2` becomes `send~ slot-1-out` |
| 180 | 351 | Bpatcher and Abstraction Arguments (`#N` Substitution) | RULE | applies equally to newobj boxes and message boxes | stays | keep (compressed) | This applies equally to newobj boxes and message boxes (`set |
| 181 | 353 | Bpatcher and Abstraction Arguments (`#N` Substitution) | RULE | box._raw; JSON numbers | stays | keep (compressed) | **Numeric bpatcher args must be serialized as JSON numbers,  |
| 182 | 355 | Bpatcher and Abstraction Arguments (`#N` Substitution) | RULE | set Label #1; Comment boxes do NOT perform `#N` substitution | stays | keep (compressed) | **Comment boxes do NOT perform `#N` substitution.** Only `ne |
| 183 | 359 | Variable I/O Objects | RULE | overrides.json; variable_io; variable_io_rules; compute_io_counts; IO_RESOLVERS | stays | keep (compressed) | Some objects change inlet/outlet count based on arguments (` |
| 184 | 360 | Variable I/O Objects | RULE | trigger b i f | stays | keep (compressed) | - `trigger b i f` has 3 outlets (not the default 2) |
| 185 | 361 | Variable I/O Objects | RULE | pack 0 0 0 0 | stays | keep (compressed) | - `pack 0 0 0 0` has 4 inlets (not the default 2) |
| 186 | 362 | Variable I/O Objects | RULE | route foo bar baz | stays | keep (compressed) | - `route foo bar baz` has 4 outlets (3 match + 1 unmatched) |
| 187 | 364 | Variable I/O Objects | RULE | Always compute actual I/O count from arguments | stays | keep (compressed) | Always compute actual I/O count from arguments when generati |
| 188 | 368 | File Conventions | RULE | .maxpat | stays | keep (compressed) | - Patches: `.maxpat` (JSON format) |
| 189 | 369 | File Conventions | RULE | .maxpat; .gendsp | stays | keep (compressed) | - Gen~ patches: `.gendsp` (JSON format, similar structure to |
| 190 | 370 | File Conventions | RULE | node.script | stays | keep (compressed) | - Node for Max: `.js` files referenced by `node.script` obje |
| 191 | 371 | File Conventions | RULE | referenced by `js` object | stays | keep (compressed) | - js object: `.js` files referenced by `js` object |
| 192 | 372 | File Conventions | RULE | .mxo | stays | keep (compressed) | - Externals: `.mxo` bundles (macOS) |
| 193 | 373 | File Conventions | RULE | .maxproj | stays | keep (compressed) | - Projects: `.maxproj` (project container) |

RULE rows without an anchor: none

## Final status (after Task 2)

Every row was executed with its planned action. All 238 RULE_ANCHORS (177 seed + 61 added) and all 30 base headings are present in the slimmed CLAUDE.md (test_rule_anchor_present a001-a238, test_claude_md_headings_preserved).

Whole units dropped (INFO, no instruction):
- #61 (line 140) "This rule exists because the generator pattern ... deprecated in milestone 2.0" -- the reason survives as "(regeneration overwrites manual edits)"; the milestone history is dropped.

INFO sentences dropped from inside kept RULE units:
- #33 "Getting this wrong causes silent bugs ..." -- reworded to "wrong order makes objects compute with stale values".
- #39/#40 "(user-confirmed tight spacing)", "(companion detection lives in defaults.py)".
- #77 "Three orphaned stashes containing significant patch work were discovered and recovered."
- #78 "a `stash && merge && pop` chain short-circuits on conflict and silently strands uncommitted work" (rationale; the imperative "check `git stash list`" stays).
- #80 the quoted replace_box docstring "(no auto-remap per CONTEXT.md locked decision)" and #81 "Silent disconnection from this trap has cost multi-version debugging cycles."
- #83 "This rule exists because presentation parity was forgotten in repeated iterations ..."
- #89 "Floats are converted to int, so a 0.-1. value leaves it at or near silence" (rationale for the kept imperative).
- #107 "(SIMD-friendly)".
- #152 "All five are in the DB" and the bundled v8 example conventions note (duplicated in max-js-agent SKILL.md).

Units moved whole (detail now verbatim at the home, one-liner + pointer in CLAUDE.md): #4 and #9 merge/group semantics, #14-#18, #97 -> db-maintenance.md; #42-#49 -> ui-presets.md "Text Contrast Resolution"; #50-#58 -> add_labeled_param_bank docstring; #63-#73 -> add_overlay_readout docstring (+ shared-capabilities "Z-Order Manipulation"); #101-#126 -> genexpr-rules.md; #136-#143 and #144-#153 -> max-js-agent SKILL.md (+ max-9.2-changes.md); #74-#79 save-gate mechanics -> severity-contract.md section 5; #96, #172, #173 -> max-9.2-changes.md; #155 valueof keys -> add_m4l_gen_synth docstring.
