"""Tests for the single GenExpr tokenizer/statement parser (Q22 / S5) and the
callers that switched to it: parse_genexpr_io (G2),
reorder_genexpr_declarations (G1), parse_genexpr_params (G4) and the
mask-based Checks 1-9 of validate_genexpr.

The parser is imported lazily inside each test so a missing module fails per
test, not at collection.
"""

from __future__ import annotations

import collections
import glob
import json
import re
import warnings
from pathlib import Path

import pytest

from src.maxpat.db_lookup import ObjectDatabase

_REPO_ROOT = Path(__file__).resolve().parent.parent

_MALFORMED = [
    "",
    None,
    "for(;;){",
    "out1 = (in1;",
    "x = in1;\r\nout1 = x;\r\n",
    "*/",
    "/* unterminated",
    'Buffer b("unterminated',
    "}}}{",
    ")))(((",
]


@pytest.fixture(scope="module")
def db() -> ObjectDatabase:
    return ObjectDatabase()


# ---------------------------------------------------------------------------
# mask
# ---------------------------------------------------------------------------

class TestMask:
    def test_length_and_newlines_kept(self):
        from src.maxpat.genexpr_parse import mask

        code = "x = 1; // c\n/* a\r\nb */ y = 2;\n"
        m = mask(code)
        assert len(m) == len(code)
        assert [i for i, c in enumerate(code) if c in "\r\n"] == [
            i for i, c in enumerate(m) if c in "\r\n"
        ]

    def test_line_and_block_comments_blanked(self):
        from src.maxpat.genexpr_parse import mask

        m = mask("a = 1; // in9 here\n/* out7 */ b = 2;")
        assert "in9" not in m
        assert "out7" not in m
        assert "a = 1;" in m
        assert "b = 2;" in m
        assert "//" not in m and "/*" not in m and "*/" not in m

    def test_crlf_block_comment(self):
        from src.maxpat.genexpr_parse import mask

        code = "/* in3\r\n out4 */\r\nout1 = in1;\r\n"
        m = mask(code)
        assert "in3" not in m and "out4" not in m
        assert "out1 = in1;" in m
        assert m.count("\r\n") == code.count("\r\n")

    def test_string_contents_blanked_quotes_kept(self):
        from src.maxpat.genexpr_parse import mask

        code = 'Buffer b("http://x"); y = 1;'
        m = mask(code)
        assert m.startswith('Buffer b("')
        assert "http" not in m
        assert m.count('"') == 2
        # `//` inside a string is not a comment: code after it survives.
        assert m.endswith("); y = 1;")

    def test_inert_markers(self):
        from src.maxpat.genexpr_parse import mask

        # `"` inside a comment and `/*` inside a // comment are inert.
        code = '// say "hi /* not a block\nx = 1;\n/* " */ y = 2;'
        m = mask(code)
        assert "x = 1;" in m
        assert "y = 2;" in m

    def test_unterminated_runs_to_eof(self):
        from src.maxpat.genexpr_parse import mask

        assert mask("x = 1; /* a\nb = 2;").strip() == "x = 1;"
        m = mask('x = "abc\ny = 2;')
        assert "y = 2" not in m
        assert len(m) == len('x = "abc\ny = 2;')

    @pytest.mark.parametrize("code", _MALFORMED)
    def test_never_raises(self, code):
        from src.maxpat.genexpr_parse import mask

        m = mask(code)
        assert isinstance(m, str)
        assert len(m) == len(code if isinstance(code, str) else "")


# ---------------------------------------------------------------------------
# statements / declarations
# ---------------------------------------------------------------------------

class TestStatements:
    def test_for_header_is_one_statement(self):
        from src.maxpat.genexpr_parse import statements

        code = "for (i = 0; i < 4; i += 1) {\n  x = i;\n}\n"
        st = statements(code)
        headers = [s for s in st if s.kind == "header"]
        assert len(headers) == 1
        assert headers[0].parents == ()
        assert code[headers[0].start:headers[0].end] == "for (i = 0; i < 4; i += 1) {"
        inner = [s for s in st if s.kind == "assign"]
        assert len(inner) == 1
        assert inner[0].parents == ("for",)
        assert inner[0].depth == 1
        assert inner[0].line == 2

    def test_multiline_param_is_one_decl(self):
        from src.maxpat.genexpr_parse import statements

        code = "x = in1;\nParam g(0.5,\n  min=0, max=1);\nout1 = x * g;\n"
        st = statements(code)
        decls = [s for s in st if s.kind == "decl"]
        assert len(decls) == 1
        assert code[decls[0].start:decls[0].end] == "Param g(0.5,\n  min=0, max=1);"
        assert decls[0].line == 2
        assert decls[0].terminated is True

    def test_unterminated_trailing_statement(self):
        from src.maxpat.genexpr_parse import statements

        code = 'out1 = in1;\nrequire("lib")'
        st = statements(code)
        assert len(st) == 2
        assert st[-1].terminated is False
        assert code[st[-1].start:st[-1].end] == 'require("lib")'

    def test_unterminated_before_close_brace(self):
        from src.maxpat.genexpr_parse import statements

        st = statements("if (a) { y = 1 }\nout1 = y;")
        texts = [(s.kind, s.text.strip(), s.terminated) for s in st]
        assert ("assign", "y = 1", False) in texts

    def test_depth_never_negative(self):
        from src.maxpat.genexpr_parse import statements

        st = statements("}}} x = 1; } y = 2;")
        assert all(s.depth >= 0 for s in st)
        assert [s.text.strip() for s in st] == ["x = 1;", "y = 2;"]

    def test_parents_keywords(self):
        from src.maxpat.genexpr_parse import statements

        code = (
            "myfn(a) {\n  return a;\n}\n"
            "if (x > 1) {\n  y = 1;\n} else {\n  y = 2;\n}\n"
            "while (k < 3) { k += 1; }\n"
        )
        st = statements(code)
        by_text = {s.text.strip(): s for s in st}
        assert by_text["return a;"].parents == ("func",)
        assert by_text["y = 1;"].parents == ("if",)
        assert by_text["y = 2;"].parents == ("else",)
        assert by_text["k += 1;"].parents == ("while",)

    def test_kinds(self):
        from src.maxpat.genexpr_parse import statements

        st = statements(
            "History h(0);\nx = 1;\ny += 2;\nd.write(x);\nif (x == 1) {\n}\nz <= 3;"
        )
        kinds = [s.kind for s in st]
        assert kinds == ["decl", "assign", "assign", "expr", "header", "expr"]

    def test_declarations_comma_list(self):
        from src.maxpat.genexpr_parse import declarations

        decls = declarations("History a(0), b(0);\nParam g(1, min=0, max=2);\n")
        assert [(t, names) for t, names, _s in decls] == [
            ("History", ["a", "b"]), ("Param", ["g"])
        ]

    def test_declarations_ignore_comments(self):
        from src.maxpat.genexpr_parse import declarations

        assert declarations("// History a(0);\n/* Param p(1); */\nx = 1;") == []

    @pytest.mark.parametrize("code", _MALFORMED)
    def test_never_raises(self, code):
        from src.maxpat import genexpr_parse as gp

        assert isinstance(gp.statements(code), list)
        assert isinstance(gp.declarations(code), list)
        assert isinstance(gp.parse_params(code), list)
        assert isinstance(gp.assigned_names(code), dict)
        assert isinstance(gp.io_counts(code), tuple)
        assert isinstance(gp.line_paren_depths(code), list)
        assert isinstance(gp.split_args(code), list)


class TestAssignedNames:
    def test_operators(self):
        from src.maxpat.genexpr_parse import assigned_names

        a = assigned_names("x = 1;\ny += 2;\nz -= 1;\nw *= 2;\nv /= 2;\n")
        assert a == {"x": [1], "y": [2], "z": [3], "w": [4], "v": [5]}

    def test_comma_lhs(self):
        from src.maxpat.genexpr_parse import assigned_names

        a = assigned_names("a, b = peek(buf, 0, 0);")
        assert a == {"a": [1], "b": [1]}

    def test_for_header_init_and_increment(self):
        from src.maxpat.genexpr_parse import assigned_names

        a = assigned_names("for (i = 0; i < 4; i += 1) {\n  s = s + i;\n}")
        assert a["i"] == [1, 1]
        assert a["s"] == [2]

    def test_single_line_if(self):
        from src.maxpat.genexpr_parse import assigned_names

        a = assigned_names("if (c) y = 1;\nelse z = 2;")
        assert a == {"y": [1], "z": [2]}

    def test_exclusions(self):
        from src.maxpat.genexpr_parse import assigned_names

        a = assigned_names(
            "Param g(1, min=20, max=30);\n"
            "History h(0);\n"
            "if (x == 1) { }\n"
            "q = x <= 3;\n"
            "r = peek(buf, i, 0, interp=\"none\");\n"
            "// fake = 1;\n"
        )
        assert set(a) == {"q", "r"}


# ---------------------------------------------------------------------------
# G2: I/O detection ignores comments
# ---------------------------------------------------------------------------

class TestIoG2:
    def test_line_comment_ignored(self):
        from src.maxpat.codegen import parse_genexpr_io

        assert parse_genexpr_io("// mix in4 and out3\nout1 = in1;") == (1, 1)

    def test_block_comment_ignored(self):
        from src.maxpat.codegen import parse_genexpr_io

        assert parse_genexpr_io("/* in9\nout9 */\nout2 = in1;") == (1, 2)

    def test_io_counts_ignores_strings(self):
        from src.maxpat.genexpr_parse import io_counts

        assert io_counts('Buffer b("in5 out6");\nout1 = in2;') == (2, 1)


# ---------------------------------------------------------------------------
# G1: reorder
# ---------------------------------------------------------------------------

def _collapsed_stmts(code):
    from src.maxpat.genexpr_parse import statements

    return [" ".join(s.text.split()) for s in statements(code)]


class TestReorderG1:
    def test_commented_declaration_stays_in_comment(self):
        from src.maxpat.codegen import reorder_genexpr_declarations
        from src.maxpat.genexpr_parse import declarations

        code = (
            "x = in1;\n"
            "/*\n"
            "History old(0);\n"
            "*/\n"
            "History h(0);\n"
            "out1 = x + h;\n"
        )
        result = reorder_genexpr_declarations(code)
        assert "x = in1;\n/*\nHistory old(0);\n*/\n" in result
        assert result.index("History h(0);") < result.index("x = in1;")
        assert [names for _t, names, _s in declarations(result)] == [["h"]]

    def test_multiline_param_moves_verbatim(self):
        from src.maxpat.codegen import reorder_genexpr_declarations
        from src.maxpat.genexpr_parse import declarations

        code = "x = in1;\nParam g(0.5,\n  min=0, max=1);\nout1 = x * g;\n"
        result = reorder_genexpr_declarations(code)
        assert result.startswith("Param g(0.5,\n  min=0, max=1);\n")
        assert result.index("Param g") < result.index("x = in1;")
        assert [names for _t, names, _s in declarations(result)] == [["g"]]

    def test_comment_above_moves_with_declaration(self):
        from src.maxpat.codegen import reorder_genexpr_declarations

        code = "x = in1;\n// state\nHistory h(0);\nout1 = x + h;\n"
        result = reorder_genexpr_declarations(code)
        assert "// state\nHistory h(0);\n" in result
        assert result.index("// state") < result.index("x = in1;")

    def test_four_histories_on_one_line(self):
        from src.maxpat.codegen import reorder_genexpr_declarations

        code = (
            "Param p(1, min=0, max=2);\n"
            "x = in1 * p;\n"
            "History a(0); History b(0); History c(0); History d(0);\n"
            "out1 = x + a + b + c + d;\n"
        )
        result = reorder_genexpr_declarations(code)
        for name in "abcd":
            assert result.index(f"History {name}(0);") < result.index("x = in1")
        lines = result.split("\n")
        # The only whitespace-only lines are the separator and the final "".
        blanks = [i for i, ln in enumerate(lines) if not ln.strip()]
        assert len(blanks) == 2
        assert blanks[-1] == len(lines) - 1

    def test_function_body_declaration_not_moved(self):
        from src.maxpat.codegen import reorder_genexpr_declarations

        code = (
            "x = in1;\n"
            "myfn(v) {\n"
            "  History h(0);\n"
            "  h = v;\n"
            "  return h;\n"
            "}\n"
            "out1 = myfn(x);\n"
        )
        assert reorder_genexpr_declarations(code) == code

    def test_statement_order_and_multiset_preserved(self):
        from src.maxpat.codegen import reorder_genexpr_declarations

        code = (
            "Param a(1, min=0, max=2);\n"
            "x = in1 * a;  // scale\n"
            "History h(0); // state\n"
            "y = x + h;\n"
            "Delay d(100);\n"
            "Param b(0.5,\n   min=0,\n   max=1);\n"
            "d.write(y);\n"
            "h = y;\n"
            "out1 = d.read(10) * b;\n"
        )
        result = reorder_genexpr_declarations(code)
        before = _collapsed_stmts(code)
        after = _collapsed_stmts(result)
        assert collections.Counter(before) == collections.Counter(after)
        nondecl = lambda xs: [s for s in xs if not re.match(  # noqa: E731
            r"(Param|History|Delay|Buffer|Data)\s", s)]
        assert nondecl(before) == nondecl(after)
        # Grouped Param, History, Delay; all before the first expression.
        idx = {k: result.index(k) for k in ("Param a", "Param b", "History h", "Delay d", "x = in1")}
        assert idx["Param a"] < idx["Param b"] < idx["History h"] < idx["Delay d"] < idx["x = in1"]
        assert "History h(0); // state\n" in result

    def test_identity_when_nothing_moves(self):
        from src.maxpat.codegen import reorder_genexpr_declarations

        for code in (
            "Param g(1,\n  min=0, max=2);\n\n// x = 1;\nHistory h(0);\nout1 = in1;",
            "/* y = 2; */\nHistory h(0);\nout1 = h;",
            "",
        ):
            assert reorder_genexpr_declarations(code) == code

    @pytest.mark.parametrize("code", [c for c in _MALFORMED if c is not None])
    def test_never_raises(self, code):
        from src.maxpat.codegen import reorder_genexpr_declarations

        assert isinstance(reorder_genexpr_declarations(code), str)


# ---------------------------------------------------------------------------
# G4: Param parsing
# ---------------------------------------------------------------------------

class TestParamsG4:
    def test_missing_max_is_none(self):
        from src.maxpat.rnbo import parse_genexpr_params

        assert parse_genexpr_params("Param freq(440, min=20);") == [
            {"name": "freq", "default": 440.0, "min": 20.0, "max": None}
        ]

    def test_whitespace_before_semicolon(self):
        from src.maxpat.rnbo import parse_genexpr_params

        assert parse_genexpr_params("Param g(0.5) ;") == [
            {"name": "g", "default": 0.5, "min": None, "max": None}
        ]

    def test_non_literal_default(self):
        from src.maxpat.rnbo import parse_genexpr_params

        assert parse_genexpr_params("Param h(samplerate*0.25, min=0, max=24000);") == [
            {"name": "h", "default": None, "min": 0.0, "max": 24000.0}
        ]

    def test_multiline_with_spaces(self):
        from src.maxpat.rnbo import parse_genexpr_params

        assert parse_genexpr_params("Param k(1,\n  min = -1,\n  max = 2);") == [
            {"name": "k", "default": 1.0, "min": -1.0, "max": 2.0}
        ]

    def test_commented_out_ignored(self):
        from src.maxpat.rnbo import parse_genexpr_params

        assert parse_genexpr_params("// Param z(1);\n/* Param y(1); */\nout1 = in1;") == []

    def test_comma_list(self):
        from src.maxpat.rnbo import parse_genexpr_params

        assert parse_genexpr_params("Param a(1, min=0, max=2), b(3);") == [
            {"name": "a", "default": 1.0, "min": 0.0, "max": 2.0},
            {"name": "b", "default": 3.0, "min": None, "max": None},
        ]

    def test_explicit_bounds_unchanged(self):
        from src.maxpat.rnbo import parse_genexpr_params

        assert parse_genexpr_params(
            "Param freq(440, min=20, max=20000);\nParam gain(0.5, min=0, max=1);"
        ) == [
            {"name": "freq", "default": 440.0, "min": 20.0, "max": 20000.0},
            {"name": "gain", "default": 0.5, "min": 0.0, "max": 1.0},
        ]

    def test_scientific_literal(self):
        from src.maxpat.genexpr_parse import parse_params

        assert parse_params("Param t(1e3, min=-0.5, max=.5);") == [
            {"name": "t", "default": 1000.0, "min": -0.5, "max": 0.5}
        ]


class TestAddRnboNoneBounds:
    def test_none_bounds_are_omitted(self):
        from src.maxpat.patcher import Patcher
        from src.maxpat.rnbo import add_rnbo

        _box, inner = add_rnbo(
            Patcher(),
            params=[{"name": "g", "default": 0.5, "min": None, "max": None}],
            audio_ins=1, audio_outs=1,
        )
        (pbox,) = [b for b in inner.boxes if b.name == "param"]
        assert "@initial 0.5" in pbox.text
        assert "None" not in pbox.text
        assert "@min" not in pbox.text
        assert "@max" not in pbox.text

    def test_missing_keys_keep_defaults(self):
        from src.maxpat.patcher import Patcher
        from src.maxpat.rnbo import add_rnbo

        _box, inner = add_rnbo(Patcher(), params=[{"name": "g"}], audio_ins=1, audio_outs=1)
        (pbox,) = [b for b in inner.boxes if b.name == "param"]
        assert pbox.text == "param @name g @min 0.0 @max 1.0 @initial 0.0"


# ---------------------------------------------------------------------------
# validate_genexpr Checks 1-9 on the mask
# ---------------------------------------------------------------------------

class TestValidateOnMask:
    def test_braces_and_delay_in_block_comment(self, db):
        from src.maxpat.code_validation import validate_genexpr

        code = "/* if (x) { delay(4) */\nout1 = in1;\n"
        msgs = [r.message for r in validate_genexpr(code, db=db)]
        assert not any("Unbalanced braces" in m for m in msgs)
        assert not any("delay()" in m for m in msgs)

    def test_multiline_param_no_check2_or_check5(self, db):
        from src.maxpat.code_validation import validate_genexpr

        code = "Param g(0.5,\n  min=0, max=1);\nHistory h(0);\nout1 = in1 * g + h;\n"
        res = validate_genexpr(code, db=db)
        assert not any("missing semicolon" in r.message for r in res)
        assert not any(r.level == "error" for r in res), [r.message for r in res]

    def test_missing_semicolon_still_warns(self, db):
        from src.maxpat.code_validation import validate_genexpr

        res = validate_genexpr("x = in1 * 2\nout1 = x", db=db)
        assert any("missing semicolon" in r.message for r in res)

    def test_trailing_comment_is_not_missing_semicolon(self, db):
        from src.maxpat.code_validation import validate_genexpr

        res = validate_genexpr("x = in1 * 2; // gain\nout1 = x;", db=db)
        assert not any("missing semicolon" in r.message for r in res)

    @pytest.mark.parametrize("code", [c for c in _MALFORMED if c is not None])
    def test_never_raises(self, code, db):
        from src.maxpat.code_validation import validate_genexpr

        assert isinstance(validate_genexpr(code, db=db), list)


# ---------------------------------------------------------------------------
# Tracer: end to end through add_gen
# ---------------------------------------------------------------------------

_TRACER_CODE = (
    "// mix in4 and out3\n"
    "x = in1;\n"
    "/* History old(0); */\n"
    "Param g(0.5,\n"
    "  min=0, max=1);\n"
    "History h(0);\n"
    "out1 = x * g + h;\n"
)


class TestAddGenTracer:
    def test_add_gen_end_to_end(self):
        from src.maxpat.patcher import Patcher
        from src.maxpat.validation import validate_patch

        p = Patcher()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            box, inner = p.add_gen(_TRACER_CODE)
        gen_warnings = [
            w for w in caught
            if issubclass(w.category, UserWarning) and str(w.message).startswith("GenExpr:")
        ]
        assert gen_warnings == [], [str(w.message) for w in gen_warnings]

        (cb,) = [b for b in inner.boxes if b.maxclass == "codebox"]
        assert (cb.numinlets, cb.numoutlets) == (1, 1)
        code = cb.extra_attrs["code"]
        assert "/* History old(0); */" in code
        assert code.index("Param g(0.5,\n  min=0, max=1);") < code.index("x = in1;")
        assert code.index("History h(0);") < code.index("x = in1;")
        assert code.index("x = in1;") < code.index("/* History old(0); */")

        errors = [r for r in validate_patch(p.to_dict()) if r.level == "error"]
        assert errors == [], [r.message for r in errors]


# ---------------------------------------------------------------------------
# Corpus identity over every committed codebox
# ---------------------------------------------------------------------------

def _walk(boxes, out):
    if not isinstance(boxes, list):
        return
    for entry in boxes:
        box = entry.get("box") if isinstance(entry, dict) else None
        if not isinstance(box, dict):
            continue
        if box.get("maxclass") == "codebox" and isinstance(box.get("code"), str):
            out.append(box["code"])
        data = box.get("data")
        for inner in (box.get("patcher"), data.get("patcher") if isinstance(data, dict) else None):
            if isinstance(inner, dict):
                _walk(inner.get("boxes"), out)


def _committed_codes():
    files = set()
    for pat in ("patches/**/*.maxpat", "patches/**/*.maxhelp", "patches/**/*.gendsp",
                "patterns/gen/**/*.gendsp"):
        files.update(glob.glob(str(_REPO_ROOT / pat), recursive=True))
    codes = []
    for f in sorted(files):
        try:
            with open(f) as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(d, dict) and isinstance(d.get("patcher"), dict):
            _walk(d["patcher"].get("boxes"), codes)
    return codes


class TestCorpusIdentity:
    def test_reorder_identity_and_io(self):
        from src.maxpat.codegen import parse_genexpr_io, reorder_genexpr_declarations

        codes = _committed_codes()
        if not codes:
            pytest.skip("no committed codeboxes")
        for code in codes:
            assert reorder_genexpr_declarations(code) == code
            raw_in = max((int(n) for n in re.findall(r"\bin(\d+)\b", code)), default=0)
            raw_out = max((int(n) for n in re.findall(r"\bout(\d+)\b", code)), default=0)
            assert parse_genexpr_io(code) == (raw_in, raw_out)
