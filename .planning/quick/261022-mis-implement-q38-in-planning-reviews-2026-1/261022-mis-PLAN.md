---
phase: quick-261022-mis
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  # Task 1: shipped-idiom allowlist (tracer)
  - tools/help_io.py
  - tools/sync_max_bundle.py
  - .claude/max-objects/idioms.json
  - src/maxpat/db_lookup.py
  - src/maxpat/validation.py
  - src/maxpat/patcher.py
  - tests/test_idioms.py
  # Task 2: objectfile aliases + string min_version (DB data)
  - tests/test_db_tooling.py
  - tests/test_domain_scope.py
  - tests/test_version_tags.py
  - tests/test_objectfile_aliases.py
  - tests/fixtures/help_io_baseline.json
  - .claude/scripts/extract_objects.py
  - .claude/scripts/extract_abstractions.py
  - .claude/max-objects/aliases.json
  - .claude/max-objects/overrides.json
  - .claude/max-objects/gen/objects.json
  - .claude/max-objects/jitter/objects.json
  - .claude/max-objects/m4l/objects.json
  - .claude/max-objects/max/objects.json
  - .claude/max-objects/mc/objects.json
  - .claude/max-objects/msp/objects.json
  - .claude/max-objects/rnbo/objects.json
  - ".claude/max-objects/packages/ABL Effect Modules/objects.json"
  - .claude/max-objects/packages/BEAP/objects.json
  - .claude/max-objects/packages/Bach/objects.json
  - .claude/max-objects/packages/CNMAT/objects.json
  - .claude/max-objects/packages/Cage/objects.json
  - .claude/max-objects/packages/Dada/objects.json
  - .claude/max-objects/packages/EARS/objects.json
  - .claude/max-objects/packages/FlowSwing/objects.json
  - .claude/max-objects/packages/FluCoMa/objects.json
  - ".claude/max-objects/packages/IRCAM Spat/objects.json"
  - ".claude/max-objects/packages/Jitter Geometry/objects.json"
  - ".claude/max-objects/packages/Jitter Tools/objects.json"
  - .claude/max-objects/packages/Mira/objects.json
  - .claude/max-objects/packages/Odot/objects.json
  - ".claude/max-objects/packages/Rhythmic Time Toolkit/objects.json"
  - .claude/max-objects/packages/VIDDLL/objects.json
  - .claude/max-objects/packages/Vizzie/objects.json
  - .claude/max-objects/packages/abclib/objects.json
  - .claude/max-objects/packages/ableton-dsp/objects.json
  - .claude/max-objects/packages/catart-mubu/objects.json
  - .claude/max-objects/packages/cv.jit/objects.json
  - .claude/max-objects/packages/ease/objects.json
  - .claude/max-objects/packages/grainflow/objects.json
  - .claude/max-objects/packages/jit.mo/objects.json
  - .claude/max-objects/packages/maxforlive-elements/objects.json
  - .claude/max-objects/packages/ml-lib/objects.json
  - .claude/max-objects/packages/ml.star/objects.json
  - .claude/max-objects/packages/nn_tilde/objects.json
  # Task 3: version-aware I/O + target_version + docs + final gate
  - .claude/max-objects/version_io.json
  - tests/test_version_io.py
  - CLAUDE.md
  - .claude/skills/references/db-maintenance.md
  - .claude/skills/references/severity-contract.md
  - TECHNICAL.md
autonomous: true
requirements: [Q38]

estimate:
  # estimate-calibration: factor 1 (sample_count 0, confidence low), so tokens == raw_tokens.
  # chars/4 over what the executor touches: plan + execute-plan workflow + summary template ~33k;
  # Task 1 ~58k (reads ~28k of help_io/sync/db_lookup/validation/patcher, writes ~15k, iterations ~15k);
  # Task 2 ~35k (reads ~10k, QDIR scripts + test edits ~10k, iterations ~15k);
  # Task 3 ~44k (reads ~8k, writes ~15k, docs ~6k, gate + iterations ~15k); SUMMARY ~5k.
  # Over the 100k smart zone (advisory). Quick mode keeps one plan; every task ends on a
  # commit boundary, so a fresh continuation can pick up at Task 2 or Task 3.
  tokens: 175000
  raw_tokens: 175000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`python3 tools/sync_max_bundle.py --apply idioms` writes `.claude/max-objects/idioms.json` from the installed bundle's `*.maxhelp` cords (bundle only, never user packages). A cord is recorded when both endpoints are idiom-eligible (walk.object_name not None, name not content-defined, no `codebox` in the name, no embedded `patcher` dict) and the source box records an outlettype at that outlet. The key is (source name, outlet, source-outlet signal class, destination name, inlet). The write is additive (a committed pair is never dropped), canonical and idempotent: a second apply leaves the bytes unchanged and the dry-run summary line reads `+0 pending`."
    - "validate_patch Layer 3 never reports a type/role finding (the `Unverified outlet types` warning, a role-tier warning, or `Signal outlet to control-only inlet`) for a cord whose alias-canonical key is in idioms.json. Bounds, missing-box and malformed-cord errors are still reported for listed pairs. Patcher.replace_box_safe rewires such a cord instead of orphaning it. On the installed bundle, every eligible help cord validated alone against the real DB has no type/role finding."
    - "aliases.json keeps its 12 hand aliases and gains exactly the 232 objectfile aliases observed at planning time (Max 9.2.0): the 13 `mc_wrapper` mc.*~ shortcuts (mc.times~ -> mc.*~, mc.plus~ -> mc.+~, ...), hslider -> slider, 31 list.* -> zl.* (the 30 RNBO-shadowed names plus list.iter), the 97 `max objectfile jit.X jit.op;` shortcuts -> jit.op, and the 90 Vizzie short names -> vz.*. Each resolves to its candidate. The 30 list.* overrides.json entries are deleted. RNBODatabase still reports every list.* name as rnbo-compatible with its RNBO entry. The help-io oracle shows no regression. The I/O snapshot changed only for those 30 list.* names. `--apply aliases --shadowed` is the only way an RNBO/Gen-shadowed name gets an alias, and a name keyed in overrides.json `objects` is aborted."
    - "Every `min_version` in `.claude/max-objects` (each `<domain>/objects.json`, each `packages/*/objects.json`, and overrides.json) is a version string such as \"8\", \"8.1\", \"9\", \"9.2\" or \"4\". extract_objects.py and extract_abstractions.py write \"8\". Nothing else in those files changed: the semantic diff ignoring min_version is empty and the I/O snapshot is unchanged."
    - "`python3 tools/sync_max_bundle.py --apply version-io` writes `.claude/max-objects/version_io.json`. It records per-name I/O changes from bundle help boxes whose saving Max versions (file appversion) disagree on (numinlets, numoutlets) for the same name and argument tokens, and only when the I/O values form a strict version-ordered partition. At planning time this is 8 names: live.meter~, metro, midiformat, midiparse, mousestate, poke~, preset, twist~. vst~ and retune~ are not recorded, because every bundle help box of each (all saved by 9.0.0) shows one I/O. SUMMARY reports this; nothing is fabricated."
    - "`validate_patch(patch, target_version=\"9.0\")` adds layer `version` warnings, never errors, in max scope only (nested max-scope patchers included, tagged with their path). It warns for a box whose min_version is newer than the target, and for a cord on a port that the target build lacks according to version_io.json. With target_version None (the default) every result is identical to before. An unparsable target raises ValueError."
    - "Regression gate: the full pytest run inside Task 3's verify has rc <= the baseline status derived from Step 0's baseline-junit.xml. junit_diff.py exits 0. Its only allowed removals are the 30 `test_exempt[list.*]` ids, and new tests must come from the five Q38 modules. `git status --porcelain patches patterns` and `git stash list` match their Step 0 snapshots. No commit touches patches/ or patterns/, and every commit names explicit paths."
  artifacts:
    - path: ".claude/max-objects/idioms.json"
      provides: "Bundle-shipped cord keys, keyed by source name -> sorted `outlet class dst inlet` strings"
      contains: "\"pairs\""
    - path: "tests/test_idioms.py"
      provides: "mining, writer, DB lookup, Layer 3 exemption, replace_box_safe mirror, live-bundle end-to-end"
      contains: "def test_bundle_help_cords_are_never_flagged"
    - path: ".claude/max-objects/aliases.json"
      provides: "12 hand aliases + 232 objectfile aliases"
      contains: "\"mc.times~\": \"mc.*~\""
    - path: "tests/test_objectfile_aliases.py"
      provides: "real-DB checks of the 232 aliases, override cleanup and RNBO compatibility"
      contains: "def test_q38_aliases_resolve"
    - path: ".claude/max-objects/version_io.json"
      provides: "per-version I/O changes mined from bundle help boxes"
      contains: "\"mousestate\""
    - path: "src/maxpat/validation.py"
      provides: "Layer 3 idiom exemption + opt-in `version` layer"
      contains: "target_version"
    - path: "tests/test_version_io.py"
      provides: "parse_version, version-io mining/writer, io_changes/min_version, target_version validation"
      contains: "def test_target_version_warns_on_missing_port"
  key_links:
    - from: "tools/sync_max_bundle.py"
      to: "tools/help_io.py"
      via: "apply_idioms / section_idioms call help_io.scan_help_idioms; apply_version_io / section_version_io call help_io.scan_version_io"
      pattern: "help_io\\.scan_(help_idioms|version_io)"
    - from: "src/maxpat/db_lookup.py"
      to: ".claude/max-objects/idioms.json"
      via: "ObjectDatabase._load reads the optional file after aliases.json and canonicalizes both endpoint names"
      pattern: "idioms\\.json"
    - from: "src/maxpat/validation.py"
      to: "src/maxpat/db_lookup.py"
      via: "_validate_connections calls db.is_shipped_idiom after the known-pair check; the version layer calls db.min_version and db.io_changes"
      pattern: "is_shipped_idiom|io_changes|min_version"
    - from: "src/maxpat/patcher.py"
      to: "src/maxpat/db_lookup.py"
      via: "_rewire_type_gated returns False for a shipped idiom (mirror of Layer 3)"
      pattern: "is_shipped_idiom"
    - from: ".claude/max-objects/aliases.json"
      to: ".claude/max-objects/overrides.json"
      via: "override keys canonicalize through aliases; apply_aliases aborts any name keyed in overrides `objects`"
      pattern: "overrides"
---

<objective>
Implement Q38 from .planning/reviews/2026-10-11-fix-plan.md:657 ("Bundle mining", review §5.5). Q9 (help-box I/O oracle, tools/help_io.py) and Q30 (objectfile alias report and `--apply aliases`, string `min_version` writer) are its prerequisites and are done.

Parts, as live-checked at planning time (HEAD 3da1f6e0, Max 9.2.0):
1. **Idiom allowlist (does not exist yet).** Mine every (src, outlet) -> (dst, inlet) cord the bundle's help patches ship. Validation never type/role-flags or proposes to strip a listed cord. At HEAD, bundle help cords produce 29 removal-proposing errors and 1218 warnings. A planning-time simulation of the allowlist kept the whole suite green (6008 passed, 5 xfailed, 1 xpassed).
2. **Aliases (the tool exists, nothing has been applied).** aliases.json holds only the 12 hand aliases. The Q30 report lists 311 unresolved objectfile names and 30 RNBO-shadowed list.* names. Apply the 232 names in the five spec categories. Each overrides.json list.* entry already says "Q38 aliases list.* to zl.*: delete this entry then". A simulation showed 0 help-io regressions and 19 improvements.
3. **Version-aware I/O (does not exist yet).** The DB holds 3,445 numeric min_version values (int 8, float 8.1, int 9, float 9.2, and cycle~'s override 4) across 35 objects.json files plus overrides.json. Nothing in src/ reads min_version. There is no per-version I/O data and no target_version parameter.

Purpose: generated patches stop losing cords MAX itself ships; the bundle's own shortcut names resolve; a patch can be checked for collaborators on an older 9.x build.
Output: idioms.json, version_io.json, 232 aliases, string min_version everywhere, `validate_patch(..., target_version=...)`, tests, docs. No `.maxpat` changes, so nothing needs confirming in MAX.

Out of scope (not in the Q38 text): the §5.5 "I/O-drift section plus `--apply io`" and bundle-generated UI-maxclass list; the other 109 unresolved objectfile names (listed in Task 2); tagging the 9.2 messages/attributes by version; critic changes.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@./CLAUDE.md
@.claude/skills/references/db-maintenance.md
@.claude/skills/references/severity-contract.md
@.planning/quick/261012-ubw-implement-q9-in-planning-reviews-2026-10/261012-ubw-SUMMARY.md
@.planning/quick/261016-jbx-implement-q30-in-planning-reviews-2026-1/261016-jbx-SUMMARY.md

QDIR below means .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1. QDIR files (snapshots, scripts, junit, reports) stay uncommitted, except this PLAN and the SUMMARY.

Rules for every task:
- Sequential on the main working tree. Never `git add .` / `git add -A`, never `git stash`. Commit with explicit paths (`git add -- <path>...`). Another instance may be active (for example an untracked `.planning/tci-phase2/`): never stage anything outside this plan's files_modified.
- Rule #1/#2: no object name, count or version is invented. Every DB value written here is either mined from the installed bundle or copied from a named source.
- Python 3.10 compatible (`from __future__ import annotations` where a module already uses it). Python edits in tools/ and src/ are syntax-gated with `ast.parse(..., feature_version=(3, 10))`.
- Every new test that reads the Max bundle carries `@pytest.mark.requires_max` (tests/conftest.py). Hermetic tests use temp dirs and never write the real DB. tests/test_db_tooling.py's module guard enforces that.
- Prefer the existing helpers: `tests/test_sync_max_bundle.py` `_make_bundle`, `_make_db`, `_entry`, `_newobj`; `tests/test_db_tooling.py` `scratch_copy_of_real_db`, `_objectfile_world`, `_add_entries`, `world`. Import the functions only. Never `import *`, which would also import the module-scoped autouse guard fixture.

Interfaces at HEAD (verified at planning time):
- tools/help_io.py: `box_args`, `signal_class(outlettype) -> "signal"|"control"` (signal = "signal" or "multichannelsignal"), `_appversion(top) -> "9.0.0"|"unknown"`, `_is_count`, `GEN_RNBO_CONTAINERS`, `SKIPPED_NAMESPACES`, `CONTENT_DEFINED` (= patcher.CONTENT_DEFINED_NAMES | validation._CONTAINER_NAMES: bpatcher gen~ jit.gen js jsui mc.gen~ mc.poly~ node.script p patcher pfft~ poly~ rnbo~ v8 v8ui), `MAX_PATCHER_DEPTH = 32`, `discover_sources`, `_SourceScan.walk` (the walk shape to mirror), `scan_help_io`, `build_baseline`, `diff_baselines` (returns regressions / improvements). The module docstring states a read-only contract and says it never imports tools.audit_db.
- src/maxpat/walk.py: `object_name(box)` (None for inlet/outlet/patcher/bpatcher, the first token for a newobj, else the maxclass), `box_name`, `box_args(box)` (quote-aware tokens after the name, `@attrs` kept; [] for non-newobj), `iter_patchers`, `scope_of`.
- tools/sync_max_bundle.py: `APPLY_MODES` (:175), `SECTION_KEYS` (:177; tests require `objectfile_aliases` right after `define_missing`, `groups` right after `inherited_attributes`, and `ui_maxclasses` last), `build_bundle_index` (:672; `index["install"]["app_path"]`, `index["install"]["short_version"] == "9.2.0"`), `run_report` (:1842), `canonical_groups_bytes` / `load_groups` / `check_groups_additive` / `write_groups_file` / `apply_groups` (:1545, :1550, :2066, :2091, :2648; the pattern to mirror for a single-file DB writer), `write_aliases_file` (:2119), `apply_aliases` (:2578), `_RNBO_GEN_DOMAINS`, `_muted_lookup`, `objectfile_candidate`, `objectfile_evidence`, `snapshot_io` / `compare_io` (:2799), `format_summary` (:2832), `build_parser` (:2913), `main(argv)` (:2978), the exceptions `WriteRefused`, `AdditiveViolation`, `StyleUnreproducible`, `AliasVerificationFailed`.
- src/maxpat/atomic_io.py: `atomic_write_bytes`, `atomic_write_many(items)` (all-or-nothing), `json_style(raw, data) -> (ensure_ascii, trailing_newline) | None`.
- src/maxpat/db_lookup.py: `ObjectDatabase._load` (:274; aliases first, then relationships, overrides, pd-blocklist, domain files, override merge, groups.json at ~:376), `is_known_pair` (:910), `_compute_implied_restrictions` (alias keys are skipped), `compute_io_counts(name, args)`, `audit_domain_scope()`.
- src/maxpat/validation.py: `validate_patch(patch, db=None, allowed_packages=None, *, scope=None)` (:160), `_validate_scope_layers` (:271), `_validate_nested_scopes` (:373), `_validate_connections` (:975; check order per cord: bounds -> known pair (:1066) -> container dst -> role-tier dispatch -> legacy signal check), `_inlet_accepts_signal`, `_tag`.
- src/maxpat/patcher.py: `_rewire_type_gated(self, src, so, dst, di, walk, inlet_accepts_signal)` (:1462), used by `replace_box_safe`.
- src/maxpat/rnbo.py: `RNBODatabase` reads rnbo/objects.json raw. It never applies aliases or overrides.
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1 (tracer): shipped-idiom allowlist end to end -- bundle help cords -> idioms.json -> ObjectDatabase -> Layer 3 + replace_box_safe</name>
  <files>tools/help_io.py, tools/sync_max_bundle.py, .claude/max-objects/idioms.json, src/maxpat/db_lookup.py, src/maxpat/validation.py, src/maxpat/patcher.py, tests/test_idioms.py</files>
  <precondition>/Applications/Max.app is installed and `python3 tools/sync_max_bundle.py` prints an `install` line with `Max 9.2.0`; `git status --porcelain .claude src tools tests CLAUDE.md TECHNICAL.md` is empty.</precondition>
  <read_first>
    - tools/help_io.py (whole file, 709 lines: docstring contract, walker, scan_help_io)
    - tools/sync_max_bundle.py lines 160-215, 1522-1600, 1842-1900, 2066-2120, 2648-2662, 2832-3100
    - src/maxpat/db_lookup.py lines 220-400 and 905-925
    - src/maxpat/validation.py lines 943-1146
    - src/maxpat/patcher.py lines 1360-1480
    - tests/test_sync_max_bundle.py lines 60-120, 320-450 (fake bundle and DB helpers)
  </read_first>
  <behavior>
    tests/test_idioms.py. Hermetic tests build a fake bundle with `_make_bundle` plus their own help files. Each help file is a dict with `patcher.appversion` and `boxes`/`lines`. Each cord is a `patchline` with `source` [id, outlet] and `destination` [id, inlet].
    - Mining: `help_io.scan_help_idioms(app)` records `"0 signal *~ 0"` under `"cycle~"` for a cycle~ -> *~ cord whose cycle~ box has outlettype ["signal"].
    - Exclusions: a cord with an inlet, outlet, `p`, bpatcher, js, `*codebox*` or embedded-patcher endpoint is counted in `excluded_cords` and not recorded. A cord whose source box has no outlettype at that index is counted in `unclassified_cords`.
    - Walk limits: cords inside a gen~ box's patcher, or in a `dsp.gen` / `rnbo` classnamespace, are never walked. Nesting deeper than MAX_PATCHER_DEPTH is counted in `depth_capped`. An unparsable help file goes to `bad_files` and nothing raises.
    - Writer: `sync.write_idioms_file` raises WriteRefused for any path other than `<db_root>/idioms.json`. It writes canonical bytes. A second identical write returns False and leaves the bytes untouched. A pair already in the file but absent from a fresh mining is kept (additive). An existing file without a `pairs` object raises StyleUnreproducible.
    - CLI: on the fake world, `--apply idioms` writes only idioms.json; every other file under the fake DB root is byte-identical. The dry-run `idioms` section reports `pending` > 0 before the apply and 0 after. The summary line matches `idioms +: N pairs ... +0 pending`.
    - Lookup: `ObjectDatabase(root).is_shipped_idiom(...)` is False when idioms.json is absent. It is alias-canonical on both ends: a pair stored under `sel` matches a query for `select`, and the reverse. The class must match, and a class of None never matches.
    - Exemption: in a scratch copy of the real DB (`scratch_copy_of_real_db`), a cycle~ outlet 0 -> print inlet 0 cord gives `Signal outlet to control-only inlet` with proposed_removal when unlisted. With `"0 signal print 0"` listed under cycle~ it gives no connections finding. The same listed names with an out-of-range outlet index still give the bounds error.
    - Role tier: a source outlet with a curated non-audio signal_role (pick one where `db.get_signal_role` is not None and not "audio", feeding a signal inlet that HEAD's validator warns on) gives no role-tier warning once its key is listed. The same cord with the source box's outlettype changed to the other class is still checked.
    - Mirror: `replace_box_safe` rewires a listed signal -> control-only cord and leaves it out of `result.orphaned`. Unlisted, the cord is orphaned, as at HEAD.
    - `@pytest.mark.requires_max` `test_bundle_help_cords_are_never_flagged`: walk every bundle `*.maxhelp`, skipping the same internals as the miner. For every cord whose endpoints are eligible and whose source class is known, build a one-cord `{"patcher": {"boxes": [...], "lines": [...]}}` from the real boxes and run `_validate_connections` with `ObjectDatabase()`. The only findings allowed are bounds, missing-box and malformed. Assert the number of cords checked is > 40000 (planning time: ~61k cords, 10,030 distinct keys).
    - `@pytest.mark.requires_max` `test_committed_idioms_are_current`: `sync.run_report(REAL_DB, MAX_APP_PATH)["sections"]["idioms"]["pending"] == 0`.
  </behavior>
  <action>
**Step 0. Baseline, before any edit** (copy the Q37 pattern):
- Write `git rev-parse HEAD` to QDIR/base-sha.txt, `git stash list` to QDIR/stash-list-before.txt, and `git status --porcelain patches patterns` to QDIR/patches-status-before.txt.
- Run `python3 tools/sync_max_bundle.py --snapshot-io QDIR/io-before.json --json QDIR/sync-before.json` and keep its printed summary in QDIR/sync-before.txt.
- Copy .planning/quick/261022-ksz-implement-q37-in-planning-reviews-2026-1/junit_diff.py to QDIR/junit_diff.py. Change only the copy:
  - the docstring says it is the Q38 gate (quick 261022-mis);
  - the `ours` predicate accepts new keys starting with `tests.test_idioms`, `tests.test_objectfile_aliases`, `tests.test_version_io`, `tests.test_db_tooling` or `tests.test_version_tags`;
  - `ALLOWED_REMOVED` is exactly the 30 keys `tests.test_domain_scope.TestRealDbRestrictions::test_exempt[list.X]`, for X in: change compare delace ecils filter group indexmap join lace len lookup median mth nth queue reg rev rot scramble sect slice sort stack stream sub sum swap thin union unique.
- Run `python3 -m pytest -q -p no:cacheprovider --junitxml=QDIR/baseline-junit.xml > QDIR/baseline-pytest.txt 2>&1` and write the exit code to QDIR/baseline-rc.txt.
  - Exit 2 or more: stop and report before any edit.
  - Exit 1: record the failing ids in SUMMARY as pre-existing.
  - Planning-time expectation: 6008 passed, 5 xfailed, 1 xpassed.

**Part A. Tests first.** Write tests/test_idioms.py with every `<behavior>` case. Run it and record the red count (collection error or failures) for SUMMARY.

**Part B. src/maxpat/db_lookup.py.**
- Module function `outlet_signal_class(outlettype, index)`. It returns "signal" for "signal" or "multichannelsignal", "control" for any other string, and None when outlettype is not a list, or index is not an int or is out of range. Miner and query share this one function, so tools/help_io.py imports it (it already imports from src.maxpat).
- Module constant `IDIOMS_FILE = "idioms.json"`.
- In `_load`, right after groups.json, read the optional idioms.json into `self._idioms`, a set of `(canonical_src, outlet, cls, canonical_dst, inlet)`. Names go through `self._aliases`. Each list item is split on single spaces into exactly 4 parts with int outlet and inlet. A malformed item raises ValueError naming the file (fail fast, like variable_io_rules).
- Public `is_shipped_idiom(src_name, src_outlet, src_class, dst_name, dst_inlet) -> bool` with an alias-canonical docstring. Like is_known_pair, it exempts only type/role checks; bounds are always enforced.

**Part C. tools/help_io.py.** Extend the docstring: Q38 consumers, and both new scans are read-only like the rest. Add:
- `idiom_endpoint(box) -> str | None`. It returns None when walk.object_name is None, when the name (or its first token) is in CONTENT_DEFINED, when "codebox" is in the name, or when the box has a `patcher` dict. Otherwise it returns the name.
- `scan_help_idioms(max_app) -> dict`. Bundle only: `<max_app>/Contents/Resources/C74/**/*.maxhelp` in sorted relative-path order, never a packages dir. Walk each patcher the way `_SourceScan.walk` does: skip GEN_RNBO_CONTAINERS boxes and SKIPPED_NAMESPACES inner patchers, and respect the MAX_PATCHER_DEPTH cap. Per scope, map box ids to boxes. For each patchline with list source/destination of length >= 2, int indices and both boxes present:
  - an ineligible endpoint -> `excluded_cords`;
  - class None -> `unclassified_cords`;
  - else add `f"{outlet} {cls} {dst} {inlet}"` to `pairs[src]`.
  - Store literal names. Canonicalization happens at load.
- Return `{"available", "reason", "files", "bad_files", "cords", "recorded_cords", "excluded_cords", "unclassified_cords", "malformed_cords", "internal_patchers_skipped", "depth_capped", "pairs"}`. `pairs` maps each source name to a sorted list (sort key: int outlet, class, dst, int inlet). Without a C74 dir, return `unavailable_section(reason)`.

**Part D. tools/sync_max_bundle.py.**
- Add `IDIOMS_FILE = "idioms.json"`, "idioms" to APPLY_MODES, and "idioms" in SECTION_KEYS directly after "groups".
- `canonical_idioms_bytes(data)`: `json.dumps(data, indent=2, ensure_ascii=False) + "\n"` with sorted keys of `pairs` and sorted lists.
- `load_idioms(db_root)`: returns None when absent; raises StyleUnreproducible when the file has no `pairs` object.
- `check_idioms_additive(old, new)`: AdditiveViolation if any old pair is missing.
- `write_idioms_file(path, data, db_root)`: refuses (WriteRefused) any path other than `<db_root>/idioms.json`, mirroring write_groups_file. Returns False on identical bytes, else `atomic_write_bytes`.
- `build_idioms_target(scan, existing, install)`: produces `{"_comment", "generator": "tools/sync_max_bundle.py --apply idioms", "max_version": install short_version, "source": "bundle help (*.maxhelp under Contents/Resources/C74)", "pairs": union(existing, mined)}`. The `_comment` says, in one sentence, what the file is, that Layer 3 never type/role-checks a listed cord while bounds are always checked, and that only this tool writes it, additively.
- `section_idioms(index, db_root)`: the scan stats, `pairs` (count), `committed` (count in the file, 0 when absent), `pending` (mined pairs not yet committed) and `file`. `run_report` adds it. An unavailable bundle reuses `_unavailable`.
- `apply_idioms(index, db_root)` returns `{written, pairs, added, file}`. Wire it into `main` (no --names needed) and its printout. Add a `format_summary` line in exactly this shape: `  idioms          : {pairs} pairs from {recorded_cords} help cords ({excluded_cords} excluded, {unclassified_cords} unclassified), +{pending} pending (--apply idioms)`.
- tools/help_io.py must not import sync or audit_db; sync imports help_io.

**Part E. Exemption and mirror.**
- src/maxpat/validation.py `_validate_connections`: directly after the known-pair `continue`, compute `src_class = outlet_signal_class(src_box.get("outlettype"), src_outlet)`. If `src_name`, `dst_name` and `src_class` are all set and `db.is_shipped_idiom(src_name, src_outlet, src_class, dst_name, dst_inlet)`, `continue`. Update the docstring's check order: bounds -> known pair -> shipped idiom -> container -> role -> legacy.
  - Layer 4 value/topology rules (gain safety, feedback, unterminated chains) are not pair-validity checks and stay untouched. Record this scoping in SUMMARY as an executor-noted design choice.
- src/maxpat/patcher.py `_rewire_type_gated`: before the inlet check, return False when `self.db.is_shipped_idiom(name, so, outlet_signal_class(src.outlettype, so), dst_name, di)`. Here dst_name is `walk.object_name({"maxclass": dst.maxclass, "text": dst.text})`, so the mirror matches validation.

**Part F. Generate and commit.**
- Run `python3 tools/sync_max_bundle.py --apply idioms`. Expect about 10,030 pairs. Then run the dry-run again: it must show `+0 pending`.
- Check `git status --porcelain .claude/max-objects` lists only idioms.json.
- Run the verify command, then the ast 3.10 gate on the four edited .py files.
- Commit with `git add -- tools/help_io.py tools/sync_max_bundle.py .claude/max-objects/idioms.json src/maxpat/db_lookup.py src/maxpat/validation.py src/maxpat/patcher.py tests/test_idioms.py`. Message: `feat(db): shipped-idiom allowlist mined from bundle help cords; Layer 3 never type/role-checks a cord MAX ships (quick 261022-mis, Q38)`.
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_idioms.py tests/test_sync_max_bundle.py tests/test_db_tooling.py tests/test_help_io.py tests/test_validation.py tests/test_validation_nondestructive.py tests/test_validation_recursive.py tests/test_domain_scope.py tests/test_integration_patches.py tests/test_inlet_types.py tests/test_save_gate.py tests/test_patcher.py tests/test_edit_keeps_user_work.py tests/test_db_lookup.py && python3 tools/sync_max_bundle.py | grep -Eq '^  idioms +: [0-9]+ pairs from [0-9]+ help cords .*\+0 pending' && python3 tools/sync_max_bundle.py --compare-io .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/io-before.json > /dev/null && test -s .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/base-sha.txt && test -s .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/baseline-junit.xml && git cat-file -e HEAD:.claude/max-objects/idioms.json && ! git cat-file -e "$(cat .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/base-sha.txt):.claude/max-objects/idioms.json" 2>/dev/null && python3 -c "import sys, xml.etree.ElementTree as E; t = list(E.parse(sys.argv[1]).getroot().iter('testcase')); assert len(t) >= 5000, len(t); assert not [c for c in t if c.get('classname', '').startswith('tests.test_idioms')], 'baseline taken after Part A'" .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/baseline-junit.xml</automated>
  </verify>
  <done>idioms.json is committed and current (dry-run `+0 pending`). Every eligible bundle help cord validates with no type/role finding. Listed pairs still get bounds errors. replace_box_safe keeps listed cords. The I/O snapshot is unchanged versus Step 0. The Step 0 baseline exists and predates tests/test_idioms.py.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: objectfile aliases (232 named) with list.* override cleanup, and string min_version across the DB</name>
  <files>tools/sync_max_bundle.py, tests/test_db_tooling.py, tests/test_domain_scope.py, tests/test_version_tags.py, tests/test_objectfile_aliases.py, tests/fixtures/help_io_baseline.json, .claude/scripts/extract_objects.py, .claude/scripts/extract_abstractions.py, .claude/max-objects/aliases.json, .claude/max-objects/overrides.json, .claude/max-objects/{gen,jitter,m4l,max,mc,msp,rnbo}/objects.json, .claude/max-objects/packages/*/objects.json (the 28 listed in files_modified)</files>
  <precondition>Task 1 is committed. The dry-run summary prints `objectfile      : 719 lines, 716 names, 311 unresolved` and `30 RNBO/Gen-shadowed`. `.claude/max-objects/aliases.json` holds exactly 12 aliases. If any figure differs, stop and report the live figures instead of guessing a new name set.</precondition>
  <read_first>
    - tools/sync_max_bundle.py lines 1188-1330 (objectfile candidate, evidence, section), 2116-2160 (write_aliases_file), 2578-2646 (apply_aliases), 2913-3010 (parser and main)
    - tests/test_db_tooling.py lines 40-125, 319-512, 545-580
    - tests/test_domain_scope.py lines 38-50 and 161-230
    - tests/test_version_tags.py (whole file)
    - .claude/max-objects/overrides.json: the `list.change` entry (~line 16642) and the `list.group` entry (it also carries inlets/outlets/_audit)
    - .claude/scripts/extract_objects.py lines 540-555, 700-712, 885-892; .claude/scripts/extract_abstractions.py lines 285-293, 536-544
  </read_first>
  <behavior>
    New tests in tests/test_db_tooling.py, class TestI6ApplyAliases (hermetic, `_objectfile_world`):
    - `--apply aliases --shadowed --names list.len` writes `list.len -> zl.len`, and lookup then returns zl.len.
    - Without `--shadowed`, list.len is still `skipped`. The existing test stays unchanged and green.
    - With `--shadowed`, a name that resolves to a non-RNBO/Gen entry (`old`) is still `skipped`.
    - An overrides.json `objects` key equal to the alias name (add `hslider` to the fake overrides) aborts that name with a reason that names overrides.json, and aliases.json stays byte-identical.
    - `--shadowed` without `--apply aliases` exits 2.

    tests/test_objectfile_aliases.py (real DB, read-only):
    - `test_q38_aliases_resolve`: aliases.json has exactly 244 aliases. The 12 hand aliases are unchanged. The 13 mc names below and hslider -> slider map as listed. The 31 list.* names map to `zl.` + suffix. Every alias resolves via `ObjectDatabase().lookup(alias)["name"] == target`. No alias key is an overrides.json `objects` key.
    - `@pytest.mark.requires_max` `test_q38_alias_groups_match_the_bundle`: from `sync.build_bundle_index(MAX_APP_PATH)["objectfiles"]["records"]`:
      - the records whose file is `jit.op` and whose name is not a raw DB key map to `jit.op` in aliases.json, 97 of them;
      - the records with package `Vizzie` whose `.maxpat` stem is a DB name map to that stem, 90 of them.
    - list.* checks: for the 30 shadowed names, `RNBODatabase().is_rnbo_compatible(name)` and `RNBODatabase().lookup(name)["domain"] == "RNBO"` still hold. `ObjectDatabase().get_effective_restrictions(name) == []`. overrides.json has no key for them, and `list.ease` is still there.

    tests/test_version_tags.py: a new `test_every_min_version_is_a_version_string` walks the same real files as `real_db_files()` minus top-level files, plus overrides.json `objects`. Every min_version present is a str matching `^\d+(\.\d+){0,2}$`. Update the module docstring's PD-3 sentence: Q38 migrated the DB to strings.
  </behavior>
  <action>
**Part A. Tool change, tests first.** In tools/sync_max_bundle.py:
- Add a `--shadowed` flag. It is valid only with `--apply aliases`; otherwise exit 2 with an error. Its help text says it lets an alias replace an RNBO/Gen-only resolution, for names `max objectfile` maps to a Max object.
- Thread it into `apply_aliases(index, db_root, names, shadowed=False)`:
  - A hit whose domain is in `_RNBO_GEN_DOMAINS` proceeds as if unresolved only when `shadowed` is true. It is aborted when the candidate's own domain is also RNBO/Gen. Every other hit is skipped as today.
  - New, unconditional: a name that is a key of overrides.json `objects` aborts with reason `overrides.json has an entry keyed {name}; an alias would retarget it onto {candidate} -- remove or move it first`. Override keys canonicalize through aliases, so the entry would silently move onto the candidate.
  - Update the docstring and the db-maintenance wording source (Task 3 documents it).
- Write the new TestI6ApplyAliases cases, red then green.
- Commit with `git add -- tools/sync_max_bundle.py tests/test_db_tooling.py`. Message: `feat(sync): --apply aliases --shadowed for RNBO-shadowed objectfile names; aliases never retarget an override (quick 261022-mis, Q38)`.

**Part B. overrides.json, one style-preserving pass** (a QDIR script, uncommitted, using json.loads, `json_style`, `atomic_write_bytes`; abort if json_style is None):
- Delete exactly the 30 `objects` keys `list.X` for the X list in Task 1 Step 0. Each must exist; abort otherwise. Leave `list.ease` alone.
  - `list.group` also carries inlets/outlets/_audit. Those correct the RNBO-domain entry that ObjectDatabase stops reaching once the alias lands. RNBODatabase never reads overrides, so the whole entry goes.
- Set `objects["cycle~"]["min_version"]` to the string `str(old value)`.
- Verify with a QDIR check script: load old (`git show HEAD:...`) and new, delete the 30 keys from old, and stringify cycle~'s min_version. The two must be equal.

**Part C. min_version migration** (QDIR script, uncommitted). Targets: every `.claude/max-objects/<d>/objects.json` for d in gen jitter m4l max mc msp rnbo, and every `.claude/max-objects/packages/*/objects.json`. Never `_pkg-source/` or `audit/`.
- For each entry dict with a non-str `min_version`, set it to `str(v)`. This gives "8", "8.1", "9", "9.2", "4". Reject bool or other types by aborting.
- Reproduce each file's style with `json_style` and abort on None. Write all files in one `atomic_write_many`.
- Verify:
  - per file, old with min_version stringified == new;
  - `python3 tools/sync_max_bundle.py --compare-io QDIR/io-before.json` exits 0;
  - planning-time count: 3,445 values in 35 files.
- In .claude/scripts/extract_objects.py (3 sites) and .claude/scripts/extract_abstractions.py (2 sites), `"min_version": 8` becomes `"min_version": "8"`.

**Part D. Apply the 232 aliases.**
- Write the dry-run report to QDIR/sync-pre-alias.json (`python3 tools/sync_max_bundle.py --json QDIR/sync-pre-alias.json`). A QDIR script builds QDIR/alias-names.txt, one name per line, from its `objectfile_aliases` section with these rules (the observed counts must match exactly, else stop):
  - (a) `entries` with basis `mc_wrapper`, a name starting `mc.` and a non-null candidate: 13 names, and exactly mc.audiounit~ -> mc.vst~, mc.equals~ -> mc.==~, mc.greaterthaneq~ -> mc.>=~, mc.greaterthan~ -> mc.>~, mc.lessthaneq~ -> mc.<=~, mc.lessthan~ -> mc.<~, mc.minus~ -> mc.-~, mc.modulo~ -> mc.%~, mc.notequals~ -> mc.!=~, mc.plusequals~ -> mc.+=~, mc.plus~ -> mc.+~, mc.rminus~ -> mc.!-~, mc.times~ -> mc.*~;
  - (b) `hslider` (candidate slider);
  - (c) all 30 `domain_shadowed` names plus `list.iter`: 31, every candidate `zl.` + suffix;
  - (d) `entries` with file `jit.op` and candidate `jit.op`: 97;
  - (e) `entries` with package `Vizzie` and a non-null candidate: 90 (smoothr and world have none).
  - Total 232.
  - Use mc_wrapper lines only for mc.*: they instantiate the same class as the target. The 11 file-basis mc.* names (mc.meter~, mc.plugout~, ...) are implemented by a mono external reading its own name, with no help evidence for their I/O, so they stay unaliased. Record that as an executor-noted design choice.
- Apply without a shell word-split, via `python3 -c` calling `tools.sync_max_bundle.main([...])` with `--apply aliases --shadowed --json QDIR/aliases-applied.json --names` followed by the names read from QDIR/alias-names.txt.
  - Expect rc 0 and 232 `written`.
  - Any abort: stop, report the reason, and restore aliases.json with `git checkout -- .claude/max-objects/aliases.json`.
- Then:
  - snapshot `--snapshot-io QDIR/io-after-aliases.json`;
  - the compare-io of the live DB against QDIR/io-before.json may change only the 30 list.* names (the verify asserts this);
  - the dry-run now shows 0 RNBO/Gen-shadowed and 109 unresolved.

**Part E. Tests that encoded the pre-Q38 state** (edit in place, keeping test ids):
- tests/test_domain_scope.py: delete LIST_EXEMPT and set `EXEMPT = sorted(["rnbo~", "rnbo.remote", "div~", "rdiv~", "rdiv"])`, with a one-line comment that list.* now alias zl.* (tests/test_objectfile_aliases.py). This removes exactly the 30 `test_exempt[list.*]` ids allowed by junit_diff.py.
- tests/test_db_tooling.py TestI6ObjectfileRealBundle:
  - `test_q38_candidates` now asserts that those four names are absent from `entries` and that aliases.json maps them to their candidates;
  - `test_non_objectmappings_init_files_and_shadowed_names` keeps the mc.abl.dsp.chorus~ check and asserts `section["domain_shadowed"] == []` and `section["unresolved_count"] == len(section["names_unresolved"]) >= 100`.
- Write tests/test_objectfile_aliases.py and the test_version_tags.py addition (`<behavior>`).

**Part F. Help-io oracle.**
- Run `python3 -m pytest -q -p no:cacheprovider tests/test_help_io.py`. Its live class must pass with no regression.
- Planning-time simulation: 0 regressions and 19 improvements, all bundle list.* count mismatches. Regenerate with `python3 tools/audit_db.py --help-io --write-baseline tests/fixtures/help_io_baseline.json`.
- Check with a QDIR script that `diff_baselines(old committed, new)` has 0 regressions and that the new file only lowers or drops per-name counts.
- Report the improvement rows in SUMMARY.

**Part G. Commit the data.** Run the verify. Then `git add --` the remaining Task 2 paths from files_modified, explicitly, quoting the package paths with spaces. Message: `feat(db): 232 objectfile aliases (mc.*~ shortcuts, hslider, list.* -> zl.*, jit.op shortcuts, Vizzie short names); min_version stored as a string everywhere (quick 261022-mis, Q38)`.

List the 109 still-unresolved objectfile names in SUMMARY as not aliased (outside the five spec categories, no candidate, or help disagrees: mc.input, xbendin2, xbendout2, jit.mo.*, jit.time.line). Leave them to a follow-up; do not alias them.
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_objectfile_aliases.py tests/test_db_tooling.py tests/test_domain_scope.py tests/test_version_tags.py tests/test_help_io.py tests/test_sync_max_bundle.py tests/test_rnbo.py tests/test_rnbo_validation.py tests/test_override_merge.py tests/test_db_lookup.py tests/test_idioms.py tests/test_extraction.py && python3 tools/sync_max_bundle.py --compare-io .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/io-after-aliases.json > /dev/null && python3 -W ignore -c "import json, sys; from pathlib import Path; from tools import sync_max_bundle as s; names = {'list.' + x for x in 'change compare delace ecils filter group indexmap join lace len lookup median mth nth queue reg rev rot scramble sect slice sort stack stream sub sum swap thin union unique'.split()}; assert len(names) == 30; changed = {c['name'] for c in s.compare_io(Path('.claude/max-objects'), json.load(open(sys.argv[1])))}; print('io changed vs Step 0:', sorted(changed)); sys.exit(0 if changed <= names else 1)" .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/io-before.json && python3 tools/sync_max_bundle.py | grep -Eq '^  objectfile +: 719 lines, 716 names, 109 unresolved .* 0 RNBO/Gen-shadowed' && test -z "$(git status --porcelain .claude/max-objects .claude/scripts tests tools src)"</automated>
  </verify>
  <done>244 aliases resolve, and the 30 list.* overrides are gone while the names stay RNBO-compatible. Every DB min_version is a string, and the I/O differs from Step 0 only for the 30 list.* names. The help-io baseline is regenerated with improvements only. Both Task 2 commits are in, and no tracked file in the DB, scripts, tests, tools or src is left dirty.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: version-aware I/O (version_io.json + validate_patch target_version), docs for all three parts, and the full regression gate</name>
  <files>tools/help_io.py, tools/sync_max_bundle.py, .claude/max-objects/version_io.json, src/maxpat/db_lookup.py, src/maxpat/validation.py, tests/test_version_io.py, CLAUDE.md, .claude/skills/references/db-maintenance.md, .claude/skills/references/severity-contract.md, TECHNICAL.md</files>
  <precondition>Tasks 1 and 2 are committed. Every DB min_version is a string (tests/test_version_tags.py passes).</precondition>
  <read_first>
    - tools/help_io.py `scan_help_idioms` (Task 1) and `_appversion`
    - tools/sync_max_bundle.py idioms section/writer (Task 1) and run_report
    - src/maxpat/validation.py lines 160-330 and 373-402
    - CLAUDE.md lines 19-27, 59, 225-231 (Supplementary Files, Rule #1 RNBO sentence, Version Compatibility); tests/test_claude_md.py CLAUDE_BUDGET_BYTES (30,000; CLAUDE.md is 27,406 bytes at planning time)
    - .claude/skills/references/db-maintenance.md (whole), .claude/skills/references/severity-contract.md sections 1-3, TECHNICAL.md lines 110-140
  </read_first>
  <behavior>
    tests/test_version_io.py:
    - `parse_version`: "9" -> (9, 0, 0), "9.0" -> (9, 0, 0), "9.0.3" -> (9, 0, 3), "8.1" -> (8, 1, 0). "nine", "9.x", "", "9.0.0.1" and non-str inputs raise ValueError.
    - Mining on a fake bundle (help files with `patcher.appversion` set):
      - `foo` saved (1,1) by 8.6.5 and (1,2) by 9.0.0 -> objects.foo.changes == [{after "8.6.5", by "9.0.0", inlets 0, outlets 1}] plus evidence segments;
      - interleaved versions (8.6.5 -> (1,1), 9.0.0 -> (1,2), 9.1.0 -> (1,1)) -> no change, counted as an ambiguous group;
      - two arg groups of one name with different deltas -> the name is listed in `conflicting` and not in objects;
      - a name seen at only one I/O -> nothing.
    - Writer: `write_version_io_file` refuses any path but `<db_root>/version_io.json`, writes canonical bytes, and is idempotent. The dry-run section reports added/removed/changed against the committed file.
    - DB:
      - `ObjectDatabase.io_changes(name)` is alias-canonical, returns copies, and gives [] for unknown names or when the file is absent;
      - `version_io_max_version` is the file's max_version or None;
      - `min_version(name)` returns the string, or None for an unknown name.
    - `test_target_version_warns_on_missing_port` (real DB): a max patch with a `mousestate` box at current I/O (1,10) and a cord from outlet 7. At target "9.0" there is one layer `version` warning naming the box id, `mousestate`, outlet 7, `9.0` and `version_io`. At target "9.0.3" it still warns (the change is between 9.0.0 and 9.0.5). At target "9.1" and with no target there is no version finding.
    - `jit.message` (min_version "9.2") at target "9.0" -> one `version` warning naming `9.2`. At "9.2", none.
    - The same mousestate case inside a `p` subpatcher -> the warning carries the nested path. Inside an rnbo~ or gen~ patcher, no version findings.
    - A metro box at the DB's (2,1) with target "9.0" -> no warning. The metro change is by 9.3.0, newer than the installed 9.2.0, so it is not part of the DB's layout.
    - `target_version="nine"` raises ValueError before validating.
    - With target_version=None, results equal those of a call without the keyword, for three committed patches (any three `patches/*/generated/*.maxpat`, read-only).
    - `@pytest.mark.requires_max` `test_committed_version_io_is_current`: the live `version_io` section has added == removed == changed == 0.
    - `@pytest.mark.requires_max` `test_vst_and_retune_have_one_io_in_the_bundle`: neither name is in version_io.json objects, the scan's `conflicting`, or its `ambiguous_names`.
  </behavior>
  <action>
**Part A. Tests first.** Write tests/test_version_io.py per `<behavior>` and record the red count.

**Part B. src/maxpat/db_lookup.py.**
- `parse_version(text) -> tuple[int, int, int]`: str only, regex `^\d+(\.\d+){0,2}$`, zero-padded to 3 parts, ValueError otherwise.
- `VERSION_IO_FILE = "version_io.json"`, loaded in `_load` after idioms.json:
  - objects keys canonicalized through aliases;
  - each change needs str `after`/`by` parsable by parse_version, with `after < by`, and int `inlets`/`outlets` deltas;
  - a malformed file raises ValueError naming it.
- `io_changes(name) -> list[dict]` (deep copies, sorted by `by`), the `version_io_max_version` property, and `min_version(name) -> str | None` (alias-canonical; `str(v)` for a stray number).

**Part C. tools/help_io.py `scan_version_io(max_app, db) -> dict`.** Bundle only, the same walk as scan_help_idioms. For every box where `idiom_endpoint(box)` is a name, `db.lookup(name)` resolves (warnings muted), numinlets and numoutlets are ints, and the box has no `patcher`:
- record `(numinlets, numoutlets)` under key `(name, tuple(walk.box_args(box)))` with the file's `_appversion` parsed by parse_version. Skip "unknown".
- A key with 2 or more distinct I/O values becomes segments: per I/O value, `first`/`last` version strings and a `boxes` count, sorted by first.
  - The key is monotone iff every `segment.last < next.first`. Otherwise count it as an ambiguous group and add its name to `ambiguous_names`.
- Per name, over its monotone keys: a key's transitions are `(after = seg_i.last, by = seg_{i+1}.first, inlets = delta, outlets = delta)`.
  - When every monotone key has the same delta sequence, the name gets `changes`: per transition, after = max of the keys' afters and by = min of their bys, and it requires after < by. Otherwise the name goes in `conflicting`.
  - Each change carries `newer_than_installed` (by > the installed version passed in).
- Return:
  - `objects` (name -> `{changes, evidence: [{args, segments, example}]}`, where example is the first help file's relative path);
  - `conflicting` and `ambiguous_names` (sorted);
  - `ambiguous_groups`, `files` and `bad_files`.
- Planning-time result with this rule: 8 names (live.meter~, metro, midiformat, midiparse, mousestate, poke~, preset, twist~), 7 ambiguous groups. metro and twist~ changes are `by 9.3.0` (help saved by a 9.3 build), so they are newer than the installed version. Report the actual list in SUMMARY even if it differs, and do not edit any entry by hand.

**Part D. tools/sync_max_bundle.py.**
- Add "version-io" to APPLY_MODES and "version_io" in SECTION_KEYS directly after "idioms".
- Add `VERSION_IO_FILE`, `canonical_version_io_bytes`, `write_version_io_file` (single-path guard as Task 1), `build_version_io_target(scan, install)` (keys `_comment`, `generator`, `max_version`, `source`, `objects`) and `section_version_io(index, db_root)` (scan stats plus `names`, `added`, `removed`, `changed` vs the committed file).
- `apply_version_io` regenerates the file wholesale. It is mined evidence, not curation; the dry-run's +/-/~ counts are the review step. Document that in its docstring and in db-maintenance.md (Part F).
- Summary line shape: `  version io      : {names} names with per-version I/O changes ({ambiguous_groups} ambiguous arg groups, {conflicting} conflicting); +{added} -{removed} ~{changed} vs version_io.json (--apply version-io)`.
- Run `python3 tools/sync_max_bundle.py --apply version-io`, then the dry-run again: it must show `+0 -0 ~0`.

**Part E. src/maxpat/validation.py.**
- `validate_patch(..., *, scope=None, target_version: str | None = None)`. Parse the target first (ValueError propagates). Thread `target` through `_validate_scope_layers` and `_validate_nested_scopes`. Run the new `_validate_target_version(patch_dict, db, target, target_text)` only when the target is set and the scope's own scope is "max". gen and rnbo scopes share names with Max objects whose versions and I/O differ.
- For each box with `walk.object_name`:
  - (1) min_version: when `db.min_version(name)` parses greater than target, emit a warning with layer "version". The message contains the box id, the name, `needs Max {mv}`, `target {target_text}` and `No such object`.
  - (2) ports: pending = changes with `target < parse_version(by) <= installed`, where installed is `db.version_io_max_version` (skip this check when it is None).
    - Run this only when pending is non-empty and `(numinlets, numoutlets) == db.compute_io_counts(name, walk.box_args(box))`, that is, when the box carries the installed layout.
    - Ports at target: `inlets_t = numinlets - sum(c["inlets"])` and `outlets_t = numoutlets - sum(c["outlets"])`.
    - Every cord in the scope with this box as source and `outlet >= outlets_t`, or as destination and `inlet >= inlets_t`, gets one warning (layer "version"). The message contains the box id, the name, the port (`outlet K` / `inlet K`), `Max {target_text}`, the change interval `{after} -> {by}`, `version_io` and `lost`.
- Never emit an error. has_blocking_errors and the save gate are unchanged. Update the validate_patch docstring.

**Part F. Docs (each call form must bind under tests/test_doc_signatures.py).**
- CLAUDE.md (stay under 30,000 bytes):
  - Supplementary Files: append to the `aliases.json` bullet that it also holds the bundle's `max objectfile` shortcuts (`mc.times~`, `hslider`, `list.*` -> `zl.*`, `jit.+`, Vizzie short names). Add an `idioms.json` bullet (cords MAX ships, Layer 3 never type/role-checks them, bounds always; written only by `--apply idioms`) and a `version_io.json` bullet (per-version I/O mined from help boxes; written only by `--apply version-io`).
  - Rule #1: change the parenthesis about RNBO-domain entries marked `[]` to name `rnbo~` and `rnbo.remote`, and say the `list.*` names are aliases of their `zl.*` objects.
  - Version Compatibility: add one bullet: `validate_patch(patch, target_version="9.0")` warns (layer `version`) when a box needs a newer Max or uses a port an older build lacks; use it for collaborators on older 9.x builds.
- db-maintenance.md:
  - a short "Shipped idioms" section (what is mined, the key, bundle only, additive, bounds not exempt, Layer 4 untouched);
  - a "Per-version I/O" section (the monotone-partition rule, wholesale regeneration, vst~/retune~ show one I/O in the bundle so they are not recorded, metro/twist~ come from 9.3-saved help);
  - the "After a Max update" sequence gains `--apply aliases --names ... [--shadowed]` (and the overrides guard), `--apply idioms`, `--apply version-io`, and `python3 tools/audit_db.py --help-io --write-baseline tests/fixtures/help_io_baseline.json`;
  - state that min_version is always a string.
- severity-contract.md §1/§2: Layer 3 skips type/role checks for listed cords (never bounds), and the opt-in `version` layer emits warnings only.
- TECHNICAL.md: the min_version example becomes `"min_version": "8",` and its description says it is a version string.

**Part G. Gate and commit.**
- Run the ast 3.10 gate on the edited .py files.
- Commit with `git add -- tools/help_io.py tools/sync_max_bundle.py .claude/max-objects/version_io.json src/maxpat/db_lookup.py src/maxpat/validation.py tests/test_version_io.py`. Message: `feat(validation): version_io.json mined from help boxes; validate_patch(target_version=...) warns collaborators on older builds (quick 261022-mis, Q38)`.
- Commit the four docs: `docs: Q38 idioms, objectfile aliases, string min_version, version_io and target_version (quick 261022-mis)`.
- Run the verify verbatim. It runs the targeted tests, then the full suite (about 3 minutes), writing QDIR/final-junit.xml, final-pytest.txt and final-rc.txt fresh inside the same command.
- SUMMARY reports:
  - the baseline and final counts, the junit_diff output, and the red counts per task;
  - the alias groups and the 109 unaliased names;
  - the version_io names;
  - the vst~/retune~ finding, as a decision for the user: the review's "vst~ 4→8, retune~ 3→5" were DB-vs-help gaps that Q11 already corrected, and no shipped help box disagrees across versions;
  - the executor-noted design choices (bounds and Layer 4 not exempt; file-basis mc.* not aliased; version_io regenerated wholesale; version layer max-scope only and warning-only).
  </action>
  <verify>
    <automated>python3 -m pytest -q -p no:cacheprovider tests/test_version_io.py tests/test_idioms.py tests/test_objectfile_aliases.py tests/test_sync_max_bundle.py tests/test_claude_md.py tests/test_doc_signatures.py tests/test_agent_skills.py && python3 tools/sync_max_bundle.py | grep -Eq '^  version io +: [0-9]+ names .*\+0 -0 ~0 vs version_io.json' && python3 tools/sync_max_bundle.py --compare-io .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/io-after-aliases.json > /dev/null && test -f .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/stash-list-before.txt && test -f .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/patches-status-before.txt && test -s .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/base-sha.txt && test -s .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/baseline-junit.xml && { python3 -m pytest -q -p no:cacheprovider --junitxml=.planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/final-junit.xml > .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/final-pytest.txt 2>&1; echo $? > .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/final-rc.txt; } && python3 -c "import sys, xml.etree.ElementTree as E; base = int(any(x.tag in ('failure', 'error') for c in E.parse(sys.argv[1]).getroot().iter('testcase') for x in c)); fin = int(open(sys.argv[2]).read().strip()); print('baseline_rc', base, 'final_rc', fin); sys.exit(0 if base >= fin else 1)" .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/baseline-junit.xml .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/final-rc.txt && python3 .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/junit_diff.py .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/baseline-junit.xml .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/final-junit.xml && test "$(git status --porcelain patches patterns)" = "$(cat .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/patches-status-before.txt)" && test "$(git stash list)" = "$(cat .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/stash-list-before.txt)" && git merge-base --is-ancestor "$(cat .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/base-sha.txt)" HEAD && test -z "$(git log --name-only --format= "$(cat .planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/base-sha.txt)"..HEAD -- patches patterns)" && test -z "$(git status --porcelain .claude/max-objects .claude/scripts .claude/skills tests tools src CLAUDE.md TECHNICAL.md)"</automated>
  </verify>
  <done>version_io.json is committed and current (dry-run `+0 -0 ~0`). target_version warns as specified and the default path is unchanged. The docs describe all three parts. The full suite is no worse than baseline and junit_diff passes. patches/, patterns/ and the stash list are untouched. SUMMARY carries the decisions to confirm.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| installed Max bundle -> mining tools | `*.maxhelp` and init files are third-party data, parsed with `json.loads` / regex only, never executed |
| mining tools -> DB tree | new writers (idioms.json, version_io.json) and the aliases/overrides/min_version edits change data every later validation trusts |
| DB -> validation verdicts | the allowlist and aliases decide whether a cord or name is flagged; a too-broad entry hides a real error |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-mis-01 | Tampering | write_idioms_file / write_version_io_file | medium | mitigate | each writer refuses any path but its own file under the DB root (WriteRefused, mirroring write_groups_file); atomic replace keeps the mode; canonical bytes; idempotent; tested in tests/test_idioms.py and tests/test_version_io.py |
| T-mis-02 | Denial of service | scan_help_idioms / scan_version_io | low | mitigate | json.loads only, MAX_PATCHER_DEPTH cap, gen/rnbo internals skipped, bad files recorded instead of raised; tested with deep and unparsable fixtures |
| T-mis-03 | Tampering | Layer 3 idiom exemption | high | mitigate | bounds/missing/malformed never exempt; key includes the source outlet's signal class from the validated box's own outlettype (an arg-dependent layout such as `sfplay~` vs `sfplay~ 2` does not match); content-defined, inlet/outlet, codebox and embedded-patcher endpoints excluded; bundle-only source (no user packages); Layer 4 untouched; hermetic tests for each guard |
| T-mis-04 | Tampering | apply_aliases | high | mitigate | an alias never lands for a name keyed in overrides.json `objects` (would silently retarget the override); RNBO/Gen-shadowed names need explicit `--shadowed`; every alias verified to resolve after the write, with restore on failure (existing); RNBODatabase reads rnbo/objects.json raw, and a test asserts list.* stay rnbo-compatible |
| T-mis-05 | Tampering | min_version migration and overrides edit | high | mitigate | json_style reproduction or abort, one atomic_write_many, per-file semantic equality modulo the intended change, I/O snapshot compare against Step 0, explicit-path commits |
| T-mis-06 | Repudiation | version layer warnings | low | accept | opt-in (target_version None by default), warnings only, never part of the save gate |
| T-mis-SC | Tampering | npm/pip/cargo installs | high | accept | no package is installed by this plan (stdlib + existing src.maxpat only); the package-legitimacy gate has nothing to check |
</threat_model>

<verification>
- Task 1 verify: the idiom suite is green, idioms.json is current (`+0 pending`), I/O is unchanged, and the baseline is valid and predates the new tests.
- Task 2 verify: the alias/override/min_version suites and the help-io oracle are green; I/O changed only for the 30 list.* names; the objectfile line reads `109 unresolved ... 0 RNBO/Gen-shadowed`.
- Task 3 verify: version-io and target_version tests are green, version_io.json is current, the doc and doc-signature tests pass, the full suite is no worse than baseline, junit_diff passes, and patches/, patterns/ and the stash list are unchanged.
- Source audit (all COVERED):

| SOURCE | ID | Item | Plan | Status | Notes |
|---|---|---|---|---|---|
| GOAL | Q38 | Bundle mining: idiom allowlist, objectfile aliases, version-aware I/O | Tasks 1-3 | COVERED | |
| REQ | Q38-1 | Mine every shipped (src,outlet)->(dst,inlet) pair; validation never flags or strips one | Task 1 | COVERED | Bounds kept (a cord past a box's own port count cannot load); Layer 4 value rules out of pair scope; both choices noted in SUMMARY |
| REQ | Q38-2 | objectfile aliases from the Q30 report: mc.*~ shortcuts, hslider, list.* -> zl.*, jit.op shortcuts, Vizzie short names | Task 2 | COVERED | 13 + 1 + 31 + 97 + 90 = 232 explicit names; the other 109 are listed, not applied |
| REQ | Q38-3 | min_version stored as a string | Task 2 | COVERED | Q30 PD-3 / follow-up "DB-wide min_version migration" |
| REQ | Q38-4 | Per-version I/O deltas where help boxes from different versions disagree (vst~ 4→8, retune~ 3→5) | Task 3 | COVERED | Mechanism plus 8 evidenced names. The two named examples have no disagreeing shipped help box: reported as a decision, not fabricated (Rule #1) |
| REQ | Q38-5 | `validate_patch(target_version="9.0")` warns collaborators on older 9.x | Task 3 | COVERED | min_version and port checks, warning-only |
| CONTEXT | Q30 follow-up | overrides.json list.* entries: "Q38 aliases list.* to zl.*: delete this entry then" | Task 2 | COVERED | 30 entries deleted, list.ease kept |
| CONTEXT | Q9 hand-off | help appversions give per-version deltas | Task 3 | COVERED | Mined directly from bundle help boxes |
| RESEARCH | review §5.5 | I/O-drift `--apply io`, bundle UI-maxclass list | — | EXCLUDED | Not in the Q38 fix-plan text |
</verification>

<success_criteria>
- A cord MAX ships in its own help patches is never flagged or proposed for removal by type/role checks, and is never orphaned by replace_box_safe. A truly out-of-range cord is still caught.
- 232 bundle shortcut names resolve in the DB. list.* resolve to zl.* in Max scope and stay RNBO-compatible. No override was silently retargeted.
- Every min_version is a string. `validate_patch(..., target_version="9.0")` tells the user which boxes and cords break for collaborators on older builds, and the default call is unchanged.
- The full suite is no worse than baseline, and SUMMARY lists every test-id change (only the 30 allowed removals plus new Q38 tests).
</success_criteria>

<output>
Create `.planning/quick/261022-mis-implement-q38-in-planning-reviews-2026-1/261022-mis-SUMMARY.md` when done.
</output>
