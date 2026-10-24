# face-tracker

Showcase patch for the Cycling '74 Vision package (Max 9.2+) face tracking, with the tracking data made easy to use elsewhere.

## Kickoff (2026-10-23)

- **Goal:** show off the jit.vis face tracking objects and make the data easily accessible.
- **Tracker:** both `jit.vis.face` (eyes/nose/lips/contour) and `jit.vis.facemesh` (dense mesh + irises/eyebrows) on one camera, switchable via umenu.
- **Data access:** named sends (`send face.*`) carrying derived features (mouth open, eye blink, head yaw/pitch/roll, face x/y/size) so any patch can `receive` them; live readouts of every feature in presentation.
- **Audio/MIDI:** small sonification demo (e.g. mouth open -> filter, head yaw -> pan) to show the data in use. No MIDI.
- **UI:** presentation panel: camera view with debugdraw overlay, feature readouts, tracker settings (smooth, minconfidence, mirrored, count).
- **Objects:** Vision package (`jit.vis.grab`, `jit.vis.face`, `jit.vis.facemesh`, `*.parts`, `jit.vis.debugdraw`, `jit.vis.tondc`). All unverified in MAX (min_version 9.2).

## Decisions (discuss, 2026-10-23)

- **Faces:** 1 face.
- **Latency:** feature math is negligible in any approach (Jitter already runs on the main thread, so js would add no thread hop); the latency is in the tracker. Default tracker is `jit.vis.face` (Apple Vision/CoreML on the Neural Engine) with `@async 0`. `jit.vis.facemesh` is web-engine only (MediaPipe in a headless jit.web; async ignored), so it is the slower, richer option. `async` and `smooth` are exposed in the UI.
- **Feature calc: pure Max, no js.** facemesh: dict -> blendshapes via dict.unpack/route + expr for yaw/pitch/roll from the 4x4 head transform. face: jit.spill + expr geometry from region positions. Lives in named subpatchers.
- **Common feature set (both modes):** x, y, size, mouth, blinkL, blinkR, yaw, pitch, roll. Face mode estimates pose from eye/nose geometry. facemesh also sends all 52 blendshapes as `face.bs.<name>`.
- **Ranges:** `face.*` sends normalized 0..1 (angles -1..1) with per-feature calibrate (learn min/max); raw values on `face.raw.*`.
- **Sonification:** saw drone. mouth -> lowpass cutoff, yaw -> pan, pitch -> detune, blink -> pluck/ping. Master gain + on/off.
- **UI:** presentation panel: camera view + debugdraw overlay, live readouts of every feature, tracker umenu (face/facemesh), smooth, minconfidence, mirrored, async.
- **Facts from refpages:** facemesh dict = 52 blendshape scores + 4x4 head transform. `mirrored` swaps blendshape L/R to the subject's own side. `smooth` (IMM Kalman, 0-0.99) affects the landmark matrix only. face = 12 regions (eyes, pupils, eyebrows, nose, lips, contour, median line), up to 4 faces.

## Research (2026-10-23)

Sources: Vision package help patches (`jit.vis.face.maxhelp`, `jit.vis.facemesh.maxhelp`), refpages, `code/jit.vis.skeleton.js`, `code/web/jit.vis.web.reduce.js`, `patchers/jit-vis-grab-ui.maxpat`.

### Camera + display (help-proven pattern)
- `jit.vis.grab` is the package's grab-UI abstraction (`jit-vis-grab-ui.maxpat`, a 250x51 bpatcher face wrapping `jit.grab @unique 1 @automatic 0`): inlet takes 0/1 and messages to jit.grab, outlet sends the video matrix. Help seeds it with `loadmess 1`. Optional `jit.playlist` -> `gswitch` lets the user drop in a movie as an alternative source.
- The video goes to both `jit.world @enable 1 @floating 1 @preserve_aspect 0` (draws the frame as its background) and the tracker. The tracker's `@debugdraw 1` draws the overlay into the implicitly found world. No extra GL objects are needed for the overlay.
- Help comment: "for lowest latency tracking set smooth to 0 and disable async". `jit.fpsgui` on the tracker's matrix outlet shows the tracking rate.

### jit.vis.face (default, CoreML on macOS)
- Matrix: float32, 4 planes (x, y, z, conf), dim 12 x 4 (regions x faces). x/y 0..1 with a top-left origin. **z = 0 on the apple engine.** conf = 0 means not detected.
- **Each row is a region CENTROID**, in this order: 0 left_eye, 1 right_eye, 2 left_pupil, 3 right_pupil, 4 left_eyebrow, 5 right_eyebrow, 6 nose, 7 nose_crest, 8 outer_lips, 9 inner_lips, 10 face_contour, 11 median_line.
- Dict: `face_0` -> region name -> `xyz` (array) + `confidence`. Help-proven read: `dict.unpack face_0:` -> `dict.unpack left_eye: right_eye: nose:` -> `dict.unpack xyz:` -> `array.tolist`.
- **Consequence for the "common feature set" decision:** centroids don't move when the eyes close, so **blink is not derivable in face mode**. Mouth is only a weak proxy: (outer_lips.y - nose.y) / eye distance, which grows as the jaw drops, and is usable after calibration. Pose can be estimated:
  - eyemid = (left_eye + right_eye) / 2, eyedist = |left_eye - right_eye|
  - x, y = face_contour (or eyemid); size = eyedist
  - roll = atan2(dy, dx) of right_eye -> left_eye
  - yaw = (nose.x - eyemid.x) / eyedist
  - pitch = (nose.y - eyemid.y) / eyedist, after calibrating the rest position
  - Recommendation: face mode sends blinkL/blinkR = 0 and the readouts show "n/a"; facemesh mode provides them.

### jit.vis.facemesh (web engine; the rich option)
- Matrix: 478 landmarks x 4 faces, planes x/y/z/conf (0-467 mesh, 468-477 irises). `jit.vis.facemesh.parts` splits it into lips / eyes / eyebrows / face_oval / irises.
- Dict (help-proven): `dict.unpack face_0: count:` -> `dict.unpack blendshapes: rotation: translation:`
  - blendshapes: 52 ARKit names (jawOpen, eyeBlinkLeft, eyeBlinkRight, mouthSmileLeft/Right, browInnerUp, ...), each 0..1
  - rotation: `dict.unpack x: y: z:`, **Euler degrees** (no matrix math needed; the column-major 4x4 + quaternion are also there)
  - translation: x y z in metres
- Features: mouth = jawOpen, blinkL/R = eyeBlinkLeft/Right, pitch/yaw/roll = rotation x/y/z, x/y/size = `jit.3m` on the face_oval part matrix (mean x/y, max - min = size). `@mirrored 1` gives subject-relative L/R.
- All 52 blendshapes -> `face.bs.<name>`: `dict.iter` (key value per entry) -> `sprintf send face.bs.%s` into `forward`, with the value sent after. Check the `dict.iter` output form in MAX.

### Data hub
- Per-feature abstraction `ft.feature.maxpat` (args: `#1` = feature name): `receive face.raw.#1` -> learn min/max (`peak` / `trough`, reset on calibrate) -> `zmap` -> `send face.#1`, plus a readout. Instancing it 9 times gives a uniform bank: easy to read, extend and reuse. Save the abstraction before the main patch (Rule #1).
- Tracker switch: two trackers fed from one `gswitch2`/`gate` (only the selected one runs, so facemesh's web engine doesn't cost CPU while idle). Both write the same `face.raw.*` names.

### Sonification
- 2 detuned `saw~` -> `lores~` (cutoff from face.mouth, scaled e.g. 200-4000 Hz via `line~`) -> constant-power pan built from `expr cos/sin` -> two `*~` with `line~` ramps (**`pan~` is RNBO-only**) -> master `*~` with a 0-1 `line~` -> `dac~`. Blink rising edge (`past 0.5`) -> `line~` ping envelope on a `cycle~`. On/off = toggle -> master gain ramp; also needs a `dac~` start message.

### Version notes
- All `jit.vis.*` need Max 9.2+ and are unverified in MAX. Every other object listed above is a standard Max 9 object and is in the DB with a Max/MSP domain.

## Build v0.1.0 (2026-10-23) — pending test in MAX

Files: `generated/face-tracker.maxpat` (opens in presentation), `generated/ft.feature.maxpat` (bpatcher row abstraction).

- **Video:** `jit.vis.grab` bpatcher (loadmess 1 = On) -> `t l l` -> offscreen `jit.world ftview @visible 0 @output_texture 1 @size/@dim 640 360` -> `jit.pwindow` 480x270; and -> `gate 2 1` (umenu index + 1) -> the selected tracker. Both trackers use `@drawto ftview`; `debugdraw` is switched per tracker. `gswitch2` is not in the DB, so `gate 2` is used instead.
- **Tracker control:** `r ft.face.ctl` / `r ft.mesh.ctl` into each tracker. UI: umenu, mirror (sends `mirror $1` to the grab UI + `mirrored $1` to both trackers), async (face only), smooth (both), minconfidence (face only), learn ranges, reset ranges (bangs the umenu).
- **jit.vis.face** `@async 0 @smooth 0 @outputdict 0`: `p face-features` -> `jit.spill` planes 0/1 (12 values) + plane 3 (conf, gate) -> `unpack` x12 -> `pack f x9` (lex rex nx cx ley rey ny ly cy) -> 7 exprs -> `face.raw.*`. Blink is fixed at 0 by the mode message.
- **jit.vis.facemesh:** `p facemesh-features`: dict face_0 -> blendshapes (jawOpen / eyeBlinkLeft / eyeBlinkRight -> mouth / blinkL / blinkR; `dict.iter` -> `sprintf send face.bs.%s` -> `forward`), rotation x/y/z -> pitch/yaw/roll, `count` -> face.detected. The face_oval part gives `jit.3m` mean x/y and max - min x (size). The blendshapes dict also goes to a `dict.view`.
- **ft.feature** args: label, raw receive, send, cfg receive, in lo, in hi, out lo, out hi. `face.learn 1` resets peak/trough to the current value, then widens them. `face.cfg.<name> range lo hi` is sent per tracker by the umenu's `;` message.
- **Sonify:** saw~ 110 + detuned saw~ -> lores~ (mouth cutoff 200-4000) -> *~ 0.2; blink pings 880/1320 (past 0.5 -> `1, 0. 400` line~); yaw cos/sin pan; master gain line~; audio toggle -> dac~.
- DB fix: `dict.unpack` outlets = keys + 1 (overrides.json variable_io_rules).

**Untested assumptions to check in MAX:**
1. The tracker draws its debugdraw overlay into the offscreen named world, and the world draws the incoming matrix as its background.
2. `jit.spill` on the 12x4 face matrix gives face 0 first.
3. facemesh rotation axes are x = pitch, y = yaw, z = roll.
4. `dict.iter` emits `key value` lists.
5. The default input ranges are guesses; use learn ranges.
6. Yaw/roll sign may flip with mirror.
