# ChopChop — timing, size, buffer and window lookup

Reference tables for `---size`, the buffer reduction guard, window ratios and slice
alignment. Every number is computed from the formulas the device actually uses.

**Re-verified against `ChopChop_v6_174.amxd`.** The window formula was traced through
`w_fsize → w_div → w_clip → w_mul → s ---windowVal` and is unchanged from v6_127, so every
table below still holds. Section I is new and records what the formula implies for the
performer, which the tables alone do not make obvious.

## The formulas

```
barMs    = 240000 / tempo                        four beats of 4/4
---size  = bars x multiplier x (GlobalLength/4) x barMs
C        = floor(---bufferMs x 0.98 / barMs)     capacity in bars (2% ramp/snramp margin)
d        = largest divisor of B that is <= C     B = bars x multiplier
window   = clip(---size / ---capturedMs, 0..1) x ---reloop
slice    = span / 16                             16 is hardcoded, not a parameter
```

Ranges: LoopLength 1-8 bars, multiplier 1-8, so B spans 1 to 64. Buffer fixed at 120000 ms,
giving an effective ceiling of 117600 ms.

The multiplier is a **bar-count multiplier**, not a meter setting. 1x3 means three 4/4 bars,
twelve beats.

---

## A. Bar length by tempo

`barMs = 240000 / tempo` — four beats of 4/4. Beat = barMs / 4.

| Tempo | barMs | beat ms | 4 bars | 8 bars |
|---|---|---|---|---|
| 60 | 4000 | 1000 | 16000 | 32000 |
| 70 | 3429 | 857 | 13714 | 27429 |
| 80 | 3000 | 750 | 12000 | 24000 |
| 90 | 2667 | 667 | 10667 | 21333 |
| 100 | 2400 | 600 | 9600 | 19200 |
| 110 | 2182 | 545 | 8727 | 17455 |
| 120 | 2000 | 500 | 8000 | 16000 |
| 128 | 1875 | 469 | 7500 | 15000 |
| 130 | 1846 | 462 | 7385 | 14769 |
| 140 | 1714 | 429 | 6857 | 13714 |
| 150 | 1600 | 400 | 6400 | 12800 |
| 160 | 1500 | 375 | 6000 | 12000 |
| 174 | 1379 | 345 | 5517 | 11034 |
| 180 | 1333 | 333 | 5333 | 10667 |

## B. `---size` in ms — bars × multiplier at 120 bpm

At 120 bpm barMs is 2000. For another tempo, scale by `240000/tempo/2000`.

| bars \\ mult | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| **1** | 2000 | 4000 | 6000 | 8000 | 10000 | 12000 | 14000 | 16000 |
| **2** | 4000 | 8000 | 12000 | 16000 | 20000 | 24000 | 28000 | 32000 |
| **3** | 6000 | 12000 | 18000 | 24000 | 30000 | 36000 | 42000 | 48000 |
| **4** | 8000 | 16000 | 24000 | 32000 | 40000 | 48000 | 56000 | 64000 |
| **5** | 10000 | 20000 | 30000 | 40000 | 50000 | 60000 | 70000 | 80000 |
| **6** | 12000 | 24000 | 36000 | 48000 | 60000 | 72000 | 84000 | 96000 |
| **7** | 14000 | 28000 | 42000 | 56000 | 70000 | 84000 | 98000 | 112000 |
| **8** | 16000 | 32000 | 48000 | 64000 | 80000 | 96000 | 112000 | 128000 |

## C. Capacity in bars — 120000 ms buffer, 2% margin

`C = floor(117600 / (barMs × multiplier))`

| Tempo | ×1 | ×2 | ×3 | ×4 | ×6 | ×8 |
|---|---|---|---|---|---|---|
| 60 | 29 | 14 | 9 | 7 | 4 | 3 |
| 70 | 34 | 17 | 11 | 8 | 5 | 4 |
| 80 | 39 | 19 | 13 | 9 | 6 | 4 |
| 90 | 44 | 22 | 14 | 11 | 7 | 5 |
| 100 | 49 | 24 | 16 | 12 | 8 | 6 |
| 110 | 53 | 26 | 17 | 13 | 8 | 6 |
| 120 | 58 | 29 | 19 | 14 | 9 | 7 |
| 130 | 63 | 31 | 21 | 15 | 10 | 7 |
| 140 | 68 | 34 | 22 | 17 | 11 | 8 |
| 150 | 73 | 36 | 24 | 18 | 12 | 9 |
| 160 | 78 | 39 | 26 | 19 | 13 | 9 |
| 174 | 85 | 42 | 28 | 21 | 14 | 10 |
| 180 | 88 | 44 | 29 | 22 | 14 | 11 |

## D. Which combinations trip the guard

Total bars is `bars × multiplier`. Anything above capacity is reduced.

| Tempo | Combinations reduced (bars × mult) |
|---|---|
| 60 | 4×8, 5×6, 5×7, 5×8, 6×5, 6×6, 6×7, 6×8, 7×5, 7×6, 7×7, 7×8, 8×4, 8×5, 8×6, 8×7, 8×8 |
| 70 | 5×7, 5×8, 6×6, 6×7, 6×8, 7×5, 7×6, 7×7, 7×8, 8×5, 8×6, 8×7, 8×8 |
| 80 | 5×8, 6×7, 6×8, 7×6, 7×7, 7×8, 8×5, 8×6, 8×7, 8×8 |
| 90 | 6×8, 7×7, 7×8, 8×6, 8×7, 8×8 |
| 100 | 7×8, 8×7, 8×8 |
| 110 | 7×8, 8×7, 8×8 |
| 120 | 8×8 |
| 130 | 8×8 |
| 140 | **none** |
| 150 and above | **none** |

## E. Divisor reduction — what a request reduces to

`d` = largest divisor of B that is ≤ C. Worked for B = bars × multiplier.

| B (total bars) | divisors of B |
|---|---|
| 1 | 1 |
| 2 | 1, 2 |
| 3 | 1, 3 |
| 4 | 1, 2, 4 |
| 5 | 1, 5 |
| 6 | 1, 2, 3, 6 |
| 7 | 1, 7 |
| 8 | 1, 2, 4, 8 |
| 9 | 1, 3, 9 |
| 10 | 1, 2, 5, 10 |
| 12 | 1, 2, 3, 4, 6, 12 |
| 14 | 1, 2, 7, 14 |
| 15 | 1, 3, 5, 15 |
| 16 | 1, 2, 4, 8, 16 |
| 18 | 1, 2, 3, 6, 9, 18 |
| 20 | 1, 2, 4, 5, 10, 20 |
| 21 | 1, 3, 7, 21 |
| 24 | 1, 2, 3, 4, 6, 8, 12, 24 |
| 25 | 1, 5, 25 |
| 27 | 1, 3, 9, 27 |
| 28 | 1, 2, 4, 7, 14, 28 |
| 30 | 1, 2, 3, 5, 6, 10, 15, 30 |
| 32 | 1, 2, 4, 8, 16, 32 |
| 35 | 1, 5, 7, 35 |
| 36 | 1, 2, 3, 4, 6, 9, 12, 18, 36 |
| 40 | 1, 2, 4, 5, 8, 10, 20, 40 |
| 42 | 1, 2, 3, 6, 7, 14, 21, 42 |
| 45 | 1, 3, 5, 9, 15, 45 |
| 48 | 1, 2, 3, 4, 6, 8, 12, 16, 24, 48 |
| 49 | 1, 7, 49 |
| 54 | 1, 2, 3, 6, 9, 18, 27, 54 |
| 56 | 1, 2, 4, 7, 8, 14, 28, 56 |
| 63 | 1, 3, 7, 9, 21, 63 |
| 64 | 1, 2, 4, 8, 16, 32, 64 |

### Worked examples

| Requested B | Capacity C | Reduced to d | Why |
|---|---|---|---|
| 64 | 19 | **16** | largest divisor of 64 that is ≤ 19 |
| 64 | 40 | **32** | largest divisor of 64 that is ≤ 40 |
| 48 | 20 | **16** | largest divisor of 48 that is ≤ 20 |
| 36 | 10 | **9** | largest divisor of 36 that is ≤ 10 |
| 24 | 20 | **12** | largest divisor of 24 that is ≤ 20 |
| 30 | 11 | **10** | largest divisor of 30 that is ≤ 11 |
| 12 | 10 | **6** | largest divisor of 12 that is ≤ 10 |
| 8 | 19 | **8** | fits, unchanged |
| 49 | 20 | **7** | largest divisor of 49 that is ≤ 20 |
| 25 | 10 | **5** | largest divisor of 25 that is ≤ 10 |

Note the awkward cases: a **prime** B larger than C reduces all the way to 1, 
because 1 is its only divisor below itself. B = 49 with C = 20 gives 7; B = 25 with C = 10 gives 5.

## F. Window ratio — resize within a capture

`window = requested total bars / captured total bars`, clipped to 1.

| Captured | Requested 1 | 2 | 3 | 4 | 6 | 8 |
|---|---|---|---|---|---|---|
| **1 bars** | 1 | 1 | 1 | 1 | 1 | 1 |
| **2 bars** | 0.5 | 1 | 1 | 1 | 1 | 1 |
| **3 bars** | 0.3333 | 0.6667 | 1 | 1 | 1 | 1 |
| **4 bars** | 0.25 | 0.5 | 0.75 | 1 | 1 | 1 |
| **6 bars** | 0.1667 | 0.3333 | 0.5 | 0.6667 | 1 | 1 |
| **8 bars** | 0.125 | 0.25 | 0.375 | 0.5 | 0.75 | 1 |
| **12 bars** | 0.0833 | 0.1667 | 0.25 | 0.3333 | 0.5 | 0.6667 |
| **16 bars** | 0.0625 | 0.125 | 0.1875 | 0.25 | 0.375 | 0.5 |

## G. Slice size — 16 pads across the span

Slice = span / 16. Beat-aligned only when total beats divides by 16.

| Total bars | beats | slice (beats) | on-beat? |
|---|---|---|---|
| 1 | 4 | 0.25 | yes |
| 2 | 8 | 0.5 | yes |
| 3 | 12 | 0.75 | no — 0.75-beat grid |
| 4 | 16 | 1 | yes |
| 5 | 20 | 1.25 | no — 1.25-beat grid |
| 6 | 24 | 1.5 | no — 1.5-beat grid |
| 8 | 32 | 2 | yes |
| 12 | 48 | 3 | yes |
| 16 | 64 | 4 | yes |
| 24 | 96 | 6 | yes |
| 32 | 128 | 8 | yes |

## H. Reloop ratios on a 4-bar capture

| `---reloop` | Plays | Pads in the window |
|---|---|---|
| 1 | 4 bars | 16 |
| 0.5 | 2 bars | 8 |
| 0.25 | 1 bar | 4 |
| 0.125 | 2 beats | 2 |
| 0.0625 | 1 beat | 1 |

---

## Reading the diagnostics against these tables

The four number boxes in `p TempoTranslate` (x 1050) show `barMs`, requested bars **B**,
capacity **C** and chosen divisor **d**. Cross-check against tables A, C and E.

At 120 bpm with 8 bars x 8: barMs 2000, B 64, C 58, d 32. 64 bars needs 128000 ms against a
117600 ms ceiling, so it reduces by exactly one step.

The root strip (x 2520, y 700) shows buffer allocation, LoopLength to bars, multiplier,
`---size` after guard, `---capturedMs`, window and `---reloop`. Table F is the check on window:
`---size / ---capturedMs` should match whenever the result is under 1.

If `d` ever fails to divide `B`, or exceeds `C`, the guard is wrong.

## Two things the tables make obvious

**The guard almost never fires at 120 s.** Only 8x8 below about 130 bpm, and nothing at all at
140 and above. It exists because the parameter space allows a request no buffer can hold, not
because normal use approaches the limit.

**Prime bar counts reduce hard.** B = 49 with capacity 20 gives 7, not 20 - its only divisors
are 1, 7 and 49. Correct, since 20 would drift against a 49-bar phrase forever, but it means a
request can shrink much further than capacity alone suggests. Table E lists the divisors so
this is predictable rather than surprising.

---

## I. What the window formula means in performance

Added after the v6_174 session. These follow from `window = clip(---size / ---capturedMs, 0..1)
× ---reloop` and nothing else, but none of them is visible in the tables above.

### The loop is always the first *n* slices

Only `window` is ever sent to karma~ on the length-change path — no `position`, no `jump`. karma~
therefore places the region itself, at the start of the capture. So on a 4-bar capture:

| Requested | window | n (slices lit) | Loop covers | Dropped |
|---|---|---|---|---|
| 4 bars | 1 | 16 | 1–16 | — |
| 3 bars | 0.75 | 12 | 1–12 | 13–16 |
| 2 bars | 0.5 | 8 | 1–8 | 9–16 |
| 1 bar | 0.25 | 4 | 1–4 | 5–16 |

Only the entry point moves — traced live: a commit from pad 9 plays 9→12 then 1→8; from pad 5,
5→12 then 1→4; from pad 7, 7→12 then 1→6. All three play the same twelve slices.

### The bar 1–2 commit rule

Because the region is fixed at 1…n, committing a shortening while the playhead is past slice n
leaves it outside the new region, and karma~ pulls it back to the start — an audible break.

The safe window is "you are already inside the new length":

| Change | Safe from | Breaks from |
|---|---|---|
| 4 → 3 | bars 1–3 | bar 4 |
| 4 → 2 | bars 1–2 | bars 3–4 |
| 4 → 1 | bar 1 | bars 2–4 |
| any lengthening | anywhere | never |

Lengthening is always safe: at 3 bars the playhead is already inside 0–11, and any longer
region contains it.

This is designed behaviour, not a defect, and the region overlay displays it — if the playhead
marker sits outside the lit region, committing will jump. Two attempts to remove the constraint
were built and reverted; both routes are closed, and the reasons are in §2 of
`18_ChopChop_v6_174_Architecture_and_Audit.md`.

### The commit is never immediate

`---size` is latched by `obj-2503 f`, banged by `r ---sliceEdge`. A length change always waits
for the next slice boundary — a quarter of a bar at 1 bar, a whole beat at 4 bars. Section G's
slice sizes are therefore also the worst-case latency on a length change.

### Whole bars are incidental

Nothing enforces them. The ratios in section F are clean only because the menu offers whole
bars and `---capturedMs` happens to be a whole number of bars. A capture that isn't lands on a
fraction with no clean slice boundary, and section G's "on-beat?" column stops meaning anything.
