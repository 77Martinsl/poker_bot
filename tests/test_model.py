"""
Checks that your model (model.Model) is a valid submission: it pickles,
and it plays legally, without faults, against every baseline.

    .venv/bin/python -m pytest tests/test_model.py -q

A failure names the fault (an exception in seed or run, or an illegal
move). This checks validity, not strength: use python -m evals for that.
"""

import pickle

import pytest

from evals.baselines import BASELINES
from evals.match import play_match
from model import Model

TIME_LIMIT = 10.0  # seconds per move, as the arena enforces it


def _you():
    """A factory like the arena's: pickled once, unpickled per use."""
    blob = pickle.dumps(Model())
    return lambda: pickle.loads(blob)


def _check(factories, deals):
    result = play_match(factories, deals)
    assert result.faults[0] == 0, result.first_faults[0]
    assert result.max_move_seconds[0] < TIME_LIMIT


def test_model_pickles():
    model = pickle.loads(pickle.dumps(Model()))
    assert hasattr(model, "seed") and hasattr(model, "run")


@pytest.mark.parametrize("opponent", list(BASELINES))
def test_plays_legally_heads_up(opponent):
    _check({"you": _you(), opponent: BASELINES[opponent]}, deals=10)


def test_plays_legally_at_a_full_table():
    # EquityBot is left out: it is slow with many players.
    others = {n: c for n, c in BASELINES.items() if n != "equity"}
    _check({"you": _you()} | others, deals=4)
