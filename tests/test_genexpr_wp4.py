"""GenExpr validator / reorder regressions (quick 261022-ud6 WP4, review-codegen.md).

- WR-03: functions before Param is Cycling '74's own form (gen.maxhelp,
  every shipped Gen codebox: functions, then declarations, then
  statements). Check 5 ignores function bodies; add_gen's reorder never
  moves declarations above function definitions; a function after a
  statement is an error (Max user guide, "Defining GenExpr Functions":
  functions must be declared before all statements).
- WR-04: phi and the upper-case constant aliases are built-in constants.
- IN-01: Checks 2 and 4 run on the Q22 statement parser.
- Q22 locked decision: tabs are an error in generated/edited code and a
  warning when already present in a loaded codebox.
"""

from __future__ import annotations

import warnings

import pytest

from src.maxpat.code_validation import validate_genexpr
from src.maxpat.codegen import reorder_genexpr_declarations
from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.genexpr_parse import CONSTANTS, function_defs, param_items


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _msgs(code, db, level=None, **kw):
    return [r.message for r in validate_genexpr(code, db=db, **kw)
            if level is None or r.level == level]


# gen.maxhelp's second codebox (Max 9.2 bundle), tabs replaced by spaces.
C74_HELP = (
    "// calculate the sum of the harmonics at a position\n"
    "calcSample(position, maximum)\n"
    "{\n"
    "    sum = 0;\n"
    "    for (j = 0; j < maximum; j += 1) {\n"
    "        sum += sin(position * (j+1) * TWOPI);\n"
    "    }\n"
    "    \n"
    "    return sum / maximum;\n"
    "}\n"
    "\n"
    "Param harmonic(1);\n"
    "Buffer waveform(\"waveform\");    // reference the buffer~ called \"waveform\"\n"
    "len = dim(waveform);            // get the number of samples in that buffer\n"
    "\n"
    "// iterate through every samples in the buffer\n"
    "for (i = 0; i < len; i += 1) {\n"
    "    tmp = calcSample(i/len, harmonic);    // call our function up there\n"
    "    poke(waveform, tmp, i);\n"
    "}\n"
    "\n"
    "out1 = i;\n"
)

REVIEW_REPRO = (
    "calc(x) {\n    y = x * 2;\n    return y;\n}\n\n"
    "Param g(0.5, min=0, max=1);\nout1 = calc(in1) * g;\n"
)


# ---------------------------------------------------------------------------
# WR-03
# ---------------------------------------------------------------------------


class TestFunctionsBeforeDeclarations:
    @pytest.mark.parametrize("code", [C74_HELP, REVIEW_REPRO], ids=["gen.maxhelp", "review"])
    def test_no_declaration_order_error(self, db, code):
        errors = _msgs(code, db, "error")
        assert not [m for m in errors if "appears after expression" in m], errors
        assert not [m for m in _msgs(code, db) if "function" in m and "defined" in m]

    def test_review_repro_does_not_block_a_save(self):
        from src.maxpat.hooks import _blocking_findings
        from src.maxpat.patcher import Patcher

        p = Patcher()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            p.add_gen(REVIEW_REPRO, x=50.0, y=50.0)
        found = _blocking_findings(p.to_dict(), is_new=True)
        assert not [r for r in found if "appears after expression" in str(getattr(r, "message", r))]

    def test_declaration_after_main_body_statement_still_errors(self, db):
        code = "calc(x) {\n    return x;\n}\nout1 = calc(in1);\nParam g(0.5, min=0, max=1);\n"
        errors = _msgs(code, db, "error")
        assert any("declaration 'Param g' appears after expression on line 4" in m for m in errors)

    def test_function_after_statement_is_an_error(self, db):
        code = "out1 = calc(in1);\ncalc(x) {\n    return x * 2;\n}\n"
        errors = _msgs(code, db, "error")
        assert any("function 'calc'" in m and "line 1" in m for m in errors), errors

    def test_function_after_declaration_is_a_warning(self, db):
        code = "Param g(0.5, min=0, max=1);\ncalc(x) {\n    return x * g;\n}\nout1 = calc(in1);\n"
        assert not [m for m in _msgs(code, db, "error") if "function" in m]
        assert any("function 'calc'" in m for m in _msgs(code, db, "warning"))

    def test_reorder_keeps_the_c74_form_byte_identical(self):
        assert reorder_genexpr_declarations(C74_HELP) == C74_HELP
        assert reorder_genexpr_declarations(REVIEW_REPRO) == REVIEW_REPRO

    def test_reorder_puts_declarations_after_leading_functions(self):
        code = ("// helper\ncalc(x) {\n    y = x * 2;\n    return y;\n}\n\n"
                "out1 = calc(in1) * g;\nParam g(0.5, min=0, max=1);\n")
        out = reorder_genexpr_declarations(code)
        assert out.index("calc(x) {") < out.index("Param g") < out.index("out1 =")
        assert out.startswith("// helper\ncalc(x) {")
        assert "y = x * 2;" in out and out.count("Param g") == 1

    def test_reorder_moves_functions_above_declarations(self):
        code = ("Param g(0.5, min=0, max=1);\n"
                "calc(x) {\n    return x * g;\n}\n"
                "out1 = calc(in1);\n")
        out = reorder_genexpr_declarations(code)
        assert out.index("calc(x) {") < out.index("Param g") < out.index("out1 =")

    def test_reordered_output_validates_clean(self, db):
        code = ("out1 = calc(in1) * g;\nParam g(0.5, min=0, max=1);\n"
                "calc(x) {\n    return x * 2;\n}\n")
        out = reorder_genexpr_declarations(code)
        assert not [m for m in _msgs(out, db) if "function" in m or "appears after" in m], out

    def test_add_gen_leaves_c74_form_alone(self):
        from src.maxpat.patcher import Patcher

        p = Patcher()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _box, inner = p.add_gen(C74_HELP)
        code = [e["box"]["code"] for e in p.to_dict()["patcher"]["boxes"][0]["box"]["patcher"]["boxes"]
                if e["box"].get("maxclass") == "codebox"]
        assert code == [C74_HELP]

    def test_function_defs_parser(self):
        defs = function_defs(C74_HELP)
        assert [(d.name, d.line) for d in defs] == [("calcSample", 2)]
        assert C74_HELP[defs[0].start:defs[0].end].endswith("}")
        assert C74_HELP[defs[0].start:defs[0].end].startswith("calcSample(")
        assert function_defs("if (x) {\n y = 1;\n}\nfor (i = 0; i < 4; i += 1) {\n}\n") == []
        assert function_defs(None) == []
        assert [d.name for d in function_defs("f(a) {\n return a;")] == ["f"]


# ---------------------------------------------------------------------------
# WR-04
# ---------------------------------------------------------------------------


class TestConstantAliases:
    @pytest.mark.parametrize("name", ["phi", "PHI", "PI", "TWOPI", "HALFPI", "INVPI", "E",
                                      "LN2", "LN10", "LOG10E", "LOG2E", "SQRT2", "SQRT1_2",
                                      "DEGTORAD", "RADTODEG"])
    def test_assignment_is_an_error(self, db, name):
        errors = _msgs(f"{name} = 0.5;\nout1 = in1 * {name};", db, "error")
        assert any(f"built-in constant '{name}'" in m for m in errors), errors

    def test_constants_set(self):
        assert {"phi", "PHI", "PI", "E", "TWOPI", "pi", "e"} <= CONSTANTS

    def test_reading_a_constant_is_fine(self, db):
        assert not _msgs("out1 = in1 * PHI + TWOPI;", db, "error")

    def test_phase_named_phase_is_fine(self, db):
        assert not _msgs("History phase(0);\nphase = wrap(phase + 0.01, 0, 1);\nout1 = phase;",
                         db, "error")


# ---------------------------------------------------------------------------
# IN-01: Checks 2 and 4 on the statement parser
# ---------------------------------------------------------------------------


class TestStatementBasedChecks:
    BASSOON = (
        "bf_out = bf_b0 * rad_in\n"
        "       + bf_b1 * bf_x1\n"
        "       - bf_a2 * bf_y2;\n"
        "rad_out = b0 * bf_out\n"
        "        + b1 * bell_x1;\n"
        "out1 = rad_out;\n"
    )

    def test_operator_continuation_is_not_a_missing_semicolon(self, db):
        assert not [m for m in _msgs(self.BASSOON, db) if "semicolon" in m]

    def test_allman_function_header_is_not_a_missing_semicolon(self, db):
        code = "f(x) // helper\n{\n    return x * 2;\n}\nout1 = f(in1);\n"
        assert not [m for m in _msgs(code, db) if "semicolon" in m]
        assert not [m for m in _msgs(C74_HELP, db) if "semicolon" in m]

    def test_braceless_if_on_two_lines_is_fine(self, db):
        code = "y = 0;\nif (in1 > 0)\n    y = 1;\nout1 = y;\n"
        assert not [m for m in _msgs(code, db) if "semicolon" in m]

    @pytest.mark.parametrize("code, line", [
        ("x = in1 * 2\nout1 = x;\n", 1),
        ("x = in1 * 2;\nout1 = x\n", 2),
        ("y = 0;\nif (in1 > 0) {\n    y = 1\n}\nout1 = y;\n", 3),
        ("foo = in1\nHistory h(0);\nout1 = foo;\n", 1),
    ])
    def test_real_missing_semicolon_warns(self, db, code, line):
        assert any(m.startswith(f"Line {line}: possible missing semicolon") for m in _msgs(code, db))

    def test_param_with_call_default_keeps_its_range(self, db):
        code = "Param g(max(1, 2), min=0, max=10);\nout1 = in1 * g;\n"
        assert not [m for m in _msgs(code, db) if "missing min/max" in m]

    @pytest.mark.parametrize("code", [
        "Param g(0.5);\nout1 = in1 * g;\n",
        "Param g(0.5, min=0);\nout1 = in1 * g;\n",
        "Param a(1, min=0, max=2), b(3);\nout1 = a + b;\n",
    ])
    def test_param_without_range_still_warns(self, db, code):
        assert [m for m in _msgs(code, db) if "missing min/max" in m]

    def test_param_items(self):
        items = param_items("Param a(1, min=0, max=2), b(max(1,2), min = 0);\n// Param c(1);\n")
        assert [(i.name, i.kwargs) for i in items] == [("a", ("min", "max")), ("b", ("min",))]
        assert param_items(None) == []


# ---------------------------------------------------------------------------
# Tabs (Q22 locked decision)
# ---------------------------------------------------------------------------


class TestTabsLoadedVsEdited:
    TABBED = "x = in1;\n\ty = x * 2;\nout1 = y;\n"

    def test_generated_code_with_tabs_is_an_error(self, db):
        assert any("Tab character" in m for m in _msgs(self.TABBED, db, "error"))

    def test_loaded_unchanged_codebox_with_tabs_is_a_warning(self, db):
        res = validate_genexpr(self.TABBED, db=db, original=self.TABBED)
        assert not [r for r in res if r.level == "error" and "Tab" in r.message]
        assert [r for r in res if r.level == "warning" and "Tab" in r.message]

    def test_new_tab_in_an_edited_codebox_is_an_error(self, db):
        edited = self.TABBED + "\tz = y;\n"
        res = validate_genexpr(edited, db=db, original=self.TABBED)
        errors = [r.message for r in res if r.level == "error" and "Tab" in r.message]
        warns = [r.message for r in res if r.level == "warning" and "Tab" in r.message]
        assert errors and "line(s) 4" in errors[0]
        assert warns and "line(s) 2" in warns[0]

    def test_original_without_tabs_keeps_error(self, db):
        res = validate_genexpr(self.TABBED, db=db, original="x = in1;\nout1 = x;\n")
        assert [r for r in res if r.level == "error" and "Tab" in r.message]

    def test_c74_help_as_loaded_has_no_tab_error(self, db):
        tabbed = C74_HELP.replace("    ", "\t")
        res = validate_genexpr(tabbed, db=db, original=tabbed)
        assert not [r for r in res if r.level == "error"], [r.message for r in res if r.level == "error"]
