"""validate_genexpr Checks 10-16 (Q22 / R6): the codebox safe-construct rules
of CLAUDE.md / genexpr-rules.md, at the spec severities (D-04, D-06).

One test class per check, a severity contract over every message family and
never-raise robustness.
"""

from __future__ import annotations

import time

import pytest

from src.maxpat.code_validation import validate_genexpr
from src.maxpat.db_lookup import ObjectDatabase


@pytest.fixture(scope="module")
def db() -> ObjectDatabase:
    return ObjectDatabase()


def _run(code, db):
    return validate_genexpr(code, db=db)


def _with(results, fragment):
    return [r for r in results if fragment in r.message]


# ---------------------------------------------------------------------------
# Check 10: tab characters (error)
# ---------------------------------------------------------------------------

class TestCheck10Tabs:
    def test_tab_line(self, db):
        res = _with(_run("x = in1;\n\tout1 = x;", db), "Tab character")
        assert len(res) == 1
        assert res[0].level == "error"
        assert res[0].message == (
            "Tab character in codebox code (line(s) 2) -- codeboxes must use "
            "spaces only; tabs are the prime suspect for MAX's generic "
            "'failed to compile genpatcher' error"
        )

    def test_tab_in_comment_still_errors(self, db):
        res = _with(_run("x = in1; //\tnote\nout1 = x;", db), "Tab character")
        assert len(res) == 1 and res[0].level == "error"
        assert "(line(s) 1)" in res[0].message

    def test_many_tab_lines_truncated(self, db):
        code = "\n".join(f"\tx{i} = in1;" for i in range(7)) + "\nout1 = x0;"
        (r,) = _with(_run(code, db), "Tab character")
        assert "(line(s) 1, 2, 3, 4, 5 and 2 more)" in r.message

    def test_spaces_only(self, db):
        assert _with(_run("x = in1;\n    out1 = x;", db), "Tab character") == []


# ---------------------------------------------------------------------------
# Check 11: built-in constant assignment (error)
# ---------------------------------------------------------------------------

class TestCheck11Constants:
    def test_pi_and_twopi(self, db):
        res = _with(_run("pi = 3.14;\ntwopi = 2.0 * pi;\nout1 = in1 * twopi;", db),
                    "built-in constant")
        assert [r.level for r in res] == ["error", "error"]
        assert [r.message for r in res] == [
            "Assignment to GenExpr built-in constant 'pi' (line 1) -- the built-in "
            "constant wins silently, so the assignment has no effect; rename the variable",
            "Assignment to GenExpr built-in constant 'twopi' (line 2) -- the built-in "
            "constant wins silently, so the assignment has no effect; rename the variable",
        ]

    def test_e(self, db):
        res = _with(_run("e = 1;\nout1 = in1 * e;", db), "built-in constant")
        assert len(res) == 1 and "'e' (line 1)" in res[0].message

    @pytest.mark.parametrize("code", [
        "TWOPI = 6.28;\nout1 = in1 * TWOPI;",
        "out1 = in1 * e * pi;",
        "x = 1e5;\nout1 = in1 * x;",
        "// pi = 3;\nout1 = in1;",
        "if (pi == in1) { }\nout1 = in1;",
    ])
    def test_not_flagged(self, code, db):
        assert _with(_run(code, db), "built-in constant") == []

    def test_comma_lhs(self, db):
        res = _with(_run("a, pi = foo(in1);\nout1 = a;", db), "built-in constant")
        assert len(res) == 1 and "'pi'" in res[0].message and res[0].level == "error"


# ---------------------------------------------------------------------------
# Check 12: Param assigned as a local (error)
# ---------------------------------------------------------------------------

class TestCheck12ParamAssigned:
    def test_assigned(self, db):
        res = _with(_run("Param g(0.5, min=0, max=1);\ng = g * 2;\nout1 = in1 * g;", db),
                    "is assigned as a local")
        assert len(res) == 1
        assert res[0].level == "error"
        assert res[0].message == (
            "Param 'g' is assigned as a local (line 2) -- GenExpr rejects it with "
            "\"can't assign to parameter\"; rename the local or the Param"
        )

    def test_comma_listed_param(self, db):
        res = _with(_run(
            "Param a(1, min=0, max=2), b(0, min=0, max=1);\nb += 1;\nout1 = a + b;", db),
            "is assigned as a local")
        assert len(res) == 1 and "Param 'b'" in res[0].message

    def test_for_init(self, db):
        res = _with(_run(
            "Param g(1, min=0, max=8);\nfor (g = 0; g < 4; g += 1) { }\nout1 = in1;", db),
            "is assigned as a local")
        assert len(res) == 1 and "Param 'g'" in res[0].message

    def test_not_flagged(self, db):
        code = (
            "Param g(1, min=0, max=8);\n"
            "if (g == 1) { }\n"
            "out1 = in1 * g;\n"
        )
        assert _with(_run(code, db), "is assigned as a local") == []


# ---------------------------------------------------------------------------
# Check 13: loop shape (warning)
# ---------------------------------------------------------------------------

class TestCheck13Loops:
    def test_nested_single_line(self, db):
        code = "for (i = 0; i < 4; i += 1) { for (j = 0; j < 4; j += 1) { } }\nout1 = in1;"
        res = _with(_run(code, db), "nested for loop")
        assert len(res) == 1
        assert res[0].level == "warning"
        assert res[0].message == (
            "Line 1: nested for loop (inside the for loop on line 1) -- codebox "
            "loops must be single and non-nested; amortize the inner scan across "
            "samples with a History cursor"
        )

    def test_nested_multi_line(self, db):
        code = (
            "s = 0;\n"
            "for (i = 0; i < 4; i += 1) {\n"
            "  s = s + i;\n"
            "  for (j = 0; j < 4; j += 1) {\n"
            "    s = s + j;\n"
            "  }\n"
            "}\n"
            "out1 = s;\n"
        )
        (r,) = _with(_run(code, db), "nested for loop")
        assert r.message.startswith("Line 4: nested for loop (inside the for loop on line 2)")

    def test_non_literal_bound(self, db):
        code = "Param win(4, min=1, max=600);\ns = 0;\nfor (i = 0; i  <  win; i += 1) { s += i; }\nout1 = s;"
        res = _with(_run(code, db), "is not a numeric literal")
        assert len(res) == 1
        assert res[0].level == "warning"
        assert res[0].message == (
            "Line 3: for loop bound 'i < win' is not a numeric literal -- use a "
            "constant bound with a variable inner guard: for (i = 0; i < 600; "
            "i += 1) { if (i < win) { ... } }"
        )

    @pytest.mark.parametrize("cond", ["i < 600", "600 > i", "i <= -1.5"])
    def test_literal_bounds_ok(self, cond, db):
        code = f"s = 0;\nfor (i = 0; {cond}; i += 1) {{ s += i; }}\nout1 = s;"
        assert _with(_run(code, db), "for loop") == []

    def test_sequential_loops_ok(self, db):
        code = (
            "s = 0;\n"
            "for (i = 0; i < 4; i += 1) { s += i; }\n"
            "for (j = 0; j < 4; j += 1) { s += j; }\n"
            "out1 = s;\n"
        )
        assert _with(_run(code, db), "for loop") == []

    def test_for_inside_if_ok(self, db):
        code = (
            "s = 0;\n"
            "if (in1 > 0) {\n"
            "  for (i = 0; i < 8; i += 1) {\n"
            "    s += i;\n"
            "  }\n"
            "}\n"
            "out1 = s;\n"
        )
        assert _with(_run(code, db), "for loop") == []

    def test_empty_condition(self, db):
        res = _with(_run("for (;;) {}\nout1 = in1;", db), "is not a numeric literal")
        assert len(res) == 1 and res[0].level == "warning"


# ---------------------------------------------------------------------------
# Check 14: de-hoist (local alias in a Param-only expression, warning)
# ---------------------------------------------------------------------------

class TestCheck14Dehoist:
    def test_alias_with_param(self, db):
        code = "Param freq(440, min=20, max=20000);\nsr = samplerate;\ninc = freq / sr;\nout1 = in1 * inc;"
        res = _with(_run(code, db), "Param-only expression")
        assert len(res) == 1
        assert res[0].level == "warning"
        assert res[0].message == (
            "Line 3: 'inc' combines local alias(es) 'sr' with Param(s) 'freq' in a "
            "Param-only expression -- gen~ hoists it and the alias can be undeclared "
            "or emitted out of order; write samplerate and constants directly or "
            "de-hoist with History one(1)"
        )

    def test_literal_alias(self, db):
        code = "Param size(1, min=0, max=2);\nRING = 1344000;\nx = size * RING;\nout1 = in1 * x;"
        res = _with(_run(code, db), "Param-only expression")
        assert len(res) == 1 and "'x' combines local alias(es) 'RING' with Param(s) 'size'" in res[0].message

    @pytest.mark.parametrize("code", [
        # de-hoisted form
        "Param freq(440, min=20, max=20000);\nHistory one(1);\nsrs = samplerate * one;\n"
        "k_freq = freq * one;\ninc = k_freq / srs;\nout1 = in1 * inc;",
        # direct form
        "Param freq(440, min=20, max=20000);\ninc = freq / samplerate;\nout1 = in1 * inc;",
        # alias assigned twice
        "Param freq(440, min=20, max=20000);\nsr = samplerate;\nsr = 44100;\n"
        "inc = freq / sr;\nout1 = in1 * inc;",
        # no Param
        "sr = samplerate;\ndt = 1.0 / sr;\nout1 = in1 * dt;",
        # unassigned constant
        "Param freq(440, min=20, max=20000);\ninc = twopi * freq;\nout1 = in1 * inc;",
    ])
    def test_not_flagged(self, code, db):
        assert _with(_run(code, db), "Param-only expression") == []


# ---------------------------------------------------------------------------
# Check 15: tanh(...)/tanh(...) normalization (D-04)
# ---------------------------------------------------------------------------

_TANH_ERR = (
    "Line 3: tanh(...)/tanh(...) normalization in a codebox with History/Delay "
    "state (a feedback path) -- the loop gain then moves with drive; normalize by "
    "the drive gain: tanh(x*g)/g"
)


class TestCheck15Tanh:
    def test_error_with_history(self, db):
        code = "Param drive(2, min=1, max=10);\nHistory h(0);\ny = tanh(in1 * drive) / tanh(drive);\nout1 = y;"
        res = _with(_run(code, db), "tanh(...)/tanh(...)")
        assert len(res) == 1
        assert res[0].level == "error"
        assert res[0].message == _TANH_ERR

    def test_error_with_delay(self, db):
        code = "Param drive(2, min=1, max=10);\nDelay d(100);\ny = tanh(in1 * drive) / tanh(drive);\nout1 = y;"
        (r,) = _with(_run(code, db), "tanh(...)/tanh(...)")
        assert r.level == "error"

    def test_warning_without_state(self, db):
        code = "Param drive(2, min=1, max=10);\nx = 0;\ny = tanh(in1 * drive) / tanh(drive);\nout1 = y + x;"
        (r,) = _with(_run(code, db), "tanh(...)/tanh(...)")
        assert r.level == "warning"
        assert r.message == (
            "Line 3: tanh(...)/tanh(...) normalization -- on a feedback path the "
            "loop gain moves with drive; prefer tanh(x*g)/g"
        )

    def test_nested_parens(self, db):
        code = "Param drive(2, min=1, max=10);\nHistory h(0);\ny = tanh((in1 + h) * drive) / tanh(drive);\nh = y;\nout1 = y;"
        (r,) = _with(_run(code, db), "tanh(...)/tanh(...)")
        assert r.level == "error"

    @pytest.mark.parametrize("line", [
        "y = tanh(in1 * g) / g;",
        "y = tanh(drive*in1) / max(tanh_drive, 0.001);",
        "y = in1; // tanh(in1 * g) / tanh(g)",
    ])
    def test_not_flagged(self, line, db):
        code = f"Param g(2, min=1, max=10);\nHistory h(0);\ntanh_drive = 1;\n{line}\nout1 = y;"
        assert _with(_run(code, db), "tanh(...)/tanh(...)") == []


# ---------------------------------------------------------------------------
# Check 16: style notes (info, D-06)
# ---------------------------------------------------------------------------

class TestCheck16Notes:
    def test_else_if(self, db):
        code = "y = 0;\nif (in1 > 0) {\n  y = 1;\n} else if (in1 < 0) {\n  y = 2;\n}\nout1 = y;"
        res = _with(_run(code, db), "'else if' chain")
        assert len(res) == 1
        assert res[0].level == "info"
        assert res[0].message == (
            "Line 4: 'else if' chain (1 in total) -- valid GenExpr; the proven-safe "
            "codebox set nests else { if ... } instead (precaution note)"
        )

    def test_else_if_in_comment(self, db):
        assert _with(_run("// } else if (x) {\nout1 = in1;", db), "'else if' chain") == []

    def test_peek_two_args(self, db):
        res = _with(_run("Buffer buf(\"b\");\nx = peek(buf, 0);\nout1 = x;", db), "2-argument peek")
        assert len(res) == 1
        assert res[0].level == "info"
        assert res[0].message == (
            "Line 2: 2-argument peek (1 in total) -- valid in MAX; the proven-safe "
            "codebox set passes the channel: peek(buf, idx, 0) (style note)"
        )

    def test_peek_kwarg_counts_as_two_positional(self, db):
        res = _with(_run('Buffer buf("b");\nx = peek(buf, 0, interp="none");\nout1 = x;', db),
                    "2-argument peek")
        assert len(res) == 1

    @pytest.mark.parametrize("call", [
        "peek(buf, 0, 0)",
        'peek(buf, 0, 0, boundmode="wrap")',
        "buf.peek(0)",
    ])
    def test_peek_not_flagged(self, call, db):
        code = f'Buffer buf("b");\nx = {call};\nout1 = x;'
        assert _with(_run(code, db), "2-argument peek") == []


# ---------------------------------------------------------------------------
# Severity contract (D-04, D-06)
# ---------------------------------------------------------------------------

_FAMILIES = [
    ("Tab character", "x = in1;\n\tout1 = x;", "error"),
    ("built-in constant", "pi = 3.14;\nout1 = in1;", "error"),
    ("is assigned as a local", "Param g(1, min=0, max=2);\ng = 2;\nout1 = in1 * g;", "error"),
    ("nested for loop", "s = 0;\nfor (i = 0; i < 4; i += 1) { for (j = 0; j < 4; j += 1) { s += j; } }\nout1 = s;", "warning"),
    ("is not a numeric literal", "Param n(4, min=1, max=8);\ns = 0;\nfor (i = 0; i < n; i += 1) { s += i; }\nout1 = s;", "warning"),
    ("Param-only expression", "Param f(1, min=0, max=2);\nsr = samplerate;\nk = f / sr;\nout1 = in1 * k;", "warning"),
    ("tanh(...)/tanh(...)", "Param d(2, min=1, max=4);\nHistory h(0);\ny = tanh(in1 * d) / tanh(d);\nout1 = y;", "error"),
    ("tanh(...)/tanh(...)", "Param d(2, min=1, max=4);\ny = tanh(in1 * d) / tanh(d);\nout1 = y;", "warning"),
    ("'else if' chain", "y = 0;\nif (in1 > 0) { y = 1; } else if (in1 < 0) { y = 2; }\nout1 = y;", "info"),
    ("2-argument peek", 'Buffer b("b");\nx = peek(b, 0);\nout1 = x;', "info"),
]


@pytest.mark.parametrize("fragment,code,level", _FAMILIES)
def test_severity_contract(fragment, code, level, db):
    res = _with(_run(code, db), fragment)
    assert res, fragment
    assert {r.level for r in res} == {level}
    assert all(r.level != "note" for r in _run(code, db))


# ---------------------------------------------------------------------------
# Robustness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code", [
    "",
    "// only a comment\n/* and a block */",
    "x = 1; /* unterminated",
    'Buffer b("unterminated',
    "out1 = (in1;",
    "for(;;){",
    "x = in1;\r\nfor (i = 0; i < 4; i += 1) {\r\n  x += i;\r\n}\r\nout1 = x;\r\n",
    "tanh(",
    "peek(",
    "a, = ;",
    "} else if",
])
def test_never_raises(code, db):
    assert isinstance(validate_genexpr(code, db=db), list)


def test_large_codebox_is_fast(db):
    lines = ["Param g(1, min=0, max=2);", "History h(0);", "sr = samplerate;"]
    for i in range(2000):
        if i % 50 == 0:
            lines.append(f"for (i{i} = 0; i{i} < 8; i{i} += 1) {{ h = h + 0.001; }}")
        else:
            lines.append(f"x{i} = in1 * g + {i} * 0.5 / sr;")
    lines.append("out1 = x1 + h;")
    code = "\n".join(lines)
    t0 = time.perf_counter()
    res = validate_genexpr(code, db=db)
    assert isinstance(res, list)
    assert time.perf_counter() - t0 < 2.0
