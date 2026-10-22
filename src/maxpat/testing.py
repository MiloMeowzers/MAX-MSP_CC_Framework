"""Manual test checklist generation from patch structure.

Bridges automated validation and manual MAX testing by generating
step-by-step checklists based on the objects found in a patch.

The object names come from every non-gen scope of ``walk.iter_patchers``
(top level and every embedded ``p`` / bpatcher / poly~ / rnbo~ patcher;
GenExpr operators are not Max objects), and from object boxes only:
comment and message text never counts (G10, Q20).

Test-results flow: :func:`save_test_results` writes
``test-results/<test_name>.md`` and overwrites a same-named file, so callers
name checklist results ``v<version>-<slug>-checklist``.

Confirmations (Q37): when the user confirms in MAX that a feature works,
:func:`record_confirmation` writes
``test-results/v<version>-<slug>-confirmed.md`` (``<date>-<slug>-...`` for
an unversioned project). It never overwrites (``-2``, ``-3``, ...), rejects
private paths and files outside the project, and commits only that path
through ``hooks._auto_commit_saved_file`` (the Rule #7 path-scoped policy).

Proven-forms entries (Q37): :func:`parse_proven_forms`,
:func:`format_proven_form` and :func:`append_proven_form` read and extend
``.claude/skills/references/proven-forms.md``. An entry is a ``###`` title
with ``- **Rule:**``, ``- **Form:**``, ``- **Why:**`` and ``- Evidence:``
lines; its evidence carries tiers from :data:`PROVEN_TIERS` (``[confirmed]``
needs a version and a date). Appending is a separate, user-consented step;
the caller commits the file by explicit path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date as _date
from pathlib import Path

from src.maxpat import walk
from src.maxpat.atomic_io import atomic_write_bytes

PROVEN_TIERS = ("confirmed", "bundle", "code", "observed")
PROVEN_FORMS_PATH = (
    Path(__file__).resolve().parents[2]
    / ".claude" / "skills" / "references" / "proven-forms.md"
)


def generate_test_checklist(
    patch_dict: dict, patch_name: str, patch_path: str = ""
) -> str:
    """Generate a markdown test checklist from a patch dictionary.

    Scans every non-gen scope of the patch for object types (object boxes
    only; comments and messages are ignored) and builds relevant manual
    test steps.
    Each step has a numbered item, descriptive name, action, and expected result
    with Pass/Fail checkboxes.

    Args:
        patch_dict: A .maxpat-style dict with patcher.boxes.
        patch_name: Human-readable name for the test checklist.
        patch_path: Optional file path for the setup section.

    Returns:
        Complete markdown string with numbered test steps.
    """
    object_names = _extract_object_names(patch_dict)

    has_signal = any(name.endswith("~") for name in object_names)
    has_dac = any(name in ("dac~", "ezdac~") for name in object_names)
    has_midi = any(name in ("notein", "midiin", "ctlin", "pgmin", "bendin") for name in object_names)
    has_toggle = "toggle" in object_names
    has_button = "button" in object_names
    has_gen = "gen~" in object_names
    has_number = any(name in ("number", "flonum") for name in object_names)
    has_metro = any(name.startswith("metro") for name in object_names)

    lines: list[str] = []
    lines.append(f"# Test Checklist: {patch_name}")
    lines.append("")

    # Setup section
    lines.append("## Setup")
    lines.append("")
    if patch_path:
        lines.append(f"1. Open `{patch_path}` in MAX")
    else:
        lines.append(f"1. Open the patch in MAX")
    if has_signal:
        lines.append("2. Turn on audio (Audio Status -> Audio On)")
    lines.append("")

    # Test steps
    lines.append("## Tests")
    lines.append("")
    step = 1

    if has_dac:
        lines.append(f"### {step}. Audio Output")
        lines.append("")
        lines.append(f"- **Action:** Toggle audio on. Verify sound comes from speakers/headphones.")
        lines.append(f"- **Expected:** Audio signal audible at safe volume level.")
        lines.append(f"- [ ] Pass  [ ] Fail")
        lines.append("")
        step += 1

    if has_midi:
        lines.append(f"### {step}. MIDI Input")
        lines.append("")
        lines.append(f"- **Action:** Play a MIDI note from controller or virtual keyboard.")
        lines.append(f"- **Expected:** Pitch change or note value displayed downstream.")
        lines.append(f"- [ ] Pass  [ ] Fail")
        lines.append("")
        step += 1

    if has_toggle:
        lines.append(f"### {step}. Toggle Interaction")
        lines.append("")
        lines.append(f"- **Action:** Click the toggle to change its state.")
        lines.append(f"- **Expected:** State change propagates to downstream objects.")
        lines.append(f"- [ ] Pass  [ ] Fail")
        lines.append("")
        step += 1

    if has_button:
        lines.append(f"### {step}. Button Click")
        lines.append("")
        lines.append(f"- **Action:** Click the button to send a bang.")
        lines.append(f"- **Expected:** Downstream objects trigger correctly.")
        lines.append(f"- [ ] Pass  [ ] Fail")
        lines.append("")
        step += 1

    if has_gen:
        lines.append(f"### {step}. gen~ Processing")
        lines.append("")
        lines.append(f"- **Action:** Enable audio and verify gen~ processes signal correctly.")
        lines.append(f"- **Expected:** gen~ output matches expected DSP behavior.")
        lines.append(f"- [ ] Pass  [ ] Fail")
        lines.append("")
        step += 1

    if has_number:
        lines.append(f"### {step}. Number Box Input")
        lines.append("")
        lines.append(f"- **Action:** Double-click number box and type a value. Press Enter.")
        lines.append(f"- **Expected:** Value propagates to connected objects.")
        lines.append(f"- [ ] Pass  [ ] Fail")
        lines.append("")
        step += 1

    if has_metro:
        lines.append(f"### {step}. Metro Timing")
        lines.append("")
        lines.append(f"- **Action:** Turn on metro (connect toggle or send bang).")
        lines.append(f"- **Expected:** Regular bangs at specified interval.")
        lines.append(f"- [ ] Pass  [ ] Fail")
        lines.append("")
        step += 1

    # Always include a basic "open and inspect" test
    if step == 1:
        # Empty or unrecognized patch -- minimal checklist
        lines.append(f"### {step}. Open and Inspect")
        lines.append("")
        lines.append(f"- **Action:** Open patch in MAX. Verify it loads without errors.")
        lines.append(f"- **Expected:** Patch opens cleanly, no error messages in console.")
        lines.append(f"- [ ] Pass  [ ] Fail")
        lines.append("")

    return "\n".join(lines)


def save_test_results(
    project_dir: Path, test_name: str, results_md: str
) -> Path:
    """Write test results to the project's test-results/ directory.

    Args:
        project_dir: Path to the project directory.
        test_name: Name for the test results file (without extension).
        results_md: Markdown content to write.

    Returns:
        Path to the written file.
    """
    results_dir = project_dir / "test-results"
    results_dir.mkdir(parents=True, exist_ok=True)

    result_path = results_dir / f"{test_name}.md"
    result_path.write_text(results_md)

    return result_path


def _extract_object_names(patch_dict) -> list[str]:
    """Object names of every object box in every non-gen scope (G10, Q20).

    Walks ``walk.iter_patchers(patch_dict)`` and skips gen-context scopes.
    Boxes whose maxclass is ``comment`` or ``message`` are ignored; every
    other box contributes ``walk.object_name(box)`` (a newobj's first
    token, else its maxclass), skipped when None (structural or empty).
    Empty, whitespace-only and non-str text never raises.
    """
    names: list[str] = []
    for _path, patcher, context in walk.iter_patchers(patch_dict):
        if context == "gen":
            continue
        boxes = patcher.get("boxes")
        for entry in boxes if isinstance(boxes, list) else ():
            box = entry.get("box") if isinstance(entry, dict) else None
            if not isinstance(box, dict):
                continue
            if walk.box_maxclass(box) in ("comment", "message"):
                continue
            name = walk.object_name(box)
            if name:
                names.append(name)
    return names


# ---------------------------------------------------------------------------
# Confirmations (Q37)
# ---------------------------------------------------------------------------

_MEMORY_NOTE_RE = re.compile(r"\b(feedback|project|reference)_[a-z0-9_]+\.md\b")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _private_path_findings(text: str) -> list[str]:
    """Private-path findings in *text*: ``/Users/``, ``/home/``,
    ``.planning/``, ``~/.claude`` and memory-note filenames (the
    tests/test_claude_md.py rule plus ``/home/`` and ``~/.claude``)."""
    text = str(text or "")
    found = []
    for marker in ("/Users/", "/home/", ".planning/", "~/.claude"):
        if marker in text:
            found.append(f"{marker} path")
    found += [f"memory-note filename {m.group(0)}" for m in _MEMORY_NOTE_RE.finditer(text)]
    return found


def _slug(text: str) -> str:
    """Lowercase ``[a-z0-9-]`` slug of at most 48 characters (``feature``
    when nothing is left)."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    slug = slug[:48].strip("-")
    return slug or "feature"


def record_confirmation(
    project_dir: Path,
    feature: str,
    evidence: str,
    *,
    version: str | None = None,
    max_version: str | None = None,
    files: list | None = None,
    lesson: str | None = None,
    date: str | None = None,
    commit: bool = True,
) -> Path:
    """Record that the user confirmed *feature* working in MAX (Q37).

    Writes ``test-results/v<version>-<slug>-confirmed.md`` (or
    ``<date>-<slug>-confirmed.md`` when the project has no versions.json)
    and never overwrites: a collision adds ``-2``, ``-3``, ... before
    ``.md``. Everything is validated before any write:

    - *project_dir* must be an existing directory (FileNotFoundError);
    - *feature*: non-empty, one line, at most 200 characters; *evidence*
      (the user's own words): non-empty;
    - *version* defaults to ``project.get_version(project_dir)`` and must be
      ``N.N.N`` (a leading ``v`` is accepted); *date* defaults to today and
      must be ``YYYY-MM-DD``;
    - every *files* entry must resolve inside *project_dir* and exist; it is
      stored relative to the project;
    - feature, evidence, lesson and max_version must hold no private path
      (``/Users/``, ``/home/``, ``.planning/``, ``~/.claude``, memory-note
      filenames).

    With *commit* the file is committed through
    ``hooks._auto_commit_saved_file``: only that path, warning (never
    raising) when it cannot commit.

    Returns:
        Path of the written confirmation file.
    """
    project_dir = Path(project_dir)
    if not project_dir.is_dir():
        raise FileNotFoundError(f"project directory not found: {project_dir}")

    feature = str(feature or "").strip()
    if not feature:
        raise ValueError("feature must be non-empty")
    if "\n" in feature or "\r" in feature:
        raise ValueError("feature must be a single line")
    if len(feature) > 200:
        raise ValueError("feature must be at most 200 characters")
    evidence = str(evidence or "").strip()
    if not evidence:
        raise ValueError("evidence must be non-empty (the user's own words)")
    if max_version is not None and ("\n" in str(max_version) or "\r" in str(max_version)):
        raise ValueError("max_version must be a single line")
    if lesson is not None and ("\n" in str(lesson) or "\r" in str(lesson)):
        raise ValueError("lesson must be a single line")

    if version is None:
        from src.maxpat.project import get_version

        try:
            version = get_version(project_dir)
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"cannot read versions.json: {exc}") from exc
    if version is not None:
        version = str(version).strip()
        if version.startswith("v"):
            version = version[1:]
        if not _VERSION_RE.match(version):
            raise ValueError(f"version must be N.N.N, got {version!r}")

    if date is None:
        date = _date.today().isoformat()
    date = str(date)
    if not _DATE_RE.match(date):
        raise ValueError(f"date must be YYYY-MM-DD, got {date!r}")

    root = project_dir.resolve()
    rel_files = []
    for entry in files or ():
        candidate = Path(entry)
        if not candidate.is_absolute():
            candidate = project_dir / candidate
        resolved = candidate.resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError(f"file outside the project: {entry}")
        if not resolved.exists():
            raise ValueError(f"file not found: {entry}")
        rel_files.append(resolved.relative_to(root).as_posix())

    findings = []
    for value in (feature, evidence, lesson, max_version):
        if value:
            findings += _private_path_findings(str(value))
    if findings:
        raise ValueError("private paths are not allowed: " + ", ".join(findings))

    slug = _slug(feature)
    stem = f"v{version}-{slug}-confirmed" if version else f"{date}-{slug}-confirmed"
    results_dir = project_dir / "test-results"
    target = results_dir / f"{stem}.md"
    n = 2
    while target.exists():
        target = results_dir / f"{stem}-{n}.md"
        n += 1

    lines = [
        f"# Confirmed in MAX: {feature}",
        "",
        f"- Project: {project_dir.name}",
        f"- Version: v{version}" if version else "- Version: unversioned",
        f"- Date: {date}",
        f"- MAX: {str(max_version).strip() if max_version else 'not recorded'}",
        "- Files: " + (", ".join(f"`{f}`" for f in rel_files) if rel_files else "none listed"),
        "- Proven-forms lesson: " + (str(lesson).strip() if lesson else "none proposed"),
        "",
        "## Evidence",
        "",
        evidence,
        "",
    ]
    results_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(target, "\n".join(lines).encode("utf-8"))

    if commit:
        from src.maxpat.hooks import _auto_commit_saved_file

        _auto_commit_saved_file(target)
    return target


# ---------------------------------------------------------------------------
# Proven-forms entries (Q37)
# ---------------------------------------------------------------------------

_FIELD_PREFIXES = (
    ("rule", "- **Rule:**"),
    ("form", "- **Form:**"),
    ("why", "- **Why:**"),
    ("evidence", "- Evidence:"),
)
_TAG_RE = re.compile(r"\[([a-z][a-z-]*)\]")


@dataclass(frozen=True)
class ProvenForm:
    """One proven-forms.md entry (``###`` title plus its four fields)."""

    section: str
    title: str
    rule: str
    form: str
    why: str
    evidence: str
    tiers: tuple[str, ...]


def _tiers(evidence: str) -> tuple[str, ...]:
    out: list[str] = []
    for tag in _TAG_RE.findall(evidence):
        if tag in PROVEN_TIERS and tag not in out:
            out.append(tag)
    return tuple(out)


def parse_proven_forms(text: str) -> list[ProvenForm]:
    """Entries of a proven-forms.md text, in file order.

    ``## `` lines set the section, each ``### `` starts an entry. A field is
    its ``- **Rule:**`` / ``- **Form:**`` / ``- **Why:**`` / ``- Evidence:``
    line plus the following indented lines (stripped), joined with
    newlines; a missing field is ``""``.
    """
    entries: list[ProvenForm] = []
    section = ""
    current: dict | None = None
    field_name: str | None = None

    def close():
        if current is not None:
            fields = {k: "\n".join(v).strip() for k, v in current["fields"].items()}
            ev = fields.get("evidence", "")
            entries.append(ProvenForm(
                section=current["section"],
                title=current["title"],
                rule=fields.get("rule", ""),
                form=fields.get("form", ""),
                why=fields.get("why", ""),
                evidence=ev,
                tiers=_tiers(ev),
            ))

    for line in str(text).splitlines():
        if line.startswith("## "):
            close()
            current, field_name = None, None
            section = line[3:].strip()
            continue
        if line.startswith("### "):
            close()
            current = {"section": section, "title": line[4:].strip(), "fields": {}}
            field_name = None
            continue
        if current is None:
            continue
        matched = False
        for name, prefix in _FIELD_PREFIXES:
            if line.startswith(prefix):
                rest = line[len(prefix):].strip()
                current["fields"][name] = [rest] if rest else []
                field_name = name
                matched = True
                break
        if matched:
            continue
        if field_name and line[:1].isspace() and line.strip():
            current["fields"][field_name].append(line.strip())
        else:
            field_name = None
    close()
    return entries


def _check_line(name: str, value) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    value = value.strip()
    if not value:
        raise ValueError(f"{name} must be non-empty")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{name} must be a single line")
    if value.startswith("#"):
        raise ValueError(f"{name} must not start with '#'")
    if "<!--" in value:
        raise ValueError(f"{name} must not contain '<!--'")
    findings = _private_path_findings(value)
    if findings:
        raise ValueError(f"{name} holds private paths: " + ", ".join(findings))
    return value


def format_proven_form(title: str, rule: str, form, why: str, evidence: str) -> str:
    """Validated markdown block for one proven-forms.md entry.

    title, rule, why and evidence (and *form*, a str or a list of str) must
    be single-line, non-empty, not start with ``#``, hold no ``<!--`` and no
    private path. The evidence needs at least one tier from
    :data:`PROVEN_TIERS`, every ``[lowercase-word]`` tag in it must be a
    tier, and every ``[confirmed]`` clause (up to the next ``;``) must name
    a version (``vN.N``) and a date (``YYYY-MM-DD``). A list *form* renders
    as nested ``  - item`` lines.
    """
    title = _check_line("title", title)
    rule = _check_line("rule", rule)
    why = _check_line("why", why)
    evidence = _check_line("evidence", evidence)
    if isinstance(form, (list, tuple)):
        if not form:
            raise ValueError("form list must be non-empty")
        items = [_check_line("form item", item) for item in form]
        form_text = "- **Form:**\n" + "\n".join(f"  - {item}" for item in items)
    else:
        form_text = "- **Form:** " + _check_line("form", form)

    tags = _TAG_RE.findall(evidence)
    unknown = [t for t in tags if t not in PROVEN_TIERS]
    if unknown:
        raise ValueError(f"unknown evidence tier(s) {unknown}; use {list(PROVEN_TIERS)}")
    if not _tiers(evidence):
        raise ValueError(f"evidence needs a tier: one of {list(PROVEN_TIERS)}")
    for clause in re.findall(r"\[confirmed\]([^;]*)", evidence):
        if not re.search(r"v\d+\.\d+", clause) or not re.search(r"\d{4}-\d{2}-\d{2}", clause):
            raise ValueError("[confirmed] evidence needs a version (vN.N) and a date "
                             "(YYYY-MM-DD) in its clause")
    return (f"### {title}\n\n- **Rule:** {rule}\n{form_text}\n"
            f"- **Why:** {why}\n- Evidence: {evidence}\n")


def append_proven_form(
    section: str,
    title: str,
    rule: str,
    form,
    why: str,
    evidence: str,
    *,
    path: Path | None = None,
    create_section: bool = False,
) -> Path:
    """Append a validated entry at the end of ``## <section>`` (Q37).

    *path* defaults to :data:`PROVEN_FORMS_PATH`. The block comes from
    :func:`format_proven_form` (which validates). Refused with ValueError:
    the ``Evidence tiers`` section, a title equal to an existing one
    (case-insensitive, any section), and an unknown section unless
    *create_section* (then ``## <section>`` is appended at the end of the
    file). Every existing line stays unchanged; the entry is inserted with
    one blank line before it and the section's trailing spacing kept after
    it. The write is atomic, then the file is re-parsed: a missing or
    incomplete entry restores the original bytes and raises RuntimeError.

    Never commits: the caller commits the file by explicit path
    (``git commit -- .claude/skills/references/proven-forms.md``) after the
    user consents.
    """
    target = Path(path) if path is not None else PROVEN_FORMS_PATH
    section = _check_line("section", section)
    if section.lower() == "evidence tiers":
        raise ValueError("the 'Evidence tiers' section takes no entries")
    original = target.read_bytes()
    text = original.decode("utf-8")
    block = format_proven_form(title, rule, form, why, evidence)
    title = title.strip()

    existing = parse_proven_forms(text)
    if any(e.title.lower() == title.lower() for e in existing):
        raise ValueError(f"an entry titled {title!r} already exists")

    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    headings = [i for i, line in enumerate(lines) if line.startswith("## ")]
    sections = [lines[i][3:].strip() for i in headings]
    block_lines = block.splitlines(keepends=True)
    if section in sections:
        start = headings[sections.index(section)]
        end = next((i for i in headings if i > start), len(lines))
        insert_at = end
        while insert_at - 1 > start and not lines[insert_at - 1].strip():
            insert_at -= 1
        new_lines = lines[:insert_at] + ["\n"] + block_lines + lines[insert_at:]
    elif create_section:
        new_lines = lines + ["\n", f"## {section}\n", "\n"] + block_lines
    else:
        raise ValueError(f"unknown section {section!r}; existing sections: "
                         + ", ".join(s for s in sections if s != "Evidence tiers"))

    atomic_write_bytes(target, "".join(new_lines).encode("utf-8"))
    parsed = parse_proven_forms(target.read_text(encoding="utf-8"))
    ok = [e for e in parsed if e.title == title and e.section == section
          and e.rule and e.form and e.why and e.evidence and e.tiers]
    if len(ok) != 1:
        atomic_write_bytes(target, original)
        raise RuntimeError("appended entry did not re-parse; the file was restored")
    return target
