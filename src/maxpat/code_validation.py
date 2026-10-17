"""Code validation for GenExpr, js object, and Node for Max JavaScript.

Report-only validators that catch common errors before opening MAX.
No auto-fix -- all results are informational or diagnostic.

Exports:
- validate_genexpr: Validate GenExpr DSP code (gen-domain operators, syntax, Params)
- validate_js: Validate js object (Legacy Engine, ES5) JavaScript (inlets/outlets,
  handlers, bounds, ES5 lint scoped to js/jsui -- never v8/v8ui; comments ignored)
- validate_n4m: Validate Node for Max JavaScript (require, handlers, outlet)
- detect_js_type: Detect whether JavaScript code is N4M or js object
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from src.maxpat.genexpr_parse import (
    CONSTANTS as _GENEXPR_CONSTANTS,
    _find_assign,
    _for_parts,
    _paren_content,
    _split_top,
    _strip_prefixes,
    assigned_names,
    declarations,
    line_paren_depths,
    mask,
    split_args,
    statements,
)
from src.maxpat.validation import ValidationResult

if TYPE_CHECKING:
    from src.maxpat.db_lookup import ObjectDatabase


# GenExpr keywords and built-ins that should NOT be checked against the operator database
_GENEXPR_KEYWORDS = frozenset({
    "if", "else", "for", "while", "return", "break", "continue",
    "Param", "History", "Delay", "Buffer", "Data", "SampleRate", "FixedArray",
    "in", "out", "min", "max", "abs", "sqrt", "pow", "exp", "log",
    "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
    "floor", "ceil", "round", "trunc", "fract",
    "clamp", "wrap", "fold", "scale", "sign",
    "mix", "smoothstep", "step",
    "noise", "latch", "sah", "peek", "poke",
    "fixdenorm", "isnan", "isinf",
    "selector", "gate", "switch",
    "sample", "nearest", "interp",
    "require",
})


# Declaration prefixes for Check 5 (declaration ordering) and Check 9 (init-
# before-if/else). Module-level so multiple checks can reuse without rebinding.
# Hoisted from validate_genexpr local scope (Phase 29 / VALID-04 / D-16).
_DECL_PREFIXES = ("Param ", "History ", "Delay ", "Buffer ", "Data ")


# Check 6 patterns (Q12 / G3).
_DECL_STATEMENT = re.compile(r"\b(?:Param|History|Delay|Buffer|Data)\s+([^;]*);")
_CALL_NAME = re.compile(r"([A-Za-z_]\w*)\s*\(")
_FUNC_DEF = re.compile(r"(?m)^[ \t]*([A-Za-z_]\w*)[ \t]*\(([^()]*)\)\s*\{")
_CALLED = re.compile(r"(?<![.\w])([A-Za-z_]\w*)\s*\(")
_CONTROL_WORDS = frozenset({"if", "else", "for", "while"})


def validate_genexpr(
    code: str,
    db: "ObjectDatabase | None" = None,
) -> list[ValidationResult]:
    """Validate GenExpr DSP code.

    Checks:
    1. Balanced braces (error)
    2. Semicolons on statement lines (warning)
    3. in/out declarations (info)
    4. Param syntax min/max (warning)
    5. Declaration ordering (error)
    6. Called names against the gen domain only (Q12 / G3): every
       ``name(`` call must be a gen/objects.json operator, a function the
       codebox defines, or a name a declaration introduces (every name of a
       comma-separated ``History a(0), b(0);``). ``.method(`` calls and
       ``/* */`` comments are skipped. A Max-only name (``metro``) is an
       error saying so; an unknown name is an error, or a warning when the
       code calls ``require(...)`` (the name may come from the library).
    7. delay() rejection -- not supported in codebox (error, D-14)
    8. Retired in Q12: GenExpr has clip(x, lo, hi). The clip() ban applies
       to the expr/vexpr/if objects and is a CLAUDE.md rule.
    9. Init-before-if/else flow analysis (error, D-16)

    Codebox safe-construct lint (Q22 / R6; the CLAUDE.md "Gen~" rules and
    genexpr-rules.md), at the spec severities (D-06: the spec's "note" is
    the validator's ``info`` level):

    10. Tab character anywhere in the RAW code, comments included (error)
    11. Assignment to a GenExpr built-in constant name such as ``pi`` or
        ``twopi`` -- the constant wins silently (error)
    12. A Param name assigned as a local ("can't assign to parameter")
        (error)
    13. Loop shape: a nested ``for``, or a ``for`` whose condition is not
        ``identifier <op> numeric literal`` (warning)
    14. De-hoist: a derived local that combines another derived local alias
        with a Param in a Param-only expression (warning)
    15. ``tanh(...)/tanh(...)`` normalization: error when the codebox has
        feedback state -- a History that is assigned somewhere, or any
        Delay (a read-only History such as the de-hoist ``History one(1)``
        is not feedback state) -- otherwise warning; no dataflow analysis
    16. Notes (info): ``else if`` chains and 2-argument ``peek``

    Checks 1-9 run on the comment/string mask from
    :mod:`src.maxpat.genexpr_parse` (Q22 / S5): comment and string-literal
    characters are blanked to spaces with offsets and newlines kept, so
    braces, ``delay(``, ``in4`` or ``Param`` inside ``//`` / ``/* */`` never
    count. Checks 2 and 5 skip continuation lines of a multi-line paren
    group (Check 2: a line that starts or ends inside an open paren;
    Check 5: a line that starts inside one), so a multi-line
    ``Param g(0.5,\n  min=0, max=1);`` is neither a missing semicolon nor
    an expression.

    All results use layer="code". Report-only, no auto-fix.

    Args:
        code: GenExpr source code string.
        db: ObjectDatabase instance. Created if None.

    Returns:
        List of ValidationResult.
    """
    results: list[ValidationResult] = []
    if not isinstance(code, str):
        code = ""

    # One comment/string mask for every check (Q22 / S5): same length and
    # newlines as `code`, so line numbers are unchanged.
    masked = mask(code)
    raw_lines = code.split("\n")
    paren_depths = line_paren_depths(code)

    # Check 1: Balanced braces
    open_count = masked.count("{")
    close_count = masked.count("}")
    if open_count != close_count:
        results.append(ValidationResult(
            "code", "error",
            f"Unbalanced braces: {open_count} opening vs {close_count} closing",
        ))

    # Check 2: Semicolons on statement lines
    lines = masked.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Continuation rule (Q22): a line inside a multi-line paren group
        # (start or end inside an open paren) is not a statement line.
        if i < len(paren_depths) and (paren_depths[i][0] > 0 or paren_depths[i][1] > 0):
            continue

        # Skip empty, comments, braces-only, preprocessor
        if not stripped:
            continue
        if stripped.startswith("//"):
            continue
        if stripped in ("{", "}", "};", "){"):
            continue
        if stripped.startswith("#"):
            continue

        # Is this a statement line? (has assignment, function call, or declaration)
        is_statement = (
            "=" in stripped
            or re.search(r"\w+\s*\(", stripped)
            or stripped.startswith("Param ")
            or stripped.startswith("History ")
            or stripped.startswith("Buffer ")
            or stripped.startswith("Data ")
        )

        if is_statement and not stripped.endswith(";") and not stripped.endswith("{") and not stripped.endswith("}"):
            results.append(ValidationResult(
                "code", "warning",
                f"Line {i + 1}: possible missing semicolon: '{raw_lines[i].strip()}'",
            ))

    # Check 3: in/out declarations
    in_matches = re.findall(r"\bin(\d+)\b", masked)
    out_matches = re.findall(r"\bout(\d+)\b", masked)
    max_in = max((int(n) for n in in_matches), default=0)
    max_out = max((int(n) for n in out_matches), default=0)
    if max_in > 0 or max_out > 0:
        results.append(ValidationResult(
            "code", "info",
            f"Detected I/O: {max_in} input(s), {max_out} output(s)",
        ))

    # Check 4: Param validation
    param_pattern = re.compile(r"Param\s+(\w+)\s*\(([^)]*)\)")
    for match in param_pattern.finditer(masked):
        param_name = match.group(1)
        param_args = match.group(2)

        if "min" not in param_args or "max" not in param_args:
            results.append(ValidationResult(
                "code", "warning",
                f"Param '{param_name}' missing min/max range specification "
                f"(recommended: Param {param_name}(default, min=N, max=N))",
            ))

    # Check 5: Declaration ordering -- all declarations must precede expressions
    # _DECL_PREFIXES is module-level (hoisted Phase 29 for Check 9 reuse).
    last_decl_line = -1
    first_expr_line = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("#"):
            continue
        # Continuation rule (Q22): a line that starts inside an open paren
        # continues the previous statement (multi-line Param args).
        if i < len(paren_depths) and paren_depths[i][0] > 0:
            continue
        if any(stripped.startswith(p) for p in _DECL_PREFIXES):
            last_decl_line = i
            if first_expr_line >= 0:
                results.append(ValidationResult(
                    "code", "error",
                    f"Line {i + 1}: declaration '{stripped.split('(')[0].strip()}' "
                    f"appears after expression on line {first_expr_line + 1}. "
                    f"All Param/Delay/History/Buffer/Data declarations must come "
                    f"before any expressions in GenExpr.",
                ))
                break  # one error is enough to flag the issue
        elif "=" in stripped or re.search(r"\w+\.\w+\(", stripped):
            if first_expr_line < 0:
                first_expr_line = i

    # Check 6: Operator validation against gen/objects.json
    if db is None:
        from src.maxpat.db_lookup import ObjectDatabase
        db = ObjectDatabase()

    # Scan the comment/string mask (// and /* */ blanked) so an ALL-CAPS
    # banner like `// === SATURATION (Pade tanh) ===` is never tokenized
    # (tape-wobble false positive: DRIFT/EQ/LFO/ROLLOFF/SATURATION/SIGNAL).
    scan = masked

    # Names introduced by declarations: every `name(` inside a declaration
    # statement, so `History z0(0.), z1(0.);` declares both z0 and z1.
    declared_names: set[str] = set()
    for stmt in _DECL_STATEMENT.finditer(scan):
        declared_names.update(_CALL_NAME.findall(stmt.group(1)))

    # Functions the codebox defines: `name(args) {` at line start.
    defined_names = {
        m.group(1) for m in _FUNC_DEF.finditer(scan)
        if m.group(1) not in _CONTROL_WORDS
    }

    # Called names: `name(` not preceded by `.` (method calls) or a word char.
    used_funcs = {
        name for name in _CALLED.findall(scan)
        if name not in _GENEXPR_KEYWORDS
        and name not in declared_names
        and name not in defined_names
    }

    uses_require = re.search(r"(?<![.\w])require\s*\(", scan) is not None
    for func_name in sorted(used_funcs):
        if db.is_gen_operator(func_name):
            continue
        if uses_require:
            results.append(ValidationResult(
                "code", "warning",
                f"GenExpr name '{func_name}' is neither a Gen operator nor a "
                f"function defined in this codebox; it may come from "
                f"require(...) -- verify",
            ))
        elif db.exists(func_name):
            results.append(ValidationResult(
                "code", "error",
                f"Unknown GenExpr operator: '{func_name}' is a Max object, not "
                f"a Gen operator; codebox code can only call Gen operators and "
                f"functions it defines",
            ))
        else:
            results.append(ValidationResult(
                "code", "error",
                f"Unknown GenExpr operator: '{func_name}' (not a Gen operator "
                f"in gen/objects.json and not defined in this codebox)",
            ))

    # Check 7: delay() rejection (D-14, VALID-04). Compile-fatal in MAX,
    # so ERROR severity. Word-boundary prevents matching Delay(...) or
    # myDelay.read(...). Runs on the comment/string mask.
    if re.search(r"\bdelay\s*\(", masked):
        results.append(ValidationResult(
            "code", "error",
            "delay() is not supported in GenExpr codebox; "
            "use Delay.read/write (declare Delay myDelay(max_samples) first)",
        ))

    # Check 8 (clip() rejection) retired in Q12 / G3: GenExpr has clip().

    # Check 9: init-before-if/else (D-16, D-20, VALID-04). Light flow
    # analysis. The genuine GenExpr "not defined" error is a READ of a name
    # at brace depth 0 whose only assignments live inside an if/else block --
    # i.e. on a path where the block did not run, the name was never
    # defined. A name assigned AND read entirely within the same branch is
    # valid GenExpr and must NOT be flagged (fixes scala-synth-voice,
    # timestretch, wormhole false positives). Two passes over `lines`:
    #   Pass 1: collect pre_block_inits (depth-0 LHS), declared
    #           (Param/History/Delay/Buffer/Data), and block_assigned
    #           (names assigned at depth >= 1 that are neither pre-init nor
    #           declared) with the line of first in-block assignment.
    #   Pass 2: walk again; on a depth-0 read of a block_assigned name
    #           (not pre-init, not a GenExpr keyword/builtin), record it as
    #           a genuine read-before-init occurrence.
    # First-error-and-stop matches Check 5 posture. Documented false-
    # positive limitations (D-20) surfaced in the suggestion line.
    declared = set()
    for match in re.finditer(
        r"(?:Param|History|Delay|Buffer|Data)\s+(\w+)\s*\(", masked
    ):
        declared.add(match.group(1))

    # `assign_pattern` anchored at line start; a `(?!=)` guard keeps it from
    # matching equality (`==`). The start anchor preserves the documented
    # single-line-if false negative (`if (c) { y = 1; }` -> matches 'if').
    assign_pattern = re.compile(r"^(\w+)\s*=(?!=)")
    ident_pattern = re.compile(r"[A-Za-z_]\w*")

    # Pass 1: assignments.
    pre_block_inits: set[str] = set()
    block_assigned: dict[str, int] = {}
    depth = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("#"):
            continue
        opens = stripped.count("{")
        closes = stripped.count("}")
        m = assign_pattern.match(stripped)
        if m:
            name = m.group(1)
            if depth == 0:
                pre_block_inits.add(name)
            elif name not in pre_block_inits and name not in declared:
                block_assigned.setdefault(name, i)
        depth += opens - closes
        if depth < 0:
            depth = 0  # unbalanced; Check 1 already flagged it

    # Pass 2: reads at depth 0. Depth is evaluated at the START of each line
    # (before applying this line's braces) so an `if (cond) {` condition and
    # a bare `out1 = name;` statement both count as depth-0 reads.
    if_else_inits: list[tuple[str, int]] = []
    seen_reads: set[str] = set()
    depth = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("#"):
            opens = stripped.count("{")
            closes = stripped.count("}")
            depth += opens - closes
            if depth < 0:
                depth = 0
            continue
        opens = stripped.count("{")
        closes = stripped.count("}")
        if depth == 0:
            # Read portion: RHS of an assignment (LHS is a write, not a
            # read), else the whole line.
            m = assign_pattern.match(stripped)
            read_src = stripped[m.end():] if m else stripped
            for tok in ident_pattern.findall(read_src):
                if (
                    tok in block_assigned
                    and tok not in pre_block_inits
                    and tok not in _GENEXPR_KEYWORDS
                    and tok not in seen_reads
                ):
                    seen_reads.add(tok)
                    if_else_inits.append((tok, block_assigned[tok]))
        depth += opens - closes
        if depth < 0:
            depth = 0

    seen = set()
    for name, line_no in if_else_inits:
        if name in seen:
            continue
        seen.add(name)
        # Guard against block_start_line=-1 (assignment seen at depth>=1
        # without a tracked outermost-block opening line, e.g., malformed
        # input). Avoid misleading "(line 0)" output.
        line_display = (
            f"line {line_no + 1}" if line_no >= 0 else "in an if/else block"
        )
        results.append(ValidationResult(
            "code", "error",
            f"variable '{name}' used inside if/else without prior init "
            f"({line_display}); GenExpr errors with 'not defined'. "
            f"Restructure to assign '{name}' before the if/else, or "
            f"if this is a false positive (e.g., shadowed inner "
            f"declaration), declare via Param/History/Delay/Buffer/Data.",
        ))
        break  # first-error-and-stop, matches Check 5

    # Checks 10-16 (Q22 / R6) run after Check 9's loop, so its
    # first-error-and-stop `break` never skips them.
    results.extend(_lint_genexpr(code, masked))

    return results


# ---------------------------------------------------------------------------
# Checks 10-16: codebox safe-construct lint (Q22 / R6)
# ---------------------------------------------------------------------------

_LINT_TANH = re.compile(r"(?<![\w.])tanh\s*\(")
_LINT_TANH_DIV = re.compile(r"\s*/\s*tanh\s*\(")
_LINT_PEEK = re.compile(r"(?<![\w.])peek\s*\(")
_LINT_ELSE_IF = re.compile(r"\belse\s+if\b")
_LINT_KWARG = re.compile(r"^\s*[A-Za-z_]\w*\s*=(?!=)")
_LINT_RHS_IDENT = re.compile(r"(?<![\w.$])[A-Za-z_]\w*")
_LINT_IDENT = re.compile(r"[A-Za-z_]\w*")
_LINT_NUM = r"-?(?:\d+(?:\.\d*)?|\.\d+)"
_LINT_CMP = r"(?:<=|<|>=|>|!=)"
_LINT_BOUND = re.compile(
    rf"^(?:[A-Za-z_]\w*{_LINT_CMP}{_LINT_NUM}|{_LINT_NUM}{_LINT_CMP}[A-Za-z_]\w*)$"
)


def _lint_line(m: str, pos: int) -> int:
    return m.count("\n", 0, pos) + 1


def _rhs_identifiers(rhs: str) -> set:
    """Identifiers an assignment RHS reads: not calls (``name(``), not
    ``kw=`` keys inside parens."""
    names = set()
    depth = 0
    depth_at = []
    for c in rhs:
        depth_at.append(depth)
        if c == "(":
            depth += 1
        elif c == ")" and depth > 0:
            depth -= 1
    for mt in _LINT_RHS_IDENT.finditer(rhs):
        after = rhs[mt.end():].lstrip()
        if after.startswith("("):
            continue
        if after.startswith("=") and not after.startswith("==") and depth_at[mt.start()] > 0:
            continue
        names.add(mt.group(0))
    return names


def _assignment_records(code: str, stmts: list) -> list:
    """(names, op, rhs, line) per assignment, sourced exactly like
    genexpr_parse.assigned_names: non-decl statements (a leading else and
    if / while / for paren group stripped) plus for-header init and
    increment parts."""
    records = []

    def add(text: str, base: int) -> None:
        a, b = _find_assign(text)
        if a < 0:
            return
        names = [x.strip() for x in split_args(text[:a])]
        names = [x for x in names if _LINT_IDENT.fullmatch(x)]
        if names:
            records.append((names, text[a:b], text[b:], code.count("\n", 0, base + a) + 1))

    for st in stmts:
        if st.kind == "decl":
            continue
        if st.kind == "header":
            fp = _for_parts(st.text)
            if fp is not None:
                base, parts = fp
                for idx in (0, 2):
                    if idx < len(parts):
                        off, part = parts[idx]
                        for sub_off, sub in _split_top(part, ","):
                            add(sub, st.start + base + off + sub_off)
            continue
        pos = _strip_prefixes(st.text)
        add(st.text[pos:], st.start + pos)
    return records


def _lint_genexpr(code: str, m: str) -> list[ValidationResult]:
    """Checks 10-16 (see validate_genexpr). Never raises."""
    out: list[ValidationResult] = []
    try:
        stmts = statements(code)
        decls = declarations(code)
        assigned = assigned_names(code)
    except Exception:  # pragma: no cover - the parser never raises
        return out

    params: list[str] = []
    state_names: set = set()
    history_names: set = set()
    has_delay = False
    for dtype, names, _st in decls:
        if dtype == "Param":
            params.extend(n for n in names if n not in params)
        else:
            state_names.update(names)
            if dtype == "History":
                history_names.update(names)
            elif dtype == "Delay":
                has_delay = True
    param_set = set(params)
    # Feedback state (Q22-fix CR-02, D-03): a History that is assigned
    # somewhere in the body, or any Delay. A read-only History such as the
    # de-hoist `History one(1)` is not feedback state.
    has_feedback_state = has_delay or bool(history_names & set(assigned))

    # Check 10: tabs in the RAW code (a tab inside a comment still counts).
    if "\t" in code:
        tab_lines = [i + 1 for i, ln in enumerate(code.split("\n")) if "\t" in ln]
        shown = ", ".join(str(n) for n in tab_lines[:5])
        if len(tab_lines) > 5:
            shown += f" and {len(tab_lines) - 5} more"
        out.append(ValidationResult(
            "code", "error",
            f"Tab character in codebox code (line(s) {shown}) -- codeboxes must "
            f"use spaces only; tabs are the prime suspect for MAX's generic "
            f"'failed to compile genpatcher' error",
        ))

    # Check 11: assignment to a built-in constant (one result per name).
    for name in sorted((n for n in assigned if n in _GENEXPR_CONSTANTS),
                       key=lambda n: (min(assigned[n]), n)):
        out.append(ValidationResult(
            "code", "error",
            f"Assignment to GenExpr built-in constant '{name}' (line "
            f"{min(assigned[name])}) -- the built-in constant wins silently, so "
            f"the assignment has no effect; rename the variable",
        ))

    # Check 12: a Param name assigned as a local (one result per name).
    for name in sorted((n for n in assigned if n in param_set),
                       key=lambda n: (min(assigned[n]), n)):
        out.append(ValidationResult(
            "code", "error",
            f"Param '{name}' is assigned as a local (line {min(assigned[name])}) "
            f"-- GenExpr rejects it with \"can't assign to parameter\"; rename "
            f"the local or the Param",
        ))

    # Check 13: loop shape -- nested `for`, non-literal bound.
    open_headers: list = []
    for st in stmts:
        open_headers = open_headers[:st.depth]
        if st.kind != "header":
            continue
        fp = _for_parts(st.text)
        if fp is not None:
            enclosing = [h for h in open_headers if _for_parts(h.text) is not None]
            if "for" in st.parents and enclosing:
                out.append(ValidationResult(
                    "code", "warning",
                    f"Line {st.line}: nested for loop (inside the for loop on line "
                    f"{enclosing[-1].line}) -- codebox loops must be single and "
                    f"non-nested; amortize the inner scan across samples with a "
                    f"History cursor",
                ))
            parts = fp[1]
            cond = parts[1][1] if len(parts) >= 3 else ""
            if not _LINT_BOUND.match("".join(cond.split())):
                out.append(ValidationResult(
                    "code", "warning",
                    f"Line {st.line}: for loop bound '{' '.join(cond.split())}' is "
                    f"not a numeric literal -- use a constant bound with a variable "
                    f"inner guard: for (i = 0; i < 600; i += 1) {{ if (i < win) "
                    f"{{ ... }} }}",
                ))
        open_headers.append(st)

    # Check 14: de-hoist fixpoint. A derived local has exactly one plain `=`
    # assignment, is not a Param or History/Delay/Buffer/Data name, and reads
    # only Params, samplerate/vectorsize, built-in constants and other
    # derived locals (a literal-only RHS counts).
    per_name: dict = {}
    for names, op, rhs, line in _assignment_records(code, stmts):
        for n in names:
            per_name.setdefault(n, []).append((op, rhs, line))
    base_names = param_set | {"samplerate", "vectorsize"} | set(_GENEXPR_CONSTANTS)
    candidates: dict = {}
    for n, recs in per_name.items():
        if (len(recs) == 1 and recs[0][0] == "="
                and n not in state_names and n not in param_set):
            candidates[n] = (_rhs_identifiers(recs[0][1]), recs[0][2])
    derived: set = set()
    changed = True
    while changed:
        changed = False
        for n, (ids, _line) in candidates.items():
            if n not in derived and ids <= (base_names | derived):
                derived.add(n)
                changed = True
    for n in sorted(derived, key=lambda k: (candidates[k][1], k)):
        ids, line = candidates[n]
        aliases = sorted(ids & derived)
        used_params = sorted(ids & param_set)
        if aliases and used_params:
            out.append(ValidationResult(
                "code", "warning",
                f"Line {line}: '{n}' combines local alias(es) "
                f"{', '.join(repr(a) for a in aliases)} with Param(s) "
                f"{', '.join(repr(p) for p in used_params)} in a Param-only "
                f"expression -- gen~ hoists it and the alias can be undeclared or "
                f"emitted out of order; write samplerate and constants directly or "
                f"de-hoist with History one(1)",
            ))

    # Check 15: tanh(...)/tanh(...) normalization (D-04, refined by Q22-fix
    # D-03: error with feedback state -- an assigned History or any Delay --
    # otherwise warning; no dataflow analysis).
    for mt in _LINT_TANH.finditer(m):
        open_pos = mt.end() - 1
        close = open_pos + 1 + len(_paren_content(m, open_pos))
        if close >= len(m) or m[close] != ")":
            continue
        if not _LINT_TANH_DIV.match(m, close + 1):
            continue
        line = _lint_line(m, mt.start())
        if has_feedback_state:
            out.append(ValidationResult(
                "code", "error",
                f"Line {line}: tanh(...)/tanh(...) normalization in a codebox with "
                f"History/Delay state (a feedback path) -- the loop gain then moves "
                f"with drive; normalize by the drive gain: tanh(x*g)/g",
            ))
        else:
            out.append(ValidationResult(
                "code", "warning",
                f"Line {line}: tanh(...)/tanh(...) normalization -- on a feedback "
                f"path the loop gain moves with drive; prefer tanh(x*g)/g",
            ))

    # Check 16: notes at `info` (the spec's "note", D-06).
    else_ifs = list(_LINT_ELSE_IF.finditer(m))
    if else_ifs:
        out.append(ValidationResult(
            "code", "info",
            f"Line {_lint_line(m, else_ifs[0].start())}: 'else if' chain "
            f"({len(else_ifs)} in total) -- valid GenExpr; the proven-safe codebox "
            f"set nests else {{ if ... }} instead (precaution note)",
        ))
    peek2: list = []
    for mt in _LINT_PEEK.finditer(m):
        args = split_args(_paren_content(m, mt.end() - 1))
        positional = [a for a in args if a.strip() and not _LINT_KWARG.match(a)]
        if len(positional) == 2:
            peek2.append(mt.start())
    if peek2:
        out.append(ValidationResult(
            "code", "info",
            f"Line {_lint_line(m, peek2[0])}: 2-argument peek ({len(peek2)} in "
            f"total) -- valid in MAX; the proven-safe codebox set passes the "
            f"channel: peek(buf, idx, 0) (style note)",
        ))

    return out


# ---------------------------------------------------------------------------
# js: comment/string mask and ES5 lint (Q22 / R6, D-01..D-03)
# ---------------------------------------------------------------------------

# Keywords after which a `/` starts a regex literal rather than a division
# (Q22-fix CR-01, D-02). Matched against the whole identifier that ends at
# the previous significant character, so `returned / 2` stays a division.
_JS_REGEX_PREFIX_KEYWORDS = frozenset({
    "return", "typeof", "instanceof", "in", "of", "new", "delete", "void",
    "throw", "case", "do", "else", "yield", "await",
})
_JS_IDENT_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_$"
)
_JS_BLANK_CHARS = frozenset(" \t\r\f\v")


def _js_mask(code: str) -> tuple[str, list]:
    """Blank JS comments, string contents, template-literal bodies and
    regex-literal bodies.

    Single left-to-right scan; the result has the same length as *code* and
    keeps every newline. ``//`` and ``/* */`` comments, ``'...'`` / ``"..."``
    contents (backslash escapes honoured) and template-literal bodies become
    spaces; the quote characters and backticks stay. Returns
    ``(mask, template_lines)`` where *template_lines* holds the 1-based line
    of each opening backtick seen outside comments, strings and regex
    literals. An unterminated comment, string or template runs to EOF.
    Never raises.

    Regex literals (Q22-fix CR-01, D-02): outside comments and strings, a
    lone ``/`` (not ``//`` or ``/*``, which always open a comment) starts a
    regex literal when the previous significant token does not end a value
    -- an identifier, a number, ``)``, ``]``, or a closing quote, backtick
    or regex ``/`` ends a value -- or when the whole identifier ending at
    the previous significant character is in ``_JS_REGEX_PREFIX_KEYWORDS``
    (``return``, ``typeof``, ``case`` ...). Otherwise it is a division.
    Whitespace and comments never change the previous token; ``}`` does not
    end a value, so ``}`` followed by ``/`` starts a regex. Inside a regex,
    character classes ``[...]`` and backslash escapes are honoured until
    the closing ``/``; the body becomes spaces while the delimiters and the
    flags stay. A regex literal cannot span lines, so an unterminated one
    ends at its line end. Known limit of this standard heuristic: a ``)``
    closing an ``if`` / ``while`` / ``for`` header directly before a regex
    literal reads as a division, and a ``/`` after a postfix ``++`` /
    ``--`` reads as a regex (both bounded to one line).
    """
    out = list(code)
    n = len(code)
    template_lines: list = []
    line = 1
    i = 0
    state = ""  # "" normal, "//", "/*", "'", '"', "`", "re"
    in_class = False
    value_end = False  # the last significant token ends a value
    last_sig = -1  # index of the last significant character (normal state)
    ident_start = -1  # start of the identifier ending at last_sig, else -1
    while i < n:
        c = code[i]
        if c == "\n":
            line += 1
            if state == "//":
                state = ""
            elif state == "re":
                # Unterminated regex literal: recover at the line end.
                state = ""
                in_class = False
                value_end = False
                ident_start = -1
            i += 1
            continue
        if state == "":
            if c == "/" and i + 1 < n and code[i + 1] in "/*":
                state = "//" if code[i + 1] == "/" else "/*"
                out[i] = out[i + 1] = " "
                i += 2
                continue
            if c in _JS_BLANK_CHARS:
                i += 1
                continue
            if c == "/":
                keyword = (
                    ident_start >= 0
                    and code[ident_start:last_sig + 1] in _JS_REGEX_PREFIX_KEYWORDS
                )
                if not value_end or keyword:
                    state = "re"
                    in_class = False
                else:
                    value_end = False
                    ident_start = -1
                    last_sig = i
                i += 1
                continue
            if c in _JS_IDENT_CHARS:
                if not (ident_start >= 0 and last_sig == i - 1):
                    ident_start = i
                value_end = True
            else:
                ident_start = -1
                value_end = c in ")]"
                if c in "'\"":
                    state = c
                elif c == "`":
                    state = "`"
                    template_lines.append(line)
            last_sig = i
            i += 1
            continue
        if state == "re":
            if c == "\\":
                out[i] = " "
                if i + 1 < n and code[i + 1] not in "\r\n":
                    out[i + 1] = " "
                    i += 2
                else:
                    i += 1
                continue
            if c == "/" and not in_class:
                state = ""
                value_end = True
                ident_start = -1
                last_sig = i
                i += 1
                continue
            if c == "[":
                in_class = True
            elif c == "]":
                in_class = False
            if c != "\r":
                out[i] = " "
            i += 1
            continue
        if state == "//":
            if c != "\r":
                out[i] = " "
            i += 1
            continue
        if state == "/*":
            if c == "*" and i + 1 < n and code[i + 1] == "/":
                out[i] = out[i + 1] = " "
                state = ""
                i += 2
                continue
            if c != "\r":
                out[i] = " "
            i += 1
            continue
        # inside a string or template literal
        if c == "\\" and i + 1 < n:
            out[i] = " "
            if code[i + 1] == "\n":
                line += 1
            elif code[i + 1] != "\r":
                out[i + 1] = " "
            i += 2
            continue
        if c == state:
            # A closing quote or backtick ends a value: a following `/` is
            # a division (no keyword lookup).
            state = ""
            value_end = True
            ident_start = -1
            last_sig = i
        elif c != "\r":
            out[i] = " "
        i += 1
    return "".join(out), template_lines


_JS_ES6_PATTERNS = (
    ("'const'", re.compile(r"\bconst\s+[A-Za-z_$]")),
    ("'let'", re.compile(r"\blet\s+[A-Za-z_$\[{]")),
    ("'=>' (arrow function)", re.compile(r"=>")),
    ("template literal", None),
    ("'class'", re.compile(r"(?<![.\w$])class\s+[A-Za-z_$]")),
    ("default parameter", None),
)
_JS_FUNC_PARAMS = re.compile(r"\bfunction\b\s*[\w$]*\s*\(([^)]*)\)")
_JS_DEFAULT_EQ = re.compile(r"(?<![=!<>])=(?!=)")
_JS_LEGACY_ENGINES = ("js", "jsui")
_JS_MODERN_ENGINES = ("v8", "v8ui")


def _js_es6_forms(masked: str, template_lines: list) -> list:
    """[(form, [lines...]), ...] for every ES6 form present, in a fixed
    order."""
    def line_of(pos: int) -> int:
        return masked.count("\n", 0, pos) + 1

    found = []
    for form, pattern in _JS_ES6_PATTERNS:
        if form == "template literal":
            lines = list(template_lines)
        elif form == "default parameter":
            lines = [
                line_of(mt.start())
                for mt in _JS_FUNC_PARAMS.finditer(masked)
                if _JS_DEFAULT_EQ.search(mt.group(1))
            ]
        else:
            lines = [line_of(mt.start()) for mt in pattern.finditer(masked)]
        if lines:
            found.append((form, lines))
    return found


def validate_js(code: str, *, engine: str | None = None) -> list[ValidationResult]:
    """Validate js object (Legacy Engine, ES5) JavaScript code.

    Checks:
    1. inlets declaration present
    2. outlets declaration present
    3. Handler function presence
    4. outlet() index bounds
    5. ES5 lint (Q22 / R6): ES6 syntax -- ``const``, ``let``, ``=>``,
       template literals, ``class``, default parameters -- scoped by
       *engine* (D-01): an error per form when engine is ``"js"`` or
       ``"jsui"`` (the Legacy Engine rejects it), nothing for ``"v8"`` /
       ``"v8ui"`` (Modern Engine), and exactly one info when the engine is
       None or unknown (D-02 note).

    Checks 1-5 run on a comment/string/regex-literal mask (Q22 / G8;
    regex literals Q22-fix CR-01, see ``_js_mask``): ``// inlets = 2``,
    ``/* outlets = 3 */``, a commented-out ``outlet(5, x)`` or ES6 syntax
    inside a string, comment or regex literal never count, and a quote,
    backtick or ``//`` inside a regex literal opens nothing.

    All results use layer="code". Report-only, no auto-fix.

    Args:
        code: js object JavaScript source code string.
        engine: The MAX object that loads the file: "js", "jsui", "v8",
            "v8ui", or None when unknown (D-03: callers that know the box
            pass its engine directly).

    Returns:
        List of ValidationResult.
    """
    results: list[ValidationResult] = []
    if not isinstance(code, str):
        code = ""
    masked, template_lines = _js_mask(code)

    # Check 1: inlets declaration
    inlets_match = re.search(r"inlets\s*=\s*(\d+)", masked)
    if not inlets_match:
        results.append(ValidationResult(
            "code", "error",
            "Missing 'inlets' declaration (required for js object)",
        ))

    # Check 2: outlets declaration
    outlets_match = re.search(r"outlets\s*=\s*(\d+)", masked)
    if not outlets_match:
        results.append(ValidationResult(
            "code", "error",
            "Missing 'outlets' declaration (required for js object)",
        ))

    # Check 3: Handler presence
    handler_names = ["bang", "msg_int", "msg_float", "list", "anything"]
    found_handlers = []
    for handler in handler_names:
        if re.search(rf"function\s+{handler}\s*\(", masked):
            found_handlers.append(handler)

    if not found_handlers:
        results.append(ValidationResult(
            "code", "warning",
            "No handler functions found (expected at least one of: "
            "bang, msg_int, msg_float, list, anything)",
        ))
    else:
        results.append(ValidationResult(
            "code", "info",
            f"Handler functions found: {', '.join(found_handlers)}",
        ))

    # Check 4: outlet() index bounds
    if outlets_match:
        num_outlets = int(outlets_match.group(1))
        outlet_calls = re.findall(r"outlet\(\s*(\d+)", masked)
        for idx_str in outlet_calls:
            idx = int(idx_str)
            if idx >= num_outlets:
                results.append(ValidationResult(
                    "code", "error",
                    f"outlet() index {idx} out of bounds "
                    f"(declared outlets = {num_outlets}, valid indices: 0-{num_outlets - 1})",
                ))

    # Check 5: ES5 lint by engine (D-01 / D-02).
    forms = _js_es6_forms(masked, template_lines)
    if forms and engine not in _JS_MODERN_ENGINES:
        if engine in _JS_LEGACY_ENGINES:
            for form, lines in forms:
                results.append(ValidationResult(
                    "code", "error",
                    f"ES6 syntax {form} on line {min(lines)} ({len(lines)} in "
                    f"total) -- js/jsui run the Legacy Engine (ES5), which "
                    f"rejects it; rewrite in ES5 or load the file with v8/v8ui",
                ))
        else:
            first = min(min(lines) for _f, lines in forms)
            results.append(ValidationResult(
                "code", "info",
                f"ES6 syntax found ({', '.join(f for f, _l in forms)}; first on "
                f"line {first}) -- legal in v8/v8ui only; an error if js/jsui "
                f"loads this file (engine unknown)",
            ))

    return results


def validate_n4m(code: str) -> list[ValidationResult]:
    """Validate Node for Max JavaScript code.

    Checks:
    1. require('max-api') present
    2. addHandler names are string literals
    3. maxAPI.outlet() called

    All results use layer="code". Report-only, no auto-fix.

    Args:
        code: N4M JavaScript source code string.

    Returns:
        List of ValidationResult.
    """
    results: list[ValidationResult] = []

    # Check 1: require('max-api')
    require_pattern = re.compile(r"""require\s*\(\s*['"]max-api['"]\s*\)""")
    if not require_pattern.search(code):
        results.append(ValidationResult(
            "code", "error",
            "Missing require('max-api') or require(\"max-api\") -- "
            "required for Node for Max scripts",
        ))

    # Check 2: addHandler calls
    handler_pattern = re.compile(r"""addHandler\s*\(\s*['"]([^'"]+)['"]""")
    handler_names = handler_pattern.findall(code)
    if handler_names:
        results.append(ValidationResult(
            "code", "info",
            f"Registered handlers: {', '.join(handler_names)}",
        ))

    # Also check for addHandler calls with non-string arguments
    non_string_pattern = re.compile(r"""addHandler\s*\(\s*[^'"\s]""")
    for match in non_string_pattern.finditer(code):
        # Make sure this isn't just a string we already matched
        pos = match.start()
        if not handler_pattern.search(code[pos:pos + 50]):
            results.append(ValidationResult(
                "code", "warning",
                "addHandler called with non-string name literal",
            ))

    # Check 3: maxAPI.outlet()
    outlet_pattern = re.compile(r"maxAPI\.outlet\(")
    if not outlet_pattern.search(code):
        results.append(ValidationResult(
            "code", "warning",
            "No maxAPI.outlet() call found -- script may not send data back to MAX",
        ))

    return results


def detect_js_type(code: str) -> str | None:
    """Detect whether JavaScript code is Node for Max or js object.

    Args:
        code: JavaScript source code string.

    Both tests read real code only (Q31 / G8): text inside comments and
    string literals is ignored via ``_js_mask``. The require test runs on
    the raw code (the mask blanks the ``'max-api'`` string) but counts only
    a match whose ``require`` token survives the mask at the same offset.

    Returns:
        "n4m" if code contains require('max-api') outside comments/strings,
        "js" if code contains an inlets declaration outside comments/strings,
        None if neither is detected.
    """
    masked = _js_mask(code)[0]
    for m in re.finditer(r"""require\s*\(\s*['"]max-api['"]\s*\)""", code):
        if masked[m.start():m.start() + len("require")] == "require":
            return "n4m"
    if re.search(r"inlets\s*=", masked):
        return "js"
    return None
