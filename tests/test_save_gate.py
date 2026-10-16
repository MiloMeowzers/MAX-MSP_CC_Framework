"""Save gate regression tests (quick 261012-qsr, fix-plan Q7).

Covers review finding A3 (saves never ran validation or the critics, so
blockers came in through auto-commits) and recommendation R1 (an automatic,
non-mutating save gate in save_patch_roundtrip / write_gendsp: refuse only
blockers the save introduces, force=True to override, one cached DB).

Every git operation here runs inside a throwaway repo under pytest's
``tmp_path``, never in the MAX repo. An autouse fixture strips GIT_DIR,
GIT_WORK_TREE and GIT_INDEX_FILE from the environment as a guard. Committed
patches under ``patches/`` are only read (json.load + deepcopy), never
written.
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import warnings
from pathlib import Path

import pytest

from src.maxpat.patcher import Patcher

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git is not installed"
)

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fixtures and helpers (copied from tests/test_save_safety.py, not imported)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch):
    """Make sure no inherited git env var can redirect git to another repo."""
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(var, raising=False)


def _git(root: Path, *args: str) -> str:
    """Run git in *root* (check=True) and return stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _repo(tmp_path: Path) -> Path:
    """Create a throwaway git repo at tmp_path/repo and return its resolved root."""
    root = tmp_path / "repo"
    root.mkdir()
    hooks = tmp_path / "empty-hooks"
    hooks.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Save Gate Test")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "config", "core.hooksPath", str(hooks))
    return root.resolve()


def _staged(root: Path) -> list[str]:
    return [l for l in _git(root, "diff", "--cached", "--name-only").splitlines() if l]


def _head_files(root: Path) -> list[str]:
    return [l for l in _git(root, "show", "--name-only", "--format=", "HEAD").splitlines() if l]


def _head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").strip()


def _has_head(root: Path) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "-q", "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _patch_path(root: Path) -> Path:
    return root / "patches" / "demo" / "generated" / "demo.maxpat"


REL_P = "patches/demo/generated/demo.maxpat"


# ---------------------------------------------------------------------------
# Patch fixtures
# ---------------------------------------------------------------------------


def _fan() -> dict:
    """FAN: number -> + 0 inlet 0, + -> print (clean). Ids obj-1..obj-3."""
    p = Patcher()
    n = p.add_box("number")
    a = p.add_box("+", ["0"])
    pr = p.add_box("print")
    p.add_connection(n, 0, a, 0)
    p.add_connection(a, 0, pr, 0)
    return p.to_dict()


def _gain() -> dict:
    """GAIN: cycle~ 440 -> dac~ (critic blocker 'Missing gain staging')."""
    p = Patcher()
    c = p.add_box("cycle~", ["440"])
    d = p.add_box("dac~")
    p.add_connection(c, 0, d, 0)
    return p.to_dict()


def _add_oor(d: dict) -> dict:
    """Append the raw out-of-range patchline obj-1:0 -> obj-2:7."""
    d["patcher"]["lines"].append(
        {"patchline": {"source": ["obj-1", 0], "destination": ["obj-2", 7]}}
    )
    return d


def _seed(root: Path, P: Path, d: dict) -> str:
    """Write d directly to P and commit it (bypasses the gate). Returns the text."""
    text = json.dumps(d, indent=4)
    P.parent.mkdir(parents=True, exist_ok=True)
    P.write_text(text)
    rel = P.relative_to(root).as_posix()
    _git(root, "add", "--", rel)
    _git(root, "commit", "-q", "-m", "seed", "--", rel)
    return text


def _box_by_id(p: Patcher, box_id: str):
    for b in p.boxes:
        if b.id == box_id:
            return b
    raise KeyError(box_id)


def _reconverge_edit(P: Path):
    """Read P (FAN), add number -> + inlet 1 (reconverging fan-out)."""
    from src.maxpat.hooks import read_patch

    p, T = read_patch(P)
    p.add_connection(_box_by_id(p, "obj-1"), 0, _box_by_id(p, "obj-2"), 1)
    return p, T


# ---------------------------------------------------------------------------
# Task 1: new-blocker gate on save_patch_roundtrip
# ---------------------------------------------------------------------------


class TestNewBlockerGate:
    def test_new_file_with_critic_blocker_refused(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, PatchValidationError
        from src.maxpat.critics import CriticResult

        root = _repo(tmp_path)
        P = _patch_path(root)
        d = _gain()
        before = copy.deepcopy(d)

        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(d, P)

        exc = excinfo.value
        assert len(exc.findings) == 1
        assert isinstance(exc.findings[0], CriticResult)
        assert "Missing gain staging" in exc.findings[0].finding
        assert exc.path == P
        assert "force=True" in str(exc)
        assert not P.exists()
        assert not _has_head(root)
        assert d == before

    def test_new_file_with_proposed_removal_refused(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, PatchValidationError
        from src.maxpat.validation import ValidationResult

        root = _repo(tmp_path)
        P = _patch_path(root)
        p = Patcher()
        p.add_box("number")
        p.add_box("print")
        d = _add_oor(p.to_dict())

        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(d, P)

        findings = excinfo.value.findings
        assert len(findings) == 1
        assert isinstance(findings[0], ValidationResult)
        assert findings[0].proposed_removal == ("obj-1", 0, "obj-2", 7)
        assert not P.exists()

    def test_new_reconverging_fanout_refused_vs_original_text(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, PatchValidationError

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_fan(), P)
        head_before = _head(root)
        staged_before = _staged(root)
        p, T = _reconverge_edit(P)

        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(p.to_dict(), P, T)

        findings = excinfo.value.findings
        assert len(findings) == 1
        assert "reconverge" in findings[0].finding
        assert P.read_text() == T
        assert _head(root) == head_before
        assert _staged(root) == staged_before

    def test_new_reconverging_fanout_refused_vs_head(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, PatchValidationError

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_fan(), P)
        head_before = _head(root)
        p, T = _reconverge_edit(P)

        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(p.to_dict(), P)

        assert any("reconverge" in f.finding for f in excinfo.value.findings)
        assert P.read_text() == T
        assert _head(root) == head_before

    def test_new_proposed_removal_on_existing_file_refused(self, tmp_path):
        """Q1 hand-off: a NEW proposed removal blocks on the edit path too."""
        from src.maxpat.hooks import save_patch_roundtrip, read_patch, PatchValidationError

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_fan(), P)
        p, T = read_patch(P)
        d = _add_oor(p.to_dict())

        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(d, P, T)

        assert any(
            getattr(f, "proposed_removal", None) == ("obj-1", 0, "obj-2", 7)
            for f in excinfo.value.findings
        )
        assert P.read_text() == T

    def test_preexisting_blockers_unchanged_save(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch

        root = _repo(tmp_path)
        P = _patch_path(root)
        _seed(root, P, _add_oor(_gain()))
        p, T = read_patch(P)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # "no changes to commit" is fine
            save_patch_roundtrip(p.to_dict(), P, T)

    def test_preexisting_blockers_edit_saves_vs_original_text(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch

        root = _repo(tmp_path)
        P = _patch_path(root)
        _seed(root, P, _add_oor(_gain()))
        head_before = _head(root)
        p, T = read_patch(P)
        p.add_box("print", ["other"])

        result = save_patch_roundtrip(p.to_dict(), P, T)

        assert result == _head(root)
        assert result != head_before

    def test_preexisting_blockers_edit_saves_vs_head(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch

        root = _repo(tmp_path)
        P = _patch_path(root)
        _seed(root, P, _add_oor(_gain()))
        p, _T = read_patch(P)
        p.add_box("print", ["other"])

        result = save_patch_roundtrip(p.to_dict(), P)

        assert result == _head(root)

    def test_second_instance_of_existing_blocker_refused(self, tmp_path):
        """Multiset: one GAIN in the baseline does not cover a second one."""
        from src.maxpat.hooks import save_patch_roundtrip, read_patch, PatchValidationError

        root = _repo(tmp_path)
        P = _patch_path(root)
        _seed(root, P, _gain())
        p, T = read_patch(P)
        c2 = p.add_box("cycle~", ["440"])
        p.add_connection(c2, 0, _box_by_id(p, "obj-2"), 1)

        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(p.to_dict(), P, T)

        findings = excinfo.value.findings
        assert len(findings) == 1
        assert f"({c2.id})" in findings[0].finding
        assert P.read_text() == T

    def test_oq1_non_git_file_on_disk_is_baseline(self, tmp_path):
        """OQ1-A (user-chosen): an existing untracked file is its own baseline."""
        from src.maxpat.hooks import save_patch_roundtrip, read_patch

        X = tmp_path / "plain" / "x.maxpat"
        X.parent.mkdir()
        X.write_text(json.dumps(_add_oor(_gain()), indent=4))
        p, _T = read_patch(X)
        p.add_box("print", ["other"])

        with pytest.warns(UserWarning, match="not inside a git repository"):
            result = save_patch_roundtrip(p.to_dict(), X)

        assert result is None
        assert json.loads(X.read_text()) == p.to_dict()

    def test_force_bypasses_with_warning(self, tmp_path):
        from src.maxpat.hooks import format_patch_text, save_patch_roundtrip, SaveGateWarning

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_fan(), P)
        p, T = _reconverge_edit(P)
        new_dict = p.to_dict()

        with pytest.warns(SaveGateWarning, match="force=True"):
            result = save_patch_roundtrip(new_dict, P, T, force=True)

        assert result == _head(root)
        expected = format_patch_text(new_dict, T)
        assert P.read_text() == expected

    def test_patch_validation_error_bare_message(self):
        from src.maxpat.hooks import PatchValidationError

        e = PatchValidationError("m")
        assert str(e) == "m"
        assert e.findings == []
        assert e.port_changes == []
        assert e.path is None

    def test_save_gate_warning_exported(self):
        from src.maxpat import SaveGateWarning
        from src.maxpat.hooks import SaveGateWarning as HooksSaveGateWarning

        assert SaveGateWarning is HooksSaveGateWarning
        assert issubclass(SaveGateWarning, UserWarning)


class TestFindingKey:
    def test_same_template_different_names_and_numbers_match(self):
        from src.maxpat.hooks import _finding_key
        from src.maxpat.critics import CriticResult

        a = CriticResult("blocker", "Thing 'foo' (obj-3) has 2 outlets", "s")
        b = CriticResult("blocker", "Thing \"bar\" (obj-3) has 17 outlets", "t")
        assert _finding_key(a) == _finding_key(b)

    def test_different_box_id_differs(self):
        from src.maxpat.hooks import _finding_key
        from src.maxpat.critics import CriticResult

        a = CriticResult("blocker", "Thing 'foo' (obj-3) has 2 outlets", "s")
        b = CriticResult("blocker", "Thing 'foo' (obj-4) has 2 outlets", "s")
        assert _finding_key(a) != _finding_key(b)

    def test_proposed_removal_ids_in_key(self):
        from src.maxpat.hooks import _finding_key
        from src.maxpat.validation import ValidationResult

        r = ValidationResult(
            "connections", "error",
            "Inlet index 7 out of bounds on 'obj-2' (has 2 inlet(s))",
            proposed_removal=("obj-1", 0, "obj-2", 7),
        )
        key = _finding_key(r)
        assert ("obj-1", "obj-2") in key
        assert ("obj-1", 0, "obj-2", 7) in key

    def test_origin_distinguishes_validation_and_review(self):
        from src.maxpat.hooks import _finding_key
        from src.maxpat.critics import CriticResult
        from src.maxpat.validation import ValidationResult

        a = CriticResult("blocker", "same text", "s")
        b = ValidationResult("domain", "error", "same text")
        assert _finding_key(a) != _finding_key(b)


    def test_path_distinguishes_keys(self):
        from src.maxpat.hooks import _finding_key
        from src.maxpat.validation import ValidationResult

        a = ValidationResult("objects", "error", "[p voice] same", path="obj-1")
        b = ValidationResult("objects", "error", "[p voice] same", path="obj-2")
        assert _finding_key(a) != _finding_key(b)
        c = ValidationResult("objects", "error", "same", path="")
        d = ValidationResult("objects", "error", "same")
        assert _finding_key(c) == _finding_key(d)


def _voice_pair(osc_in: str) -> dict:
    """Two `p voice` boxes (obj-1, obj-2) with identical inner ids; the one
    named by *osc_in* holds osc~ (a PD-object blocker), the other cycle~."""

    def voice(box_id: str, text: str) -> dict:
        return {"box": {
            "id": box_id, "maxclass": "newobj", "text": "p voice",
            "numinlets": 0, "numoutlets": 0, "outlettype": [],
            "patching_rect": [10.0, 10.0, 60.0, 22.0],
            "patcher": {"boxes": [{"box": {
                "id": "obj-10", "maxclass": "newobj", "text": text,
                "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                "patching_rect": [10.0, 10.0, 60.0, 22.0],
            }}], "lines": []},
        }}

    return {"patcher": {"boxes": [
        voice("obj-1", "osc~ 440" if osc_in == "obj-1" else "cycle~ 440"),
        voice("obj-2", "osc~ 440" if osc_in == "obj-2" else "cycle~ 440"),
    ], "lines": []}}


class TestNestedGateKey:
    def test_moved_nested_blocker_is_new(self):
        from src.maxpat.hooks import _gate_report

        baseline = _voice_pair("obj-1")
        new = _voice_pair("obj-2")
        report = _gate_report(new, baseline, [])
        assert len(report.new_blockers) == 1, report.new_blockers
        assert report.new_blockers[0].path == "obj-2"
        assert "'osc~'" in report.new_blockers[0].message


class TestGateDb:
    def test_gate_db_cached(self):
        from src.maxpat.hooks import _gate_db

        assert _gate_db() is _gate_db()

    def test_review_patch_accepts_db(self):
        from src.maxpat.hooks import _gate_db
        from src.maxpat.critics import review_patch

        d = _gain()
        with_db = [r.severity for r in review_patch(d, db=_gate_db())]
        without = [r.severity for r in review_patch(d)]
        assert with_db == without
        assert "blocker" in with_db

    def test_clean_save_constructs_no_database(self, tmp_path, monkeypatch):
        from src.maxpat.hooks import _gate_db, save_patch_roundtrip
        from src.maxpat import db_lookup

        d = _fan()  # Patcher() builds its own DB; do this first
        _gate_db()
        root = _repo(tmp_path)
        P = _patch_path(root)

        calls = []
        original = db_lookup.ObjectDatabase.__init__

        def counting(self, *args, **kwargs):
            calls.append(1)
            original(self, *args, **kwargs)

        monkeypatch.setattr(db_lookup.ObjectDatabase, "__init__", counting)
        result = save_patch_roundtrip(d, P)

        assert result == _head(root)
        assert calls == []


# ---------------------------------------------------------------------------
# Task 2: cord-removal warning, port x-rank block, write_gendsp gate
# ---------------------------------------------------------------------------


def _sub() -> dict:
    """SUB: top-level p ctl (obj-1; inner inlets obj-1 x50, obj-2 x130,
    outlet obj-3, inner cord obj-1:0 -> obj-3:0), number (obj-2) -> p ctl
    inlet 0, p ctl outlet 0 -> print (obj-3)."""
    p = Patcher()
    box, inner = p.add_subpatcher("ctl", inlets=2, outlets=1)
    inner.add_connection(inner.get_inlets()[0], 0, inner.get_outlets()[0], 0)
    n = p.add_box("number")
    pr = p.add_box("print")
    p.add_connection(n, 0, box, 0)
    p.add_connection(box, 0, pr, 0)
    return p.to_dict()


def _abs() -> dict:
    """ABS: abstraction top level with inlet obj-1, outlets obj-2 (x50), obj-3 (x130)."""
    _, inner = Patcher().add_subpatcher("abs", inlets=1, outlets=2)
    return inner.to_dict()


def _ctl_box(d: dict) -> dict:
    for entry in d["patcher"]["boxes"]:
        if entry["box"].get("text") == "p ctl":
            return entry["box"]
    raise KeyError("p ctl")


def _inner_box(patcher: dict, box_id: str) -> dict:
    for entry in patcher["boxes"]:
        if entry["box"]["id"] == box_id:
            return entry["box"]
    raise KeyError(box_id)


def _swap_x(patcher: dict, id_a: str, id_b: str) -> None:
    a = _inner_box(patcher, id_a)["patching_rect"]
    b = _inner_box(patcher, id_b)["patching_rect"]
    a[0], b[0] = b[0], a[0]


def _add_inner_inlet(d: dict, x: float) -> None:
    ctl = _ctl_box(d)
    ctl["patcher"]["boxes"].append({"box": {
        "id": "obj-90", "maxclass": "inlet", "numinlets": 0, "numoutlets": 1,
        "outlettype": [""], "patching_rect": [x, 30.0, 30.0, 30.0],
    }})
    ctl["numinlets"] = 3


def _drop_line(patcher: dict, src: str, dst: str) -> None:
    patcher["lines"] = [
        l for l in patcher["lines"]
        if not (l["patchline"]["source"][0] == src and l["patchline"]["destination"][0] == dst)
    ]


def _disk_edit(P: Path, T: str, mutate) -> None:
    """Write a modified copy of T to P without committing (a MAX save)."""
    data = json.loads(T)
    mutate(data)
    P.write_text(json.dumps(data, indent=4))


def _gate_warnings(record) -> list:
    from src.maxpat.hooks import SaveGateWarning

    return [w for w in record if issubclass(w.category, SaveGateWarning)]


class TestCordRemoval:
    def test_removed_top_level_cord_warns_once(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_fan(), P)
        p, T = read_patch(P)
        d = p.to_dict()
        _drop_line(d["patcher"], "obj-2", "obj-3")

        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            result = save_patch_roundtrip(d, P, T)

        gate = _gate_warnings(record)
        assert len(gate) == 1
        msg = str(gate[0].message)
        assert "1 cord(s) removed compared with HEAD" in msg
        assert "obj-2:0 -> obj-3:0" in msg
        assert "endpoint box deleted" not in msg
        assert result == _head(root)

    def test_deleted_endpoint_marked(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_fan(), P)
        p, T = read_patch(P)
        p.remove_box(_box_by_id(p, "obj-3"))

        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            save_patch_roundtrip(p.to_dict(), P, T)

        gate = _gate_warnings(record)
        assert len(gate) == 1
        msg = str(gate[0].message)
        assert "obj-2:0 -> obj-3:0" in msg
        assert "(endpoint box deleted)" in msg

    def test_removed_nested_cord_warns_with_path(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_sub(), P)
        p, T = read_patch(P)
        d = p.to_dict()
        _drop_line(_ctl_box(d)["patcher"], "obj-1", "obj-3")

        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            save_patch_roundtrip(d, P, T)

        gate = _gate_warnings(record)
        assert len(gate) == 1
        msg = str(gate[0].message)
        assert "1 cord(s) removed" in msg
        assert "p ctl" in msg
        assert "obj-1:0 -> obj-3:0" in msg

    def test_cord_removed_before_this_save_is_exempt(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_fan(), P)
        T0 = P.read_text()
        _disk_edit(P, T0, lambda d: _drop_line(d["patcher"], "obj-2", "obj-3"))
        p, T = read_patch(P)
        p.add_box("print", ["other"])

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = save_patch_roundtrip(p.to_dict(), P, T)

        assert result == _head(root)

    def test_clean_edit_emits_no_warning(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_fan(), P)
        p, T = read_patch(P)
        p.add_box("print", ["other"])

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = save_patch_roundtrip(p.to_dict(), P, T)

        assert result == _head(root)


class TestPortOrder:
    def test_swapped_inner_inlets_refused(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch, PatchValidationError

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_sub(), P)
        head_before = _head(root)
        p, T = read_patch(P)
        d = p.to_dict()
        _swap_x(_ctl_box(d)["patcher"], "obj-1", "obj-2")

        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(d, P, T)

        changes = excinfo.value.port_changes
        joined = "\n".join(changes)
        assert "inlet obj-1" in joined
        assert "inlet obj-2" in joined
        assert "p ctl" in joined
        assert "x-rank" in str(excinfo.value)
        assert P.read_text() == T
        assert _head(root) == head_before

    def test_swapped_inner_inlets_force_saves(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch, SaveGateWarning

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_sub(), P)
        p, T = read_patch(P)
        d = p.to_dict()
        _swap_x(_ctl_box(d)["patcher"], "obj-1", "obj-2")

        with pytest.warns(SaveGateWarning, match="force=True"):
            result = save_patch_roundtrip(d, P, T, force=True)

        assert result == _head(root)
        assert json.loads(P.read_text()) == d

    def test_abstraction_top_level_outlet_swap_refused(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch, PatchValidationError

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_abs(), P)
        p, T = read_patch(P)
        d = p.to_dict()
        _swap_x(d["patcher"], "obj-2", "obj-3")

        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(d, P, T)

        assert any("top" in c for c in excinfo.value.port_changes)
        assert P.read_text() == T

    def test_mid_insert_refused(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch, PatchValidationError

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_sub(), P)
        p, T = read_patch(P)
        d = p.to_dict()
        _add_inner_inlet(d, 90.0)

        with pytest.raises(PatchValidationError) as excinfo:
            save_patch_roundtrip(d, P, T)

        assert any("inlet obj-2 rank 1 -> 2" in c for c in excinfo.value.port_changes)

    def test_append_rightmost_saves(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_sub(), P)
        p, T = read_patch(P)
        d = p.to_dict()
        _add_inner_inlet(d, 210.0)

        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            result = save_patch_roundtrip(d, P, T)

        assert _gate_warnings(record) == []
        assert result == _head(root)

    def test_port_order_changed_before_this_save_is_exempt(self, tmp_path):
        from src.maxpat.hooks import save_patch_roundtrip, read_patch

        root = _repo(tmp_path)
        P = _patch_path(root)
        save_patch_roundtrip(_sub(), P)
        T0 = P.read_text()
        _disk_edit(P, T0, lambda d: _swap_x(_ctl_box(d)["patcher"], "obj-1", "obj-2"))
        p, T = read_patch(P)
        p.add_box("print", ["other"])

        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            result = save_patch_roundtrip(p.to_dict(), P, T)

        assert _gate_warnings(record) == []
        assert result == _head(root)


class TestWriteGendspGate:
    CODE = "out1 = in1 * 0.5;"

    def _x(self, root: Path) -> Path:
        return root / "patches" / "demo" / "generated" / "x.gendsp"

    def test_clean_write_commits_without_warning(self, tmp_path):
        from src.maxpat.hooks import write_gendsp

        root = _repo(tmp_path)
        x = self._x(root)

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = write_gendsp(self.CODE, x, num_inputs=1, num_outputs=1)

        assert result.commit_hash == _head(root)

    def _inject_blocker(self, monkeypatch):
        import src.maxpat.critics as critics
        from src.maxpat.critics import CriticResult

        monkeypatch.setattr(
            critics, "review_patch",
            lambda *a, **k: [CriticResult("blocker", "injected (obj-1)", "s")],
        )

    def test_blocker_on_new_gendsp_refused(self, tmp_path, monkeypatch):
        from src.maxpat.hooks import write_gendsp, PatchValidationError

        root = _repo(tmp_path)
        x = self._x(root)
        self._inject_blocker(monkeypatch)

        with pytest.raises(PatchValidationError) as excinfo:
            write_gendsp(self.CODE, x, num_inputs=1, num_outputs=1)

        assert "injected" in excinfo.value.findings[0].finding
        assert not x.exists()
        assert not _has_head(root)

    def test_blocker_on_new_gendsp_force_writes(self, tmp_path, monkeypatch):
        from src.maxpat.hooks import write_gendsp, SaveGateWarning

        root = _repo(tmp_path)
        x = self._x(root)
        self._inject_blocker(monkeypatch)

        with pytest.warns(SaveGateWarning, match="force=True"):
            result = write_gendsp(self.CODE, x, num_inputs=1, num_outputs=1, force=True)

        assert x.exists()
        assert result.commit_hash == _head(root)

    def test_rewrite_over_committed_gendsp_saves(self, tmp_path):
        from src.maxpat.hooks import write_gendsp

        root = _repo(tmp_path)
        x = self._x(root)
        first = write_gendsp(self.CODE, x, num_inputs=1, num_outputs=1)
        assert first.commit_hash == _head(root)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # "no changes to commit" is fine
            result = write_gendsp(self.CODE, x, num_inputs=1, num_outputs=1)

        assert json.loads(x.read_text()) == dict(result)


def _committed_patch_files() -> list[Path]:
    files = sorted(REPO_ROOT.glob("patches/*/generated/*.maxpat"))
    files += sorted(REPO_ROOT.glob("patches/*/generated/*.gendsp"))
    return files


_COMMITTED = _committed_patch_files()


@pytest.mark.parametrize(
    "path", _COMMITTED, ids=[p.relative_to(REPO_ROOT).as_posix() for p in _COMMITTED]
)
class TestRoundTripNoFalseBlocks:
    def test_round_trip_reports_nothing(self, path):
        from src.maxpat.hooks import _gate_db, _gate_report

        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d.get("patcher"), dict):
            pytest.skip("no patcher dict")
        new = Patcher.from_dict(copy.deepcopy(d), db=_gate_db()).to_dict()

        report = _gate_report(new, d, [d])

        assert report.new_blockers == []
        assert report.removed_cords == []
        assert report.port_changes == []
