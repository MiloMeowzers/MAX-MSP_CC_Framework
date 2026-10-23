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
* It reads JSON only (``json.loads`` on the help files and
  ``package-info.json``). It never executes Max, a package's code or anything
  it reads, and spawns no subprocess.
* It writes nothing itself. ``tools/audit_db.py --help-io`` owns the CLI, the
  output-path guard and every file write.
* It never imports ``tools.audit_db`` (``tools/sync_max_bundle.py`` imports
  that module at load; a cycle would break the sync tool).

Sources
-------
* ``bundle``: every ``*.maxhelp`` under ``<max-app>/Contents/Resources/C74``.
* ``package:<dir>``: for each package dir under ``--packages-dir``, the
  ``*.maxhelp`` under its immediate ``help`` / ``Help`` child (help files kept
  elsewhere, e.g. ``patchers/``, are not scanned).

Comparison definition
---------------------
* The walk never descends into gen~ / rnbo~ / jit.gen internals: a box named
  in :data:`GEN_RNBO_CONTAINERS`, or an inner patcher whose
  ``classnamespace`` is in :data:`SKIPPED_NAMESPACES`. Every other inner
  patcher is walked, up to :data:`MAX_PATCHER_DEPTH`.
* newobj boxes: the name is token 0 of the quote-aware tokens
  (``io_resolvers.split_box_text``); the arguments are the following tokens
  up to (not including) the first token starting with ``@`` -- attributes
  are not arguments. Other boxes (OQ1-A) are keyed by
  their maxclass with no arguments.
* Not compared, only counted: malformed boxes (non-int counts, empty or
  non-string newobj text), content-defined boxes (an embedded ``patcher``,
  a name in :data:`CONTENT_DEFINED`, or a name containing ``codebox``) and
  names ``ObjectDatabase.lookup`` does not resolve.
* Saved ``(numinlets, numoutlets)`` differing from ``compute_io_counts`` is a
  *count mismatch*, signature ``count args=<n> max=<i>,<o> db=<i>,<o>``.
* Otherwise, when the saved ``outlettype`` is a list of length numoutlets
  (> 0), each outlet's signal class (``signal`` / ``multichannelsignal`` are
  signal, anything else control) is compared with the class of
  ``get_outlet_types``: a *type mismatch*, signature ``type max=<a/b> db=<a/b>``.
  The signal vs multichannel flavour is not compared (C9's definition).
* Report and baseline keys are the literal box name (``sel`` and ``select``
  stay separate) so they do not move when aliases.json changes; the full
  report adds the alias-resolved ``canonical`` name.

Bundle-mining scans (Q38, quick 261022-mis)
-------------------------------------------
* :func:`scan_help_idioms` collects every cord the bundle's help patches
  ship, keyed ``(source name, outlet, source-outlet signal class,
  destination name, inlet)``; ``tools/sync_max_bundle.py --apply idioms``
  writes it to ``idioms.json`` (validation Layer 3 never type/role-checks a
  listed cord).
* :func:`scan_version_io` collects per-version I/O changes from help boxes
  whose saving Max versions disagree; ``--apply version-io`` writes it to
  ``version_io.json``.
* Both read the bundle only (never a packages dir), walk exactly like the
  oracle above and are read-only in the same way: JSON only, no writes,
  no subprocess, no ``tools.audit_db`` / ``tools.sync_max_bundle`` import.
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

from src.maxpat import io_resolvers, walk as _walk  # noqa: E402
from src.maxpat.db_lookup import outlet_signal_class, parse_version  # noqa: E402
from src.maxpat.patcher import CONTENT_DEFINED_NAMES  # noqa: E402
from src.maxpat.validation import _CONTAINER_NAMES  # noqa: E402

SCHEMA_VERSION = 1

# Bound on recursion into nested `patcher` dicts (mirrors audit_db).
MAX_PATCHER_DEPTH = 32

DEFAULT_PACKAGES_DIR = Path.home() / "Documents" / "Max 9" / "Packages"

# Boxes whose inner patcher is gen / rnbo / jit.gen code, never MAX objects.
# Matched by name too, because old gen~ patchers carry no classnamespace.
GEN_RNBO_CONTAINERS = frozenset({
    "gen~", "mc.gen~", "mcs.gen~", "gen", "jit.gen", "jit.pix", "jit.gl.pix",
    "rnbo~", "mc.rnbo~", "mcs.rnbo~",
})
SKIPPED_NAMESPACES = frozenset({"dsp.gen", "jit.gen", "rnbo"})

# Objects whose I/O comes from their content, not their arguments. Imported,
# never copied, so the oracle and the patch builder agree (S4).
CONTENT_DEFINED = CONTENT_DEFINED_NAMES | _CONTAINER_NAMES

# Boxes whose saved outlettype comes from the cord INTO their patcher, not
# from the box: an `inlet` saves "signal" when its parent cord is a signal
# and "" otherwise. Their counts are compared, their outlet types are not
# (quick 261022-ud6 WP1: once the DB gave `inlet` MAX's 0/1 I/O, the 1845
# bundle inlet boxes reached the type comparison).
CONTEXT_TYPED = frozenset({"inlet"})

BASELINE_GENERATOR = (
    "python3 tools/audit_db.py --help-io --write-baseline "
    "tests/fixtures/help_io_baseline.json"
)

_STAT_KEYS = (
    "newobj_boxes",
    "other_boxes",
    "compared",
    "compared_newobj_boxes",
    "content_defined",
    "unresolved",
    "malformed",
    "internal_patchers_skipped",
    "depth_capped",
    "compare_errors",
    "names_compared",
    "mismatching_boxes",
    "mismatching_newobj_boxes",
    "mismatching_other_boxes",
    "mismatching_names",
    "mismatching_names_canonical",
    "count_mismatch_names",
    "type_mismatch_names",
)

_DIFF_FIELDS = ("count_mismatches", "type_mismatches")

MAX_EXAMPLES = 3
MAX_COMPARE_ERRORS = 50
_SIGNAL_TYPES = ("signal", "multichannelsignal")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def box_args(text: str) -> tuple[str, list[str]]:
    """Split newobj text into (name, positional args); args stop at the first @.

    Delegates to :func:`src.maxpat.io_resolvers.box_args` (Q10 hand-off):
    double quotes and backslash escapes are respected, so
    ``t "LCD Text / Icon (Inactive)"`` has one argument.
    """
    return io_resolvers.box_args(text)


def signal_class(outlettype) -> str:
    """Collapse an outlettype string to ``"signal"`` or ``"control"``."""
    return "signal" if outlettype in _SIGNAL_TYPES else "control"


def unavailable_section(reason: str) -> dict:
    """The section shape for a scan that could not run."""
    return {"available": False, "reason": reason}


def _appversion(top: dict) -> str:
    patcher = top.get("patcher")
    av = patcher.get("appversion") if isinstance(patcher, dict) else None
    if isinstance(av, dict):
        parts = [av.get("major"), av.get("minor"), av.get("revision")]
        if all(_is_count(p) for p in parts):
            return "{}.{}.{}".format(*parts)
    return "unknown"


def _is_count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


# ---------------------------------------------------------------------------
# Source discovery
# ---------------------------------------------------------------------------


def _sorted_files(root: Path, files) -> list[tuple[str, Path]]:
    pairs = [(p.relative_to(root).as_posix(), p) for p in files if p.is_file()]
    pairs.sort(key=lambda pair: pair[0])
    return pairs


def _package_version(pkg: Path) -> str | None:
    try:
        info = json.loads((pkg / "package-info.json").read_bytes())
    except (OSError, ValueError):
        return None
    version = info.get("version") if isinstance(info, dict) else None
    return version if isinstance(version, str) else None


def discover_sources(max_app, packages_dir, bundle_version) -> dict:
    """Return ``{"sources": {sid: source}, "packages_reason": str | None}``.

    Each source carries ``kind``, ``root``, ``version`` and ``files`` (a list
    of ``(relative posix path, Path)`` sorted by the relative path). Packages
    without help files produce no source; an unreadable packages dir yields
    no package sources plus a reason, never an error.
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

    reason = None
    pkg_root = Path(packages_dir)
    try:
        packages = sorted((p for p in pkg_root.iterdir() if p.is_dir()),
                          key=lambda p: p.name)
    except FileNotFoundError:
        packages, reason = [], f"packages dir not found: {pkg_root}"
    except NotADirectoryError:
        packages, reason = [], f"packages dir is not a directory: {pkg_root}"
    except OSError as exc:  # PermissionError included (TCC-blocked Documents)
        packages, reason = [], f"cannot read packages dir {pkg_root}: {exc}"

    for pkg in packages:
        files: list[Path] = []
        try:
            children = sorted(pkg.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        for child in children:
            if child.is_dir() and child.name.lower() == "help":
                files.extend(child.rglob("*.maxhelp"))
        pairs = _sorted_files(pkg, files)
        if not pairs:
            continue
        sources[f"package:{pkg.name}"] = {
            "kind": "package",
            "root": pkg,
            "version": _package_version(pkg),
            "files": pairs,
        }
    return {"sources": sources, "packages_reason": reason}


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


class _SourceScan:
    """Per-source accumulator."""

    def __init__(self, sid: str, db, compare_errors: list) -> None:
        self.sid = sid
        self.db = db
        self.compare_errors = compare_errors
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
            name = self._box(box)
            inner = box.get("patcher")
            if not isinstance(inner, dict):
                continue
            if name in GEN_RNBO_CONTAINERS or \
                    inner.get("classnamespace") in SKIPPED_NAMESPACES:
                self.stats["internal_patchers_skipped"] += 1
                continue
            self.walk(inner, depth + 1)

    def _box(self, box: dict) -> str | None:
        """Classify and maybe compare one box; return its name (or None)."""
        maxclass = box.get("maxclass")
        if maxclass == "newobj":
            self.stats["newobj_boxes"] += 1
            kind = "newobj"
            text = box.get("text")
            if not isinstance(text, str) or not text.split():
                self.stats["malformed"] += 1
                return None
            name, args = box_args(text)
        else:
            self.stats["other_boxes"] += 1
            kind = "box"
            if not isinstance(maxclass, str) or not maxclass:
                self.stats["malformed"] += 1
                return None
            name, args, text = maxclass, [], maxclass

        ni, no = box.get("numinlets"), box.get("numoutlets")
        if not _is_count(ni) or not _is_count(no):
            self.stats["malformed"] += 1
            return name

        canonical = self.db._aliases.get(name, name)
        if isinstance(box.get("patcher"), dict) or name in CONTENT_DEFINED \
                or canonical in CONTENT_DEFINED or "codebox" in name:
            self.stats["content_defined"] += 1
            return name

        try:
            resolved = self.db.lookup(name)
        except Exception as exc:  # noqa: BLE001 -- recorded, never fixed here
            self._error(box, text, exc)
            return name
        if resolved is None:
            self.stats["unresolved"] += 1
            self.unresolved[name] = self.unresolved.get(name, 0) + 1
            return name

        try:
            exp_in, exp_out = self.db.compute_io_counts(name, args)
            sig = None
            field = None
            if (ni, no) != (exp_in, exp_out):
                field = "count_mismatches"
                sig = f"count args={len(args)} max={ni},{no} db={exp_in},{exp_out}"
            else:
                saved = box.get("outlettype")
                if (
                    isinstance(saved, list) and no > 0 and len(saved) == no
                    and canonical not in CONTEXT_TYPED
                ):
                    max_cls = [signal_class(t) for t in saved]
                    db_cls = [signal_class(t) for t in self.db.get_outlet_types(name, args)]
                    if max_cls != db_cls:
                        field = "type_mismatches"
                        sig = f"type max={'/'.join(max_cls)} db={'/'.join(db_cls)}"
        except Exception as exc:  # noqa: BLE001 -- recorded, never fixed here
            self._error(box, text, exc)
            return name

        self.stats["compared"] += 1
        if kind == "newobj":
            self.stats["compared_newobj_boxes"] += 1
        entry = self.names.setdefault(name, {
            "canonical": canonical,
            "kinds": set(),
            "boxes": 0,
            "count_mismatches": 0,
            "type_mismatches": 0,
            "signatures": {},
        })
        entry["kinds"].add(kind)
        entry["boxes"] += 1
        if sig is not None:
            entry[field] += 1
            self._record(entry, sig, box, text, kind)
        return name

    def _error(self, box: dict, text, exc: Exception) -> None:
        self.stats["compare_errors"] += 1
        if len(self.compare_errors) < MAX_COMPARE_ERRORS:
            self.compare_errors.append({
                "source": self.sid,
                "file": self.file,
                "box": box.get("id"),
                "text": text,
                "error": f"{type(exc).__name__}: {exc}",
            })

    def _record(self, entry: dict, sig: str, box: dict, text: str, kind: str) -> None:
        self.stats["mismatching_boxes"] += 1
        self.stats["mismatching_newobj_boxes" if kind == "newobj"
                   else "mismatching_other_boxes"] += 1
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
    section: dict = {
        "available": True,
        "reason": None,
        "packages_dir": str(packages_dir),
        "packages_reason": None,
        "sources": {},
        "mismatches": {},
        "unresolved": {},
        "compare_errors": [],
        "summary": {},
    }
    with warnings.catch_warnings():
        # lookup() warns once per empty-I/O or not-installed name; the oracle
        # reports those boxes, it does not need the console noise.
        warnings.simplefilter("ignore")
        found = discover_sources(max_app, packages_dir, bundle_version)
        section["packages_reason"] = found["packages_reason"]
        for sid, src in found["sources"].items():
            _scan_source(section, sid, src, db)
    section["summary"] = _summarize(section)
    return section


def _scan_source(section: dict, sid: str, src: dict, db) -> None:
    scan = _SourceScan(sid, db, section["compare_errors"])
    for rel, path in src["files"]:
        scan.file = rel
        try:
            top = json.loads(path.read_bytes())
        except (OSError, ValueError) as exc:
            scan.bad_files.append({"file": rel, "reason": f"{type(exc).__name__}: {exc}"})
            continue
        if not isinstance(top, dict):
            scan.bad_files.append({"file": rel, "reason": f"top level is {type(top).__name__}"})
            continue
        scan.appversion = _appversion(top)
        scan.appversions[scan.appversion] = scan.appversions.get(scan.appversion, 0) + 1
        scan.walk(top.get("patcher"), 0)

    mism = scan.mismatches()
    stats = scan.stats
    stats["names_compared"] = len(scan.names)
    stats["mismatching_names"] = len(mism)
    stats["mismatching_names_canonical"] = len({e["canonical"] for e in mism.values()})
    stats["count_mismatch_names"] = sum(1 for e in mism.values() if e["count_mismatches"])
    stats["type_mismatch_names"] = sum(1 for e in mism.values() if e["type_mismatches"])
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


_SUMMED = (
    "newobj_boxes", "other_boxes", "compared", "compared_newobj_boxes",
    "content_defined", "unresolved",
    "malformed", "internal_patchers_skipped", "depth_capped", "compare_errors",
    "mismatching_boxes", "mismatching_newobj_boxes", "mismatching_other_boxes",
)


def _summarize(section: dict) -> dict:
    """Cross-source totals; name counts are unions of literal names."""
    totals = {k: 0 for k in _SUMMED}
    files = bad = 0
    appversions: dict[str, int] = {}
    literal: set[str] = set()
    canonical: set[str] = set()
    count_names: set[str] = set()
    type_names: set[str] = set()
    newobj_names: set[str] = set()
    other_names: set[str] = set()
    for sid, src in section["sources"].items():
        files += src["files"]
        bad += len(src["bad_files"])
        for k in totals:
            totals[k] += src["stats"][k]
        for v, n in src["appversions"].items():
            appversions[v] = appversions.get(v, 0) + n
        for name, e in section["mismatches"][sid].items():
            literal.add(name)
            canonical.add(e["canonical"])
            if e["count_mismatches"]:
                count_names.add(name)
            if e["type_mismatches"]:
                type_names.add(name)
            if "newobj" in e["kinds"]:
                newobj_names.add(name)
            if "box" in e["kinds"]:
                other_names.add(name)
    return {
        "sources": len(section["sources"]),
        "package_sources": sum(1 for s in section["sources"].values()
                               if s["kind"] == "package"),
        "files": files,
        "bad_files": bad,
        **totals,
        "mismatching_names": len(literal),
        "mismatching_names_canonical": len(canonical),
        "count_mismatch_names": len(count_names),
        "type_mismatch_names": len(type_names),
        "newobj_mismatching_names": len(newobj_names),
        "other_mismatching_names": len(other_names),
        "appversions": dict(sorted(appversions.items())),
    }


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------


def build_baseline(section: dict) -> dict:
    """Reduce a report section to the canonical, machine-neutral baseline.

    Only source ids, versions, counts and mismatching names survive: no roots,
    files, examples, appversions, canonical names or timestamps.
    """
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
    """Compare two baselines; a regression is a per-name mismatch increase.

    Only sources present in both at an equal ``version`` are compared. For
    those, a (source, name) whose ``count_mismatches`` or ``type_mismatches``
    is higher live than in the baseline is a regression (a missing name
    counts as 0); lower is an improvement. Stale-version, new and missing
    sources are reported but never produce regressions.

    Raises:
        ValueError: when either side's ``schema`` is not :data:`SCHEMA_VERSION`.
    """
    for label, doc in (("baseline", baseline), ("live", live)):
        if doc.get("schema") != SCHEMA_VERSION:
            raise ValueError(
                f"{label} help-io baseline has schema {doc.get('schema')!r}; "
                f"expected {SCHEMA_VERSION}"
            )
    regressions: list[dict] = []
    improvements: list[dict] = []
    b_src = baseline.get("sources", {})
    l_src = live.get("sources", {})
    compared: list[str] = []
    stale: dict[str, dict] = {}
    for sid in sorted(set(b_src) & set(l_src)):
        b_ver, l_ver = b_src[sid].get("version"), l_src[sid].get("version")
        if b_ver == l_ver:
            compared.append(sid)
        else:
            stale[sid] = {"baseline": b_ver, "live": l_ver}
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
    def _key(row: dict) -> tuple:
        return (row["source"], row["name"], row["field"])

    return {
        "regressions": sorted(regressions, key=_key),
        "improvements": sorted(improvements, key=_key),
        "compared_sources": compared,
        "stale_sources": stale,
        "new_sources": sorted(set(l_src) - set(b_src)),
        "missing_sources": sorted(set(b_src) - set(l_src)),
    }


# ---------------------------------------------------------------------------
# Shipped idioms (Q38)
# ---------------------------------------------------------------------------


def idiom_endpoint(box) -> str | None:
    """The name a help cord endpoint is keyed by, or None when ineligible.

    None for structural boxes (``walk.object_name`` is None: inlet, outlet,
    patcher, bpatcher, empty newobj), content-defined names
    (:data:`CONTENT_DEFINED`: ``p``, ``poly~``, ``js``, ``gen~`` ...),
    any name containing ``codebox`` and any box with an embedded
    ``patcher`` dict -- their I/O comes from their content, so a cord on
    them says nothing about the name.
    """
    if not isinstance(box, dict):
        return None
    name = _walk.object_name(box)
    if not name:
        return None
    first = name.split()[0] if name.split() else name
    if name in CONTENT_DEFINED or first in CONTENT_DEFINED or "codebox" in name:
        return None
    if isinstance(box.get("patcher"), dict):
        return None
    return name


def _bundle_help_files(max_app) -> tuple[Path, list[tuple[str, Path]]] | None:
    """(C74 dir, sorted bundle ``*.maxhelp`` files) or None without a C74 dir."""
    c74 = Path(max_app) / "Contents" / "Resources" / "C74"
    if not c74.is_dir():
        return None
    return c74, _sorted_files(c74, c74.rglob("*.maxhelp"))


def _load_help(path: Path, rel: str, bad_files: list) -> dict | None:
    try:
        top = json.loads(path.read_bytes())
    except (OSError, ValueError) as exc:
        bad_files.append({"file": rel, "reason": f"{type(exc).__name__}: {exc}"})
        return None
    if not isinstance(top, dict):
        bad_files.append({"file": rel, "reason": f"top level is {type(top).__name__}"})
        return None
    return top


def _iter_scopes(patcher, depth: int, stats: dict):
    """Yield every patcher the oracle walks (gen / rnbo internals skipped).

    Mirrors :meth:`_SourceScan.walk`: a box named in
    :data:`GEN_RNBO_CONTAINERS`, or an inner patcher whose
    ``classnamespace`` is in :data:`SKIPPED_NAMESPACES`, is counted in
    ``internal_patchers_skipped``; nesting past :data:`MAX_PATCHER_DEPTH`
    is counted in ``depth_capped``.
    """
    if not isinstance(patcher, dict):
        return
    if depth > MAX_PATCHER_DEPTH:
        stats["depth_capped"] += 1
        return
    yield patcher
    boxes = patcher.get("boxes")
    if not isinstance(boxes, list):
        return
    for entry in boxes:
        box = entry.get("box") if isinstance(entry, dict) else None
        if not isinstance(box, dict):
            continue
        inner = box.get("patcher")
        if not isinstance(inner, dict):
            continue
        if _walk.box_name(box) in GEN_RNBO_CONTAINERS or \
                inner.get("classnamespace") in SKIPPED_NAMESPACES:
            stats["internal_patchers_skipped"] += 1
            continue
        yield from _iter_scopes(inner, depth + 1, stats)


def _scope_boxes(patcher: dict) -> dict:
    """Box id -> box dict for one patcher (non-dict entries ignored)."""
    out: dict = {}
    boxes = patcher.get("boxes")
    for entry in boxes if isinstance(boxes, list) else []:
        box = entry.get("box") if isinstance(entry, dict) else None
        if isinstance(box, dict) and isinstance(box.get("id"), str):
            out[box["id"]] = box
    return out


def _port(value) -> bool:
    return _is_count(value) and value >= 0


def _idiom_sort_key(item: str) -> tuple:
    outlet, cls, dst, inlet = item.split(" ")
    return (int(outlet), cls, dst, int(inlet))


def scan_help_idioms(max_app) -> dict:
    """Every cord the bundle's help patches ship, keyed for idioms.json (Q38).

    Bundle only: ``<max_app>/Contents/Resources/C74/**/*.maxhelp`` in sorted
    relative-path order, never a packages dir. Per walked patcher, each
    ``patchline`` whose source / destination are lists of length >= 2 with
    non-negative int ports and boxes present in that patcher is:

    * ``excluded_cords`` when either endpoint fails :func:`idiom_endpoint`;
    * ``unclassified_cords`` when the source box records no outlettype at
      that outlet (:func:`outlet_signal_class` is None);
    * otherwise recorded as ``"<outlet> <class> <dst> <inlet>"`` under
      ``pairs[<src>]``. Names are literal; ObjectDatabase canonicalises them
      through aliases.json at load.

    Every other patchline is ``malformed_cords``. Unparsable files go to
    ``bad_files``; nothing raises.
    """
    found = _bundle_help_files(max_app)
    if found is None:
        c74 = Path(max_app) / "Contents" / "Resources" / "C74"
        return unavailable_section(f"no C74 resources directory at {c74}")
    _c74, files = found
    stats = {k: 0 for k in (
        "cords", "recorded_cords", "excluded_cords", "unclassified_cords",
        "malformed_cords", "internal_patchers_skipped", "depth_capped",
    )}
    bad_files: list[dict] = []
    pairs: dict[str, set[str]] = {}
    for rel, path in files:
        top = _load_help(path, rel, bad_files)
        if top is None:
            continue
        for patcher in _iter_scopes(top.get("patcher"), 0, stats):
            lines = patcher.get("lines")
            if not isinstance(lines, list) or not lines:
                continue
            boxes = _scope_boxes(patcher)
            for line in lines:
                stats["cords"] += 1
                pl = line.get("patchline") if isinstance(line, dict) else None
                src_ref = pl.get("source") if isinstance(pl, dict) else None
                dst_ref = pl.get("destination") if isinstance(pl, dict) else None
                if not (
                    isinstance(src_ref, list) and isinstance(dst_ref, list)
                    and len(src_ref) >= 2 and len(dst_ref) >= 2
                    and _port(src_ref[1]) and _port(dst_ref[1])
                    and isinstance(src_ref[0], str) and isinstance(dst_ref[0], str)
                    and src_ref[0] in boxes and dst_ref[0] in boxes
                ):
                    stats["malformed_cords"] += 1
                    continue
                src_box, dst_box = boxes[src_ref[0]], boxes[dst_ref[0]]
                src = idiom_endpoint(src_box)
                dst = idiom_endpoint(dst_box)
                if src is None or dst is None:
                    stats["excluded_cords"] += 1
                    continue
                outlet, inlet = src_ref[1], dst_ref[1]
                cls = outlet_signal_class(src_box.get("outlettype"), outlet)
                if cls is None:
                    stats["unclassified_cords"] += 1
                    continue
                stats["recorded_cords"] += 1
                pairs.setdefault(src, set()).add(f"{outlet} {cls} {dst} {inlet}")
    return {
        "available": True,
        "reason": None,
        "files": len(files),
        "bad_files": bad_files,
        **stats,
        "pairs": {
            name: sorted(items, key=_idiom_sort_key) for name, items in sorted(pairs.items())
        },
    }


# ---------------------------------------------------------------------------
# Per-version I/O (Q38)
# ---------------------------------------------------------------------------


def _vtext(version: tuple[int, int, int]) -> str:
    return "{}.{}.{}".format(*version)


def scan_version_io(max_app, db, installed: str | None = None) -> dict:
    """Per-name I/O changes from bundle help boxes saved by different Max builds (Q38).

    Bundle only, the same walk as :func:`scan_help_idioms`. Every box whose
    :func:`idiom_endpoint` is a name ``db.lookup`` resolves (warnings muted)
    and whose ``numinlets`` / ``numoutlets`` are ints records that I/O under
    the key ``(name, walk.box_args(box))`` at the file's saving version
    (``patcher.appversion``; files of unknown version are skipped).

    * A key seen with 2+ distinct I/O values becomes segments, one per I/O
      value (``first`` / ``last`` version, ``boxes``), sorted by ``first``.
      It is monotone iff every segment's ``last`` < the next one's
      ``first``; otherwise it is an ambiguous group (``ambiguous_groups``,
      its name in ``ambiguous_names``).
    * A monotone key's transitions are ``(after = seg_i.last, by =
      seg_{i+1}.first, inlets / outlets deltas)``. When every monotone key
      of a name has the same delta sequence, the name gets ``changes``:
      per transition, after = the latest after and by = the earliest by
      over its keys, which must still satisfy after < by. Otherwise the
      name is ``conflicting``.
    * Each change carries ``newer_than_installed`` (``by`` > *installed*,
      False without *installed*).

    Returns ``objects`` (name -> ``{changes, evidence: [{args, segments,
    example}]}``), sorted ``conflicting`` / ``ambiguous_names``,
    ``ambiguous_groups``, ``files``, ``bad_files``, ``available`` and
    ``reason``. Read-only; nothing raises for a bad help file.
    """
    found = _bundle_help_files(max_app)
    if found is None:
        c74 = Path(max_app) / "Contents" / "Resources" / "C74"
        return unavailable_section(f"no C74 resources directory at {c74}")
    _c74, files = found
    installed_v = parse_version(installed) if installed is not None else None
    stats = {"internal_patchers_skipped": 0, "depth_capped": 0}
    bad_files: list[dict] = []
    # (name, args) -> io -> {"first", "last", "boxes"}; plus the first file per key
    groups: dict[tuple[str, tuple[str, ...]], dict[tuple[int, int], dict]] = {}
    examples: dict[tuple[str, tuple[str, ...]], str] = {}
    resolves: dict[str, bool] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for rel, path in files:
            top = _load_help(path, rel, bad_files)
            if top is None:
                continue
            av = _appversion(top)
            if av == "unknown":
                continue
            version = parse_version(av)
            for patcher in _iter_scopes(top.get("patcher"), 0, stats):
                for box in _scope_boxes(patcher).values():
                    name = idiom_endpoint(box)
                    if name is None:
                        continue
                    ni, no = box.get("numinlets"), box.get("numoutlets")
                    if not _is_count(ni) or not _is_count(no):
                        continue
                    if name not in resolves:
                        try:
                            resolves[name] = db.lookup(name) is not None
                        except Exception:  # noqa: BLE001 -- unresolvable is "no evidence"
                            resolves[name] = False
                    if not resolves[name]:
                        continue
                    key = (name, tuple(_walk.box_args(box)))
                    examples.setdefault(key, rel)
                    seg = groups.setdefault(key, {}).setdefault(
                        (ni, no), {"first": version, "last": version, "boxes": 0}
                    )
                    seg["first"] = min(seg["first"], version)
                    seg["last"] = max(seg["last"], version)
                    seg["boxes"] += 1

    ambiguous_groups = 0
    ambiguous_names: set[str] = set()
    monotone: dict[str, list[tuple[tuple, list[tuple]]]] = {}
    for key in sorted(groups):
        by_io = groups[key]
        if len(by_io) < 2:
            continue
        segments = sorted(by_io.items(), key=lambda kv: (kv[1]["first"], kv[1]["last"], kv[0]))
        if not all(a[1]["last"] < b[1]["first"] for a, b in zip(segments, segments[1:])):
            ambiguous_groups += 1
            ambiguous_names.add(key[0])
            continue
        monotone.setdefault(key[0], []).append((key, segments))

    objects: dict[str, dict] = {}
    conflicting: list[str] = []
    for name in sorted(monotone):
        keyed = monotone[name]
        transitions = []
        for _key, segments in keyed:
            transitions.append([
                (a[1]["last"], b[1]["first"], b[0][0] - a[0][0], b[0][1] - a[0][1])
                for a, b in zip(segments, segments[1:])
            ])
        deltas = {tuple((t[2], t[3]) for t in trans) for trans in transitions}
        if len(deltas) != 1:
            conflicting.append(name)
            continue
        changes = []
        for i, (d_in, d_out) in enumerate(next(iter(deltas))):
            after = max(trans[i][0] for trans in transitions)
            by = min(trans[i][1] for trans in transitions)
            if not after < by:
                changes = None
                break
            changes.append({
                "after": _vtext(after),
                "by": _vtext(by),
                "inlets": d_in,
                "outlets": d_out,
                "newer_than_installed": installed_v is not None and by > installed_v,
            })
        if changes is None:
            conflicting.append(name)
            continue
        objects[name] = {
            "changes": changes,
            "evidence": [
                {
                    "args": list(key[1]),
                    "segments": [
                        {"inlets": io[0], "outlets": io[1], "first": _vtext(seg["first"]),
                         "last": _vtext(seg["last"]), "boxes": seg["boxes"]}
                        for io, seg in segments
                    ],
                    "example": examples[key],
                }
                for key, segments in keyed
            ],
        }
    return {
        "available": True,
        "reason": None,
        "files": len(files),
        "bad_files": bad_files,
        **stats,
        "objects": objects,
        "conflicting": sorted(conflicting),
        "ambiguous_groups": ambiguous_groups,
        "ambiguous_names": sorted(ambiguous_names),
    }


# ---------------------------------------------------------------------------
# Text summary
# ---------------------------------------------------------------------------


def _top_names(section: dict, limit: int = 10) -> list[str]:
    agg: dict[str, list[int]] = {}
    for per_source in section["mismatches"].values():
        for name, e in per_source.items():
            row = agg.setdefault(name, [0, 0])
            row[0] += e["count_mismatches"] + e["type_mismatches"]
            row[1] += e["boxes"]
    ranked = sorted(agg.items(), key=lambda kv: (-kv[1][0], kv[0]))[:limit]
    return [f"{name} {m}/{b}" for name, (m, b) in ranked]


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
        srcs = section["sources"]
        bundle_files = srcs.get("bundle", {}).get("files", 0)
        pkg_files = sum(v["files"] for v in srcs.values() if v["kind"] == "package")
        where = section.get("packages_reason") or section.get("packages_dir")
        lines.append(
            f"  sources         : bundle {bundle_files} files; "
            f"{s['package_sources']} packages, {pkg_files} files ({where})"
        )
        lines.append(
            f"  boxes           : {s['compared']} compared "
            f"({s['compared_newobj_boxes']} newobj), "
            f"{s['content_defined']} content-defined, {s['unresolved']} unresolved, "
            f"{s['malformed']} malformed, {s['internal_patchers_skipped']} internal "
            f"patchers skipped, {s['bad_files']} bad files"
        )
        lines.append(
            f"  mismatching     : {s['mismatching_names']} names "
            f"({s['mismatching_names_canonical']} alias-resolved; "
            f"{s['count_mismatch_names']} count, {s['type_mismatch_names']} signal-role; "
            f"{s['newobj_mismatching_names']} newobj, "
            f"{s['other_mismatching_names']} other), "
            f"{s['mismatching_boxes']} boxes"
        )
        ranked = sorted(s["appversions"].items(), key=lambda kv: (-kv[1], kv[0]))
        shown = ", ".join(f"{v} x{n}" for v, n in ranked[:5])
        more = f" (+{len(ranked) - 5} more)" if len(ranked) > 5 else ""
        lines.append(f"  help versions   : {shown}{more}")
        for sid, src in srcs.items():
            st = src["stats"]
            lines.append(
                f"    {sid:<30} {src['version'] or '-':<10} {src['files']:>5} files "
                f"{st['compared']:>6} compared {st['mismatching_names']:>4} names "
                f"{st['mismatching_boxes']:>5} boxes"
            )
        top = _top_names(section)
        if top:
            lines.append(f"  top names       : {', '.join(top)}")
        if section.get("compare_errors"):
            lines.append(f"  compare errors  : {s['compare_errors']}")
    if json_path is not None:
        lines.append(f"  json            : {json_path}")
    if baseline_path is not None:
        lines.append(f"  baseline        : {baseline_path}")
    return "\n".join(lines)
