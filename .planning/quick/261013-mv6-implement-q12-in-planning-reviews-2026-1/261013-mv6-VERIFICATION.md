---
task: quick-261013-mv6
verified: 2026-10-13T00:00:00Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
gaps: []
---

# Q12 Verification: RNBO/Gen-only names and the GenExpr namespace (C3, G3, C11, J5)

**Goal:** Restrict RNBO/Gen-only names and fix the GenExpr namespace.
**Range checked:** 0ef102ea..HEAD (a62a6be1, 903cce2e, 778cec00, merge 3261b39d).
**Status:** passed

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Implied restriction from rnbo/gen-only DB sources; explicit-only `get_domain_restrictions`; `get_implied/effective_restrictions` | VERIFIED | `audit_domain_scope()` returns implied=367, explicit=2, exempt=35. `expr~`, `wrap~`, `counter~` -> implied `['rnbo']`; `history` -> `['gen']`. Explicit `get_domain_restrictions('expr~')` is `[]`, as D-05 requires. |
| 2 | 35 exemptions with `domain_restricted: []`; `codebox` is `[gen, rnbo]`; `floor~` keeps `[rnbo]` | VERIFIED | `rnbo~`, `div~`, `rdiv`, `list.append` -> effective `[]`. `codebox` -> `['gen','rnbo']`. `floor~` -> explicit `['rnbo']`. The overrides diff is +320 lines, all `_domain_scope` notes. `TestBundleOracle` passes (requires_max, not skipped). |
| 3 | `validate_patch` scope resolution; Layer 2 errors; `floor~` unchanged | VERIFIED | A top-level Max patch gives one `objects`-layer error for each of `expr~`, `wrap~`, `counter~` and `history`. The `wrap~` message includes the MAX equivalent `pong~ 1 0. 1.`. `floor~` gives exactly one `domain` finding and no `objects` finding. `cycle~` gives none. |
| 4 | `add_box` refusal; `replace_box` pre-check; inner contexts | VERIFIED | Top-level `add_box` raises ValueError for `expr~`, `wrap~`, `counter~`, `history` and `floor~`; `cycle~` is allowed. Inside `add_rnbo`, `expr~` and `wrap~` are allowed and gen-only `history` is refused. Inside `add_gen`, `history` is allowed and `expr~` is refused. Contexts: `add_rnbo` -> rnbo, `add_gen` -> gen, a subpatcher in a Max patch -> max, a subpatcher in an rnbo~ -> rnbo. `replace_box(cycle~ -> expr~)` raises and the original box is preserved. |
| 5 | Save gate scopes by suffix; new .maxpat with `expr~` refused; .gendsp still saves | VERIFIED | `TestSaveGate` and `TestHooksScope` pass: `test_save_gate_gendsp_saves`, `test_save_gate_maxpat_refused`, `test_read_patch_gendsp`, `test_generate_gendsp_validates_clean`. `SCOPE_BY_SUFFIX` is wired in hooks.py. |
| 6 | `validate_genexpr` is gen-domain only | VERIFIED | `clip()` gives no error. User-defined functions, multi-name `History a(0), b(0)`, `.read(` method calls and commented-out `metro(1)` are all clean. `metro()`, `coll()` and `route()` give an error saying "is a Max object, not a Gen operator". An unknown name with `require(` present gives a warning. An unknown name without `require` gives an error. The Gen codebox bundle oracle test (requires_max) passes. |
| 7 | pd-blocklist: `clip~` removed, `wrap~` -> `pong~ 1 0. 1.` | VERIFIED | The diff matches. `is_pd_object('clip~')` is False and `suggest_max_equivalent('wrap~')` is `pong~ 1 0. 1.`. |
| 8 | CLAUDE.md changes in exactly 3 lines | VERIFIED | The diff shows 3 lines changed: the line-53 `expr~` removal, Rule #1 with the `lookup()['domain']` / `get_effective_restrictions` note, and the clip() rule scoped to `expr`/`vexpr`/`if` with a note that GenExpr has `clip()`. |
| 9 | Before/after identical (triage, codebox, help-io); `patches/` untouched; suite green; Python 3.10 | VERIFIED | I re-ran validate_patch triage independently over 69 files on HEAD against `triage-base.json` taken at the base commit: 0 differing files. `codebox-base.json` equals `codebox-t3.json`. The help-io baseline and after files differ only in `generated_at`. `git diff --stat 0ef102ea HEAD -- patches` is empty. The 7 changed `src/maxpat` files parse with `feature_version=(3,10)`. `git stash list` is empty. |

## Test Suite

`python3 -m pytest -q -p no:cacheprovider` -> **3081 passed, 1 xfailed, 1 xpassed, 29 warnings**. The base was 2921 passed with the same xfail/xpass/warning counts, so 160 tests were added. Of those, 149 are in `tests/test_domain_scope.py`. No failures and no skips of the requires_max tests.

## Key Links

| From | To | Status |
|------|----|--------|
| validation.py | db_lookup `get_implied_restrictions`, `suggest_max_equivalent` | WIRED (behavior observed: Layer 2 error with suggestion) |
| builders.py `add_box` | `get_effective_restrictions` vs `domain_context` | WIRED (refusals and allowances observed) |
| hooks.py | `SCOPE_BY_SUFFIX` -> validate_patch(scope=) | WIRED (save gate tests pass) |
| code_validation.py | `db.is_gen_operator` | WIRED (clip/metro behavior observed) |
| overrides.json | explicit `domain_restricted` pre-empting implied | WIRED (`rnbo~`, `list.*` effective `[]`) |

## Anti-Patterns

I did not scan the changed files for debt markers beyond the test and behavior checks. The 160 new tests pass, and nothing in the observed behavior points to stubs.

## Human Verification

None required. The changes are validator/builder logic covered by deterministic tests. No patch files changed, so there is nothing new to confirm in MAX or Live.

## Gaps

None.

_Verifier: Claude (gsd-verifier)_
