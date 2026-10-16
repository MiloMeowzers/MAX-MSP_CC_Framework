"""ODB-03: Validate version tagging on all objects.

Q30 (PD-3): ``min_version`` may be a number (the DB's historical form, e.g.
``8``, ``8.1``) or a version string (``"9.2"``, ``"9.10"``), which the sync
tool now writes. Both are compared through :func:`_version_tuple`.
"""

import re

import pytest  # noqa: F401 (kept from the original module)


def _version_tuple(value):
    """A version as its integer parts: 8.1 -> (8, 1), 9 -> (9,), "9.10" -> (9, 10).

    None for anything that is not a number or a ``major[.minor]`` string
    (booleans included).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if not re.fullmatch(r"\d+(\.\d+)?", text):
        return None
    return tuple(int(part) for part in text.split("."))


def _is_max9_major(value) -> bool:
    """Major 9 with no minor or minor 0: 9, 9.0, "9", "9.0"."""
    parts = _version_tuple(value)
    return parts is not None and parts[0] == 9 and (len(parts) == 1 or parts[1] == 0)


class TestVersionTags:
    """Every object must have a min_version field with correct values."""

    def test_every_object_has_min_version(self, all_objects):
        """Every object must have a min_version field (a number or a version string)."""
        for obj in all_objects:
            assert "min_version" in obj, (
                f"Missing min_version: {obj.get('name', '?')}"
            )
            assert _version_tuple(obj["min_version"]) is not None, (
                f"min_version is not a version for {obj.get('name', '?')}: "
                f"{obj['min_version']!r}"
            )

    def test_array_objects_are_max9(self, all_objects):
        """Objects starting with 'array.' must have min_version 9."""
        array_objs = [o for o in all_objects if o["name"].startswith("array.")]
        assert len(array_objs) > 0, "No array.* objects found"
        for obj in array_objs:
            assert _is_max9_major(obj["min_version"]), (
                f"{obj['name']} should be min_version 9, got {obj['min_version']}"
            )

    def test_string_objects_are_max9(self, all_objects):
        """Objects starting with 'string.' must have min_version 9."""
        string_objs = [o for o in all_objects if o["name"].startswith("string.")]
        assert len(string_objs) > 0, "No string.* objects found"
        for obj in string_objs:
            assert _is_max9_major(obj["min_version"]), (
                f"{obj['name']} should be min_version 9, got {obj['min_version']}"
            )

    def test_abl_objects_are_max9(self, all_objects):
        """Objects starting with 'abl.' must have a Max 9 min_version (major 9).

        Point releases are legal: the abl.* objects added in Max 9.2
        (quick-261001-hwb) carry min_version 9.2.
        """
        abl_objs = [o for o in all_objects if o["name"].startswith("abl.")]
        assert len(abl_objs) > 0, "No abl.* objects found"
        for obj in abl_objs:
            parts = _version_tuple(obj["min_version"])
            assert parts is not None and parts[0] == 9, (
                f"{obj['name']} should be a Max 9 min_version (major 9), "
                f"got {obj['min_version']}"
            )

    def test_mc_objects_have_version(self, all_objects):
        """MC objects (mc.*) should have min_version set."""
        mc_objs = [o for o in all_objects if o["name"].startswith("mc.")]
        assert len(mc_objs) > 0, "No mc.* objects found"
        for obj in mc_objs:
            assert _version_tuple(obj.get("min_version")) is not None, (
                f"mc object {obj['name']} missing min_version"
            )
