"""validate_js ES5 lint scoped by engine (Q22 / R6, D-01..D-03), comment-aware
inlets/outlets parsing (the js part of G8), and validate_code_file engine
resolution from the project's .maxpat files (D-02).
"""

from __future__ import annotations

import json
import warnings

import pytest

_HEADER = "inlets = 1;\noutlets = 1;\nfunction bang() {}\n"

# (form text in the message, ES6 line, line number of that line)
_FORMS = [
    ("'const'", "const a = 1;"),
    ("'let'", "let a = 1;"),
    ("'=>' (arrow function)", "var g = (x) => x;"),
    ("template literal", "var s = `hi`;"),
    ("'class'", "class A {}"),
    ("default parameter", "function f(a, b = 2) {}"),
]


def _es6(results):
    return [r for r in results if "ES6 syntax" in r.message]


def _code(line):
    return _HEADER + line + "\n"


# ---------------------------------------------------------------------------
# D-01: ES6 forms by engine
# ---------------------------------------------------------------------------

class TestEs6ByEngine:
    @pytest.mark.parametrize("engine", ["js", "jsui"])
    @pytest.mark.parametrize("form,line", _FORMS)
    def test_error_for_legacy_engine(self, form, line, engine):
        from src.maxpat.code_validation import validate_js

        res = _es6(validate_js(_code(line), engine=engine))
        assert len(res) == 1, [r.message for r in res]
        assert res[0].level == "error"
        assert res[0].message == (
            f"ES6 syntax {form} on line 4 (1 in total) -- js/jsui run the Legacy "
            f"Engine (ES5), which rejects it; rewrite in ES5 or load the file "
            f"with v8/v8ui"
        )

    @pytest.mark.parametrize("engine", ["v8", "v8ui"])
    @pytest.mark.parametrize("form,line", _FORMS)
    def test_nothing_for_v8(self, form, line, engine):
        from src.maxpat.code_validation import validate_js

        assert _es6(validate_js(_code(line), engine=engine)) == []

    @pytest.mark.parametrize("form,line", _FORMS)
    def test_info_when_engine_unknown(self, form, line):
        from src.maxpat.code_validation import validate_js

        for res in (validate_js(_code(line), engine=None), validate_js(_code(line))):
            es6 = _es6(res)
            assert len(es6) == 1
            assert es6[0].level == "info"
            assert es6[0].message.startswith("ES6 syntax found (")
            assert form in es6[0].message
            assert "first on line 4" in es6[0].message

    def test_one_error_per_form_with_count(self):
        from src.maxpat.code_validation import validate_js

        code = _HEADER + "const a = 1;\nconst b = 2;\nvar f = x => x;\n"
        res = _es6(validate_js(code, engine="js"))
        assert len(res) == 2
        assert any("'const' on line 4 (2 in total)" in r.message for r in res)
        assert any("'=>' (arrow function) on line 6 (1 in total)" in r.message for r in res)

    def test_unknown_engine_single_info_lists_forms(self):
        from src.maxpat.code_validation import validate_js

        code = _HEADER + "let a = 1;\nconst b = 2;\n"
        (r,) = _es6(validate_js(code))
        assert r.level == "info"
        assert r.message == (
            "ES6 syntax found ('const', 'let'; first on line 4) -- legal in v8/v8ui "
            "only; an error if js/jsui loads this file (engine unknown)"
        )


class TestNoFalseEs6:
    @pytest.mark.parametrize("line", [
        'var s = "const x = () => 1";',
        "var t = 'let y = `z`';",
        "// let x = 1",
        "/* class A {} */",
        "obj.class = 2;",
        "var letter = 1;",
        "if (a >= 1 && b == 2 && c <= 3) {}",
        "function f(a, b) { return a == b; }",
        "function g(a) { return a != 1 && a <= 2 && a >= 0; }",
    ])
    def test_not_flagged(self, line):
        from src.maxpat.code_validation import validate_js

        assert _es6(validate_js(_code(line), engine="js")) == []


# ---------------------------------------------------------------------------
# G8 (js): inlets/outlets in comments are not declarations
# ---------------------------------------------------------------------------

class TestCommentAwareDeclarations:
    def test_commented_declarations_missing(self):
        from src.maxpat.code_validation import validate_js

        res = validate_js("// inlets = 2\n// outlets = 1\nfunction bang() {}")
        msgs = [r.message for r in res if r.level == "error"]
        assert "Missing 'inlets' declaration (required for js object)" in msgs
        assert "Missing 'outlets' declaration (required for js object)" in msgs

    def test_block_comment_outlets_ignored(self):
        from src.maxpat.code_validation import validate_js

        code = "/* outlets = 3 */\ninlets = 1;\noutlets = 1;\nfunction bang() { outlet(2, 1); }"
        res = validate_js(code)
        assert any(
            r.level == "error" and "outlet() index 2 out of bounds" in r.message
            and "declared outlets = 1" in r.message
            for r in res
        )

    def test_commented_outlet_call_not_checked(self):
        from src.maxpat.code_validation import validate_js

        code = "inlets = 1;\noutlets = 1;\nfunction bang() {\n  // outlet(5, x)\n  outlet(0, 1);\n}"
        res = validate_js(code)
        assert not any("out of bounds" in r.message for r in res)

    def test_commented_handler_not_found(self):
        from src.maxpat.code_validation import validate_js

        res = validate_js("inlets = 1;\noutlets = 1;\n// function bang() {}\n")
        assert any(r.level == "warning" and "No handler functions" in r.message for r in res)


class TestJsRobustness:
    @pytest.mark.parametrize("code", [
        "", "`", 'var s = "unterminated', "var s = 'unterminated", "/* unterminated",
        "var t = `unterminated ${x", "inlets = 1;\noutlets = 1;\n//", "\\",
        None,
    ])
    @pytest.mark.parametrize("engine", [None, "js", "v8"])
    def test_never_raises(self, code, engine):
        from src.maxpat.code_validation import validate_js

        assert isinstance(validate_js(code, engine=engine), list)


# ---------------------------------------------------------------------------
# Q22-fix CR-01 (D-02): regex literals in the js mask
# ---------------------------------------------------------------------------

_BT = "`"
_BS = "\\"
_REPRO_QUOTE = 'var s = x.replace(/"/g, "");\noutlets = 1;\nfunction bang() { outlet(3, 1); }'
_REPRO_BACKTICK = "inlets = 1;\noutlets = 1;\nvar r = /" + _BT + "/;\nfunction bang() { outlet(3, 1); }"
_REPRO_SLASHES = "inlets = 1;\noutlets = 1;\nfunction bang() { var re = " + r"/\/\//" + "; outlet(3, 1); }"


def _in_bang(stmt):
    return "inlets = 1;\noutlets = 1;\nfunction bang() { " + stmt + " }"


def _oob_found(results):
    hits = [
        r for r in results
        if r.level == "error" and "outlet() index 3 out of bounds" in r.message
        and "declared outlets = 1" in r.message
    ]
    return len(hits) == 1


class TestRegexLiterals:
    def test_review_repro_quote_in_regex(self):
        from src.maxpat.code_validation import validate_js

        res = validate_js(_REPRO_QUOTE, engine="js")
        msgs = [r.message for r in res]
        assert "Missing 'outlets' declaration (required for js object)" not in msgs
        assert not any("No handler functions found" in m for m in msgs)
        assert "Handler functions found: bang" in msgs
        assert _oob_found(res)

    @pytest.mark.parametrize("engine", ["js", "jsui"])
    def test_review_repro_backtick_in_regex(self, engine):
        from src.maxpat.code_validation import validate_js

        res = validate_js(_REPRO_BACKTICK, engine=engine)
        assert _es6(res) == []
        assert "Handler functions found: bang" in [r.message for r in res]
        assert _oob_found(res)

    def test_review_repro_escaped_slashes(self):
        from src.maxpat.code_validation import validate_js

        assert _REPRO_SLASHES.count("/\\/\\//") == 1
        assert _oob_found(validate_js(_REPRO_SLASHES, engine="js"))

    @pytest.mark.parametrize("prefix", [
        "return", "typeof", "case", "x =", "f(", "a,", "c ?", "!", "a &&",
        "{", ";", "}",
    ])
    def test_regex_after_keyword_or_punctuation(self, prefix):
        from src.maxpat.code_validation import validate_js

        stmt = prefix + ' /"/.test(s); outlet(3, 1);'
        assert _oob_found(validate_js(_in_bang(stmt), engine="js"))

    @pytest.mark.parametrize("division", [
        "var h = a / 2;",
        "var h = 10 / 2;",
        "var h = 1.5 / 2;",
        "var h = f(a) / 2;",
        "var h = arr[0] / 2;",
        "var h = a.b / 2;",
        "var h = 4; h /= 2;",
        "var h = a /* c */ / 2;",
        'var h = "s" / 2;',
        "var h = returned / 2;",
    ])
    def test_division_is_not_regex(self, division):
        from src.maxpat.code_validation import validate_js

        stmt = division + ' var q = "/"; outlet(3, h);'
        assert _oob_found(validate_js(_in_bang(stmt), engine="js"))

    def test_slash_inside_character_class(self):
        from src.maxpat.code_validation import validate_js

        stmt = 'var re = /[/"]/g; outlet(3, 1);'
        assert _oob_found(validate_js(_in_bang(stmt), engine="js"))

    def test_unterminated_regex_recovers_at_line_end(self):
        from src.maxpat.code_validation import validate_js

        code = 'var re = /"abc\ninlets = 1;\noutlets = 1;\nfunction bang() { outlet(3, 1); }'
        res = validate_js(code, engine="js")
        msgs = [r.message for r in res]
        assert not any("Missing 'inlets'" in m for m in msgs)
        assert not any("Missing 'outlets'" in m for m in msgs)
        assert _oob_found(res)

    def test_template_literal_after_regex_still_flagged(self):
        from src.maxpat.code_validation import validate_js

        code = _HEADER + "var r = /x/; var s = " + _BT + "t" + _BT + ";"
        res = _es6(validate_js(code, engine="js"))
        assert len(res) == 1
        assert res[0].level == "error"
        assert "template literal" in res[0].message
        assert "on line 4" in res[0].message

    @pytest.mark.parametrize("stmt", [
        'var h = a; /* / " */ outlet(3, h);',
        'var h = a; // /"/\noutlet(3, h);',
    ])
    def test_comment_still_wins_over_regex(self, stmt):
        from src.maxpat.code_validation import validate_js

        assert _oob_found(validate_js(_in_bang(stmt), engine="js"))

    @pytest.mark.parametrize("code", [
        _REPRO_QUOTE,
        _REPRO_BACKTICK,
        _REPRO_SLASHES,
        "x = /a/;\r\ny = 1;\r\n",
        'var r = /[\\/"]/g;\n',
    ])
    def test_mask_preserves_length_and_line_breaks(self, code):
        from src.maxpat.code_validation import _js_mask

        result = _js_mask(code)
        assert isinstance(result, tuple)
        masked, template_lines = result
        assert isinstance(masked, str)
        assert isinstance(template_lines, list)
        assert len(masked) == len(code)
        for i, ch in enumerate(code):
            if ch in "\r\n":
                assert masked[i] == ch, i

    @pytest.mark.parametrize("code", [
        "/", "x = /", "x = /[/", "x = /" + _BS, "return /", "}/",
        "a = /[" + _BS + "]",
        "x = /a/g", "/\n/", "a / / b", "x = /" + _BT, 'x = /"\n',
    ])
    @pytest.mark.parametrize("engine", [None, "js", "v8"])
    def test_regex_never_raises(self, code, engine):
        from src.maxpat.code_validation import validate_js

        assert isinstance(validate_js(code, engine=engine), list)


# ---------------------------------------------------------------------------
# D-02: engine resolution from the project's patches
# ---------------------------------------------------------------------------

_ES6_JS = "inlets = 1;\noutlets = 1;\nconst k = 2;\nfunction bang() { outlet(0, k); }\n"


def _newobj(box_id, text):
    return {"box": {"id": box_id, "maxclass": "newobj", "text": text,
                    "numinlets": 1, "numoutlets": 1, "patching_rect": [0, 0, 50, 22]}}


def _patch(boxes):
    return {"patcher": {"fileversion": 1, "boxes": boxes, "lines": []}}


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data)
    else:
        path.write_text(json.dumps(data))


def _es6_levels(path, **kw):
    from src.maxpat.hooks import validate_code_file

    return [r.level for r in validate_code_file(path, **kw) if "ES6 syntax" in r.message]


class TestEngineResolution:
    def test_js_reference_errors(self, tmp_path):
        _write(tmp_path / "x.js", _ES6_JS)
        _write(tmp_path / "x.maxpat", _patch([_newobj("obj-1", "js x.js")]))
        assert _es6_levels(tmp_path / "x.js") == ["error"]

    def test_v8_reference_no_result(self, tmp_path):
        _write(tmp_path / "x.js", _ES6_JS)
        _write(tmp_path / "x.maxpat", _patch([_newobj("obj-1", "v8 x.js")]))
        assert _es6_levels(tmp_path / "x.js") == []

    def test_no_patch_info_only(self, tmp_path):
        _write(tmp_path / "x.js", _ES6_JS)
        from src.maxpat.hooks import validate_code_file

        res = validate_code_file(tmp_path / "x.js")
        assert [r.level for r in res if "ES6 syntax" in r.message] == ["info"]
        assert not any(r.level == "error" for r in res)

    def test_jsui_filename_errors(self, tmp_path):
        _write(tmp_path / "x.js", _ES6_JS)
        _write(tmp_path / "ui.maxpat", _patch([{"box": {
            "id": "obj-1", "maxclass": "jsui", "filename": "x.js",
            "numinlets": 1, "numoutlets": 1, "patching_rect": [0, 0, 64, 64]}}]))
        assert _es6_levels(tmp_path / "x.js") == ["error"]

    def test_extensionless_reference_in_subpatcher(self, tmp_path):
        _write(tmp_path / "x.js", _ES6_JS)
        sub = {"box": {"id": "obj-1", "maxclass": "newobj", "text": "p sub",
                       "numinlets": 0, "numoutlets": 0, "patching_rect": [0, 0, 50, 22],
                       "patcher": _patch([_newobj("obj-2", "js x 3")])["patcher"]}}
        _write(tmp_path / "main.maxpat", _patch([sub]))
        assert _es6_levels(tmp_path / "x.js") == ["error"]

    def test_js_wins_over_v8(self, tmp_path):
        _write(tmp_path / "x.js", _ES6_JS)
        _write(tmp_path / "a.maxpat", _patch([_newobj("obj-1", "v8 x.js")]))
        _write(tmp_path / "b.maxpat", _patch([_newobj("obj-1", "js x.js")]))
        assert _es6_levels(tmp_path / "x.js") == ["error"]

    def test_project_dir_scanned_recursively(self, tmp_path):
        js = tmp_path / "patches" / "demo" / "generated" / "x.js"
        _write(js, _ES6_JS)
        _write(tmp_path / "patches" / "demo" / "other" / "y.maxpat",
               _patch([_newobj("obj-1", "js x.js")]))
        assert _es6_levels(js) == ["error"]

    def test_loose_file_scan_is_not_recursive(self, tmp_path):
        js = tmp_path / "loose" / "x.js"
        _write(js, _ES6_JS)
        _write(tmp_path / "loose" / "deeper" / "z.maxpat",
               _patch([_newobj("obj-1", "js x.js")]))
        assert "error" not in _es6_levels(js)

    def test_other_file_names_do_not_match(self, tmp_path):
        _write(tmp_path / "x.js", _ES6_JS)
        _write(tmp_path / "x.maxpat", _patch([
            _newobj("obj-1", "js xy.js"), _newobj("obj-2", "js x.json"),
            _newobj("obj-3", "jsx x.js")]))
        assert _es6_levels(tmp_path / "x.js") == ["info"]

    def test_malformed_patches_never_raise(self, tmp_path):
        _write(tmp_path / "x.js", _ES6_JS)
        _write(tmp_path / "bad.maxpat", "{not json")
        _write(tmp_path / "list.maxpat", "[1, 2, 3]")
        _write(tmp_path / "odd.maxpat", json.dumps({"patcher": {"boxes": [1, {"box": 2},
                                                                           {"box": {"text": 5}}]}}))
        assert _es6_levels(tmp_path / "x.js") == ["info"]


# ---------------------------------------------------------------------------
# D-03 / orchestrator: explicit engine override
# ---------------------------------------------------------------------------

class TestEngineOverride:
    def test_explicit_v8_overrides_js_reference(self, tmp_path):
        _write(tmp_path / "x.js", _ES6_JS)
        _write(tmp_path / "x.maxpat", _patch([_newobj("obj-1", "js x.js")]))
        assert _es6_levels(tmp_path / "x.js", engine="v8") == []

    def test_explicit_js_without_patch(self, tmp_path):
        _write(tmp_path / "x.js", _ES6_JS)
        assert _es6_levels(tmp_path / "x.js", engine="js") == ["error"]

    def test_write_js_passes_engine(self, tmp_path):
        from src.maxpat.hooks import write_js

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            res = write_js(_ES6_JS, tmp_path / "w.js", engine="js")
        assert any(r.level == "error" and "ES6 syntax 'const'" in r.message for r in res)
