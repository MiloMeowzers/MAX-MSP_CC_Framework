---
scope: tools/ (sync_max_bundle, help_io, audit_db, max_bridge, max_verify_live, extract_pkg_io) + release readiness
range: 0f96a6f1..8ddcdc49 (HEAD == origin/main)
reviewed: 2026-10-22
findings:
  blocker: 1
  warning: 6
  info: 7
---

# Q1–Q40 regression review: tools and release readiness

## How this was checked (evidence base)

- **Python 3.10.** Every tracked `.py` file parses under a real CPython 3.10.19 (uv). `uvx vermin -t=3.10-` over all 194 tracked files found **one** violation (BL-01). The full suite was run in a fresh `git clone --depth 1` of HEAD (tracked files only, like CI) on a Python 3.10 venv built from `requirements-dev.txt`: **6287 passed, 5 xfailed, 1 xpassed**. Max was installed, so the `requires_max` tests ran too.
- **CI.** GitHub Actions run 39901917571 (HEAD 8ddcdc49), ubuntu: 3.10 and 3.12 both show `6248 passed, 39 skipped, 5 xfailed, 1 xpassed`. The 39 skips are the `requires_max` tests, which skip because `/Applications/Max.app` is absent. No test depends on untracked files: the clean clone passes.
- **Release archive.** `scripts/build_release.sh /private/tmp/claude-501/rel/framework.tar.gz` built 190 files. That list equals `git ls-files` minus the export-ignored trees (and `.gitattributes`). It ships: every `src/maxpat` module, all 8 `.claude/skills/references/*.md`, `groups.json`, `idioms.json`, `version_io.json`, `audit/width-overrides.json`, `.claude/scripts/`, `tools/`, and `max-diagnose.md`. It leaves out `.planning`, `tests`, `patches`, `scripts`, `installer`, `.claude/projects`, the other audit reports, and any nested tarball.
- **Compared with v5.0.0.** I downloaded the v5.0.0 asset and diffed the two lists. Files removed since then: `memory.py`, `verified-objects.json`, `bore_only.py`. Files that only v5.0.0 had: a nested `framework.tar.gz`, `.release-ignore`, and a maintainer memory note. Leaving those three out now is correct.
- **Extracted archive.** In a bare Python 3.10 venv (no numpy), every `src.maxpat` module imports except `dsp_sim`. `validate_patch` works. The tools ran from the extracted layout: `audit_db` and `max_verify_live` behave, but the bridge cannot run (WR-01).
- **Sync tools.** `sync_max_bundle.py` (dry-run) and `audit_db.py` (default and `--help-io`) run cleanly on 3.10 against Max 9.2.0. After both runs, `git status .claude` showed no change.

---

## BLOCKER

### BL-01: `math.exp2` is Python 3.11+. Any GenExpr `exp2()` breaks the smoke interpreter on the 3.10 target

**File:** `src/maxpat/dsp_sim/genexpr_interp.py:1119` (Q35)

**Defect:** `_exp2` calls `math.exp2(x)`, which was added in Python 3.11. On 3.10 it raises `AttributeError`. The interpreter catches the error per corner, so every codebox that uses `exp2` gets UNSUPPORTED instead of a verdict.

**Repro:**
```
$ venv310/bin/python -c 'from src.maxpat.dsp_sim.smoke import smoke_codebox; print(smoke_codebox("out1 = exp2(in1) * 0.1;").findings[0])'
Finding(check='unsupported', ..., detail="interpreter error: AttributeError: module 'math' has no attribute 'exp2'")
# same call on 3.14 -> verdict pass
```

**Why CI is green:** no test feeds `exp2` to the interpreter. This is the only 3.11+ API in the repo (vermin).

**Fix:**
```python
def _exp2(x):
    try:
        return 2.0 ** x          # or math.pow(2.0, x)
    except OverflowError:
        return _INF
```
Then add a smoke/interp test for `exp2` so the 3.10 CI leg covers it. Optionally add `uvx vermin -t=3.10- --violations` as a CI step.

---

## WARNING

### WR-01: `/max-verify --live` and `tools/max_bridge.py` ship, but the bridge patch does not. The feature cannot run in any npm or curl install

**Files:** `.gitattributes:15` (`/patches export-ignore`), `tools/max_bridge.py:110` (`BRIDGE_PATCH = REPO_ROOT/"patches"/"max-bridge"/...`), `tools/max_verify_live.py:315-316`, `.claude/commands/max-verify.md:31-44`, `README.md:168`

**Defect:** The archive excludes the whole `patches/` tree, so `patches/max-bridge/generated/max-bridge.maxpat` is not in the release. The `/max-verify --live` command doc ships anyway and tells the user to open that file.

**Repro (extracted release, project `demo`):**
```
$ python3 tools/max_verify_live.py --project demo
Live check skipped: bridge patch not available in this install (patches/ is not shipped in releases)   exit=2
$ python3 tools/max_bridge.py ping
... open patches/max-bridge/generated/max-bridge.maxpat in MAX ...   # the file does not exist
```
The README also lists `max-bridge` (and about 30 other projects) under "The `patches/` directory contains example and user-created projects". None of them ship.

**Fix (recommended):** move the bridge patch into a shipped location, e.g. `tools/max-bridge.maxpat`, and point `BRIDGE_PATCH` and the hints there. Doing that inside `patches/` would make it show up as a user project in `/max-switch`. Alternatively, mark `--live` as maintainer-only in `max-verify.md` and the README, and reword the README "Patches" section as "in the repository (not in releases)".

### WR-02: The DSP pre-flight gate hard-blocks saves in a release install. Bare `pytest` cannot import `src`

**File:** `.claude/skills/max-dsp-agent/SKILL.md:323-336` (invocation), `:348-352` (registration)

**Defect:** In a release `tests/` is not shipped, so the registration step creates `tests/dsp_sim/test_<name>.py` with no `__init__.py` and no conftest. The gate then runs `["pytest", fixture, "-q"]`. Pytest's rootdir insertion puts `tests/dsp_sim` on `sys.path`, not the repo root, so collection fails. The return code is non-zero, and the skill raises `PatchValidationError`, which blocks every save of that patch. If `pytest` is not on PATH (e.g. a `pip --user` install), `subprocess.run` raises `FileNotFoundError`, which the snippet does not handle. This predates the range: v5.0.0 had the same snippet. It is still unfixed in a release that advertises the gate (README prerequisites).

**Repro (extracted archive):**
```
$ pytest tests/dsp_sim/test_demo.py -q            # test imports src.maxpat.dsp_sim
E   ModuleNotFoundError: No module named 'src'     -> 1 error during collection
$ python -m pytest tests/dsp_sim/test_demo.py -q  -> 1 passed
```

**Fix:** use `[sys.executable, "-m", "pytest", str(fixture), "-q"]` (python -m puts cwd on `sys.path`) and run it with `cwd=REPO_ROOT`. Alternatively, ship a root `conftest.py` or set `pythonpath = .` in a shipped `pytest.ini`.

### WR-03: `audit_db.py` ("read-only") overwrites a DB object file when `--db-root` or `--repo-root` points elsewhere

**File:** `tools/audit_db.py:150-161` (`guard_output_path`), `:1173-1178`, `:1212-1213`

**Defect:** The guard only protects `<repo_root>/patches` and `<repo_root>/.claude/max-objects`. It never protects `--db-root`, which is the DB actually being audited, and with `--repo-root X` it no longer protects the real repo DB either. The write is a plain non-atomic `write_text`. `sync_max_bundle.guard_report_path` (line 2442) already adds the db-root check; `audit_db` does not.

**Repro (on a scratch DB copy):**
```
$ python3 tools/audit_db.py --db-root $S/max-objects --json $S/max-objects/msp/objects.json   # exit 0
md5 f02969d9... -> 4616bef2...   # msp/objects.json replaced by the audit report
$ python3 tools/sync_max_bundle.py --db-root $S/max-objects --json $S/max-objects/msp/x.json
error: refusing to write ...: inside the DB root            # the sync tool refuses
$ python3 -c "from tools.audit_db import guard_output_path; print(guard_output_path('.claude/max-objects/max/objects.json','/private/tmp'))"
/Users/taylorbrook/Dev/MAX/.claude/max-objects/max/objects.json   # accepted
```

**Fix:** give `guard_output_path` a `db_root` parameter (or reuse the sync tool's `guard_report_path`). Apply it to `--json` and `--write-baseline`. Also always protect the tool's own `ROOT` trees, not just `--repo-root`.

### WR-04: `max_bridge.py check` crashes with a traceback and exit 1 ("findings") on a malformed patch

**File:** `tools/max_bridge.py:1303` (`instrument(src, ...)`, outside any try), `:563-564`

**Defect:** `json.loads` / `Patcher.from_dict` errors are not caught. The documented contract is exit 2 for bad input or bridge failure and exit 1 for findings. An unreadable `.maxpat` therefore exits 1 with a Python traceback, so a script or `/max-verify` caller sees "findings". `max_verify_live` turns it into a generic "live check crashed" warning.

**Repro:**
```
$ echo '{"patcher": ' > $TMPDIR/bad.maxpat
$ python3 tools/max_bridge.py check $TMPDIR/bad.maxpat --dry-run   -> JSONDecodeError traceback, exit=1
```

**Fix:** wrap the read and instrument step:
```python
try:
    copy, inst = instrument(src, note=bool(note))
except (OSError, ValueError) as exc:          # JSONDecodeError is a ValueError
    report["error"] = f"cannot read {src}: {exc}"
    return report                             # verdict bridge_failed, exit_code 2, copy None
```

### WR-05: The NPM_TOKEN secret is almost certainly expired. `npm publish` will fail after the GH release is already public

**File:** `.github/workflows/release.yml:41-44`

**Evidence:** `gh secret list` shows `NPM_TOKEN 2026-03-19`. The last successful npm publish was 5.0.0 on 2026-05-01. Since npm's late-2025 token changes, write-capable granular tokens expire after at most 90 days, and classic tokens were revoked. A token created on 2026-03-19 is past any allowed lifetime. I could not read the expiry directly, so this is strongly evidenced, not proven.

**Failure:** the job order is test, then GH Release, then publish. If publish returns 401/403, the tag and GH release (and therefore `releases/latest`, which the installers download) are already live, but npm stays at 5.0.0. The impact is limited: the installer always downloads `latest`, so `npx create-max-framework` still installs the new framework, only with the old `--version` string. The workflow will still show as failed.

**Fix:** before tagging, check the token's expiry on npmjs.com, or rotate it. Better: switch to trusted publishing (OIDC). Add `permissions: id-token: write` to the release job, register the repo/workflow as a trusted publisher for `create-max-framework`, and run `npm publish --provenance` (Node 24 ships npm 11, which supports this). You could also move the publish step before the GH release step, so a failure does not leave half a release.

### WR-06: The validator accepts cords into `inlet` boxes and into `outlet` inlet 1. MAX has neither (DB I/O for `inlet`/`outlet` is wrong). help_io measured it and the baseline pinned it

**Files:** the DB `inlet` / `outlet` entries; `Patcher.add_box("inlet"/"outlet")` writes `numinlets` 1 / 2. This is surfaced by the tool under review, `tools/help_io.py`.

**Evidence (`audit_db.py --help-io`):** `inlet  count args=0 max=0,1 db=1,1` on 1845 bundle boxes; `outlet count args=0 max=1,0 db=2,0` on 1629 bundle boxes. Every Max version from 7.0.0 to 9.3.0 and every package agrees. `compute_io_counts('inlet') == (1, 1)` and `compute_io_counts('outlet') == (2, 0)`. A patch with `message -> inlet[0]` and `message -> outlet[1]` validates with no bounds error. Rule #2 says this must not happen, and MAX refuses those cords. These two names are the top two of the oracle's "top names" list, and `tests/fixtures/help_io_baseline.json` records them as accepted.

**Fix:** add per-port overrides `inlet: inlets []` and `outlet: inlets [1 port]` in `overrides.json`, check that `Patcher.add_box` / `add_subpatcher` pick them up, re-run `--write-baseline`, and check the save gate does not newly block existing patches that carry the stale counts. This is outside the tools area; route it to the DB reviewer.

---

## INFO

### IN-01: Docs still advertise the removed `bore_only` topology
`.claude/skills/max-dsp-agent/SKILL.md:348` and `TECHNICAL.md:612` both list `bore_only`. Q25 removed it, and `get_topology('bore_only')` now raises `TopologyError: unknown topology 'bore_only'`. An agent following the skill gets an error. Fix: drop it from both lists.

### IN-02: A non-strict xfail now passes and hides regressions
`tests/test_round_trip.py:1104` (`test_max_saved_file_byte_identical`, `strict=False`) XPASSes on CI and locally, because Q29 made the save byte-identical. While it stays marked xfail, a Q29 regression would be reported as XFAIL instead of failing. Fix: remove the xfail, or make it `strict=True`.

### IN-03: README and TECHNICAL counts are stale
README.md:212 and TECHNICAL.md:755 say "3,345 tests"; CI collects 6,287. "~22,200 LOC" (README.md:211, TECHNICAL.md:293) is low: `src/maxpat` is about 35.9k lines. The README milestone table ends at v5.0, with nothing for the Q1–Q40 release. The 3,445 object / 29 package counts are still correct.

### IN-04: The `max_bridge.py` status docstring is stale
`tools/max_bridge.py:4-8` says v0.3.0 is "pending", but v0.3.0 was confirmed in MAX 9.2 (commit "docs(max-bridge): v0.3.0 /max-verify --live confirmed").

### IN-05: `extract_pkg_io.py` bypasses `atomic_io` for `overrides.json`
`tools/extract_pkg_io.py:326-328` uses a fixed-name `.json.tmp` + `os.replace`, with no fsync and no mode preservation. The format is hard-coded (`indent=2`, ASCII, no trailing newline). That style matches the file today, but `sync_max_bundle` goes through `atomic_write_bytes` + `json_style`. The return annotation `tuple[int, int]` is also wrong: the function returns three values. Fix: use `atomic_write_bytes(OVERRIDES_PATH, ...)` with `json_style`.

### IN-06: Python deps are documented but not checked
README says numpy/scipy are required, but `install.sh` and `create-max-framework.js` only check the Python version, and `installer/README.md` does not mention `requirements-dev.txt` or git. Core validation works without numpy (verified in a bare 3.10 venv). Only `dsp_sim` (smoke test, pre-flight gate, `max_bridge analyze`) fails, with `ModuleNotFoundError`. Fix: print a hint after install (`pip install -r requirements-dev.txt`).

### IN-07: The `v*` tag filter accepts non-semver tags
The `v5.0` tag run (25236249889) failed in `npm version 5.0`. Only push `vMAJOR.MINOR.PATCH` tags. Optionally tighten the filter to `tags: ['v[0-9]+.[0-9]+.[0-9]+']`.

### Checked, no defect found
- **atomic_io:** `atomic_write_bytes` / `atomic_write_many` preserve mode, roll back, and clean up temp files.
- **sync_max_bundle write guards:** the allow-list, additive check, style reproduction and alias rollback hold. The report-path guard includes db-root.
- **Bridge kill switch:** `loadbang -> 0 -> toggle -> t i i`; the right outlet closes `gate 1 0` before `/listen 0`. Every UDP command, `/ping` included, passes the gate, so with the toggle OFF a run skips or aborts as documented.
- **Bridge client safety:** `/open` is refused unless the file is a `__maxbridge_*` copy, and the input guard limits inputs to the repo or temp dir and rejects copies. DSP is restored only if it was off before. The copy is deleted in `finally`. `max_verify_live` never toggles or opens the bridge.
- `test.yml` / `release.yml` gating is correct.
- Both installers handle the Q8 "no pointer" layout, and `get_active_project` returns None on a fresh install.
- The dev requirements' lower bounds resolve on 3.10.

---

## Release checklist

**Recommended version: `v6.0.0` (major).** The range breaks the public Python API and its behaviour:
- `validate_patch` no longer mutates. Invalid cords become `proposed_removal`, and only `apply_fixes()` removes them (Q1). Callers that relied on the in-place strip silently change behaviour.
- `save_patch_roundtrip` / `write_gendsp` now raise `PatchValidationError` on newly introduced blockers and on port x-rank changes (Q7 save gate).
- Removed public API (Q32): `src.maxpat.memory` (whole module), `is_complex_patch` (dropped from `src.maxpat.__all__`), `suggest_subpatchers`, `add_node_script`, `contrast_text_color`, `project.build_examples_catalog`.
- `dsp_sim` topology `bore_only` removed (Q25).
- `.release-ignore` was replaced by `.gitattributes`, and the active-project pointer is no longer written by the installers.

Note: `TECHNICAL.md:138` ("shim removal scheduled for v6.0+") and `src/maxpat/dsp_sim/README.md:269` ("v6.0 roadmap item") will read as already delivered under 6.0.0. Reword them to "a later major" (or use 7.0) when you bump.

Before tagging:
1. Fix BL-01 (`math.exp2`) and add the 3.10 regression test. Consider a vermin CI step.
2. Decide WR-01: ship the bridge patch outside `patches/`, or document `--live` as maintainer-only.
3. Fix WR-02, the gate invocation (`sys.executable -m pytest`, `cwd=REPO_ROOT`).
4. Recommended: WR-03 (db-root guard) and WR-04 (exit code for bad input). Hand WR-06 to the DB owner.
5. Docs: IN-01 (`bore_only`), IN-03 (counts and milestone row), IN-04, and the v6.0 wording above.
6. Rotate or check `NPM_TOKEN`, or switch to OIDC trusted publishing (WR-05).
7. Commit, push to main, and wait for the Tests run on that SHA to go green (3.10 and 3.12).
8. Locally: `bash scripts/build_release.sh /private/tmp/claude-501/rel/framework.tar.gz` and `python -m pytest tests/test_release.py -q`.
9. `git tag v6.0.0 && git push origin v6.0.0`. Use the full semver form (IN-07).
10. After the run: the GH release has `framework.tar.gz`; `npm view create-max-framework version` shows 6.0.0; `npx create-max-framework@latest /tmp/x` extracts, and `python3 -c "import src.maxpat"` works inside it.
