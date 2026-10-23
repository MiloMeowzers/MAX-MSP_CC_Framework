"""Domain-scope regression tests (quick 261013-mv6, fix-plan Q12).

Covers review findings C3 and C11:

* C3 -- about 360 names whose only DB entries live in ``rnbo/`` and/or
  ``gen/`` passed existence checks at Max top level (``expr~`` is "No such
  object" in MAX; hit for real in tremolo-am-ringmod on 2026-10-04). They are
  now restricted to their domains (implied restriction). An explicit
  ``domain_restricted`` key, even ``[]``, wins; the real Max objects among the
  RNBO-domain entries carry ``[]`` plus bundle evidence. Validation Layer 2
  errors on them outside their scope, Layer 4b is scope-aware, the save gate
  refuses them in a new .maxpat, and ``Patcher.add_box`` refuses them outside
  rnbo~/gen~ patchers.
* C11 (pd-blocklist part) -- ``clip~`` is a real MSP object; MSP has no
  ``wrap~`` (its MAX equivalent is ``pong~ 1 0. 1.``).

Test hygiene: every test uses the repo DB (or a mini DB under ``tmp_path``)
except the ``requires_max`` classes, which read the installed Max bundle.
Files are written only under ``tmp_path``; the repo is never written.
"""

from __future__ import annotations

import copy
import json
import warnings
from pathlib import Path

import pytest

from src.maxpat.db_lookup import (
    DOMAIN_SCOPES,
    ObjectDatabase,
    detect_patcher_scope,
    inner_patcher_scope,
)
from src.maxpat.validation import has_blocking_errors, validate_patch

REPO_ROOT = Path(__file__).resolve().parent.parent

# list.* now alias zl.* (Q38; tests/test_objectfile_aliases.py), so they need no exemption.
EXEMPT = sorted(["rnbo~", "rnbo.remote", "div~", "rdiv~", "rdiv"])


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch):
    """Make sure no inherited git env var can redirect git to another repo."""
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(scope="module")
def db():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ObjectDatabase()


def _box(box_id: str, text: str, n_in: int = 1, n_out: int = 1,
         maxclass: str = "newobj", **extra) -> dict:
    box = {
        "id": box_id,
        "maxclass": maxclass,
        "numinlets": n_in,
        "numoutlets": n_out,
        "outlettype": [""] * n_out,
        "patching_rect": [10.0, 10.0, 80.0, 22.0],
    }
    if maxclass == "newobj":
        box["text"] = text
    box.update(extra)
    return {"box": box}


def _patch(boxes: list, lines: list | None = None, **patcher_keys) -> dict:
    patcher = {"boxes": boxes, "lines": lines or []}
    patcher.update(patcher_keys)
    return {"patcher": patcher}


def _errors(results, layer: str, name: str | None = None) -> list:
    return [
        r for r in results
        if r.layer == layer and r.level == "error"
        and (name is None or f"'{name}'" in r.message)
    ]


def _obj(name: str, domain: str) -> dict:
    return {
        "name": name,
        "maxclass": "newobj",
        "module": domain.lower(),
        "domain": domain,
        "inlets": [{"id": 0, "type": "", "signal": False, "hot": True}],
        "outlets": [{"id": 0, "type": "", "signal": False}],
        "arguments": [],
        "messages": [],
        "min_version": "5.0",
        "verified": True,
        "rnbo_compatible": False,
        "variable_io": False,
    }


def _mini_db(tmp_path: Path, overrides: dict | None = None) -> ObjectDatabase:
    """Build an isolated DB: rnbo/, gen/, msp/, packages/Foo/ plus the four
    supplementary files. Modelled on test_schema_extensions._make_db_root."""
    root = tmp_path / "mini-db"
    files = {
        "rnbo": ["onlyrnbo~", "shared~", "both", "foo~", "exempt~", "pdname~",
                 "aliased~"],
        "gen": ["both", "genonly"],
        "msp": ["bar~", "baz~"],
    }
    domains = {"rnbo": "RNBO", "gen": "Gen", "msp": "MSP"}
    for d, names in files.items():
        (root / d).mkdir(parents=True)
        (root / d / "objects.json").write_text(
            json.dumps({n: _obj(n, domains[d]) for n in names})
        )
    (root / "packages" / "Foo").mkdir(parents=True)
    (root / "packages" / "Foo" / "objects.json").write_text(
        json.dumps({"shared~": _obj("shared~", "Foo")})
    )
    (root / "aliases.json").write_text(json.dumps({"aliases": {"al": "aliased~"}}))
    (root / "relationships.json").write_text(json.dumps({"pairs": [
        {"objects": ["foo~", "bar~"], "relationship": "equivalent"},
        {"objects": ["pdname~", "baz~"], "relationship": "equivalent"},
    ]}))
    (root / "pd-blocklist.json").write_text(json.dumps({"blocklist": {
        "pdname~": {"max_equivalent": "cycle~ 1", "reason": "test"},
    }}))
    objects = {"exempt~": {"domain_restricted": []}}
    objects.update(overrides or {})
    (root / "overrides.json").write_text(
        json.dumps({"objects": objects, "variable_io_rules": {}})
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ObjectDatabase(root)


# ---------------------------------------------------------------------------
# Real DB: implied / effective / explicit restrictions
# ---------------------------------------------------------------------------


class TestRealDbRestrictions:
    @pytest.mark.parametrize("name,expected", [
        ("expr~", ["rnbo"]),
        ("wrap~", ["rnbo"]),
        ("counter~", ["rnbo"]),
        ("dcblock~", ["rnbo"]),
        ("list.store", ["rnbo"]),
        ("history", ["gen"]),
        ("phasor", ["gen"]),
        ("latch", ["gen", "rnbo"]),
        ("clamp", ["gen", "rnbo"]),
        ("mstosamps", ["gen", "rnbo"]),
    ])
    def test_implied(self, db, name, expected):
        assert db.get_implied_restrictions(name) == expected
        assert db.get_effective_restrictions(name) == expected
        # D-05: the explicit accessor stays explicit-only.
        assert db.get_domain_restrictions(name) == []

    @pytest.mark.parametrize("name", [
        "cycle~", "trunc~", "sig~", "param", "in", "out", "gen~", "metro",
        "t", "f",
    ])
    def test_unrestricted(self, db, name):
        assert db.get_implied_restrictions(name) == []
        assert db.get_effective_restrictions(name) == []

    @pytest.mark.parametrize("name", EXEMPT)
    def test_exempt(self, db, name):
        assert db.get_effective_restrictions(name) == []
        assert db.get_implied_restrictions(name) == []
        overrides = json.loads(
            (REPO_ROOT / ".claude/max-objects/overrides.json").read_text()
        )["objects"]
        entry = overrides[name]
        assert entry["domain_restricted"] == []
        scope = entry["_domain_scope"]
        assert {"finding", "evidence", "confidence"} <= set(scope)

    def test_exempt_audit_is_exactly_the_evidence_set(self, db):
        assert db.audit_domain_scope()["exempt"] == EXEMPT

    def test_floor_tilde_explicit(self, db):
        assert db.get_implied_restrictions("floor~") == []
        assert db.get_effective_restrictions("floor~") == ["rnbo"]
        assert db.get_domain_restrictions("floor~") == ["rnbo"]

    def test_codebox_gen_and_rnbo(self, db):
        assert db.get_effective_restrictions("codebox") == ["gen", "rnbo"]
        assert db.get_implied_restrictions("codebox") == []

    def test_explicit_audit(self, db):
        explicit = db.audit_domain_scope()["explicit"]
        assert "floor~" in explicit and "codebox" in explicit

    def test_implied_audit(self, db):
        implied = db.audit_domain_scope()["implied"]
        assert len(implied) >= 300
        assert implied == sorted(implied)
        for name in implied:
            assert set(db.get_sources(name)) <= {"gen", "rnbo"}, name
        assert not set(implied) & set(EXEMPT)
        assert not {"floor~", "codebox", "f"} & set(implied)

    def test_domain_coverage_unchanged(self, db):
        assert db.audit_domain_coverage() == {"restricted_no_coverage": []}

    def test_unknown_name(self, db):
        assert db.get_implied_restrictions("no-such-object~") == []
        assert db.get_effective_restrictions("no-such-object~") == []
        assert db.get_sources("no-such-object~") == []

    def test_fresh_lists(self, db):
        db.get_implied_restrictions("expr~").append("max")
        db.get_effective_restrictions("floor~").append("max")
        assert db.get_implied_restrictions("expr~") == ["rnbo"]
        assert db.get_effective_restrictions("floor~") == ["rnbo"]


class TestRealDbHelpers:
    def test_sources(self, db):
        assert db.get_sources("cycle~") == ["msp", "rnbo"]

    @pytest.mark.parametrize("name,expected", [
        ("clip", True), ("history", True), ("cycle", True),
        ("metro", False), ("coll", False), ("route", False),
    ])
    def test_is_gen_operator(self, db, name, expected):
        assert db.is_gen_operator(name) is expected

    def test_suggest_wrap(self, db):
        assert db.suggest_max_equivalent("wrap~") == "pong~ 1 0. 1."

    def test_suggest_none(self, db):
        assert db.suggest_max_equivalent("expr~") is None

    def test_pd_blocklist_c11(self, db):
        assert db.is_pd_object("clip~") is False
        assert db.is_pd_object("wrap~") is True
        assert db.exists("clip~")


# ---------------------------------------------------------------------------
# Mini DB: semantics in isolation
# ---------------------------------------------------------------------------


class TestMiniDb:
    def test_rnbo_only_restricted(self, tmp_path):
        mdb = _mini_db(tmp_path)
        assert mdb.get_implied_restrictions("onlyrnbo~") == ["rnbo"]
        assert mdb.get_sources("onlyrnbo~") == ["rnbo"]

    def test_package_source_unrestricts(self, tmp_path):
        mdb = _mini_db(tmp_path)
        assert mdb.get_sources("shared~") == ["packages/Foo", "rnbo"]
        assert mdb.get_implied_restrictions("shared~") == []

    def test_gen_and_rnbo(self, tmp_path):
        mdb = _mini_db(tmp_path)
        assert mdb.get_implied_restrictions("both") == ["gen", "rnbo"]
        assert mdb.get_implied_restrictions("genonly") == ["gen"]

    def test_override_empty_suppresses(self, tmp_path):
        mdb = _mini_db(tmp_path)
        assert mdb.get_implied_restrictions("exempt~") == []
        assert mdb.get_effective_restrictions("exempt~") == []
        assert mdb.audit_domain_scope()["exempt"] == ["exempt~"]

    def test_relationships_equivalent_suggestion(self, tmp_path):
        mdb = _mini_db(tmp_path)
        assert mdb.suggest_max_equivalent("foo~") == "bar~"

    def test_pd_blocklist_wins_over_relationships(self, tmp_path):
        mdb = _mini_db(tmp_path)
        assert mdb.suggest_max_equivalent("pdname~") == "cycle~ 1"

    def test_alias_of_restricted_name(self, tmp_path):
        mdb = _mini_db(tmp_path)
        assert mdb.get_implied_restrictions("al") == ["rnbo"]
        assert mdb.get_effective_restrictions("al") == ["rnbo"]
        assert "al" not in mdb.audit_domain_scope()["implied"]

    def test_unrestricted_partner_only(self, tmp_path):
        # bar~'s partner foo~ is restricted -> no suggestion for bar~.
        mdb = _mini_db(tmp_path)
        assert mdb.suggest_max_equivalent("bar~") is None


# ---------------------------------------------------------------------------
# Scope helpers
# ---------------------------------------------------------------------------


class TestScopeHelpers:
    def test_scopes(self):
        assert DOMAIN_SCOPES == ("max", "gen", "rnbo")

    @pytest.mark.parametrize("ns,expected", [
        ("dsp.gen", "gen"), ("jit.gen", "gen"), ("rnbo", "rnbo"),
        ("box", "max"), (None, "max"),
    ])
    def test_classnamespace(self, ns, expected):
        patcher = {"boxes": [], "lines": []}
        if ns is not None:
            patcher["classnamespace"] = ns
        assert detect_patcher_scope({"patcher": patcher}) == expected
        assert detect_patcher_scope(patcher) == expected

    def test_default(self):
        assert detect_patcher_scope({"boxes": []}, default="rnbo") == "rnbo"

    def test_codebox_means_gen(self):
        d = _patch([_box("c", "", maxclass="codebox", code="out1 = in1;")],
                   classnamespace="box")
        assert detect_patcher_scope(d) == "gen"
        assert detect_patcher_scope(d["patcher"]) == "gen"

    @pytest.mark.parametrize("text,maxclass,expected", [
        ("gen~", "newobj", "gen"),
        ("mc.gen~ @chans 4", "newobj", "gen"),
        ("jit.pix", "newobj", "gen"),
        ("rnbo~", "newobj", "rnbo"),
        ("", "rnbo~", "rnbo"),
        ("p sub", "newobj", "max"),
    ])
    def test_inner_scope(self, text, maxclass, expected):
        box = {"maxclass": maxclass, "patcher": {"boxes": [], "lines": []}}
        if maxclass == "newobj":
            box["text"] = text
        assert inner_patcher_scope(box, "max") == expected

    def test_p_inherits(self):
        box = {"maxclass": "newobj", "text": "p x",
               "patcher": {"boxes": [], "lines": []}}
        assert inner_patcher_scope(box, "rnbo") == "rnbo"
        assert inner_patcher_scope(box, "gen") == "gen"

    def test_p_with_rnbo_namespace(self):
        box = {"maxclass": "newobj", "text": "p x",
               "patcher": {"classnamespace": "rnbo", "boxes": [], "lines": []}}
        assert inner_patcher_scope(box, "max") == "rnbo"


# ---------------------------------------------------------------------------
# validate_patch: Layer 2 / Layer 4b with scope
# ---------------------------------------------------------------------------


class TestValidateScope:
    @pytest.mark.parametrize("text", ["expr~ $v1", "wrap~ 0 1", "counter~", "history"])
    def test_spec_names_error_at_max(self, db, text):
        name = text.split()[0]
        results = validate_patch(_patch([_box("b1", text)]), db=db)
        errs = _errors(results, "objects", name)
        assert len(errs) == 1, [r.message for r in results]
        assert "No such object" in errs[0].message
        assert errs[0].auto_fixed is False and errs[0].proposed_removal is None
        assert has_blocking_errors(results)
        if name == "wrap~":
            assert "pong~ 1 0. 1." in errs[0].message
        if name == "history":
            assert "['gen']" in errs[0].message
            assert "gen~" in errs[0].message
        else:
            assert "['rnbo']" in errs[0].message
            assert "rnbo~" in errs[0].message

    def test_floor_tilde_unchanged(self, db):
        results = validate_patch(_patch([_box("f1", "floor~ 0.5")]), db=db)
        dom = _errors(results, "domain", "floor~")
        assert len(dom) == 1, [r.message for r in results]
        assert dom[0].message.startswith(
            "'floor~' is restricted to ['rnbo']; not allowed at MSP/Max top level."
        )
        assert _errors(results, "objects", "floor~") == []

    @pytest.mark.parametrize("text", ["rnbo~", "list.len", "rnbo.remote", "cycle~ 440"])
    def test_unrestricted_clean(self, db, text):
        results = validate_patch(_patch([_box("b1", text)]), db=db)
        assert _errors(results, "objects") == []
        assert _errors(results, "domain") == []

    def test_scope_rnbo_kwarg(self, db):
        d = _patch([_box("b1", "expr~ $v1")])
        assert _errors(validate_patch(d, db=db, scope="rnbo"), "objects") == []

    def test_scope_gen_kwarg(self, db):
        d = _patch([_box("b1", "history"), _box("b2", "expr~ $v1")])
        errs = _errors(validate_patch(d, db=db, scope="gen"), "objects")
        assert [e for e in errs if "'history'" in e.message] == []
        assert len([e for e in errs if "'expr~'" in e.message]) == 1

    def test_classnamespace_rnbo(self, db):
        d = _patch([_box("b1", "expr~ $v1")], classnamespace="rnbo")
        assert _errors(validate_patch(d, db=db), "objects") == []

    def test_classnamespace_dsp_gen(self, db):
        d = _patch([_box("b1", "history")], classnamespace="dsp.gen")
        assert _errors(validate_patch(d, db=db), "objects") == []

    def test_top_level_codebox_means_gen(self, db):
        d = _patch([
            _box("c1", "", maxclass="codebox", code="out1 = in1;"),
            _box("b1", "history"),
        ])
        results = validate_patch(d, db=db)
        assert _errors(results, "objects") == []
        assert _errors(results, "domain") == []

    def test_bogus_scope(self, db):
        with pytest.raises(ValueError):
            validate_patch(_patch([]), db=db, scope="bogus")

    def test_input_not_mutated(self, db):
        d = _patch([_box("b1", "expr~ $v1")])
        before = copy.deepcopy(d)
        validate_patch(d, db=db)
        assert d == before

    def test_layer4b_floor_in_rnbo_scope(self, db):
        d = _patch([_box("f1", "floor~ 0.5")])
        assert _errors(validate_patch(d, db=db, scope="rnbo"), "domain") == []

    def test_layer4b_codebox_newobj(self, db):
        d = _patch([_box("c1", "codebox")])
        dom = _errors(validate_patch(d, db=db), "domain", "codebox")
        assert len(dom) == 1
        assert "['gen', 'rnbo']" in dom[0].message
        assert _errors(validate_patch(d, db=db, scope="gen"), "domain") == []

    def test_layer4b_scope_message(self, db):
        d = _patch([_box("f1", "floor~ 0.5")])
        dom = _errors(validate_patch(d, db=db, scope="gen"), "domain", "floor~")
        assert len(dom) == 1
        assert dom[0].message == (
            "'floor~' is restricted to ['rnbo']; not allowed in a gen patcher."
        )

    def test_generate_gendsp_validates_clean(self, db):
        from src.maxpat.codegen import generate_gendsp
        d = generate_gendsp("out1 = in1;", 1, 1)
        results = validate_patch(d, db=db)
        assert _errors(results, "objects") == []
        assert _errors(results, "domain") == []


# ---------------------------------------------------------------------------
# Save gate, end to end
# ---------------------------------------------------------------------------


class TestSaveGate:
    def test_new_maxpat_with_expr_tilde_refused(self, tmp_path):
        from src.maxpat.hooks import PatchValidationError, save_patch_roundtrip
        d = _patch([
            _box("obj-1", "cycle~ 440", n_in=2, n_out=1, outlettype=["signal"]),
            _box("obj-2", "expr~ $v1", n_in=1, n_out=1, outlettype=["signal"]),
        ])
        target = tmp_path / "new.maxpat"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pytest.raises(PatchValidationError) as exc:
                save_patch_roundtrip(d, target)
        msgs = [getattr(f, "message", "") for f in exc.value.findings]
        assert any(
            getattr(f, "layer", None) == "objects" and "'expr~'" in m
            for f, m in zip(exc.value.findings, msgs)
        ), msgs
        assert not target.exists()


# ---------------------------------------------------------------------------
# requires_max: the installed bundle is the oracle
# ---------------------------------------------------------------------------


def _bundle_root():
    from tests.conftest import MAX_APP_PATH
    return MAX_APP_PATH / "Contents" / "Resources" / "C74"


def _walk_max_scope_boxes(patcher: dict, scope: str, out: list) -> None:
    for entry in patcher.get("boxes", []) or []:
        box = entry.get("box") if isinstance(entry, dict) else None
        if not isinstance(box, dict):
            continue
        if scope == "max" and box.get("maxclass") == "newobj":
            text = box.get("text")
            if isinstance(text, str) and text.split():
                out.append(text.split()[0])
        inner = box.get("patcher")
        if isinstance(inner, dict):
            _walk_max_scope_boxes(inner, inner_patcher_scope(box, scope), out)


@pytest.fixture(scope="module")
def bundle_max_scope_names():
    """{name: first relpath} for every Max-scope newobj box in the bundle."""
    root = _bundle_root()
    names: dict[str, str] = {}
    files = sorted(
        list(root.rglob("*.maxpat")) + list(root.rglob("*.maxhelp"))
    )
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8", errors="replace"))
        except (ValueError, OSError):
            continue
        if not isinstance(d, dict) or not isinstance(d.get("patcher"), dict):
            continue
        out: list[str] = []
        _walk_max_scope_boxes(d["patcher"], detect_patcher_scope(d), out)
        rel = str(f.relative_to(root))
        for n in out:
            names.setdefault(n, rel)
    return names


@pytest.mark.requires_max
class TestBundleOracle:
    def test_no_max_scope_box_is_implied_restricted(self, db, bundle_max_scope_names):
        bad = {
            n: where for n, where in bundle_max_scope_names.items()
            if db.get_implied_restrictions(n)
        }
        assert bad == {}

    def test_every_exemption_has_bundle_evidence(self, db, bundle_max_scope_names):
        root = _bundle_root()
        mapping_text = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in (root / "init").glob("*objectmappings*.txt")
        )
        mapped = set()
        for line in mapping_text.splitlines():
            toks = line.replace(";", " ").split()
            if len(toks) >= 4 and toks[0] == "max" and toks[1] in ("objectfile", "define"):
                mapped.update(toks[2:4])
        mxo = {p.name[:-4] for p in root.rglob("*.mxo")}
        missing = [
            n for n in db.audit_domain_scope()["exempt"]
            if n not in mapped and n not in mxo and n not in bundle_max_scope_names
        ]
        assert missing == []


# ===========================================================================
# Task 2: builder contexts (Patcher.domain_context)
# ===========================================================================


def _new_patcher(db, **kw):
    from src.maxpat.patcher import Patcher
    return Patcher(db=db, **kw)


class TestPatcherContext:
    def test_default_max(self, db):
        assert _new_patcher(db).domain_context == "max"

    def test_bogus_context(self, db):
        with pytest.raises(ValueError):
            _new_patcher(db, domain_context="bogus")

    @pytest.mark.parametrize("name", ["expr~", "wrap~", "counter~", "history", "floor~"])
    def test_add_box_refused_at_max(self, db, name):
        p = _new_patcher(db)
        p.add_box("cycle~", args=["440"])
        n_boxes, next_id = len(p.boxes), p._next_id
        with pytest.raises(ValueError) as exc:
            p.add_box(name)
        msg = str(exc.value)
        assert f"'{name}'" in msg
        assert repr(db.get_effective_restrictions(name)) in msg
        assert "max" in msg and "Rule #1" in msg
        if name == "wrap~":
            assert "pong~ 1 0. 1." in msg
        assert len(p.boxes) == n_boxes and p._next_id == next_id

    @pytest.mark.parametrize("name", ["cycle~", "rnbo~", "list.len", "div~"])
    def test_add_box_accepted_at_max(self, db, name):
        p = _new_patcher(db)
        assert p.add_box(name).name == name

    def test_m4l_carve_out(self, tmp_path):
        mdb = _mini_db(tmp_path, {"baz~": {"domain_restricted": ["m4l"]}})
        p = _new_patcher(mdb)
        assert p.add_box("baz~").name == "baz~"
        with pytest.raises(ValueError):
            p.add_box("onlyrnbo~")


class TestInnerContexts:
    def test_add_rnbo_inner(self, db):
        from src.maxpat.rnbo import add_rnbo
        p = _new_patcher(db)
        _, inner = add_rnbo(p)
        assert inner.domain_context == "rnbo"
        inner.add_box("expr~", args=["$v1"])
        inner.add_box("wrap~")
        with pytest.raises(ValueError):
            inner.add_box("history")

    def test_add_gen_inner(self, db):
        p = _new_patcher(db)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _, inner = p.add_gen("out1 = in1;")
        assert inner.domain_context == "gen"
        inner.add_box("history")
        inner.add_box("phasor")
        inner.add_box("codebox")
        with pytest.raises(ValueError):
            inner.add_box("expr~")

    def test_subpatcher_inherits(self, db):
        from src.maxpat.rnbo import add_rnbo
        p = _new_patcher(db)
        _, sub = p.add_subpatcher("sub")
        assert sub.domain_context == "max"
        with pytest.raises(ValueError):
            sub.add_box("expr~")
        _, rinner = add_rnbo(p)
        _, rsub = rinner.add_subpatcher("rsub")
        assert rsub.domain_context == "rnbo"
        rsub.add_box("expr~")

    def test_embedded_bpatcher_inherits(self, db):
        from src.maxpat.rnbo import add_rnbo
        p = _new_patcher(db)
        _, top_bp = p.add_bpatcher(embedded=True)
        assert top_bp.domain_context == "max"
        _, rinner = add_rnbo(p)
        _, bp = rinner.add_bpatcher(embedded=True)
        assert bp.domain_context == "rnbo"
        bp.add_box("expr~")

    def test_validate_gen_inner(self, db):
        p = _new_patcher(db)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _, inner = p.add_gen("out1 = in1;")
        inner.add_box("history")
        assert _errors(validate_patch(inner), "objects") == []

    def test_validate_uses_domain_context(self, db):
        # No codebox and no classnamespace: only domain_context says gen.
        p = _new_patcher(db, domain_context="gen")
        p.add_box("history")
        assert _errors(validate_patch(p), "objects") == []
        assert len(_errors(validate_patch(p, scope="max"), "objects", "history")) == 1


def _inner(boxes, **keys) -> dict:
    d = {"boxes": boxes, "lines": []}
    d.update(keys)
    return d


def _container(box_id, text, inner, maxclass="newobj"):
    entry = _box(box_id, text, maxclass=maxclass)
    entry["box"]["patcher"] = inner
    return entry


class TestFromDict:
    def _loaded(self, db, d, **kw):
        from src.maxpat.patcher import Patcher
        return Patcher.from_dict(copy.deepcopy(d), db=db, **kw)

    def test_rnbo_container_and_nested_p(self, db):
        d = _patch([
            _container("obj-1", "rnbo~", _inner(
                [_container("obj-2", "p inner", _inner([_box("obj-3", "expr~ $v1")]))],
                classnamespace="rnbo",
            )),
            _container("obj-4", "gen~", _inner([_box("obj-5", "history")])),
            _container("obj-6", "p top", _inner([_box("obj-7", "cycle~ 440")])),
        ])
        p = self._loaded(db, d)
        assert p.domain_context == "max"
        by_id = {b.id: b for b in p.boxes}
        rnbo_inner = by_id["obj-1"]._inner_patcher
        assert rnbo_inner.domain_context == "rnbo"
        assert rnbo_inner.boxes[0]._inner_patcher.domain_context == "rnbo"
        assert by_id["obj-4"]._inner_patcher.domain_context == "gen"
        assert by_id["obj-6"]._inner_patcher.domain_context == "max"
        assert p.to_dict() == d

    def test_top_level_dsp_gen(self, db):
        d = _patch([_box("obj-1", "history")], classnamespace="dsp.gen")
        assert self._loaded(db, d).domain_context == "gen"

    def test_explicit_context(self, db):
        d = _patch([_box("obj-1", "expr~ $v1")])
        p = self._loaded(db, d, domain_context="rnbo")
        assert p.domain_context == "rnbo"
        assert p.to_dict() == d


class TestRefusedEditsLeavePatchIntact:
    def _setup(self, db):
        p = _new_patcher(db)
        c = p.add_box("cycle~", args=["440"])
        g = p.add_box("*~", args=["0.5"])
        p.add_connection(c, 0, g, 0)
        return p, c, g

    @staticmethod
    def _snapshot(p):
        return (
            [b.id for b in p.boxes],
            [(ln.source_id, ln.source_outlet, ln.dest_id, ln.dest_inlet) for ln in p.lines],
            p._next_id,
        )

    def test_replace_box(self, db):
        p, c, _ = self._setup(db)
        before = self._snapshot(p)
        with pytest.raises(ValueError):
            p.replace_box(c, "expr~", args=["$v1"])
        assert self._snapshot(p) == before
        assert c in p.boxes

    def test_replace_box_safe(self, db):
        p, c, _ = self._setup(db)
        before = self._snapshot(p)
        with pytest.raises(ValueError):
            p.replace_box_safe(c, "expr~", args=["$v1"])
        assert self._snapshot(p) == before

    def test_insert_into_connection(self, db):
        p, c, g = self._setup(db)
        before = self._snapshot(p)
        with pytest.raises(ValueError):
            p.insert_into_connection(c, g, "expr~", args=["$v1"])
        assert self._snapshot(p) == before


def _visual_gen_dict(db) -> dict:
    """A visual (no codebox) Gen patcher: in 1 -> history -> out 1."""
    def box(bid, text):
        name = text.split()[0]
        args = text.split()[1:]
        n_in, n_out = db.compute_io_counts(name, args)
        return _box(bid, text, n_in=n_in, n_out=n_out)
    return _patch(
        [box("obj-1", "in 1"), box("obj-2", "history"), box("obj-3", "out 1")],
        [
            {"patchline": {"source": ["obj-1", 0], "destination": ["obj-2", 0]}},
            {"patchline": {"source": ["obj-2", 0], "destination": ["obj-3", 0]}},
        ],
        classnamespace="box",
    )


class TestHooksScope:
    def test_read_patch_gendsp(self, db, tmp_path):
        from src.maxpat.hooks import read_patch
        f = tmp_path / "v.gendsp"
        f.write_text(json.dumps(_visual_gen_dict(db)))
        p, _ = read_patch(f)
        assert p.domain_context == "gen"
        assert _errors(validate_patch(p), "objects") == []

    def test_read_patch_maxpat(self, db, tmp_path):
        from src.maxpat.hooks import read_patch
        f = tmp_path / "v.maxpat"
        f.write_text(json.dumps(_visual_gen_dict(db)))
        p, _ = read_patch(f)
        assert p.domain_context == "max"

    def test_validate_file(self, db, tmp_path):
        from src.maxpat.hooks import validate_file
        d = _visual_gen_dict(db)
        g = tmp_path / "v.gendsp"
        g.write_text(json.dumps(d))
        m = tmp_path / "v.maxpat"
        m.write_text(json.dumps(d))
        assert _errors(validate_file(g), "objects", "history") == []
        assert len(_errors(validate_file(m), "objects", "history")) == 1

    def test_save_gate_gendsp_saves(self, db, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip
        target = tmp_path / "v2.gendsp"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            save_patch_roundtrip(_visual_gen_dict(db), target)
        assert target.exists()

    def test_save_gate_maxpat_refused(self, db, tmp_path):
        from src.maxpat.hooks import PatchValidationError, save_patch_roundtrip
        target = tmp_path / "v.maxpat"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with pytest.raises(PatchValidationError) as exc:
                save_patch_roundtrip(_visual_gen_dict(db), target)
        assert any(
            getattr(f, "layer", None) == "objects" and "'history'" in f.message
            for f in exc.value.findings
        )
        assert not target.exists()
