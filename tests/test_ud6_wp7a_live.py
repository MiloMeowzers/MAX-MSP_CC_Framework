"""WP7a (quick 261022-ud6): WP6 handoff. A malformed patch inside a
``/max-verify --live`` batch is reported as refused with the bridge's own
``cannot read`` text -- never as "live check crashed" -- and the batch goes on.
"""
from __future__ import annotations

import pytest

import tools.max_verify_live as live
from tests.test_max_bridge import FakeBridge, _tone_patch
from tests.test_max_verify_live import (  # noqa: F401 -- autouse fixtures
    _no_real_max,
    _run,
    _run_dirs,
    db,
)


@pytest.mark.parametrize("payload", [
    b'{"patcher": ',
    b'\xff\xfe not utf-8',
    b'{"patcher": 3}',
    b'[]',
])
def test_malformed_patch_in_batch_is_refused(tmp_path, db, capsys, payload):  # noqa: F811
    bad = tmp_path / "a-bad.maxpat"
    bad.write_bytes(payload)
    good = _tone_patch(tmp_path / "b-good.maxpat", db)
    with FakeBridge() as fb:
        rc, res = _run(fb.port, bad, good, capsys=capsys)
    first, second = res["patches"]
    assert first["status"] == "refused", first
    (finding,) = first["findings"]
    assert "cannot read" in finding["finding"]
    assert "crashed" not in finding["finding"]
    assert second["status"] == "checked"
    assert fb.addresses.count("/open") == 1
    assert rc in (0, 1)


def test_scan_patch_raises_value_error_on_non_patch(tmp_path):
    bad = tmp_path / "x.maxpat"
    bad.write_text('{"patcher": 3}')
    with pytest.raises(ValueError):
        live.scan_patch(bad)
