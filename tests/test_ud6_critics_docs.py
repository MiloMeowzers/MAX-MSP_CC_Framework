"""CR-04 / WR-03 (quick 261022-ud6 WP3): the build critic loop and the save
gate agree on ``is_new``, and the severity contract documents it."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (ROOT / rel).read_text()


def test_max_build_loop_reviews_new_files_as_new():
    text = _read(".claude/commands/max-build.md")
    assert "review_patch(patch_dict, code_context, is_new=True)" in text


def test_max_critic_skill_and_protocol_pass_is_new():
    assert "is_new=" in _read(".claude/skills/max-critic/SKILL.md")
    protocol = _read(".claude/skills/max-critic/references/critic-protocol.md")
    assert "ext_archetype=ext_archetype, is_new=is_new)" in protocol


def test_severity_contract_documents_is_new_and_nested_scopes():
    text = _read(".claude/skills/references/severity-contract.md")
    assert 'ext_archetype="message", *, db=None, is_new=False)' in text
    assert "**`is_new`**" in text
    assert "Blocking findings come from every scope" in text
    assert "top-level patcher (plus Layer 5" not in text


def test_build_loop_sees_the_gate_blocker():
    """The shape CR-04 names: a dial cabled to gen~ with no load init is a
    blocker for a new file and a warning for an edit."""
    from src.maxpat.critics import review_patch
    from tests.test_critics_recursive import _box, _line, _patch

    boxes = [
        _box("obj-1", None, 1, 1, maxclass="dial", outlettype=["float"]),
        _box("obj-2", "gen~", 1, 1, outlettype=["signal"]),
    ]
    d = _patch(boxes, [_line("obj-1", 0, "obj-2", 0)])
    new = [r.severity for r in review_patch(d, is_new=True) if r.rule == "uninitialized_state"]
    edit = [r.severity for r in review_patch(d) if r.rule == "uninitialized_state"]
    assert new == ["blocker"] and edit == ["warning"]
