"""Tests for src/maxpat/diagnose.py: console diagnosis (Q37, quick 261022-ksz).

Covers the troubleshooting.md parse contract (depth-0 code spans), the
match tiers, the read-only box locator on a synthetic project, object
facts, the /max-iterate proposal, the CLI end to end on the committed
max-bridge fixtures (read-only, hashed before and after), an AST gate that
keeps the module read-only, and the input caps.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.maxpat import diagnose
from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.diagnose import (
    GEN_SECTION,
    MAX_LINES,
    diagnose_console,
    load_troubleshooting,
    locate_boxes,
    match_line,
    normalize_console_line,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "src" / "maxpat" / "diagnose.py"
BRIDGE_DIR = REPO_ROOT / "patches" / "max-bridge"

NO_SUCH = "<objectname>: No such object"
GENPATCHER = "dsp.gen: ... failed to compile genpatcher"
GEN_LINE = ('gen_domain: dsp.gen: [string "-- main2.lua..."]:727: '
            "failed to compile genpatcher")


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


@pytest.fixture(scope="module")
def entries():
    return load_troubleshooting()


def _rows_with(entries, fragment):
    return [e for e in entries if fragment in e.message]


def _kept_rows(matches):
    return [m.entry.row for m in matches]


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


class TestParse:
    def test_sections_in_file_order(self, entries):
        assert len(entries) >= 32
        order = []
        for e in entries:
            if not order or order[-1] != e.section:
                order.append(e.section)
        assert order == ["Object creation", "Messages", GEN_SECTION,
                         "FluCoMa and files"]
        rows = [e.row for e in entries]
        assert rows == sorted(rows)

    def test_six_no_such_object_rows(self, entries):
        six = [e for e in entries if e.patterns == (NO_SUCH,)]
        assert len(six) == 6
        assert all(e.section == "Object creation" for e in six)

    def test_depth0_oracle(self, entries):
        def one(fragment):
            rows = _rows_with(entries, fragment)
            assert len(rows) == 1, fragment
            return rows[0].patterns

        assert one("already in use") == ("<objectname>: <name>: already in use",)
        assert one("identifier 'sr'") == ("use of undeclared identifier 'sr'",)
        assert one("identifier 'maxb_NN'") == ("use of undeclared identifier 'maxb_NN'",)
        assert one("Wrong Point Size") == ("Wrong Point Size",)
        assert one("labelDict is null") == (
            "Please provide a valid dictionary...", "labelDict is null")
        assert one("Could not open file for writing") == (
            "Could not open file for writing", "... not found")
        delay = one("The delay() operator")
        assert len(delay) == 1 and "delay()" in delay[0]

    def test_genpatcher_row_has_grounded_companion(self, entries):
        rows = [e for e in entries if GENPATCHER in e.patterns]
        assert len(rows) == 1
        assert rows[0].patterns == (GENPATCHER, "gen~: failed to compile patcher")
        assert "max-bridge v0.3.0" in rows[0].source

    def test_two_gen_rows_without_pattern(self, entries):
        empty = [e for e in entries if e.section == GEN_SECTION and not e.patterns]
        assert len(empty) == 2

    def test_three_cell_row_skipped(self, tmp_path):
        md = tmp_path / "t.md"
        md.write_text(
            "## Sec\n\n| Console message | Cause | Fix | Source |\n|---|---|---|---|\n"
            "| `a: b` | c | d |\n| `x: y` | cause | fix | src |\n",
            encoding="utf-8")
        got = load_troubleshooting(md)
        assert [e.patterns for e in got] == [("x: y",)]
        assert got[0].section == "Sec"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_troubleshooting(tmp_path / "nope.md")


class TestSelfMatch:
    def test_every_pattern_matches_its_row(self, entries):
        import re

        for entry in entries:
            for pattern in entry.patterns:
                counter = iter(range(1, 100))
                text = re.sub(r"<[^<>\s]+>", lambda _m: "w%d" % next(counter), pattern)
                text = text.replace("...", "zz")
                kept = match_line(text, entries)
                assert entry.row in _kept_rows(kept), (pattern, text)


# ---------------------------------------------------------------------------
# Normalize and match
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_doubled_prefix(self):
        assert normalize_console_line("osc~: osc~: No such object") == "osc~: No such object"

    def test_whitespace_and_quotes(self):
        assert normalize_console_line('  a\t\tb   "c"  ') == "a b c"


class TestMatch:
    def _captures(self, m):
        return dict(m.captures)

    @pytest.mark.parametrize("line", ["osc~: osc~: No such object",
                                      "newobj: osc~: No such object"])
    def test_no_such_object(self, entries, line):
        kept = match_line(line, entries)
        assert len(kept) == 6
        assert all(m.pattern == NO_SUCH and m.tier == "exact" for m in kept)
        assert all(self._captures(m) == {"objectname": "osc~"} for m in kept)

    def test_bare_no_such_object(self, entries):
        kept = match_line("No such object", entries)
        assert len(kept) == 6
        assert all(m.pattern == NO_SUCH and m.tier == "no-prefix" for m in kept)
        assert all(not m.captures for m in kept)

    def test_bad_arguments(self, entries):
        kept = match_line("send: bad arguments creating object", entries)
        assert kept and kept[0].pattern == "bad arguments creating object"

    @pytest.mark.parametrize("line", ["codebox: can't assign to parameter g",
                                      "can't assign to parameter g"])
    def test_cant_assign(self, entries, line):
        kept = match_line(line, entries)
        assert len(kept) == 1
        assert kept[0].pattern == "codebox: can't assign to parameter <name>"
        assert self._captures(kept[0]) == {"name": "g"}

    @pytest.mark.parametrize("line", [GEN_LINE, "gen~: failed to compile patcher"])
    def test_genpatcher(self, entries, line):
        kept = match_line(line, entries)
        assert kept and GENPATCHER in kept[0].entry.patterns
        assert kept[0].entry.section == GEN_SECTION

    def test_sr_only(self, entries):
        kept = match_line("use of undeclared identifier 'sr'", entries)
        assert [m.pattern for m in kept] == ["use of undeclared identifier 'sr'"]

    def test_any_identifier(self, entries):
        kept = match_line("use of undeclared identifier 'k_drive'", entries)
        assert [m.pattern for m in kept] == [
            "use of undeclared identifier 'sr'",
            "use of undeclared identifier 'maxb_NN'",
        ]
        assert all(m.tier == "any-identifier" for m in kept)
        assert all(self._captures(m) == {"identifier": "k_drive"} for m in kept)

    def test_clip_first(self, entries):
        kept = match_line("function clip not found", entries)
        assert kept[0].pattern == "function clip not found"

    def test_umenu_first_no_flucoma(self, entries):
        kept = match_line("umenu: doesn't understand a", entries)
        assert kept[0].pattern == "umenu: doesn't understand a"
        assert not any("fluid.dataset~" in m.pattern for m in kept)

    def test_no_match(self, entries):
        assert match_line("print: hello", entries) == []


# ---------------------------------------------------------------------------
# Locate (synthetic project)
# ---------------------------------------------------------------------------


def _box(box_id, text=None, maxclass="newobj", **extra):
    box = {"id": box_id, "maxclass": maxclass}
    if text is not None:
        box["text"] = text
    box.update(extra)
    return {"box": box}


def _patch(boxes, **top):
    patcher = {"boxes": boxes, "lines": []}
    patcher.update(top)
    return {"patcher": patcher}


@pytest.fixture()
def demo(tmp_path):
    proj = tmp_path / "patches" / "demo"
    gen_inner = {"boxes": [
        _box("obj-1", "in 1"),
        _box("obj-2", maxclass="codebox", code="Param g(0.5);\ng = in1;\nout1 = g;"),
        _box("obj-3", "out 1"),
    ], "lines": []}
    synth_inner = {"boxes": [_box("obj-1", "osc~ 220")], "lines": []}
    main = _patch([
        _box("obj-1", "osc~ 440"),
        _box("obj-2", "p synth", patcher=synth_inner),
        _box("obj-3", maxclass="comment", text="osc~ is a Pure Data name"),
        _box("obj-4", "gen~", patcher=gen_inner),
        _box("obj-5", "uzi 2 base 0"),
    ])
    (proj / "generated").mkdir(parents=True)
    (proj / "generated" / "demo.maxpat").write_text(json.dumps(main), encoding="utf-8")
    (proj / "generated" / "__maxbridge_demo.maxpat").write_text(
        json.dumps(_patch([_box("obj-9", "osc~ 1")])), encoding="utf-8")
    (proj / "test-results").mkdir()
    (proj / "test-results" / "copy.maxpat").write_text(
        json.dumps(_patch([_box("obj-8", "osc~ 2")])), encoding="utf-8")
    (proj / "generated" / "broken.maxpat").write_text("{not json", encoding="utf-8")
    gendsp = _patch([
        _box("obj-1", maxclass="codebox",
             code="Param drive(1);\ny = in1 * k_drive;\nout1 = y;"),
    ], classnamespace="dsp.gen")
    (proj / "generated" / "shaper.gendsp").write_text(json.dumps(gendsp), encoding="utf-8")
    return proj


def _hits(report, idx=0):
    return [(h.file, h.where, h.box_id, h.reason) for h in report.diagnoses[idx].hits]


class TestLocate:
    def test_osc_hits_object_boxes_only(self, demo):
        report = diagnose_console("osc~: osc~: No such object", demo)
        assert _hits(report) == [
            ("generated/demo.maxpat", "", "obj-1", "object"),
            ("generated/demo.maxpat", "[p synth] ", "obj-1", "object"),
        ]
        assert any(s.startswith("generated/broken.maxpat (") for s in report.skipped)
        assert "generated/demo.maxpat" in report.files
        assert not any("__maxbridge_" in f or "test-results" in f for f in report.files)

    def test_argument_fallback(self, demo):
        report = diagnose_console("base: bad number", demo)
        assert _hits(report) == [("generated/demo.maxpat", "", "obj-5", "argument")]

    def test_cant_assign_codebox(self, demo):
        report = diagnose_console("codebox: can't assign to parameter g", demo)
        hits = report.diagnoses[0].hits
        assert len(hits) == 1
        assert hits[0].where == "[gen~] " and hits[0].box_id == "obj-2"
        assert hits[0].reason == "code" and hits[0].code_lines == (1, 2, 3)

    def test_undeclared_identifier_in_gendsp(self, demo):
        report = diagnose_console("use of undeclared identifier 'k_drive'", demo)
        assert _hits(report) == [("generated/shaper.gendsp", "", "obj-1", "code")]
        assert report.diagnoses[0].hits[0].code_lines == (2,)

    def test_genpatcher_fallback(self, demo):
        report = diagnose_console(GEN_LINE, demo)
        got = _hits(report)
        assert ("generated/demo.maxpat", "", "obj-4", "gen container") in got
        assert ("generated/demo.maxpat", "[gen~] ", "obj-2", "gen container") in got
        assert ("generated/shaper.gendsp", "", "obj-1", "gen container") in got

    def test_locate_boxes_direct(self, demo):
        hits, skipped = locate_boxes(demo, objects=("osc~",))
        assert [h.box_id for h in hits] == ["obj-1", "obj-1"]
        assert skipped and skipped[0].startswith("generated/broken.maxpat")

    def test_malformed_boxes_never_raise(self, tmp_path):
        proj = tmp_path / "patches" / "odd"
        proj.mkdir(parents=True)
        odd = {"patcher": {"boxes": [1, {"box": None}, {"box": {"maxclass": 3}},
                                     {"box": {"maxclass": "newobj", "text": None}}]}}
        (proj / "odd.maxpat").write_text(json.dumps(odd), encoding="utf-8")
        (proj / "list.maxpat").write_text("[1, 2]", encoding="utf-8")
        report = diagnose_console("osc~: No such object\nbad number", proj)
        assert report.diagnoses[0].hits == ()
        assert any(s.startswith("list.maxpat") for s in report.skipped)


# ---------------------------------------------------------------------------
# Facts and proposal
# ---------------------------------------------------------------------------


class TestFactsAndProposal:
    def test_pd_fact(self, db):
        report = diagnose_console("osc~: No such object", db=db)
        assert any("Pure Data" in f and "cycle~" in f for f in report.diagnoses[0].facts)

    def test_restriction_fact(self, db):
        report = diagnose_console("expr~: No such object", db=db)
        assert any(f.startswith("expr~: only valid inside") for f in report.diagnoses[0].facts)

    def test_unknown_fact(self, db):
        report = diagnose_console("frobnicate~: No such object", db=db)
        assert report.diagnoses[0].facts == ("frobnicate~: not in the object database",)

    def test_no_db_no_facts(self):
        report = diagnose_console("osc~: No such object")
        assert report.diagnoses[0].facts == ()

    def test_proposal(self, demo, entries):
        report = diagnose_console("osc~: osc~: No such object", demo)
        diag = report.diagnoses[0]
        fix = diag.matches[0].entry.fix
        first = diagnose._first_sentence(fix)
        assert first and fix.startswith(first)
        assert diag.proposal == (
            '/max-iterate demo fix "osc~: No such object" at '
            "generated/demo.maxpat obj-1 [osc~ 440]: " + first)

    def test_first_sentence_keeps_ellipsis(self):
        fix = ("Apply the rules: nested `else { if ... }`, single loops. "
               "Look for a codebox error.")
        assert diagnose._first_sentence(fix) == (
            "Apply the rules: nested `else { if ... }`, single loops.")
        assert diagnose._first_sentence("Use `x`, e.g. y. Next one.") == "Use `x`, e.g. y."

    def test_proposal_without_project_or_hits(self):
        report = diagnose_console("send: bad arguments creating object")
        assert report.diagnoses[0].proposal.startswith(
            '/max-iterate fix "send: bad arguments creating object": ')
        assert report.project is None

    def test_unmatched_has_no_proposal(self):
        report = diagnose_console("print: hello")
        assert report.diagnoses[0].proposal is None
        assert "no troubleshooting entry" in report.render()

    def test_render_fragments(self, demo, db):
        text = diagnose_console("osc~: osc~: No such object\nosc~: No such object\n"
                                "print: hello", demo, db=db).render()
        assert "Console diagnosis: 2 distinct line(s), 1 matched, 1 unmatched" in text
        assert "Project: demo (" in text and "patch file(s) scanned)" in text
        assert "Skipped: generated/broken.maxpat (" in text
        assert "[1] osc~: No such object  (x2)" in text
        assert "  entry: Object creation -- `<objectname>: No such object` [exact]" in text
        assert "  box: generated/demo.maxpat [p synth] obj-1 [osc~ 220] (object)" in text
        assert "  fact: osc~: Pure Data name, not MAX; MAX equivalent cycle~" in text
        assert "  propose: /max-iterate demo" in text

    def test_render_no_project_and_empty(self):
        assert "Project: none -- boxes not located (pass --project NAME)" in \
            diagnose_console("osc~: No such object").render()
        assert diagnose_console("").render() == "no console lines"


# ---------------------------------------------------------------------------
# CLI end to end (committed max-bridge, read-only)
# ---------------------------------------------------------------------------


def _hash_tree(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


GROUNDED = "\n".join([
    "osc~: osc~: No such object",
    "send: bad arguments creating object",
    "codebox: can't assign to parameter g",
    GEN_LINE,
    "gen~: failed to compile patcher",
]) + "\n"


def _cli(*args, stdin=None):
    return subprocess.run(
        [sys.executable, "-m", "src.maxpat.diagnose", *args],
        cwd=REPO_ROOT, input=stdin, capture_output=True, text=True, timeout=120)


@pytest.mark.skipif(not BRIDGE_DIR.is_dir(), reason="max-bridge project not present")
class TestCli:
    def test_cli_max_bridge_read_only(self, tmp_path):
        paste = tmp_path / "console.txt"
        paste.write_text(GROUNDED, encoding="utf-8")
        before = _hash_tree(BRIDGE_DIR)
        proc = _cli("--project", "max-bridge", "--base-dir", str(REPO_ROOT), str(paste))
        after = _hash_tree(BRIDGE_DIR)
        assert proc.returncode == 0, proc.stderr
        out = proc.stdout
        assert "fixtures/fx-nosuchobj.maxpat obj-3" in out
        assert "fixtures/fx-genfail.maxpat [gen~] obj-2" in out
        assert "cycle~" in out
        assert "/max-iterate max-bridge" in out
        assert "fixtures/fx-nosuchobj.maxpat obj-1" not in out  # comment, not a hit
        assert before == after

    def test_cli_stdin(self):
        proc = _cli("--project", "max-bridge", "-", stdin="osc~: osc~: No such object\n")
        assert proc.returncode == 0, proc.stderr
        assert "fixtures/fx-nosuchobj.maxpat obj-3" in proc.stdout

    @pytest.mark.parametrize("name", ["../x", "nope-not-a-project", ".", ""])
    def test_cli_bad_project(self, name):
        proc = _cli("--project", name, "-", stdin="osc~: No such object\n")
        assert proc.returncode == 2

    def test_cli_unreadable_file(self, tmp_path):
        proc = _cli("--project", "max-bridge", str(tmp_path / "missing.txt"))
        assert proc.returncode == 2

    def test_main_in_process(self, tmp_path, capsys):
        paste = tmp_path / "c.txt"
        paste.write_text("codebox: can't assign to parameter g\n", encoding="utf-8")
        rc = diagnose.main(["--project", "max-bridge", "--base-dir", str(REPO_ROOT),
                            "--no-db", str(paste)])
        assert rc == 0
        assert "fixtures/fx-genfail.maxpat [gen~] obj-2" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Read-only AST gate and caps
# ---------------------------------------------------------------------------


class TestReadOnlyGate:
    BANNED_MODULES = {"src.maxpat.hooks", "src.maxpat.atomic_io", "subprocess", "shutil"}
    BANNED_CALLS = {"write_text", "write_bytes", "unlink", "rename", "replace",
                    "mkdir", "rmdir", "touch"}

    @pytest.fixture(scope="class")
    def tree(self):
        return ast.parse(MODULE_PATH.read_text(encoding="utf-8"))

    def test_no_banned_imports(self, tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                names = {mod} | {"%s.%s" % (mod, a.name) for a in node.names}
            else:
                continue
            assert not names & self.BANNED_MODULES, names

    def test_no_writing_calls(self, tree):
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            assert name not in self.BANNED_CALLS, (name, node.lineno)
            if name == "open":
                modes = [a for a in node.args[1:2]] + [
                    k.value for k in node.keywords if k.arg == "mode"]
                for mode in modes:
                    assert isinstance(mode, ast.Constant), node.lineno
                    assert not set(str(mode.value)) & set("wax+"), node.lineno


class TestCaps:
    def test_line_cap(self):
        text = "\n".join("line %d: hello" % i for i in range(2500))
        report = diagnose_console(text)
        assert report.truncated is True
        assert sum(d.count for d in report.diagnoses) <= MAX_LINES
        assert "Input truncated to 2000 lines." in report.render()

    def test_long_line(self):
        report = diagnose_console("x" * 5000 + ": No such object")
        assert len(report.diagnoses) == 1
        report = diagnose_console("a" * 5000)
        assert report.diagnoses[0].matches == ()
