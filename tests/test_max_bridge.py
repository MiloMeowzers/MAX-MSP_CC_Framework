"""quick-261016-uy1 (Q34): hermetic tests for tools/max_bridge.py.

The bridge spike drives a running MAX 9.2 over UDP/OSC. Nothing here needs
MAX: the OSC codec, the temp-copy instrumentation, the wav analysis, the
screenshot helpers (subprocess faked) and the full check sequence run
against an in-process FakeBridge on 127.0.0.1. House convention
(tests/test_sync_max_bundle.py): import the tool as a module and call its
functions directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.maxpat.db_lookup import ObjectDatabase
from src.maxpat.patcher import Patcher
from src.maxpat.validation import validate_patch


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ---------------------------------------------------------------------------
# Task 1: DB fix
# ---------------------------------------------------------------------------

class TestSfrecordOverride:

    def test_inlet_1_is_signal(self, db):
        inlets = db.lookup("sfrecord~")["inlets"]
        assert inlets[1]["type"] == "signal"
        assert inlets[1]["signal"] is True

    def test_receive_to_sfrecord_inlet_1_validates(self, db):
        p = Patcher(db=db)
        r = p.add_box("receive~", ["x"], x=20, y=20)
        rec = p.add_box("sfrecord~", ["2"], x=20, y=80)
        assert rec.numinlets == 2
        p.add_connection(r, 0, rec, 1)
        msgs = [r.message for r in validate_patch(p.to_dict(), db=db)]
        assert not [m for m in msgs if "control-only inlet" in m]

    def test_audit_source_kept_and_cites_q34(self):
        ov = json.loads(Path(".claude/max-objects/overrides.json").read_text())
        src = ov["objects"]["sfrecord~"]["_audit"]["source"]
        assert src.startswith("Q11 / C9 (261013-e43)")
        assert "Q34 (261016-uy1)" in src
        assert "Each inlet of sfrecord~ accepts a signal" in src
