"""WP7a (quick 261022-ud6): DB handoffs from WP3.

Evidence (Max 9.2.0 bundle + installed bach package):
* bach.slice -- refpage outletlist has 2 outlets (left / right part of the
  split llll); the help box ``bach.slice 3 @out t`` is saved 1 in / 2 out.
* zplane~ -- refpage digests for outlets 1-3 are "List of ... Pairs" /
  "List of ... Gains"; both MAX-saved help boxes have
  ``outlettype: ["list", "list", "list", "list"]``.
* mc.range~ -- outlet 1 is refpage type ``list`` and every help box saves
  it as ``list``; its signal_role was ``float`` (one atom), a disagreement.
"""
import pytest

from src.maxpat.db_lookup import ObjectDatabase


@pytest.fixture(scope="module")
def db():
    return ObjectDatabase()


def test_bach_slice_has_two_outlets(db):
    assert db.compute_io_counts("bach.slice", ["3"]) == (1, 2)
    outs = db.lookup("bach.slice")["outlets"]
    assert [o["id"] for o in outs] == [0, 1]
    assert not any(o.get("signal") for o in outs)


@pytest.mark.parametrize("outlet", [0, 1, 2, 3])
def test_zplane_outlets_are_lists(db, outlet):
    o = db.lookup("zplane~")["outlets"][outlet]
    assert o["type"] == "list"
    assert o["signal_role"] == "list"


def test_mc_range_list_outlet_role(db):
    o = db.lookup("mc.range~")["outlets"][1]
    assert o["type"] == "list"
    assert o["signal_role"] == "list"
