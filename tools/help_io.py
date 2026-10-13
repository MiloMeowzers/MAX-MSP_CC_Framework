"""Help-box I/O oracle: compare MAX-saved help boxes with the object DB.

Every ``.maxhelp`` Cycling '74 ships (and every help file of an installed
package) is a patch MAX itself serialized, so each box records the
``numinlets`` / ``numoutlets`` / ``outlettype`` MAX really created. This
module walks those files and compares each box with what
:meth:`ObjectDatabase.compute_io_counts` and
:meth:`ObjectDatabase.get_outlet_types` predict for the same name and
arguments. It is the review's §5.5 bundle-mining foundation (quick
261012-ubw, Q9): Q10 (variable-I/O rules, C1), Q11 (overrides and signal
roles, C2/C9) and Q38 (per-version I/O) consume its report and baseline.

Read-only
---------
* It reads JSON only (``json.loads`` on the help files). It never executes
  Max, a package's code or anything it reads, and spawns no subprocess.
* It writes nothing itself. ``tools/audit_db.py --help-io`` owns the CLI, the
  output-path guard and every file write.
* It never imports ``tools.audit_db`` (``tools/sync_max_bundle.py`` imports
  that module at load; a cycle would break the sync tool).

Comparison definition
---------------------
* newobj boxes: the name is token 0 of ``text.split()``; the arguments are
  the following tokens up to (not including) the first token starting with
  ``@`` -- attributes are not arguments.
* Saved ``(numinlets, numoutlets)`` differing from ``compute_io_counts`` is a
  *count mismatch*, signature ``count args=<n> max=<i>,<o> db=<i>,<o>``.
* Report and baseline keys are the literal box name (``sel`` and ``select``
  stay separate) so they do not move when aliases.json changes.
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

# Project root: this file is at tools/help_io.py
ROOT = Path(__file__).resolve().parent.parent

# Allow `from src.maxpat...` when run from anywhere.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA_VERSION = 1

# Bound on recursion into nested `patcher` dicts (mirrors audit_db).
MAX_PATCHER_DEPTH = 32

DEFAULT_PACKAGES_DIR = Path.home() / "Documents" / "Max 9" / "Packages"

BASELINE_GENERATOR = (
    "python3 tools/audit_db.py --help-io --write-baseline "
    "tests/fixtures/help_io_baseline.json"
)

_STAT_KEYS = (
    "newobj_boxes",
    "other_boxes",
    "compared",
    "content_defined",
    "unresolved",
    "malformed",
    "internal_patchers_skipped",
    "depth_capped",
    "compare_errors",
    "names_compared",
    "mismatching_boxes",
    "mismatching_names",
    "count_mismatch_names",
    "type_mismatch_names",
)

_DIFF_FIELDS = ("count_mismatches", "type_mismatches")

MAX_EXAMPLES = 3


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def box_args(text: str) -> tuple[str, list[str]]:
    """Split newobj text into (name, positional args); args stop at the first @."""
    tokens = text.split()
    if not tokens:
        return ("", [])
    args: list[str] = []
    for tok in tokens[1:]:
        if tok.startswith("@"):
            break
        args.append(tok)
    return (tokens[0], args)


def unavailable_section(reason: str) -> dict:
    """The section shape for a scan that could not run."""
    return {"available": False, "reason": reason}


def _appversion(top: dict) -> str:
    patcher = top.get("patcher")
    av = patcher.get("appversion") if isinstance(patcher, dict) else None
    if isinstance(av, dict):
        parts = [av.get("major"), av.get("minor"), av.get("revision")]
        if all(isinstance(p, int) and not isinstance(p, bool) for p in parts):
            return "{}.{}.{}".format(*parts)
    return "unknown"


def _is_count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


# ---------------------------------------------------------------------------
# Source discovery
# ---------------------------------------------------------------------------


def _sorted_files(root: Path, files) -> list[tuple[str, Path]]:
    pairs = [(p.relative_to(root).as_posix(), p) for p in files]
    pairs.sort(key=lambda pair: pair[0])
    return pairs


def discover_sources(max_app, packages_dir, bundle_version) -> dict:
    """Return the help-file sources to scan, keyed by source id.

    ``bundle`` is every ``*.maxhelp`` under ``<max-app>/Contents/Resources/C74``.
    Each value carries ``kind``, ``root``, ``version`` and ``files`` (a list of
    ``(relative posix path, Path)`` sorted by the relative path).
    """
    sources: dict[str, dict] = {}
    c74 = Path(max_app) / "Contents" / "Resources" / "C74"
    if c74.is_dir():
        sources["bundle"] = {
            "kind": "bundle",
            "root": c74,
            "version": bundle_version,
            "files": _sorted_files(c74, c74.rglob("*.maxhelp")),
        }
    return {"sources": sources, "packages_reason": None}


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


class _SourceScan:
    """Per-source accumulator."""

    def __init__(self, sid: str, db) -> None:
        self.sid = sid
        self.db = db
        self.stats = {k: 0 for k in _STAT_KEYS}
        self.names: dict[str, dict] = {}
        self.unresolved: dict[str, int] = {}
        self.bad_files: list[dict] = []
        self.appversions: dict[str, int] = {}
        self.file = ""
        self.appversion = "unknown"

    def walk(self, patcher, depth: int) -> None:
        if not isinstance(patcher, dict):
            return
        if depth > MAX_PATCHER_DEPTH:
            self.stats["depth_capped"] += 1
            return
        boxes = patcher.get("boxes")
        if not isinstance(boxes, list):
            return
        for entry in boxes:
            box = entry.get("box") if isinstance(entry, dict) else None
            if not isinstance(box, dict):
                continue
            if box.get("maxclass") == "newobj":
                self.stats["newobj_boxes"] += 1
                self._newobj(box)
            inner = box.get("patcher")
            if isinstance(inner, dict):
                self.walk(inner, depth + 1)

    def _newobj(self, box: dict) -> None:
        text = box.get("text")
        ni, no = box.get("numinlets"), box.get("numoutlets")
        if not isinstance(text, str) or not text.split() or not _is_count(ni) \
                or not _is_count(no):
            self.stats["malformed"] += 1
            return
        name, args = box_args(text)
        if isinstance(box.get("patcher"), dict):
            self.stats["content_defined"] += 1
            return
        if self.db.lookup(name) is None:
            self.stats["unresolved"] += 1
            self.unresolved[name] = self.unresolved.get(name, 0) + 1
            return
        self.stats["compared"] += 1
        entry = self.names.setdefault(name, {
            "canonical": self.db._aliases.get(name, name),
            "kinds": set(),
            "boxes": 0,
            "count_mismatches": 0,
            "type_mismatches": 0,
            "signatures": {},
        })
        entry["kinds"].add("newobj")
        entry["boxes"] += 1
        exp_in, exp_out = self.db.compute_io_counts(name, args)
        if (ni, no) != (exp_in, exp_out):
            entry["count_mismatches"] += 1
            sig = f"count args={len(args)} max={ni},{no} db={exp_in},{exp_out}"
            self._record(entry, sig, box, text)

    def _record(self, entry: dict, sig: str, box: dict, text: str) -> None:
        self.stats["mismatching_boxes"] += 1
        s = entry["signatures"].setdefault(
            sig, {"count": 0, "appversions": set(), "examples": []}
        )
        s["count"] += 1
        s["appversions"].add(self.appversion)
        if len(s["examples"]) < MAX_EXAMPLES:
            s["examples"].append({"file": self.file, "box": box.get("id"), "text": text})

    def mismatches(self) -> dict:
        out: dict[str, dict] = {}
        for name in sorted(self.names):
            e = self.names[name]
            if e["count_mismatches"] + e["type_mismatches"] == 0:
                continue
            out[name] = {
                "canonical": e["canonical"],
                "kinds": sorted(e["kinds"]),
                "boxes": e["boxes"],
                "count_mismatches": e["count_mismatches"],
                "type_mismatches": e["type_mismatches"],
                "signatures": {
                    sig: {
                        "count": s["count"],
                        "appversions": sorted(s["appversions"]),
                        "examples": s["examples"],
                    }
                    for sig, s in sorted(e["signatures"].items())
                },
            }
        return out


def scan_help_io(max_app, packages_dir, db, bundle_version) -> dict:
    """Scan every help source and return the ``help_io`` report section."""
    c74 = Path(max_app) / "Contents" / "Resources" / "C74"
    if not c74.is_dir():
        return unavailable_section(f"no C74 resources directory at {c74}")
    found = discover_sources(max_app, packages_dir, bundle_version)
    section: dict = {
        "available": True,
        "reason": None,
        "packages_dir": str(packages_dir),
        "packages_reason": found["packages_reason"],
        "sources": {},
        "mismatches": {},
        "unresolved": {},
        "compare_errors": [],
        "summary": {},
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for sid, src in found["sources"].items():
            scan = _SourceScan(sid, db)
            for rel, path in src["files"]:
                scan.file = rel
                try:
                    top = json.loads(path.read_bytes())
                except (OSError, ValueError) as exc:
                    scan.bad_files.append({"file": rel, "reason": str(exc)})
                    continue
                if not isinstance(top, dict):
                    scan.bad_files.append(
                        {"file": rel, "reason": f"top level is {type(top).__name__}"}
                    )
                    continue
                scan.appversion = _appversion(top)
                scan.appversions[scan.appversion] = (
                    scan.appversions.get(scan.appversion, 0) + 1
                )
                scan.walk(top.get("patcher"), 0)
            mism = scan.mismatches()
            stats = scan.stats
            stats["names_compared"] = len(scan.names)
            stats["mismatching_names"] = len(mism)
            stats["count_mismatch_names"] = sum(
                1 for e in mism.values() if e["count_mismatches"]
            )
            stats["type_mismatch_names"] = sum(
                1 for e in mism.values() if e["type_mismatches"]
            )
            section["sources"][sid] = {
                "kind": src["kind"],
                "root": str(src["root"]),
                "version": src["version"],
                "files": len(src["files"]),
                "bad_files": scan.bad_files,
                "appversions": dict(sorted(scan.appversions.items())),
                "stats": stats,
            }
            section["mismatches"][sid] = mism
            section["unresolved"][sid] = dict(sorted(scan.unresolved.items()))
    section["summary"] = _summarize(section)
    return section


def _summarize(section: dict) -> dict:
    totals = {k: 0 for k in _STAT_KEYS if not k.endswith("_names")}
    files = bad = 0
    literal: set[str] = set()
    canonical: set[str] = set()
    count_names: set[str] = set()
    type_names: set[str] = set()
    for sid, src in section["sources"].items():
        files += src["files"]
        bad += len(src["bad_files"])
        for k in totals:
            totals[k] += src["stats"][k]
        for name, e in section["mismatches"][sid].items():
            literal.add(name)
            canonical.add(e["canonical"])
            if e["count_mismatches"]:
                count_names.add(name)
            if e["type_mismatches"]:
                type_names.add(name)
    return {
        "sources": len(section["sources"]),
        "files": files,
        "bad_files": bad,
        **totals,
        "mismatching_names": len(literal),
        "mismatching_names_canonical": len(canonical),
        "count_mismatch_names": len(count_names),
        "type_mismatch_names": len(type_names),
    }


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------


def build_baseline(section: dict) -> dict:
    """Reduce a report section to the canonical, machine-neutral baseline."""
    bundle = section["sources"].get("bundle", {})
    sources: dict[str, dict] = {}
    names: dict[str, dict] = {}
    for sid, src in section["sources"].items():
        stats = src["stats"]
        sources[sid] = {
            "version": src["version"],
            "files": src["files"],
            "boxes_compared": stats["compared"],
            "mismatching_boxes": stats["mismatching_boxes"],
            "mismatching_names": stats["mismatching_names"],
        }
        names[sid] = {
            name: {
                "boxes": e["boxes"],
                "count_mismatches": e["count_mismatches"],
                "type_mismatches": e["type_mismatches"],
                "signatures": {sig: s["count"] for sig, s in e["signatures"].items()},
            }
            for name, e in section["mismatches"].get(sid, {}).items()
        }
    summary = section["summary"]
    return {
        "schema": SCHEMA_VERSION,
        "generator": BASELINE_GENERATOR,
        "max_version": bundle.get("version"),
        "sources": sources,
        "names": names,
        "totals": {
            "files": summary["files"],
            "boxes_compared": summary["compared"],
            "mismatching_boxes": summary["mismatching_boxes"],
            "mismatching_names": summary["mismatching_names"],
            "count_mismatch_names": summary["count_mismatch_names"],
            "type_mismatch_names": summary["type_mismatch_names"],
        },
    }


def dump_baseline(baseline: dict) -> str:
    """Canonical text form: sorted keys, indent 1, trailing newline."""
    return json.dumps(baseline, sort_keys=True, indent=1) + "\n"


def diff_baselines(baseline: dict, live: dict) -> dict:
    """Compare two baselines; a regression is a per-name mismatch increase."""
    regressions: list[dict] = []
    improvements: list[dict] = []
    b_src = baseline.get("sources", {})
    l_src = live.get("sources", {})
    compared = sorted(set(b_src) & set(l_src))
    for sid in compared:
        b_names = baseline.get("names", {}).get(sid, {})
        l_names = live.get("names", {}).get(sid, {})
        for name in sorted(set(b_names) | set(l_names)):
            for field in _DIFF_FIELDS:
                b = b_names.get(name, {}).get(field, 0)
                v = l_names.get(name, {}).get(field, 0)
                row = {"source": sid, "name": name, "field": field,
                       "baseline": b, "live": v}
                if v > b:
                    regressions.append(row)
                elif v < b:
                    improvements.append(row)
    return {
        "regressions": regressions,
        "improvements": improvements,
        "compared_sources": compared,
    }


# ---------------------------------------------------------------------------
# Text summary
# ---------------------------------------------------------------------------


def format_help_io_summary(envelope: dict, json_path=None, baseline_path=None) -> str:
    """Render the scannable text summary of a help-io envelope."""
    install = envelope.get("install", {})
    section = envelope.get("help_io", {})
    lines = [f"MAX help-box I/O oracle  ({envelope.get('generated_at')})"]
    if install.get("available"):
        lines.append(
            f"  install         : Max {install.get('short_version')} "
            f"(build {install.get('build_id') or install.get('build_version')})"
        )
    else:
        lines.append(f"  install         : unavailable ({install.get('reason')})")
    if not section.get("available"):
        lines.append(f"  help-box I/O    : unavailable ({section.get('reason')})")
    else:
        s = section["summary"]
        lines.append(
            f"  sources         : {s['sources']} ({s['files']} help files)"
        )
        lines.append(
            f"  boxes           : {s['compared']} compared, "
            f"{s['content_defined']} content-defined, {s['unresolved']} unresolved, "
            f"{s['malformed']} malformed"
        )
        lines.append(
            f"  mismatching     : {s['mismatching_names']} names, "
            f"{s['mismatching_boxes']} boxes"
        )
        for sid, src in section["sources"].items():
            st = src["stats"]
            lines.append(
                f"    {sid:<28} {src['version'] or '-':<10} {src['files']:>5} files "
                f"{st['compared']:>6} compared {st['mismatching_names']:>4} names "
                f"{st['mismatching_boxes']:>5} boxes"
            )
    if json_path is not None:
        lines.append(f"  json            : {json_path}")
    if baseline_path is not None:
        lines.append(f"  baseline        : {baseline_path}")
    return "\n".join(lines)
