"""WP7a (quick 261022-ud6): WP4 -> WP5 handoff. The interpreter knows every
GenExpr built-in constant the validator knows (genexpr_parse.BUILTIN_CONSTANTS:
the 13 lower-case names, phi and every upper-case alias), with the upper-case
alias equal to its lower-case value.
"""
import pytest

from src.maxpat.dsp_sim.genexpr_interp import GEN_CONSTANTS
from src.maxpat.genexpr_parse import BUILTIN_CONSTANTS
from tests.dsp_sim.test_genexpr_interp import run


def test_interpreter_covers_every_builtin_constant():
    assert set(BUILTIN_CONSTANTS) <= set(GEN_CONSTANTS)


@pytest.mark.parametrize("name", sorted(n for n in BUILTIN_CONSTANTS if n.isupper()))
def test_upper_alias_equals_lower(name):
    assert GEN_CONSTANTS[name] == GEN_CONSTANTS[name.lower()]
    (o,) = run(f"out1 = {name};", n=1)
    assert o[0] == GEN_CONSTANTS[name.lower()]
