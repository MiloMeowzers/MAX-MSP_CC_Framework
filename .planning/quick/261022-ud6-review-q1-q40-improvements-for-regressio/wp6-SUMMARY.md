---
quick_id: 261022-ud6
work_package: WP6
scope: tools/release (review-tools-release.md)
status: complete
base: 8ddcdc49
branch: worktree-agent-a97e11013ec6800dd
---

# WP6: tools and release-readiness fixes

Every finding in `review-tools-release.md` is fixed except BL-01 (`math.exp2`; WP5 owns dsp_sim) and WR-06 (`inlet`/`outlet` DB I/O; WP1 owns the DB). Each fix has a regression test that failed before the fix.

## Findings

| ID | Status | How | Commit |
|---|---|---|---|
| WR-01 | fixed | `git mv patches/max-bridge/generated/max-bridge.maxpat tools/max_bridge/max-bridge.maxpat` (content unchanged, R100). `BRIDGE_PATCH`, both hints (`_bridge_hint`, `max_verify_live.preflight`), `/max-verify` (`.claude/commands/max-verify.md`) and the `patches/max-bridge/context.md` pointer all use the new path. New `bridge_patch_display()` keeps the hints valid when `BRIDGE_PATCH` lies outside the repo. `tools/max_bridge/` has no `__init__.py`, so `import tools.max_bridge` still resolves to the module (tested). The fixtures and checklists stay in `patches/max-bridge/`: only the tests and the manual checklists use them, the tool never does at runtime. | 89a7099c |
| WR-02 | fixed | The gate snippet in `.claude/skills/max-dsp-agent/SKILL.md` now runs `[sys.executable, "-m", "pytest", str(fixture), "-q", "-p", "no:cacheprovider"]` with `cwd=REPO_ROOT` (`Path.cwd()`, the framework root), and raises a clear `PatchValidationError` when pytest is not installed (it used to raise `FileNotFoundError`). Tests run the skill's own snippet in a release-like layout (no `tests/__init__.py`, no conftest) for the pass, fail and no-fixture cases. | 82cb742f |
| WR-03 | fixed | `guard_output_path(json_path, repo_root, db_root=None)` refuses `--db-root` and always protects the tool's own `ROOT/patches` and `ROOT/.claude/max-objects`, whatever `--repo-root` says. It screens both `--json` and `--write-baseline`, which are now written via `atomic_write_bytes`. `sync_max_bundle.guard_report_path` reuses it. The review repro now exits 2 and the scratch `msp/objects.json` md5 is unchanged. | 63ab6100 |
| WR-04 | fixed | `_load_patch` maps truncated JSON, undecodable bytes and non-patch JSON (`{"patcher": 3}`, `[]`) to `ValueError`. `run_check` catches `OSError`/`ValueError` around `instrument` and returns verdict `bridge_failed`, exit 2, `copy None`, with one line `cannot read <path>: ...`. Covered with and without `--dry-run`. | 7d9e275b |
| WR-05 | fixed | `release.yml`: `permissions: id-token: write` (plus `contents: write`) on the release job, Node 24 + `npm install -g npm@^11.5.1`, `npm publish --provenance --access public`, no `NODE_AUTH_TOKEN` / `secrets.NPM_TOKEN`. New step order: build archive → npm version → `npm publish --dry-run` → publish → GitHub release. A failed publish therefore leaves no public release. On a re-run, publish is skipped when `npm view <name>@<version>` already exists. Shell syntax checked; `npm publish --dry-run` passed on a scratch copy stamped 6.0.0. | 425f27a1 |
| IN-02 | fixed | Removed the non-strict xfail from `test_max_saved_file_byte_identical`. Why it passes now: Q29 made saves reproduce the file's own JSON layout (comp-band.maxpat keeps MAX 9.1's expanded arrays), so the round-trip is byte-identical. It now fails on any regression. | 0d289255 |
| IN-04 | fixed | The `max_bridge.py` docstring now records v0.3.0 as confirmed (f935e550). | 0ca8aaef |
| IN-05 | fixed | `merge_into_overrides` reads the bytes, keeps the file's `json_style` (falling back to the historical ASCII / no trailing newline), writes via `atomic_write_bytes` (fsync, mode kept, no fixed `.json.tmp`), skips no-op writes, and has the return annotation `tuple[int, int, int]`. New `tests/test_extract_pkg_io.py`. | 510807b0 |
| IN-06 | fixed | `install.sh` and `create-max-framework.js` check numpy/scipy/pytest (by import) and git, besides Python 3.10+. Missing packages print a hint to run `python3 -m pip install -r requirements-dev.txt`. All checks are warnings only. New `--check-deps` flag in both (exit 1 only when Python 3.10+ is missing). `installer/README.md` lists git, the packages and the flag. Tests drive both installers with a stubbed PATH. | a66ccee0 |
| IN-07 | fixed | Tag filter is `tags: ['v[0-9]+.[0-9]+.[0-9]+']`. | 425f27a1 |
| BL-01 follow-up | added | `test.yml` gains a `vermin -t=3.10- --violations` step over `src tools tests scripts .claude/scripts` (release-checklist item 1, "consider a vermin CI step"). **It fails until WP5's `math.exp2` fix is merged** (that is the only violation, checked locally with vermin 1.9.2). Merge WP5 and WP6 before pushing. | 8b59205e |
| BL-01 | not WP6 | WP5 (dsp_sim). | -- |
| WR-06 | not WP6 | WP1 (DB `inlet`/`outlet` overrides + help_io baseline). | -- |
| IN-01 | WP8 | Doc-only. See "Doc impacts". | -- |
| IN-03 | WP8 | Doc-only. See "Doc impacts". | -- |

## Verification

- Full suite on Python 3.14 (local default) and on a Python 3.10.19 venv built from `requirements-dev.txt`: see "Final test counts" below.
- `bash scripts/build_release.sh` into a scratch path gives 190 files: exactly the base archive (8ddcdc49, 189) plus `tools/max_bridge/max-bridge.maxpat`. Checks in the extracted archive:
  - `tools/max_bridge.py ping` exits 2 with a hint that names `tools/max_bridge/max-bridge.maxpat`, which exists.
  - The max-dsp-agent gate snippet, taken from the extracted SKILL.md and run with Python 3.10 from the framework root: a passing fixture passes; a failing fixture raises `PatchValidationError` with the assertion text; a bare 3.10 venv without pytest raises the "pytest is not installed" `PatchValidationError`. No `.pytest_cache` is created.
  - `audit_db.py --json .claude/max-objects/msp/objects.json` is refused (exit 2); `--json ../audit.json` writes.
  - `install.sh --check-deps` is quiet with all packages present. Against the bare 3.10 venv, both installers warn about numpy, scipy and pytest and print the requirements-dev hint.
- Nothing was pushed, tagged or published (`npm publish` ran only with `--dry-run`, on a scratch copy).

## Handoffs

- **WP5:** BL-01 `math.exp2` must merge with WP6, or the new vermin CI step fails.
- **WP1:** WR-06 (`inlet` inlets `[]`, `outlet` one inlet; re-run `audit_db.py --help-io --write-baseline tests/fixtures/help_io_baseline.json`). `--write-baseline` into `tests/fixtures/` is still allowed by the new guard.
- **WP2 (round-trip owner), observation:** `tests/test_round_trip.py::test_framework_file_byte_identical` is a non-strict xfail that can never pass. It fails on its precondition (`detect_indent == "  "`), because rhythmic-sampler.maxpat was re-saved by MAX with 4-space indent, so it tests nothing. Point it at a framework-written 2-space file, or delete it.
- **max_verify_live, minor:** a malformed patch in a `/max-verify --live` batch still shows as a "live check crashed" warning, because `scan_patch` parses it before `run_check`. `tools/max_bridge.py check` alone now exits 2 cleanly. Optional polish: catch `ValueError` from `scan_patch` and report it as "refused" with the same `cannot read` text.

## Doc impacts for WP8

- **IN-01 `bore_only`:** `.claude/skills/max-dsp-agent/SKILL.md` ("How to Register a New Sim Test", the topology list `bore_only`, `reed_bore`, `reed_bore_post_radiation`) and `TECHNICAL.md:612` ("Three waveguide topologies ..."). Drop `bore_only` from both. WP6 did not touch these lines.
- **IN-03 counts:** README.md:211-212 and TECHNICAL.md:293/755 ("3,345 tests", "~22,200 LOC") are stale, and the README milestone table needs a v6.0 row. Final count from this WP is below; the total changes again after the other WPs merge.
- **WR-01:** README.md:168 lists `max-bridge` under the `patches/` projects. Say that the bridge patch ships at `tools/max_bridge/max-bridge.maxpat`, and that `patches/` (including `max-bridge`'s fixtures and checklists) is repository-only and not in releases. Also mention `/max-verify --live` → open `tools/max_bridge/max-bridge.maxpat`. The historical checklists in `patches/max-bridge/test-results/` and `versions.json` keep the old `generated/` path: they are records, not edited.
- **IN-06:** the README prerequisites could mention `npx create-max-framework --check-deps` / `install.sh --check-deps` and `python3 -m pip install -r requirements-dev.txt`.
- **WR-05:** release docs (README / TECHNICAL release section, if any) should say that releases publish to npm via trusted publishing (no NPM_TOKEN secret), and that only `vX.Y.Z` tags release.
- **Release checklist wording:** TECHNICAL.md:138 ("shim removal scheduled for v6.0+") and `src/maxpat/dsp_sim/README.md:269` ("v6.0 roadmap item") should read "a later major" under 6.0.0.

## npm trusted publisher settings (user action on npmjs.com)

npmjs.com → package `create-max-framework` → Settings → Trusted Publisher → GitHub Actions:

| Field | Value |
|---|---|
| Organization or user | `taylorbrook` |
| Repository | `MAX-MSP_CC_Framework` |
| Workflow filename | `release.yml` |
| Environment name | *(leave empty: the release job uses no GitHub environment)* |

After linking, the `NPM_TOKEN` repository secret can be deleted (`gh secret delete NPM_TOKEN`). Optionally set the package's publishing access to "Require two-factor authentication and disallow tokens" once the first OIDC publish succeeds. `installer/package.json` `repository.url` already matches the repo (required for provenance).

**Needs confirmation on the first tagged run:** the trusted-publishing handshake (OIDC token exchange with `setup-node`'s `registry-url` `.npmrc`, npm 11.5.1+) cannot be exercised locally. Watch the "Publish to npm" step of the v6.0.0 run. If it 404s/401s, the trusted publisher is not linked or does not match the fields above. No GitHub release is created in that case; fix the link and re-run the job.

## Final test counts

At 8b59205e, with Max installed so the `requires_max` tests ran:
- Python 3.14.2: `python3 -m pytest -q` → **6314 passed, 5 xfailed**, 0 xpassed (was 6287 passed, 5 xfailed, 1 xpassed at base).
- Python 3.10.19 (uv venv from requirements-dev.txt): **6314 passed, 5 xfailed**.

## Self-Check: PASSED

The 10 commits 89a7099c..8b59205e exist on `worktree-agent-a97e11013ec6800dd`, and `tools/max_bridge/max-bridge.maxpat`, `tests/test_extract_pkg_io.py` and this file all exist. No committed patch file had its contents edited: the bridge patch is a pure rename, and `patches/max-bridge/context.md` is a project doc pointer.
