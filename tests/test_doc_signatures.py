"""Doc call-form checker and documentation regression guards (Q16).

Agents copy the call forms they read in CLAUDE.md, TECHNICAL.md, the skills and
the commands literally, so a documented form that raises becomes a broken build.
This module extracts Python call snippets of public ``src.maxpat`` API names from
those docs and binds each one against ``inspect.signature``:

- keyword names and positional arity (``bind_partial`` with dummy objects);
- a positional bare name that is the name of a *different* parameter of the
  same signature (e.g. ``db`` landing on ``box_id``);
- an obvious type mismatch (a Box or Patcher passed where ``str`` or ``dict``
  is annotated).

Listings written as parameter lists (``write_gendsp(code, path, ..., *,
force=False)``) are checked in "def mode": every listed parameter must exist.

The guard tests below lock the Q16 doc fixes (review findings J1-J4, J6-J13).
"""

from __future__ import annotations

import ast
import functools
import importlib
import inspect
import re
from pathlib import Path

import pytest

# ── Doc file set ───────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[1]


def _doc_files() -> list[Path]:
    files = [
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "TECHNICAL.md",
        REPO_ROOT / "README.md",
        REPO_ROOT / "patterns" / "gen" / "INDEX.md",
    ]
    files += list((REPO_ROOT / ".claude" / "skills").rglob("*.md"))
    files += list((REPO_ROOT / ".claude" / "commands").glob("*.md"))
    return sorted(p.relative_to(REPO_ROOT) for p in files if p.is_file())


DOC_FILES: list[Path] = _doc_files()


def _read(rel: Path) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


# ── API index ──────────────────────────────────────────────────────

_INDEX_MODULES = (
    "src.maxpat",
    "src.maxpat.project",
    "src.maxpat.critics",
    "src.maxpat.hooks",
    "src.maxpat.layout",
    "src.maxpat.aesthetics",
    "src.maxpat.memory",
    "src.maxpat.testing",
    "src.maxpat.m4l_polish",
)


def _safe_signature(obj) -> inspect.Signature | None:
    try:
        return inspect.signature(obj)
    except (TypeError, ValueError):
        return None


def _method_signatures(cls) -> dict[str, inspect.Signature]:
    out: dict[str, inspect.Signature] = {}
    for name in dir(cls):
        if name.startswith("_"):
            continue
        static = inspect.getattr_static(cls, name)
        if isinstance(static, property):
            continue
        attr = getattr(cls, name)
        if not callable(attr):
            continue
        sig = _safe_signature(attr)
        if sig is None:
            continue
        if inspect.isfunction(attr) and not isinstance(static, staticmethod):
            params = list(sig.parameters.values())[1:]  # drop self
            sig = sig.replace(parameters=params)
        out[name] = sig
    return out


@functools.lru_cache(maxsize=1)
def _api_index() -> dict[str, dict[str, inspect.Signature]]:
    """Return {"module": {...}, "patcher": {...}, "db": {...}} signature maps."""
    module_sigs: dict[str, inspect.Signature] = {}
    for modname in _INDEX_MODULES:
        mod = importlib.import_module(modname)
        for name, obj in vars(mod).items():
            if name.startswith("_"):
                continue
            if not (inspect.isfunction(obj) or inspect.isclass(obj)):
                continue
            if not getattr(obj, "__module__", "").startswith("src.maxpat"):
                continue
            sig = _safe_signature(obj)
            if sig is not None:
                module_sigs.setdefault(name, sig)
    from src.maxpat import Patcher
    from src.maxpat.db_lookup import ObjectDatabase

    return {
        "module": module_sigs,
        "patcher": _method_signatures(Patcher),
        "db": _method_signatures(ObjectDatabase),
    }


_PATCHER_RECEIVERS = {"patcher", "Patcher", "Patcher()", "p", "inner", "sub", "self", "parent"}
_DB_RECEIVERS = {"db", "self.db", "patcher.db", "ObjectDatabase", "ObjectDatabase()"}


def _candidates(receiver: str, name: str) -> list[inspect.Signature]:
    idx = _api_index()
    if receiver == "":
        cands = []
        if name in idx["module"]:
            cands.append(idx["module"][name])
        if name in idx["patcher"]:
            cands.append(idx["patcher"][name])
        return cands
    if receiver in _DB_RECEIVERS or receiver.endswith("db"):
        return [idx["db"][name]] if name in idx["db"] else []
    if receiver in _PATCHER_RECEIVERS:
        return [idx["patcher"][name]] if name in idx["patcher"] else []
    return []


# ── Snippet extraction ─────────────────────────────────────────────

_CALL_RE = re.compile(r"(?<![\w.])((?:[A-Za-z_]\w*(?:\(\))?\.)*)([A-Za-z_]\w*)\(")
_FENCE_RE = re.compile(r"^\s*(```+|~~~+)\s*([\w+-]*)")
_INLINE_RE = re.compile(r"`([^`\n]+)`")
_PY_FENCE_LANGS = {"", "python", "py"}


def _balanced(text: str, open_idx: int) -> str | None:
    """Return the text between text[open_idx] == '(' and its match, or None."""
    depth = 0
    quote = ""
    i = open_idx
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1 : i]
        i += 1
    return None


def _strip_comments(text: str) -> str:
    out_lines = []
    for line in text.split("\n"):
        quote = ""
        cut = len(line)
        i = 0
        while i < len(line):
            ch = line[i]
            if quote:
                if ch == "\\":
                    i += 2
                    continue
                if ch == quote:
                    quote = ""
            elif ch in "\"'":
                quote = ch
            elif ch == "#":
                cut = i
                break
            i += 1
        out_lines.append(line[:cut])
    return "\n".join(out_lines)


def _segments(text: str) -> list[tuple[str, int]]:
    """Return (segment_text, first_line_number) for python fences + inline spans."""
    segs: list[tuple[str, int]] = []
    lines = text.split("\n")
    in_fence = False
    fence_lang = ""
    fence_start = 0
    fence_buf: list[str] = []
    for lineno, line in enumerate(lines, start=1):
        m = _FENCE_RE.match(line)
        if m:
            if not in_fence:
                in_fence = True
                fence_lang = m.group(2).lower()
                fence_start = lineno + 1
                fence_buf = []
            else:
                if fence_lang in _PY_FENCE_LANGS:
                    segs.append(("\n".join(fence_buf), fence_start))
                in_fence = False
            continue
        if in_fence:
            fence_buf.append(line)
            continue
        for sm in _INLINE_RE.finditer(line):
            segs.append((sm.group(1), lineno))
    return segs


# ── Type sentinel ──────────────────────────────────────────────────

_NAME_TYPES = {
    "patcher": "Patcher",
    "p": "Patcher",
    "inner": "Patcher",
    "patch_dict": "dict",
    "db": "ObjectDatabase",
    "patchline": "Patchline",
    "box": "Box",
    "old_box": "Box",
    "new_box": "Box",
    "src": "Box",
    "dst": "Box",
    "src_box": "Box",
    "dst_box": "Box",
}
_CTOR_TYPES = {"Box", "Patcher", "Patchline"}
_SENTINEL_TYPES = ("str", "dict", "Box", "Patcher", "Patchline", "ObjectDatabase",
                   "list", "int", "float", "bool")


def _infer_type(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return _NAME_TYPES.get(node.id)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in _CTOR_TYPES:
            return node.func.id
    return None


def _annotation_names(param: inspect.Parameter) -> set[str]:
    ann = param.annotation
    if ann is inspect.Parameter.empty:
        return set()
    text = ann if isinstance(ann, str) else getattr(ann, "__name__", str(ann))
    return {t for t in _SENTINEL_TYPES if re.search(rf"\b{t}\b", text)}


# ── Checking ───────────────────────────────────────────────────────


def _takes_var_kw(sig: inspect.Signature) -> bool:
    return any(p.kind is p.VAR_KEYWORD for p in sig.parameters.values())


def _check_call(sig: inspect.Signature, call: ast.Call) -> list[str]:
    reasons: list[str] = []
    params = sig.parameters
    starred = any(isinstance(a, ast.Starred) for a in call.args)
    double = any(k.arg is None for k in call.keywords)
    kw_names = [k.arg for k in call.keywords if k.arg is not None]
    if starred or double:
        if not _takes_var_kw(sig):
            for k in kw_names:
                if k not in params:
                    reasons.append(f"unknown keyword {k!r}")
        return reasons
    dummies = [object() for _ in call.args]
    try:
        bound = sig.bind_partial(*dummies, **{k: object() for k in kw_names})
    except TypeError as exc:
        return [f"does not bind: {exc}"]
    # Map each positional argument to the parameter it bound to.
    pos_params = [
        p for p in params.values()
        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
    ]
    for i, node in enumerate(call.args):
        if i >= len(pos_params):
            break  # absorbed by *args
        target = pos_params[i]
        if target.name not in bound.arguments:
            continue
        if isinstance(node, ast.Name) and node.id != target.name and node.id in params:
            reasons.append(
                f"positional {node.id!r} lands on parameter {target.name!r}"
            )
        inferred = _infer_type(node)
        if inferred is not None:
            names = _annotation_names(target)
            if names and inferred not in names:
                reasons.append(
                    f"{inferred} passed to {target.name!r} annotated "
                    f"{target.annotation}"
                )
    return reasons


def _check_def(sig: inspect.Signature, args: str) -> list[str] | None:
    items = [s for s in _split_top_level(args) if s.strip() != "..."]
    try:
        tree = ast.parse(f"def f({', '.join(items)}): pass")
    except SyntaxError:
        return None
    fn = tree.body[0]
    assert isinstance(fn, ast.FunctionDef)
    a = fn.args
    names = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]
    if a.vararg:
        names.append(a.vararg.arg)
    if a.kwarg:
        names.append(a.kwarg.arg)
    if _takes_var_kw(sig):
        return []
    params = sig.parameters
    reasons = []
    for n in names:
        if n in params:
            continue
        # *args / **kwargs listings match the signature's own var params.
        kinds = {p.kind for p in params.values() if p.name == n}
        if not kinds:
            reasons.append(f"listed parameter {n!r} not in signature")
    return reasons


def _split_top_level(args: str) -> list[str]:
    parts, depth, quote, cur = [], 0, "", []
    i = 0
    while i < len(args):
        ch = args[i]
        if quote:
            cur.append(ch)
            if ch == "\\" and i + 1 < len(args):
                cur.append(args[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
            cur.append(ch)
        elif ch in "([{":
            depth += 1
            cur.append(ch)
        elif ch in ")]}":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    if "".join(cur).strip():
        parts.append("".join(cur))
    return parts


_PROSE_ELLIPSIS_RE = re.compile(r"\.\.\.[^.\[\](){},=]+\.\.\.")


def _check_snippet(sigs: list[inspect.Signature], args: str) -> list[str]:
    """Return [] if any candidate signature accepts the args, else reasons."""
    # Prose placeholders such as ``[...all generated file paths...]`` stand for
    # an elided value; reduce them to a bare ``...`` so the form parses.
    args = _PROSE_ELLIPSIS_RE.sub("...", args)
    try:
        expr = ast.parse(f"f({args})", mode="eval")
        call = expr.body
        assert isinstance(call, ast.Call)
    except SyntaxError:
        call = None
    all_reasons: list[str] = []
    if call is not None:
        if not call.args and not call.keywords:
            return []
        for sig in sigs:
            reasons = _check_call(sig, call)
            if not reasons:
                return []
            all_reasons.extend(reasons)
        return all_reasons
    parsed_any = False
    for sig in sigs:
        reasons = _check_def(sig, args)
        if reasons is None:
            continue
        parsed_any = True
        if not reasons:
            return []
        all_reasons.extend(reasons)
    if not parsed_any:
        return ["unparseable call form"]
    return all_reasons


def _scan_text(text: str, label: str) -> tuple[list[str], int]:
    findings: list[str] = []
    checked = 0
    for seg, first_line in _segments(text):
        for m in _CALL_RE.finditer(seg):
            prefix = seg[max(0, m.start() - 6) : m.start()]
            if re.search(r"\b(def|class)\s+$", prefix):
                continue
            receiver = m.group(1)[:-1] if m.group(1) else ""
            name = m.group(2)
            sigs = _candidates(receiver, name)
            if not sigs:
                continue
            inner = _balanced(seg, m.end() - 1)
            if inner is None:
                continue  # truncated mention (span ends mid-call)
            checked += 1
            args = _strip_comments(inner).strip()
            reasons = _check_snippet(sigs, args)
            if reasons:
                line = first_line + seg.count("\n", 0, m.start())
                shown = f"{receiver + '.' if receiver else ''}{name}({' '.join(inner.split())})"
                findings.append(f"{label}:{line}: {shown} -> {'; '.join(reasons)}")
    return findings, checked


# ── Checker self-tests ─────────────────────────────────────────────

BAD_FORMS = [
    pytest.param('`patcher.add_box(Box("cycle~", ["440"], db))`', id="add_box-of-Box-ctor"),
    pytest.param('`Box("gen~", ["smooth-ramp"], db)`', id="Box-db-on-box_id"),
    pytest.param("`apply_layout(patcher, layout_options=opts)`", id="apply_layout-kw"),
    pytest.param("`patcher.insert_into_connection(src, dst, new_box)`", id="insert-new_box"),
    pytest.param('`patcher.replace_box(box, "phasor~", ["220"])`', id="replace_box-positional"),
    pytest.param("`save_patch_roundtrip(patcher, path)`", id="roundtrip-patcher"),
    pytest.param('`patcher.find_box("cycle~", "name", True)`', id="find_box-positional"),
]

GOOD_FORMS = [
    pytest.param('`patcher.add_box("gen~", ["smooth-ramp"])`', id="add_box"),
    pytest.param("`apply_layout(patcher, options=LayoutOptions(v_spacing=20.0))`", id="apply_layout"),
    pytest.param('`patcher.insert_into_connection(src, dst, "*~", ["0.5"])`', id="insert"),
    pytest.param('`patcher.replace_box_safe(box, "cycle~", args=["440"])`', id="replace_box_safe"),
    pytest.param("`save_patch_roundtrip(patcher.to_dict(), path, original_text)`", id="roundtrip"),
    pytest.param("`write_gendsp(code, path, ..., *, force=False)`", id="write_gendsp-listing"),
    pytest.param("`finalize_patch(is_new=True)`", id="finalize-prose"),
    pytest.param('`patcher.add_overlay_readout(target, *, format="%.2f")`', id="overlay-listing"),
    pytest.param("`outlet(0, value)`", id="js-outlet"),
    pytest.param(
        '`auto_commit_patch(project_dir, base_dir, description="x", files=[...all paths...])`',
        id="prose-ellipsis-placeholder",
    ),
]


@pytest.mark.parametrize("md", BAD_FORMS)
def test_checker_flags_bad_form(md: str) -> None:
    findings, checked = _scan_text(md, "inline")
    assert checked >= 1, f"snippet not resolved: {md}"
    assert findings, f"checker accepted a raising form: {md}"


@pytest.mark.parametrize("md", GOOD_FORMS)
def test_checker_accepts_good_form(md: str) -> None:
    findings, _ = _scan_text(md, "inline")
    assert findings == [], "\n".join(findings)


def test_scan_covers_enough_call_snippets() -> None:
    total = sum(_scan_text(_read(p), str(p))[1] for p in DOC_FILES)
    assert total >= 200, f"only {total} call snippets checked"


@pytest.mark.parametrize("rel", DOC_FILES, ids=[str(p) for p in DOC_FILES])
def test_doc_call_forms_match_signatures(rel: Path) -> None:
    findings, _ = _scan_text(_read(rel), str(rel))
    assert findings == [], "\n".join(findings)


# ── J3: replace_box wording ────────────────────────────────────────


def test_replace_box_docs_point_to_safe_variant() -> None:
    for rel in (
        Path(".claude/skills/references/shared-capabilities.md"),
        Path(".claude/commands/max-iterate.md"),
        Path("TECHNICAL.md"),
    ):
        assert "replace_box_safe" in _read(rel), f"{rel} does not name replace_box_safe"
    bad = []
    for rel in DOC_FILES:
        for n, line in enumerate(_read(rel).split("\n"), start=1):
            if not re.search(r"\breplace_box\(", line):
                continue
            if "replace_box_safe" in line or "orphan" in line.lower():
                continue
            if re.search(r"remap|preserves all positions and connections", line, re.I):
                bad.append(f"{rel}:{n}: {line.strip()}")
    assert bad == [], "replace_box documented as keeping connections:\n" + "\n".join(bad)


# ── Q16 doc regression guards (Task 2) ─────────────────────────────


@pytest.fixture(scope="module")
def db():
    from src.maxpat.db_lookup import ObjectDatabase

    return ObjectDatabase()


def _doc_lines():
    for rel in DOC_FILES:
        for n, line in enumerate(_read(rel).split("\n"), start=1):
            yield rel, n, line


def test_js_anything_handler_uses_messagename() -> None:
    """J1: MAX passes the selector in ``messagename``, never as a parameter."""
    bad = []
    for rel, n, line in _doc_lines():
        if "msg_int(" in line and not (
            "messagename" in line and "arrayfromargs(arguments)" in line
        ):
            bad.append(f"{rel}:{n}: handler list lacks messagename/arrayfromargs")
        if re.search(r"anything\(\s*[A-Za-z_]", line):
            bad.append(f"{rel}:{n}: anything() documented with a named parameter")
    assert bad == [], "\n".join(bad)


def test_gain_rule_scoped_to_multiply_tilde() -> None:
    """J2/J6: the 0-1 rule is for the ``*~`` multiplier; gain~ takes slider positions."""
    lines = [line for _, _, line in _doc_lines()]
    assert not any("feeding `*~` or `gain~`" in line for line in lines)
    assert any("`scale 0. 127. 0. 1.`" in line for line in lines)
    assert any("`gain~`" in line and "slider position" in line for line in lines)


_TILDE_OBJ_RE = re.compile(r"(?<![\w.~/$#-])((?:[a-z]\w*\.)*[A-Za-z]\w*~)(?![\w*])")
_PKG_OBJ_RE = re.compile(r"(?<![\w/-])((?:fluid|bp)\.[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*~?)(?![\w*])")
_TEMPLATE_FILES = [
    Path(".claude/skills/max-dsp-agent/SKILL.md"),
    Path(".claude/skills/max-patch-agent/BOUNDARIES.md"),
]


@pytest.mark.parametrize("rel", _TEMPLATE_FILES, ids=[str(p) for p in _TEMPLATE_FILES])
def test_dsp_templates_use_db_objects(rel: Path, db) -> None:
    """J8: every object the DSP templates name resolves in ObjectDatabase."""
    text = _read(rel)
    missing = set()
    for rx in (_TILDE_OBJ_RE, _PKG_OBJ_RE):
        for m in rx.finditer(text):
            tok = m.group(1)
            if tok == "Gen~" or tok.endswith((".maxpat", ".gendsp")):
                continue
            if db.is_pd_object(tok):
                continue
            if not db.exists(tok):
                missing.add(tok)
    assert not missing, f"{rel}: objects not in DB: {sorted(missing)}"


def test_flucoma_templates_use_fit_predict() -> None:
    """J8: FluCoMa models train with ``fit`` and query with ``predict``/``predictpoint``."""
    text = _read(Path(".claude/skills/max-dsp-agent/SKILL.md"))
    assert not re.search(r"[\"`]train[\"`]", text)
    assert re.search(r"[\"`]fit[\"`]", text)
    assert re.search(r"[\"`]predict(point)?[\"`]", text)


def test_ui_presets_dial_chain_uses_trigger() -> None:
    """J9: the dial example fans out through ``t f f`` (Rule #3/#4)."""
    text = _read(Path(".claude/skills/references/ui-presets.md"))
    start = text.index("## Complete Dial Chain Example")
    nxt = text.find("\n## ", start + 3)
    section = text[start : nxt if nxt != -1 else len(text)]
    assert re.search(r"^\s*(t|trigger) f f\b", section, re.M), section


def test_no_references_to_missing_commands() -> None:
    """J10: every /max-* command a doc names has a .claude/commands file."""
    commands = REPO_ROOT / ".claude" / "commands"
    bad = []
    for rel, n, line in _doc_lines():
        for m in re.finditer(r"(?<![\w./-])/(max-[a-z][a-z0-9-]*)", line):
            if not (commands / f"{m.group(1)}.md").is_file():
                bad.append(f"{rel}:{n}: /{m.group(1)}")
    assert bad == [], "\n".join(bad)


_SPECIALIST_SKILLS = ["max-patch-agent", "max-dsp-agent", "max-ui-agent", "max-rnbo-agent"]


def test_missing_config_is_core_only() -> None:
    """J10: a missing config.json means core-only (allowed_packages=[]), never STOP."""
    router = _read(Path(".claude/skills/max-router/SKILL.md"))
    assert "`allowed_packages=[]`" in router
    assert not [
        line for line in router.split("\n") if "config.json" in line and "STOP" in line
    ]
    assert "core-only" in _read(Path(".claude/skills/max-lifecycle/references/project-structure.md"))
    for skill in _SPECIALIST_SKILLS:
        text = _read(Path(f".claude/skills/{skill}/SKILL.md"))
        lines = [line for line in text.split("\n") if "load_project_config()" in line]
        assert lines, f"{skill}: no load_project_config() step"
        for line in lines:
            assert "core-only" in line, f"{skill}: {line.strip()}"


def test_variable_io_docs_point_to_overrides() -> None:
    """J11: no per-object io_rule field exists; rules live in variable_io_rules."""
    bad = [f"{rel}:{n}" for rel, n, line in _doc_lines() if re.search(r"\bio_rule\b", line)]
    assert bad == [], "docs mention a nonexistent io_rule field: " + ", ".join(bad)
    claude = _read(Path("CLAUDE.md"))
    assert "variable_io_rules" in claude
    assert "compute_io_counts" in claude


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    m = re.search(r"^#{1,6} ", text[start + len(heading):], re.M)
    end = start + len(heading) + m.start() if m else len(text)
    return text[start:end]


def test_technical_io_formula_table_matches_code() -> None:
    """J11: TECHNICAL's formula table lists exactly the supported formulas."""
    from src.maxpat.db_lookup import SUPPORTED_IO_FORMULAS

    section = _section(_read(Path("TECHNICAL.md")), "### Variable I/O Rules")
    documented = set()
    for line in section.split("\n"):
        if not line.startswith("|") or set(line.strip()) <= set("|-: "):
            continue
        first = line.strip().strip("|").split("|")[0]
        documented.update(re.findall(r"`([^`]+)`", first))
    expected = (set(SUPPORTED_IO_FORMULAS) - {""}) | {"fixed:N"}
    assert documented == expected


def test_spectroscope_claim_matches_db(db) -> None:
    """J4 lock (fixed by Q11 d6a4393a): doc I/O claims match the DB."""
    expected = db.compute_io_counts("spectroscope~", [])
    hits = []
    for rel, n, line in _doc_lines():
        for m in re.finditer(r"spectroscope~[^\n]*?(\d+) inlets? / (\d+) outlets?", line):
            hits.append((rel, n, (int(m.group(1)), int(m.group(2)))))
    assert hits, "no spectroscope~ I/O claim found"
    wrong = [h for h in hits if h[2] != tuple(expected)]
    assert wrong == []
