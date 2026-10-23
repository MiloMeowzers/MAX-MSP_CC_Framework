"""Code generators and js checks: review-codegen.md IN-02, IN-03, IN-04 (quick 261022-ud6 WP4)."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from src.maxpat.code_validation import detect_js_type, validate_js
from src.maxpat.codegen import generate_gendsp, generate_n4m_script


# ---------------------------------------------------------------------------
# IN-02: a codebox with no inN still has one inlet (MAX's shape)
# ---------------------------------------------------------------------------


def _codebox(d):
    (box,) = [e["box"] for e in d["patcher"]["boxes"] if e["box"]["maxclass"] == "codebox"]
    return box


@pytest.mark.parametrize("code, n_in", [
    ("out1 = noise();", 1),
    ("out1 = in1;", 1),
    ("out1 = in1 + in2 + in3;", 3),
])
def test_gendsp_codebox_has_at_least_one_inlet(code, n_in):
    d = generate_gendsp(code)
    assert _codebox(d)["numinlets"] == n_in


def test_gendsp_zero_input_keeps_no_in_boxes():
    d = generate_gendsp("out1 = noise();")
    texts = [e["box"].get("text") for e in d["patcher"]["boxes"]]
    assert "in 1" not in texts
    assert not [ln for ln in d["patcher"]["lines"]
                if ln["patchline"]["destination"][0] == _codebox(d)["id"]]


# ---------------------------------------------------------------------------
# IN-03: `numinlets = 2` is not an inlets declaration
# ---------------------------------------------------------------------------


def _missing(code):
    return {r.message for r in validate_js(code) if r.level == "error" and "Missing" in r.message}


def test_numinlets_variable_is_not_a_declaration():
    code = "var numinlets = 2;\nvar numoutlets = 1;\nfunction bang() { outlet(0, 1); }\n"
    assert _missing(code) == {
        "Missing 'inlets' declaration (required for js object)",
        "Missing 'outlets' declaration (required for js object)",
    }
    assert detect_js_type(code) is None


@pytest.mark.parametrize("decl", ["inlets = 1;\noutlets = 1;", "this.inlets = 1;\nthis.outlets = 1;"])
def test_real_declarations_still_count(decl):
    code = decl + "\nfunction bang() { outlet(0, 1); }\n"
    assert _missing(code) == set()
    assert detect_js_type(code) == "js"


def test_inlets_comparison_is_not_a_declaration():
    assert detect_js_type("if (inlets == 2) { post(1); }\n") is None


# ---------------------------------------------------------------------------
# IN-04: handler selectors are JSON-escaped in generated N4M scripts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ['say "hi"', "back\\slash", "plain"])
def test_n4m_handler_name_is_escaped(name):
    src = generate_n4m_script(handlers=[{"name": name, "args": ["x"], "body": "maxAPI.outlet(x);"}])
    assert f"maxAPI.addHandler({json.dumps(name)}, " in src


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_n4m_script_with_quote_in_selector_parses(tmp_path):
    src = generate_n4m_script(handlers=[{"name": 'a"b\\c', "args": [], "body": "return 1;"}])
    f = tmp_path / "s.js"
    f.write_text(src, encoding="utf-8")
    proc = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
