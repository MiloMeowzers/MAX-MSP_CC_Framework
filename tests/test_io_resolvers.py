"""quick-261013-cyg (Q10): argument-dependent I/O counts match MAX (C1, S6).

Every ``MAX_SAVED`` row is a box MAX itself serialized -- a help patch or
example shipped in the Max 9.2.0 bundle or an installed package -- with the
``(numinlets, numoutlets)`` MAX saved. The citation names the file and the
box text. Rows whose citation says "refpage" have no MAX-saved box and come
from the object's maxref XML; SUMMARY flags them for confirmation in MAX.

Test hygiene:

* Everything except ``TestOracleTargets`` uses only the repo DB (runs in CI
  without Max on Python 3.10 and 3.12).
* ``TestOracleTargets`` (``requires_max``) runs the live help-io oracle and
  asserts every name in :data:`Q10_TARGETS` has 0 count mismatches in the
  bundle.
* Tests never write to the repo; tmp_path only.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

import tools.audit_db as audit_db
from src.maxpat.db_lookup import SUPPORTED_IO_FORMULAS, ObjectDatabase
from src.maxpat.io_resolvers import (
    IO_RESOLVERS,
    box_args,
    normalize_args,
    split_box_text,
)
from src.maxpat.patcher import Patcher
from tests.conftest import MAX_APP_PATH
from tools import help_io

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE = REPO_ROOT / "tests" / "fixtures" / "help_io_baseline.json"

# Names (literal box names, as the oracle keys them) that Q10 fixes. The live
# oracle must report 0 count mismatches for each of them in the bundle.
Q10_TARGETS = (
    "r", "receive", "t",
)

LCD = '"LCD Text / Icon (Inactive)"'
LCD_PRESPLIT = ['"LCD', "Text", "/", "Icon", '(Inactive)"']


@pytest.fixture(scope="module")
def db() -> ObjectDatabase:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ObjectDatabase()


# ── Tokenizer ─────────────────────────────────────────────────────


class TestSplitBoxText:
    def test_quotes_group_and_are_kept(self) -> None:
        assert split_box_text('t "a b" c') == ["t", '"a b"', "c"]

    def test_escaped_space_does_not_split(self) -> None:
        assert split_box_text("x\\ y z") == ["x\\ y", "z"]

    def test_escaped_commas_stay_in_one_token(self) -> None:
        assert split_box_text("expr store(tab3[-1]\\,$i1\\,$i2)") == [
            "expr", "store(tab3[-1]\\,$i1\\,$i2)",
        ]

    def test_escaped_quote_does_not_toggle(self) -> None:
        assert split_box_text('a \\"b c') == ["a", '\\"b', "c"]

    def test_unbalanced_quote_runs_to_end(self) -> None:
        assert split_box_text('"unclosed a b') == ['"unclosed a b']

    def test_trailing_backslash_kept(self) -> None:
        assert split_box_text("a b\\") == ["a", "b\\"]

    @pytest.mark.parametrize("text", ["", "   ", "\t\n"])
    def test_empty(self, text: str) -> None:
        assert split_box_text(text) == []

    def test_tabs_and_newlines_split(self) -> None:
        assert split_box_text("a\tb\nc  d") == ["a", "b", "c", "d"]

    def test_never_raises_on_odd_input(self) -> None:
        assert split_box_text(None) == []  # type: ignore[arg-type]
        assert split_box_text('"' * 7 + "\\") == ['"' * 7 + "\\"]
        assert len(split_box_text("a " * 10000)) == 10000


class TestBoxArgs:
    def test_attributes_stop_args(self) -> None:
        assert box_args("gate~ 3 @ramptime 100") == ("gate~", ["3"])

    def test_quoted_arg_is_one_token(self) -> None:
        assert box_args('route "A B" c') == ("route", ['"A B"', "c"])

    def test_empty(self) -> None:
        assert box_args("") == ("", [])
        assert box_args("   ") == ("", [])

    def test_help_io_delegates(self) -> None:
        for text in ('t "a b" c', "gate~ 3 @ramptime 100", "", "x\\ y z"):
            assert help_io.box_args(text) == box_args(text)
        assert help_io.box_args(f"t {LCD}") == ("t", [LCD])


class TestNormalizeArgs:
    def test_presplit_and_quoted_agree(self) -> None:
        assert normalize_args(LCD_PRESPLIT) == [LCD]
        assert normalize_args([LCD]) == [LCD]

    def test_attributes_dropped(self) -> None:
        assert normalize_args(["sound", "74", "@triggers", "1"]) == ["sound", "74"]

    def test_non_str_elements(self) -> None:
        assert normalize_args([1, 2.5, "x"]) == ["1", "2.5", "x"]

    def test_none(self) -> None:
        assert normalize_args(None) == []
        assert normalize_args([]) == []


# ── MAX-saved counts ──────────────────────────────────────────────

# (name, args, expected (numinlets, numoutlets), citation)
MAX_SAVED = [
    # Task 1: receive, quote-aware trigger
    ("r", ["todrive"], (0, 1), "C74/help/jitter/jit.anim.drive.maxhelp `r todrive`"),
    ("receive", ["bem"], (0, 1), "C74/help/max/forward.maxhelp `receive bem`"),
    ("receive", [], (1, 1), "C74/help/max/receive.maxhelp `receive`"),
    ("t", [LCD], (1, 1), f"C74/help/m4l/live.routing.maxhelp `t {LCD}`"),
    ("t", LCD_PRESPLIT, (1, 1), f"C74/help/m4l/live.routing.maxhelp `t {LCD}` (pre-split)"),
]


@pytest.mark.parametrize(
    "name,args,expected,citation", MAX_SAVED,
    ids=[f"{r[0]}-{i}" for i, r in enumerate(MAX_SAVED)],
)
def test_max_saved_counts(db, name, args, expected, citation) -> None:
    assert db.compute_io_counts(name, args) == expected, citation


# ── Invariants ────────────────────────────────────────────────────


class TestInvariants:
    def test_formula_vocabulary_frozen(self) -> None:
        assert SUPPORTED_IO_FORMULAS == frozenset({
            "", "arg_count", "arg_count+1", "arg_count_or_default",
            "first_arg", "first_arg+1", "second_arg", "second_arg+1",
            "second_arg+2", "inherited_from_subpatch",
        })

    def test_resolver_keys_are_canonical_db_names(self, db) -> None:
        for name in IO_RESOLVERS:
            assert name not in db._aliases, name
            assert db.lookup(name) is not None, name
            assert name not in db._variable_io_rules, name

    def test_resolver_and_rule_objects_report_variable_io(self, db) -> None:
        for name in list(IO_RESOLVERS) + [
            n for n in db._variable_io_rules if not n.startswith("_")
        ]:
            assert db.lookup(name)["variable_io"] is True, name

    def test_resolver_rule_conflict_raises(self, tmp_path: Path) -> None:
        root = tmp_path / "db"
        (root / "max").mkdir(parents=True)
        port = {"id": 0, "type": "anything", "signal": False}
        (root / "max" / "objects.json").write_text(json.dumps({
            "receive": {"name": "receive", "inlets": [port], "outlets": [port]},
        }))
        (root / "overrides.json").write_text(json.dumps({
            "objects": {},
            "variable_io_rules": {
                "receive": {"inlet_count": "fixed:0", "outlet_count": "fixed:1"},
            },
        }))
        with pytest.raises(ValueError, match="receive"):
            ObjectDatabase(root)


class TestPatcherBoxes:
    def test_add_box_named_receive_has_no_inlet(self) -> None:
        p = Patcher()
        b = p.add_box("r", ["foo"])
        assert (b.numinlets, b.numoutlets) == (0, 1)

    def test_receive_box_is_not_content_defined(self) -> None:
        p = Patcher()
        b = p.add_box("r", ["foo"])
        assert p.db.lookup("receive")["variable_io"] is True
        assert p._io_is_content_defined(b) is False


# ── Live oracle ───────────────────────────────────────────────────


@pytest.fixture(scope="module")
def live_section() -> dict:
    envelope = audit_db.run_help_io(max_app=MAX_APP_PATH)
    section = envelope["help_io"]
    assert section["available"], section.get("reason")
    return help_io.build_baseline(section)


@pytest.mark.requires_max
class TestOracleTargets:
    """Every Q10 target has 0 count mismatches against MAX-saved bundle boxes."""

    def test_targets_clean_in_bundle(self, live_section: dict) -> None:
        committed = json.loads(BASELINE.read_text())
        diff = help_io.diff_baselines(committed, live_section)
        stale = diff["stale_sources"].get("bundle")
        if stale is not None:
            pytest.skip(
                f"help-io baseline recorded against Max {stale['baseline']}, "
                f"installed {stale['live']}"
            )
        bundle = live_section["names"].get("bundle", {})
        bad = {
            name: bundle[name]["signatures"]
            for name in Q10_TARGETS
            if bundle.get(name, {}).get("count_mismatches", 0)
        }
        assert not bad, bad
