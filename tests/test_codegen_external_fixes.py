"""Q31 / G5 G6 G7 G8 G3: codegen and Min-DevKit template regression tests; tmp_path only, no network."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.maxpat.critics.ext_critic import review_external
from src.maxpat import ext_templates
from src.maxpat.ext_templates import (
    render_cmake_template,
    render_dsp_template,
    render_message_template,
    render_scheduler_template,
    render_test_template,
)
from src.maxpat.externals import scaffold_external

STUB_DIR = Path("tests/fixtures/min_api_stub")

needs_clang = pytest.mark.skipif(
    shutil.which("clang++") is None, reason="clang++ not on PATH"
)

DSP_IO_CASES = [(0, 1), (1, 1), (2, 1), (1, 2), (2, 2), (0, 2), (3, 2)]

_GAIN_PARAM = [{"name": "gain", "default": 0.5, "min": 0.0, "max": 1.0}]


def _syntax_check(tmp_path: Path, sources: dict[str, str]) -> subprocess.CompletedProcess:
    """Write each source to tmp_path and type-check them all in one clang++ call."""
    files = []
    for fname, code in sources.items():
        path = tmp_path / fname
        path.write_text(code)
        files.append(str(path))
    return subprocess.run(
        ["clang++", "-std=c++17", "-fsyntax-only", "-I", str(STUB_DIR.resolve()), *files],
        capture_output=True,
        text=True,
        timeout=300,
    )


def _template_cases() -> list[tuple[str, str, str]]:
    """Every generated template the stub compile and the critic review cover.

    Returns (label, archetype, code) tuples: the 7 DSP input/output counts
    named ``foo~`` (one param), DSP ``my.ext~`` and ``plain``, and the
    message and scheduler templates named ``foo~``, ``my.ext~`` and ``plain``.
    """
    cases: list[tuple[str, str, str]] = []
    for n_in, n_out in DSP_IO_CASES:
        cases.append((
            f"dsp_foo_tilde_{n_in}_{n_out}", "dsp",
            render_dsp_template("foo~", "d", n_in, n_out, _GAIN_PARAM),
        ))
    for label, name in (("my_ext_tilde", "my.ext~"), ("plain", "plain")):
        cases.append((
            f"dsp_{label}_1_1", "dsp",
            render_dsp_template(name, "d", 1, 1, []),
        ))
    for label, name in (("foo_tilde", "foo~"), ("my_ext_tilde", "my.ext~"), ("plain", "plain")):
        cases.append((
            f"message_{label}", "message",
            render_message_template(
                name, "d",
                inlets=[{"comment": "(anything) input"}, {"comment": "(number) right"}],
                outlets=[{"comment": "(anything) output"}],
                handlers=["bang", "list"],
            ),
        ))
        cases.append((
            f"scheduler_{label}", "scheduler",
            render_scheduler_template(
                name, "d", 250.0,
                [{"name": "depth", "type": "double", "default": 0.5, "min": 0.0, "max": 1.0}],
            ),
        ))
    return cases


def _blockers(results) -> list[str]:
    return [r.finding for r in results if r.severity == "blocker"]


def _strip_strings(code: str) -> str:
    return re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', code)


def _operator_signature(code: str) -> tuple[str, str]:
    m = re.search(r"(samples<\d+>|sample) operator\(\)\(([^)]*)\)", code)
    assert m, code
    return m.group(1), m.group(2)


def _box_texts(node) -> list[str]:
    out: list[str] = []
    if isinstance(node, dict):
        if isinstance(node.get("text"), str):
            out.append(node["text"])
        for v in node.values():
            out.extend(_box_texts(v))
    elif isinstance(node, list):
        for v in node:
            out.extend(_box_texts(v))
    return out


# ---------------------------------------------------------------------------
# G5: DSP template and ~ names
# ---------------------------------------------------------------------------


class TestG5TracerTildeDspExternal:
    """foo~ DSP scaffold -> foo_tilde source -> no critic blocker -> stub compile."""

    @pytest.fixture
    def scaffold(self, tmp_path):
        return scaffold_external(
            tmp_path, "foo~", "dsp", "d", num_inputs=2, num_outputs=2,
        )

    def test_paths_use_cmake_folder_form(self, tmp_path, scaffold):
        assert scaffold["root"] == tmp_path / "foo_tilde"
        assert scaffold["source"] == tmp_path / "foo_tilde" / "source" / "foo_tilde.cpp"
        assert scaffold["help"] == tmp_path / "foo_tilde" / "help" / "foo~.maxhelp"
        for key in ("root", "source", "cmake", "help"):
            assert scaffold[key].exists()

    def test_source_declares_foo_tilde(self, scaffold):
        code = scaffold["source"].read_text()
        assert (
            "class foo_tilde : public object<foo_tilde>, public sample_operator<2, 2>"
            in code
        )
        assert "samples<2> operator()(sample input1, sample input2)" in code
        assert "return { input1, input2 };" in code
        assert "MIN_EXTERNAL(foo_tilde);" in code

    def test_current_critic_has_no_blocker(self, scaffold):
        code = scaffold["source"].read_text()
        assert _blockers(review_external(code, archetype="dsp")) == []

    def test_help_box_keeps_max_name(self, scaffold):
        data = json.loads(scaffold["help"].read_text())
        assert "foo~" in _box_texts(data)

    @needs_clang
    def test_source_type_checks(self, tmp_path, scaffold):
        code = scaffold["source"].read_text()
        res = _syntax_check(tmp_path, {"foo_tilde_check.cpp": code})
        assert res.returncode == 0, res.stderr


class TestG5DspIoCounts:
    """render_dsp_template is valid min-api for 0, 1 and 2+ inputs."""

    @pytest.mark.parametrize("n_in,n_out", DSP_IO_CASES)
    def test_operator_shape(self, n_in, n_out):
        code = render_dsp_template("foo~", "d", n_in, n_out, [])
        ret, params = _operator_signature(code)
        expected_params = ", ".join(f"sample input{i + 1}" for i in range(n_in))
        assert params == expected_params
        values = [f"input{k + 1}" if k < n_in else "0.0" for k in range(n_out)]
        if n_out == 1:
            assert ret == "sample"
            assert f"return {values[0]};" in code
        else:
            assert ret == f"samples<{n_out}>"
            assert "return { " + ", ".join(values) + " };" in code
        assert f"sample_operator<{n_in}, {n_out}>" in code
        if n_in == 0:
            assert code.count("(anything) messages") == 1
            assert "(signal) audio input" not in code
        else:
            assert "(anything) messages" not in code
            assert code.count("(signal) audio input") == n_in
        assert _blockers(review_external(code, archetype="dsp")) == []

    @pytest.mark.parametrize("n_in,n_out", [(1, 0), (-1, 1), (True, 1), (1, True), (1.0, 1)])
    def test_unsupported_counts_raise(self, n_in, n_out):
        with pytest.raises(ValueError):
            render_dsp_template("foo~", "d", n_in, n_out, [])


@needs_clang
class TestG5StubCompile:
    """Every generated template type-checks against the min-api stub."""

    def test_all_templates_compile(self, tmp_path):
        sources = {f"{label}.cpp": code for label, _arch, code in _template_cases()}
        res = _syntax_check(tmp_path, sources)
        assert res.returncode == 0, res.stderr


@needs_clang
class TestG5StubFidelity:
    """The stub rejects the f1f39215 bugs and accepts min-devkit's own shapes."""

    MUST_FAIL = {
        "bad_1_1_samples": '''#include "c74_min.h"
using namespace c74::min;
class bad11 : public object<bad11>, public sample_operator<1, 1> {
public:
    inlet<>  m_input  { this, "(signal) audio input 1" };
    outlet<> m_output { this, "(signal) audio output 1", "signal" };
    samples<1> operator()(sample input) {
        return { input };
    }
};
MIN_EXTERNAL(bad11);
''',
        "bad_2_2_input": '''#include "c74_min.h"
using namespace c74::min;
class bad22 : public object<bad22>, public sample_operator<2, 2> {
public:
    samples<2> operator()(sample input1, sample input2) {
        return { input };
    }
};
MIN_EXTERNAL(bad22);
''',
        "bad_tilde_class": '''#include "c74_min.h"
using namespace c74::min;
class foo~ : public object<foo~> {
public:
    inlet<> m_input { this, "(anything) input" };
};
MIN_EXTERNAL(foo~);
''',
    }

    MUST_COMPILE = {
        "phasor_shape": '''#include "c74_min.h"
using namespace c74::min;
class phasor_like : public object<phasor_like>, public sample_operator<0, 1> {
public:
    inlet<>  in1  { this, "(number) frequency" };
    outlet<> out1 { this, "(signal) ramp wave", "signal" };
    sample operator()() {
        return 0.0;
    }
};
MIN_EXTERNAL(phasor_like);
''',
        "xfade_shape": '''#include "c74_min.h"
using namespace c74::min;
class xfade_like : public object<xfade_like>, public sample_operator<3, 1> {
public:
    sample operator()(sample a, sample b, sample position) {
        return a * (1.0 - position) + b * position;
    }
};
MIN_EXTERNAL(xfade_like);
''',
    }

    @pytest.mark.parametrize("label", sorted(MUST_FAIL))
    def test_rejects(self, tmp_path, label):
        res = _syntax_check(tmp_path, {f"{label}.cpp": self.MUST_FAIL[label]})
        assert res.returncode != 0, f"stub accepted {label}"

    def test_accepts_min_devkit_shapes(self, tmp_path):
        sources = {f"{k}.cpp": v for k, v in self.MUST_COMPILE.items()}
        res = _syntax_check(tmp_path, sources)
        assert res.returncode == 0, res.stderr


class TestG5CppNames:
    """A MAX name maps to a C++ identifier and to min-api's CMake folder form."""

    @pytest.mark.parametrize("name,expected", [
        ("foo~", "foo_tilde"),
        ("my.ext~", "my_ext_tilde"),
        ("plain", "plain"),
        ("2x", "_2x"),
        ("", "_"),
    ])
    def test_cpp_identifier(self, name, expected):
        assert ext_templates.cpp_identifier(name) == expected

    @pytest.mark.parametrize("name,expected", [
        ("foo~", "foo_tilde"),
        ("my.ext~", "my.ext_tilde"),
        ("plain", "plain"),
    ])
    def test_cmake_folder_name(self, name, expected):
        assert ext_templates.cmake_folder_name(name) == expected

    @pytest.mark.parametrize("render", [
        lambda n: render_message_template(n, "d", [{}], [{}], ["bang"]),
        lambda n: render_dsp_template(n, "d", 1, 1, []),
        lambda n: render_scheduler_template(n, "d", 100.0, []),
    ], ids=["message", "dsp", "scheduler"])
    def test_templates_declare_foo_tilde(self, render):
        code = render("foo~")
        assert "class foo_tilde : public object<foo_tilde>" in code
        assert "MIN_EXTERNAL(foo_tilde);" in code
        assert "foo~" not in _strip_strings(code)

    def test_test_template_includes_folder_source(self):
        src = render_test_template("foo~")
        assert '#include "foo_tilde.cpp"' in src
        assert 'TEST_CASE("foo~' in src

    def test_plain_scaffold_paths_unchanged(self, tmp_path):
        res = scaffold_external(tmp_path, "plain", "message", "d")
        assert res["root"] == tmp_path / "plain"
        assert res["source"] == tmp_path / "plain" / "source" / "plain.cpp"
        assert res["help"] == tmp_path / "plain" / "help" / "plain.maxhelp"
        assert "MIN_EXTERNAL(plain);" in res["source"].read_text()


# ---------------------------------------------------------------------------
# G7: CMake hint
# ---------------------------------------------------------------------------


class TestG7CmakeHint:
    def test_hint_points_at_setup_min_devkit(self):
        src = render_cmake_template("x")
        assert "setup_min_devkit" in src
        assert "git clone --recursive" in src
        assert "git submodule" not in src


# ---------------------------------------------------------------------------
# G5: ext_critic identifiers and comment masking
# ---------------------------------------------------------------------------

_F1F_TILDE_MESSAGE = '''#include "c74_min.h"

using namespace c74::min;

class foo~ : public object<foo~> {
public:
    inlet<>  m_input  { this, "(anything) input" };
    outlet<> m_output { this, "(anything) output" };
};

MIN_EXTERNAL(foo~);
'''

_VALID_BODY = '''class my_object : public object<my_object> {
public:
    inlet<>  m_input  { this, "(anything) input" };
    outlet<> m_output { this, "(anything) output" };
};
'''


class TestG5ExtCriticIdentifiers:
    def test_tilde_name_reports_identifier_not_missing(self):
        blockers = [r for r in review_external(_F1F_TILDE_MESSAGE, archetype="message")
                    if r.severity == "blocker"]
        assert len(blockers) == 1, [b.finding for b in blockers]
        b = blockers[0]
        assert "'foo~' is not a valid C++ identifier" in b.finding
        assert "class declaration and MIN_EXTERNAL" in b.finding
        assert "foo_tilde" in b.suggestion
        assert not any("Missing MIN_EXTERNAL" in r.finding
                       for r in review_external(_F1F_TILDE_MESSAGE, archetype="message"))

    def test_commented_old_min_external_ignored(self):
        code = ('#include "c74_min.h"\nusing namespace c74::min;\n' + _VALID_BODY
                + "// MIN_EXTERNAL(old_name);\nMIN_EXTERNAL(my_object);\n")
        assert _blockers(review_external(code, archetype="message")) == []

    def test_min_external_only_in_block_comment_is_missing(self):
        code = ('#include "c74_min.h"\nusing namespace c74::min;\n' + _VALID_BODY
                + "/* MIN_EXTERNAL(my_object); */\n")
        assert any("Missing MIN_EXTERNAL" in f
                   for f in _blockers(review_external(code, archetype="message")))

    def test_include_only_in_comment_is_missing(self):
        code = ('// #include "c74_min.h"\nusing namespace c74::min;\n' + _VALID_BODY
                + "MIN_EXTERNAL(my_object);\n")
        assert any("c74_min.h" in f
                   for f in _blockers(review_external(code, archetype="message")))

    def test_helper_class_before_object_class(self):
        code = ('#include "c74_min.h"\nusing namespace c74::min;\n'
                "struct base_thing {};\n"
                "class helper : public base_thing {};\n" + _VALID_BODY
                + "MIN_EXTERNAL(my_object);\n")
        assert _blockers(review_external(code, archetype="message")) == []

    def test_empty_min_external(self):
        code = ('#include "c74_min.h"\nusing namespace c74::min;\n' + _VALID_BODY
                + "MIN_EXTERNAL();\n")
        assert any("names no class" in f
                   for f in _blockers(review_external(code, archetype="message")))

    def test_mismatch_text_kept(self):
        code = ('#include "c74_min.h"\nusing namespace c74::min;\n'
                "class a : public object<a> {\npublic:\n"
                '    inlet<> m_input { this, "in" };\n};\nMIN_EXTERNAL(b);\n')
        assert _blockers(review_external(code, archetype="message")) == [
            "MIN_EXTERNAL(b) does not match class declaration 'a'"
        ]

    @pytest.mark.parametrize("label,archetype,code", _template_cases(),
                             ids=[c[0] for c in _template_cases()])
    def test_every_template_reviews_clean(self, label, archetype, code):
        assert _blockers(review_external(code, archetype=archetype)) == []


# ---------------------------------------------------------------------------
# G7: setup_min_devkit clones into the external's own gitignored folder
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_run(monkeypatch):
    """Replace subprocess.run in src.maxpat.externals; never touches the network."""
    import src.maxpat.externals as externals

    state = {"calls": [], "returncode": 0, "raises": None, "readme": False}

    def run(argv, cwd=None, **kwargs):
        state["calls"].append((list(argv), cwd))
        if state["raises"] is not None:
            raise state["raises"]
        if state["returncode"] == 0:
            if argv[:2] == ["git", "clone"]:
                dest = Path(cwd) / argv[-1]
                (dest / "source" / "min-api").mkdir(parents=True)
                if state["readme"]:
                    (dest / "README.md").write_text("min-devkit\n")
            elif argv[:3] == ["git", "submodule", "update"]:
                (Path(cwd) / "source" / "min-api").mkdir(parents=True)
        return subprocess.CompletedProcess(argv, state["returncode"], "", "")

    monkeypatch.setattr(externals.subprocess, "run", run)
    return state


def _gitignore_lines(ext_dir: Path) -> list[str]:
    return (ext_dir / ".gitignore").read_text().splitlines()


class TestG7SetupMinDevkitClones:
    def test_clone_into_ext_dir(self, tmp_path, fake_run):
        from src.maxpat.externals import MIN_DEVKIT_URL, setup_min_devkit

        ext = tmp_path / "ext"
        ext.mkdir()
        assert setup_min_devkit(ext) is True
        assert fake_run["calls"] == [
            (["git", "clone", "--recursive", MIN_DEVKIT_URL, "min-devkit"], str(ext))
        ]
        for argv, cwd in fake_run["calls"]:
            assert not ("submodule" in argv and "add" in argv)
            assert Path(cwd).resolve().is_relative_to(ext.resolve())
        assert _gitignore_lines(ext).count("min-devkit/") == 1

    def test_idempotent(self, tmp_path, fake_run):
        from src.maxpat.externals import setup_min_devkit

        assert setup_min_devkit(tmp_path) is True
        n = len(fake_run["calls"])
        assert setup_min_devkit(tmp_path) is True
        assert len(fake_run["calls"]) == n
        assert _gitignore_lines(tmp_path).count("min-devkit/") == 1

    def test_existing_gitignore_kept(self, tmp_path, fake_run):
        from src.maxpat.externals import setup_min_devkit

        (tmp_path / ".gitignore").write_text("build/\n*.o")
        assert setup_min_devkit(tmp_path) is True
        text = (tmp_path / ".gitignore").read_text()
        assert text.startswith("build/\n*.o\n")
        lines = text.splitlines()
        assert lines[:2] == ["build/", "*.o"]
        assert lines.count("min-devkit/") == 1

    def test_half_present_checkout_repaired_inside(self, tmp_path, fake_run):
        from src.maxpat.externals import setup_min_devkit

        (tmp_path / "min-devkit" / ".git").mkdir(parents=True)
        assert setup_min_devkit(tmp_path) is True
        assert fake_run["calls"] == [
            (["git", "submodule", "update", "--init", "--recursive"],
             str(tmp_path / "min-devkit"))
        ]

    def test_non_git_folder_refused(self, tmp_path, fake_run):
        from src.maxpat.externals import setup_min_devkit

        user = tmp_path / "min-devkit" / "mine.txt"
        user.parent.mkdir()
        user.write_text("keep")
        assert setup_min_devkit(tmp_path) is False
        assert fake_run["calls"] == []
        assert sorted(p.name for p in user.parent.iterdir()) == ["mine.txt"]
        assert user.read_text() == "keep"

    def test_clone_failure(self, tmp_path, fake_run):
        from src.maxpat.externals import setup_min_devkit

        fake_run["returncode"] = 1
        assert setup_min_devkit(tmp_path) is False

    def test_git_missing(self, tmp_path, fake_run):
        from src.maxpat.externals import setup_min_devkit

        fake_run["raises"] = FileNotFoundError("git")
        assert setup_min_devkit(tmp_path) is False

    def test_missing_ext_dir(self, tmp_path, fake_run):
        from src.maxpat.externals import setup_min_devkit

        missing = tmp_path / "nope"
        assert setup_min_devkit(missing) is False
        assert fake_run["calls"] == []
        assert not missing.exists()

    def test_marker_present(self, tmp_path, fake_run):
        from src.maxpat.externals import setup_min_devkit

        (tmp_path / "min-devkit" / "source" / "min-api").mkdir(parents=True)
        assert setup_min_devkit(tmp_path) is True
        assert fake_run["calls"] == []


@pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")
class TestG7GitIgnoresCheckout:
    def test_enclosing_repo_does_not_see_checkout(self, tmp_path, monkeypatch):
        import src.maxpat.externals as externals

        repo = tmp_path / "repo"
        ext = repo / "ext"
        ext.mkdir(parents=True)
        (ext / "CMakeLists.txt").write_text("# ext\n")
        subprocess.run(["git", "init", "-q", str(repo)], check=True,
                       capture_output=True, text=True)

        real_run = subprocess.run

        def fake(argv, cwd=None, **kwargs):
            assert argv[:2] == ["git", "clone"]
            dest = Path(cwd) / argv[-1]
            (dest / "source" / "min-api").mkdir(parents=True)
            (dest / "README.md").write_text("min-devkit\n")
            return subprocess.CompletedProcess(argv, 0, "", "")

        with monkeypatch.context() as m:
            m.setattr(externals.subprocess, "run", fake)
            assert externals.setup_min_devkit(ext) is True

        out = real_run(
            ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
            check=True, capture_output=True, text=True,
        ).stdout
        paths = [line[3:] for line in out.splitlines()]
        assert "ext/.gitignore" in paths
        assert not any(p.startswith("ext/min-devkit") for p in paths), paths


class TestG7ExtAgentDocs:
    SKILL = Path(".claude/skills/max-ext-agent/SKILL.md")
    BOUNDARIES = Path(".claude/skills/max-ext-agent/BOUNDARIES.md")

    def test_no_submodule_wording(self):
        for path in (self.SKILL, self.BOUNDARIES):
            assert "submodule" not in path.read_text().lower(), path

    def test_skill_describes_clone(self):
        text = self.SKILL.read_text()
        assert "min-devkit/" in text
        assert ".gitignore" in text
        for name in ("setup_min_devkit", "scaffold_external", "build_external"):
            assert name in text
