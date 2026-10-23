"""WP7a (quick 261022-ud6): M4L handoffs.

* WP3 -> m4l_device: exporting a live.thisdevice-only helper abstraction
  raises a clear "helper abstraction; pass kind=" error.
* WP4 -> WP3: review_m4l calls the duplicate-device-I/O hook
  (rule ``duplicate_device_io``) at the top scope.
* Q40 IN-03: ``param_range`` ignores ``parameter_initial`` unless
  ``parameter_initial_enable`` is set (Live ignores it too).
* WP4: ``Patcher.add_m4l_device`` docstring documents reuse / refusal /
  info text / overlap shift.
"""
import pytest

from src.maxpat.critics.m4l_critic import detect_m4l_device_type, review_m4l
from src.maxpat.m4l_device import export_amxd
from src.maxpat.patcher import Patcher
from tests.test_m4l_device import _box, _line, _patch, _pdial, _plugout


def _rules(results, rule):
    return [r for r in results if r.rule == rule]


def _helper():
    boxes = [
        _box("obj-1", "inlet", 0, 1, maxclass="inlet", outlettype=[""]),
        _box("obj-2", "live.thisdevice", 1, 3, outlettype=["bang", "int", "int"]),
        _box("obj-4", "outlet", 1, 0, maxclass="outlet", outlettype=[]),
    ]
    return _patch(boxes, [_line("obj-2", 0, "obj-4", 0)])


class TestExportHelperAbstraction:
    def test_clear_error(self, tmp_path):
        assert detect_m4l_device_type(_helper()) == "m4l_abstraction"
        with pytest.raises(ValueError, match=r"helper abstraction.*kind="):
            export_amxd(_helper(), tmp_path / "helper.amxd")
        assert not (tmp_path / "helper.amxd").exists()

    def test_explicit_kind_still_exports(self, tmp_path):
        out = export_amxd(_helper(), tmp_path / "helper.amxd", kind="audio_effect")
        assert out.exists()


class TestDuplicateDeviceIO:
    def test_two_plugouts_warn(self):
        d = _patch([_plugout("obj-90"), _plugout("obj-91")])
        hits = _rules(review_m4l(d, device_type="instrument"), "duplicate_device_io")
        assert len(hits) == 1
        assert hits[0].severity == "warning"
        assert set(hits[0].box_ids) == {"obj-90", "obj-91"}

    def test_single_plugout_quiet(self):
        d = _patch([_plugout("obj-90")])
        assert not _rules(review_m4l(d, device_type="instrument"), "duplicate_device_io")

    def test_builder_output_quiet(self):
        p = Patcher()
        p.add_m4l_device("audio_effect", [{"name": "Mix", "min": 0.0, "max": 1.0, "default": 0.5}])
        d = p.to_dict()
        assert not _rules(review_m4l(d, device_type="audio_effect"), "duplicate_device_io")


class TestParamInitialEnable:
    def _run(self, **v):
        d = _patch([_plugout(), _pdial("obj-3", **v)])
        return _rules(review_m4l(d, device_type="instrument"), "param_range")

    def test_disabled_initial_ignored(self):
        assert not self._run(parameter_mmin=0, parameter_mmax=100, parameter_initial=[500])
        assert not self._run(parameter_mmin=0, parameter_mmax=100,
                             parameter_initial=[500], parameter_initial_enable=0)

    def test_enabled_initial_checked(self):
        hits = self._run(parameter_mmin=0, parameter_mmax=100,
                         parameter_initial=[500], parameter_initial_enable=1)
        assert len(hits) == 1

    def test_inverted_range_still_flagged_without_enable(self):
        assert len(self._run(parameter_mmin=10, parameter_mmax=10)) == 1


def test_add_m4l_device_docstring_documents_reuse_and_refusal():
    doc = Patcher.add_m4l_device.__doc__ or ""
    for needle in ("reuse", "ValueError", "info", "shift"):
        assert needle in doc, needle
