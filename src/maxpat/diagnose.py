"""Console diagnosis: MAX console lines -> troubleshooting entries -> boxes (Q37).

The user pastes MAX console output; :func:`diagnose_console` maps every line
to ranked entries of ``.claude/skills/references/troubleshooting.md`` (cause,
fix, source), locates the offending boxes in the project's patches and
drafts one ``/max-iterate`` proposal per matched line. The CLI
(``python3 -m src.maxpat.diagnose --project NAME FILE|-``) prints the report.

Read-only guarantee
    Nothing here writes, renames, deletes, commits or spawns a process: the
    module never imports ``src.maxpat.hooks``, ``src.maxpat.atomic_io``,
    ``subprocess`` or ``shutil`` (pinned by an AST gate in
    tests/test_diagnose.py). Every fix goes through a user-approved
    ``/max-iterate`` (edit_patch session, save gate, path-scoped commit).

Parse contract (troubleshooting.md is the single source of the wordings)
    Each ``## `` heading names a section; each four-cell table row
    (``| message | cause | fix | source |``, header and separator skipped) is
    one :class:`TroubleEntry`. Its console patterns are the code spans of the
    first cell at parenthesis depth 0, where parentheses are counted only
    outside code spans, so ``(seen as `...`)`` examples are not patterns and
    ``delay()`` inside a code span stays intact. In a pattern ``<...>``
    matches one non-space token and ``...`` matches any text. A row whose
    first cell has no depth-0 code span ("wording not recorded") has no
    pattern. The file is read at call time, never at import.

Match tiers (best tier wins; only matches in the best tier are kept)
    * ``exact`` (bonus 3000): the pattern as written;
    * ``any-identifier`` (2000): each quoted literal (``'sr'``) matches any
      quoted identifier, captured as ``identifier``;
    * ``no-prefix`` (1000): the pattern with its leading ``token: `` made
      optional (a bare ``No such object``).
    The score is the bonus plus the pattern's literal character count; an
    entry keeps its best pattern. Lines are normalized first: double quotes
    dropped, whitespace collapsed, a doubled ``X: X: `` prefix collapsed
    (the rule of ``tools/max_bridge._error_key``, mirrored here because src
    never imports tools/), then deduplicated with counts.

Locate rules (``patches/<project>/``, read-only)
    Every .maxpat, .maxhelp and .gendsp under the project is walked with
    :func:`src.maxpat.walk.iter_patchers`; ``test-results/``, ``.git``,
    ``node_modules`` and ``__pycache__`` directories and ``__maxbridge_*``
    copies are skipped, symlinked directories are not followed, files that
    resolve outside the project are skipped, and malformed files are listed
    instead of raising. A line outside the gen~ compile section gives object
    hits (``walk.object_name`` equal to a captured ``<objectname>``, else
    the line's leading token), falling back to newobj argument tokens. A
    gen~ compile line gives codebox hits (code containing a captured or
    quoted identifier, with 1-based line numbers), falling back to gen
    containers and codeboxes.

No I/O happens at import: stdlib and ``src.maxpat`` only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from src.maxpat import walk

TROUBLESHOOTING_PATH = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "skills" / "references" / "troubleshooting.md"
)
GEN_SECTION = "gen~ compile"
MAX_LINES = 2000
MAX_LINE_CHARS = 2000
MAX_HITS = 10
PATCH_SUFFIXES = (".maxpat", ".maxhelp", ".gendsp")
SKIP_DIRS = {"test-results", ".git", "node_modules", "__pycache__"}

TIER_BONUS = {"exact": 3000, "any-identifier": 2000, "no-prefix": 1000}

_PLACEHOLDER_RE = re.compile(r"<[^<>\s]+>")
_TEMPLATE_TOKEN_RE = re.compile(r"(<[^<>\s]+>|\.\.\.)")
# A quoted literal: ' not after a word character, non-space non-quote
# characters, ' not before a word character (doesn't / can't stay literal).
_QUOTED_RE = re.compile(r"(?<!\w)'([^\s']+)'(?!\w)")
_PREFIX_RE = re.compile(r"^(?:<[^<>\s]+>|[^\s:<>]+): ")
_LEADING_TOKEN_RE = re.compile(r"^([^\s:]+):(?:\s|$)")
_SENTENCE_END_RE = re.compile(r"(?<!\.\.)(?<=[.!?])\s+(?=[A-Z`])")


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TroubleEntry:
    """One troubleshooting.md table row."""

    section: str
    message: str
    patterns: tuple[str, ...]
    cause: str
    fix: str
    source: str
    row: int


@dataclass(frozen=True)
class EntryMatch:
    """An entry matched by one pattern in one tier."""

    entry: TroubleEntry
    pattern: str
    tier: str
    score: int
    captures: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class BoxHit:
    """A box located for a console line (``file`` relative to the project)."""

    file: str
    where: str
    box_id: str
    label: str
    reason: str
    code_lines: tuple[int, ...] = ()


@dataclass
class Diagnosis:
    """One distinct console line with its matches, hits and proposal."""

    line: str
    count: int
    matches: tuple[EntryMatch, ...] = ()
    objects: tuple[str, ...] = ()
    identifiers: tuple[str, ...] = ()
    hits: tuple[BoxHit, ...] = ()
    hits_omitted: int = 0
    facts: tuple[str, ...] = ()
    proposal: str | None = None


@dataclass
class DiagnoseReport:
    """The whole diagnosis; :meth:`render` gives the CLI text."""

    project: str | None
    files: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    diagnoses: list[Diagnosis] = field(default_factory=list)
    truncated: bool = False

    def render(self) -> str:
        if not self.diagnoses:
            return "no console lines"
        matched = sum(1 for d in self.diagnoses if d.matches)
        out = [
            "Console diagnosis: %d distinct line(s), %d matched, %d unmatched"
            % (len(self.diagnoses), matched, len(self.diagnoses) - matched)
        ]
        if self.project:
            out.append("Project: %s (%d patch file(s) scanned)"
                       % (self.project, len(self.files)))
        else:
            out.append("Project: none -- boxes not located (pass --project NAME)")
        for item in self.skipped:
            out.append("Skipped: " + item)
        if self.truncated:
            out.append("Input truncated to %d lines." % MAX_LINES)
        for i, diag in enumerate(self.diagnoses, 1):
            out.append("")
            head = "[%d] %s" % (i, diag.line)
            if diag.count > 1:
                head += "  (x%d)" % diag.count
            out.append(head)
            for m in diag.matches:
                out.append("  entry: %s -- `%s` [%s]" % (m.entry.section, m.pattern, m.tier))
                out.append("    cause: " + m.entry.cause)
                out.append("    fix: " + m.entry.fix)
                out.append("    source: " + m.entry.source)
            if not diag.matches:
                out.append("  no troubleshooting entry: diagnose from the CLAUDE.md "
                           "rules and the object database; never invent console wording")
            for fact in diag.facts:
                out.append("  fact: " + fact)
            for hit in diag.hits:
                reason = hit.reason
                if hit.code_lines:
                    reason += "; lines " + ", ".join(str(n) for n in hit.code_lines)
                out.append("  box: %s %s%s [%s] (%s)"
                           % (hit.file, hit.where, hit.box_id, hit.label, reason))
            if diag.hits_omitted:
                out.append("  ... and %d more box(es)" % diag.hits_omitted)
            if diag.proposal:
                out.append("  propose: " + diag.proposal)
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def _depth0_code_spans(cell: str) -> tuple[str, ...]:
    """Code spans of *cell* outside parentheses (counted outside spans)."""
    spans = []
    depth = 0
    i = 0
    n = len(cell)
    while i < n:
        ch = cell[i]
        if ch == "`":
            end = cell.find("`", i + 1)
            if end < 0:
                break
            if depth == 0:
                span = cell[i + 1:end].strip()
                if span:
                    spans.append(span)
            i = end + 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")" and depth > 0:
            depth -= 1
        i += 1
    return tuple(spans)


def load_troubleshooting(path: str | Path | None = None) -> list[TroubleEntry]:
    """Parse the troubleshooting.md tables into entries, in file order.

    Raises FileNotFoundError when the file is missing. Rows without exactly
    four cells are skipped.
    """
    target = Path(path) if path is not None else TROUBLESHOOTING_PATH
    text = target.read_text(encoding="utf-8")
    entries: list[TroubleEntry] = []
    section = ""
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("|") or line.startswith("|---"):
            continue
        inner = line[1:]
        if inner.endswith("|"):
            inner = inner[:-1]
        cells = [c.strip() for c in inner.split(" | ")]
        if len(cells) != 4:
            continue
        if cells[0] == "Console message":
            continue
        entries.append(TroubleEntry(
            section=section,
            message=cells[0],
            patterns=_depth0_code_spans(cells[0]),
            cause=cells[1],
            fix=cells[2],
            source=cells[3],
            row=lineno,
        ))
    return entries


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------


def normalize_console_line(line: str) -> str:
    """Drop double quotes, collapse whitespace, collapse ``X: X: `` to ``X: ``."""
    text = " ".join(str(line).translate({34: None}).split())
    while True:
        new = re.sub(r"^(\S+): \1: ", r"\1: ", text)
        if new == text:
            return text
        text = new


def _compile_template(template: str, quoted_any: bool):
    """Regex, capture names and literal character count for *template*.

    ``<x>`` -> ``(\\S+)`` named x; ``...`` -> ``.*?`` (dropped at either
    end, where it matches nothing anyway); with *quoted_any* each quoted
    literal becomes ``'([^']+)'`` named ``identifier``.
    """
    parts = [p for p in _TEMPLATE_TOKEN_RE.split(template) if p]
    while parts and parts[0] == "...":
        parts.pop(0)
    while parts and parts[-1] == "...":
        parts.pop()
    regex: list[str] = []
    names: list[str] = []
    literal = 0
    for idx, part in enumerate(parts):
        if part == "...":
            regex.append(".*?")
        elif _PLACEHOLDER_RE.fullmatch(part):
            if idx == 0:
                regex.append(r"(?<!\S)")  # anchor at a token start (linear search)
            regex.append(r"(\S+)")
            names.append(part[1:-1])
        elif quoted_any:
            pos = 0
            for qm in _QUOTED_RE.finditer(part):
                chunk = part[pos:qm.start()]
                regex.append(re.escape(chunk))
                regex.append("'([^']+)'")
                names.append("identifier")
                literal += len(chunk) + 2
                pos = qm.end()
            regex.append(re.escape(part[pos:]))
            literal += len(part) - pos
        else:
            regex.append(re.escape(part))
            literal += len(part)
    if not regex:
        return None
    return re.compile("".join(regex), re.IGNORECASE), tuple(names), literal


_VARIANT_CACHE: dict[str, tuple] = {}


def _variants(pattern: str) -> tuple:
    """``(tier, regex, names, literal)`` variants of one pattern (cached)."""
    cached = _VARIANT_CACHE.get(pattern)
    if cached is not None:
        return cached
    out = []
    exact = _compile_template(pattern, False)
    if exact:
        out.append(("exact",) + exact)
    if _QUOTED_RE.search(pattern):
        anyid = _compile_template(pattern, True)
        if anyid:
            out.append(("any-identifier",) + anyid)
    prefix = _PREFIX_RE.match(pattern)
    if prefix and pattern[prefix.end():].strip():
        bare = _compile_template(pattern[prefix.end():], False)
        if bare:
            out.append(("no-prefix",) + bare)
    result = tuple(out)
    _VARIANT_CACHE[pattern] = result
    return result


def match_line(line: str, entries: list[TroubleEntry]) -> list[EntryMatch]:
    """Matches of one console line, best tier only, best score first."""
    text = normalize_console_line(line)
    if not text:
        return []
    best: dict[int, EntryMatch] = {}
    for idx, entry in enumerate(entries):
        for pattern in entry.patterns:
            for tier, regex, names, literal in _variants(pattern):
                found = regex.search(text)
                if found is None:
                    continue
                score = TIER_BONUS[tier] + literal
                current = best.get(idx)
                if current is None or score > current.score:
                    best[idx] = EntryMatch(
                        entry=entry,
                        pattern=pattern,
                        tier=tier,
                        score=score,
                        captures=tuple(zip(names, found.groups())),
                    )
    if not best:
        return []
    top_bonus = max(TIER_BONUS[m.tier] for m in best.values())
    kept = [m for m in best.values() if TIER_BONUS[m.tier] == top_bonus]
    kept.sort(key=lambda m: (-m.score, m.entry.row))
    return kept


# ---------------------------------------------------------------------------
# Locate
# ---------------------------------------------------------------------------


def _patch_files(project_dir: Path) -> list[tuple[str, Path]]:
    root = Path(project_dir)
    found = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.startswith("__maxbridge_"):
                continue
            if not name.endswith(PATCH_SUFFIXES):
                continue
            full = Path(dirpath) / name
            found.append((full.relative_to(root).as_posix(), full))
    return found


def _load(project_dir: Path, cache: dict) -> list[tuple[str, dict]]:
    """Parsed patch files of the project; reasons for unreadable ones go
    into *cache* as str values."""
    root = Path(project_dir).resolve()
    loaded = []
    for rel, full in _patch_files(project_dir):
        if rel not in cache:
            try:
                resolved = full.resolve()
                if resolved != root and root not in resolved.parents:
                    cache[rel] = "outside the project"
                else:
                    data = json.loads(full.read_text(encoding="utf-8"))
                    cache[rel] = data if isinstance(data, dict) else "not a JSON object"
            except (OSError, UnicodeDecodeError, ValueError) as exc:
                cache[rel] = type(exc).__name__
        value = cache[rel]
        if isinstance(value, dict):
            loaded.append((rel, value))
    return loaded


def _label(box) -> str:
    text = walk.box_text(box) if walk.box_maxclass(box) == "newobj" else ""
    label = " ".join(text.split()) or walk.box_label(box)
    if len(label) > 40:
        label = label[:37] + "..."
    return label


def _iter_boxes(files: list[tuple[str, dict]]):
    for rel, data in files:
        try:
            for path, patcher, context in walk.iter_patchers(data):
                boxes = patcher.get("boxes")
                if not isinstance(boxes, list):
                    continue
                where = walk.path_prefix(path)
                for entry in boxes:
                    box = entry.get("box") if isinstance(entry, dict) else None
                    if isinstance(box, dict):
                        yield rel, where, context, box
        except Exception:  # malformed structure yields less, never raises
            continue


def _hit(rel, where, box, reason, lines=()) -> BoxHit:
    box_id = box.get("id")
    return BoxHit(
        file=rel,
        where=where,
        box_id=str(box_id) if box_id is not None else "?",
        label=_label(box),
        reason=reason,
        code_lines=tuple(lines),
    )


def locate_boxes(project_dir, *, objects=(), identifiers=(), gen_fallback=False,
                 cache=None) -> tuple[list[BoxHit], list[str]]:
    """Boxes in *project_dir* that a console line points at (read-only).

    Order: object hits (``walk.object_name`` in *objects*); if none,
    argument hits (a newobj argument token in *objects*); code hits (a
    gen-context box whose str ``code`` contains an identifier as a word,
    with 1-based line numbers); if *gen_fallback* and no code hits, gen
    containers and codeboxes. Returns ``(hits, skipped)`` where *skipped*
    lists ``"<rel> (<reason>)"`` for unreadable files. *cache* (a dict)
    is reused across calls so every file is read once.
    """
    if cache is None:
        cache = {}
    files = _load(Path(project_dir), cache)
    skipped = ["%s (%s)" % (rel, value) for rel, value in sorted(cache.items())
               if isinstance(value, str)]
    objects = tuple(o for o in objects if o)
    identifiers = tuple(i for i in identifiers if i)
    hits: list[BoxHit] = []

    if objects:
        wanted = set(objects)
        for rel, where, _ctx, box in _iter_boxes(files):
            if walk.object_name(box) in wanted:
                hits.append(_hit(rel, where, box, "object"))
        if not hits:
            for rel, where, _ctx, box in _iter_boxes(files):
                if walk.box_maxclass(box) != "newobj":
                    continue
                if wanted.intersection(walk.box_args(box)):
                    hits.append(_hit(rel, where, box, "argument"))

    code_hits: list[BoxHit] = []
    if identifiers:
        regexes = [re.compile(r"\b%s\b" % re.escape(i)) for i in identifiers]
        for rel, where, ctx, box in _iter_boxes(files):
            code = box.get("code")
            if ctx != "gen" or not isinstance(code, str):
                continue
            lines = [n for n, text in enumerate(code.splitlines(), 1)
                     if any(r.search(text) for r in regexes)]
            if lines:
                code_hits.append(_hit(rel, where, box, "code", lines))
    hits.extend(code_hits)

    if gen_fallback and not code_hits:
        for rel, where, _ctx, box in _iter_boxes(files):
            if walk.is_gen_container(box) or isinstance(box.get("code"), str):
                hits.append(_hit(rel, where, box, "gen container"))
    return hits, skipped


# ---------------------------------------------------------------------------
# Diagnose
# ---------------------------------------------------------------------------


def _first_sentence(text: str) -> str:
    return _SENTENCE_END_RE.split(text.strip(), maxsplit=1)[0]


def _unique(items) -> tuple[str, ...]:
    seen: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.append(item)
    return tuple(seen)


def _facts(db, names) -> tuple[str, ...]:
    facts = []
    for name in names:
        try:
            obj = db.lookup(name)
            if obj is None:
                if db.is_pd_object(name):
                    facts.append("%s: Pure Data name, not MAX; MAX equivalent %s"
                                 % (name, db.get_pd_equivalent(name)))
                else:
                    facts.append("%s: not in the object database" % name)
                continue
            restrictions = db.get_effective_restrictions(name)
            if restrictions:
                facts.append("%s: only valid inside %s (domain %s)"
                              % (name, ", ".join(restrictions), obj.get("domain")))
        except Exception:
            continue
    return tuple(facts)


def diagnose_console(text: str, project_dir=None, *, db=None,
                     entries=None) -> DiagnoseReport:
    """Diagnose pasted console *text* against troubleshooting.md.

    *project_dir* (``patches/<project>``) enables box locating; *db* (an
    ObjectDatabase) adds object facts; *entries* defaults to
    :func:`load_troubleshooting`. Read-only.
    """
    if entries is None:
        entries = load_troubleshooting()
    raw_lines = str(text or "").splitlines()
    truncated = len(raw_lines) > MAX_LINES
    raw_lines = raw_lines[:MAX_LINES]
    counts: dict[str, int] = {}
    for raw in raw_lines:
        line = normalize_console_line(raw[:MAX_LINE_CHARS])
        if line:
            counts[line] = counts.get(line, 0) + 1

    project_dir = Path(project_dir) if project_dir is not None else None
    project = project_dir.name if project_dir is not None else None
    cache: dict = {}
    if project_dir is not None:
        locate_boxes(project_dir, cache=cache)

    diagnoses = []
    for line, count in counts.items():
        matches = match_line(line, entries)
        gen_mode = bool(matches) and matches[0].entry.section == GEN_SECTION
        objects: tuple[str, ...] = ()
        identifiers: tuple[str, ...] = ()
        if gen_mode:
            identifiers = _unique(
                [v for m in matches for k, v in m.captures if k in ("name", "identifier")]
                + _QUOTED_RE.findall(line)
            )
        else:
            objects = _unique(v for m in matches for k, v in m.captures if k == "objectname")
            if not objects:
                lead = _LEADING_TOKEN_RE.match(line)
                if lead:
                    objects = (lead.group(1),)

        hits: list[BoxHit] = []
        if project_dir is not None:
            hits, _ = locate_boxes(project_dir, objects=objects,
                                   identifiers=identifiers,
                                   gen_fallback=gen_mode, cache=cache)
        facts = _facts(db, objects) if (db is not None and not gen_mode) else ()

        proposal = None
        if matches:
            proposal = "/max-iterate "
            if project:
                proposal += project + " "
            proposal += 'fix "%s"' % line
            if hits:
                h = hits[0]
                proposal += " at %s %s%s [%s]" % (h.file, h.where, h.box_id, h.label)
            proposal += ": " + _first_sentence(matches[0].entry.fix)

        diagnoses.append(Diagnosis(
            line=line,
            count=count,
            matches=tuple(matches),
            objects=objects,
            identifiers=identifiers,
            hits=tuple(hits[:MAX_HITS]),
            hits_omitted=max(0, len(hits) - MAX_HITS),
            facts=facts,
            proposal=proposal,
        ))

    files: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()
    if project_dir is not None:
        files = tuple(sorted(rel for rel, v in cache.items() if isinstance(v, dict)))
        skipped = tuple("%s (%s)" % (rel, v) for rel, v in sorted(cache.items())
                        if isinstance(v, str))
    return DiagnoseReport(project=project, files=files, skipped=skipped,
                          diagnoses=diagnoses, truncated=truncated)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _valid_name(name: str) -> bool:
    return bool(name) and name not in (".", "..") and not any(
        c in name for c in ("/", "\\", "\0"))


def main(argv=None) -> int:
    """CLI: ``python3 -m src.maxpat.diagnose [--project NAME] [FILE|-]``."""
    parser = argparse.ArgumentParser(
        prog="python3 -m src.maxpat.diagnose",
        description="Map MAX console lines to troubleshooting.md entries and "
                    "locate the boxes (read-only).")
    parser.add_argument("file", nargs="?", default="-",
                        help="file holding the console text, or - for stdin")
    parser.add_argument("--project", help="project name under patches/")
    parser.add_argument("--base-dir", default=None,
                        help="repo root holding patches/ (default: cwd)")
    parser.add_argument("--no-db", action="store_true",
                        help="skip the object-database facts")
    args = parser.parse_args(argv)

    base_dir = Path(args.base_dir) if args.base_dir else Path.cwd()
    project_dir = None
    if args.project is not None:
        name = args.project
        if not _valid_name(name) or not (base_dir / "patches" / name).is_dir():
            print("diagnose: no project %r under %s" % (name, base_dir / "patches"),
                  file=sys.stderr)
            return 2
        project_dir = base_dir / "patches" / name
    else:
        from src.maxpat.project import get_active_project

        active = get_active_project(base_dir)
        if active is not None:
            project_dir = base_dir / "patches" / active["name"]

    try:
        if args.file == "-":
            text = sys.stdin.read()
        else:
            text = Path(args.file).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print("diagnose: cannot read %s: %s" % (args.file, exc), file=sys.stderr)
        return 2

    db = None
    if not args.no_db:
        from src.maxpat.db_lookup import ObjectDatabase

        db = ObjectDatabase()
    report = diagnose_console(text, project_dir, db=db)
    print(report.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
