import math

import pytest
from hypothesis import given, settings, strategies as st

from evals_test_helpers import (
    INF, Bare, LateCloseRaiser, BoomCloseRaiser, Boom, Booms, Caller, CardBot, CloseError,
    CloseRaiser, Factory, FactoryError, Folder, Oddball, RunRaiser,
    SeedRaiser, Sleeper, SlowRaiser, SometimesFaults, deck_for, factories,
    oracle,
)
from evals.match import MatchResult, play_match

approx = pytest.approx


def models_of(facs):
    return [m for f in facs.values() for m in f.models]


def assert_matches_oracle(result, expected):
    assert result.bb_per_100 == approx(expected["bb_per_100"], abs=1e-9)
    assert result.round_bb_per_100 == [
        approx(row, abs=1e-9) for row in expected["round_bb_per_100"]]
    for got, want in zip(result.ci95, expected["ci95"]):
        assert got == INF if want == INF else got == approx(want, abs=1e-7)
    assert result.faults == expected["faults"]
    assert result.first_faults == expected["first_faults"]
    assert result.hands == expected["hands"]


# -- validation --------------------------------------------------------------

def _invalid():
    return {
        "no models": (dict(), {}),
        "one model": (dict(a=Caller), {}),
        "ten models": ({f"m{i}": Caller for i in range(10)}, {}),
        "deals 0": (dict(a=Caller, b=Caller), dict(deals=0)),
        "deals -1": (dict(a=Caller, b=Caller), dict(deals=-1)),
        "rounds 0": (dict(a=Caller, b=Caller), dict(rounds=0)),
        "sb > bb": (dict(a=Caller, b=Caller),
                    dict(small_blind=30, big_blind=20)),
        "sb 0": (dict(a=Caller, b=Caller), dict(small_blind=0)),
        "sb negative": (dict(a=Caller, b=Caller), dict(small_blind=-5)),
        "bb 0": (dict(a=Caller, b=Caller), dict(small_blind=0, big_blind=0)),
        "stack negative": (dict(a=Caller, b=Caller), dict(stack=-1)),
        "stack below bb": (dict(a=Caller, b=Caller), dict(stack=19)),
        "empty name": ({"": Caller, "b": Caller}, {}),
        "int name": ({1: Caller, "b": Caller}, {}),
        "None name": ({None: Caller, "b": Caller}, {}),
    }


@pytest.mark.parametrize("case", list(_invalid()))
def test_M01_M02_M03_invalid_input(case):
    """M-01..M-03: too few/many models, deals or rounds < 1, bad blinds, negative stack, stack < big blind, or a name that is not a non-empty str raise ValueError before any factory is called."""
    spec, kw = _invalid()[case]
    facs = {name: Factory(cls, name) for name, cls in spec.items()}
    kw = dict(kw)
    kw.setdefault("deals", 1)
    with pytest.raises(ValueError):
        play_match(facs, **kw)
    assert all(f.calls == 0 for f in facs.values())


@pytest.mark.parametrize("n", [2, 9])
def test_M01_table_sizes_accepted(n):
    """M-01: 2 and 9 models are accepted."""
    facs = factories({f"m{i}": Caller for i in range(n)})
    result = play_match(facs, deals=1)
    assert result.hands == n


def test_M03_stack_equal_to_big_blind_accepted():
    """M-03: a stack equal to the big blind is accepted."""
    result = play_match(factories(dict(a=Caller, b=Caller)), deals=1,
                        stack=20)
    assert result.hands == 2


# -- schedule ----------------------------------------------------------------

def test_M04_fresh_models_per_rotation():
    """M-04: each factory is called rounds*n times; each model plays exactly `deals` hands, always in the same seat."""
    facs = factories(dict(a=Caller, b=Caller, c=Caller))
    play_match(facs, deals=2, rounds=2)
    for f in facs.values():
        assert f.calls == 6
        assert len({id(m) for m in f.models}) == 6
        for m in f.models:
            assert len(m.seeds) == 2
            assert len({pid for _, pid in m.seeds}) == 1


def test_M05_rotation_seating():
    """M-05: in rotation k, seat i is played by names[(i + k) % n], rotations in order within each round."""
    names = ["c", "a", "b"]
    facs = factories({nm: Caller for nm in names})
    play_match(facs, deals=1, rounds=2)
    for nm, f in facs.items():
        for t, m in enumerate(f.models):
            k = t % 3
            pid = m.seeds[0][1]
            assert names[(pid + k) % 3] == nm


def test_M06_decks_from_string_seed():
    """M-06: round r, deal d deals full_deck() shuffled by random.Random(f"{seed}:{r}:{d}"); seat i gets deck[2i:2i+2] in every rotation."""
    facs = factories(dict(a=Caller, b=Caller, c=Caller))
    play_match(facs, deals=2, rounds=2, seed=7)
    for f in facs.values():
        for t, m in enumerate(f.models):
            r = t // 3
            for d, (hand, pid) in enumerate(m.seeds):
                assert hand == deck_for(7, r, d)[2 * pid:2 * pid + 2]


def test_M07_hand_setup():
    """M-07: every hand uses button 0, the given blinds, [stack]*n before blinds, and teams = seated names in seat order."""
    names = ["x", "y", "z"]
    facs = factories({nm: Caller for nm in names})
    play_match(facs, deals=2, stack=300, small_blind=5, big_blind=10)
    for nm, f in facs.items():
        for k, m in enumerate(f.models):
            seated = tuple(names[(i + k) % 3] for i in range(3))
            pid = m.seeds[0][1]
            assert m.runs
            for run in m.runs:
                assert run["teams"] == seated
                assert run["button"] == 0
                assert (run["small_blind"], run["big_blind"]) == (5, 10)
                assert sum(run["stacks"]) + run["pot"] == 900
            if pid == 0:  # UTG acts first preflop, nothing before it
                firsts = [run for run in m.runs if run["actions"] == []]
                assert len(firsts) == 2
                assert all(run["stacks"] == (300, 295, 290)
                           for run in firsts)


def test_M08_close_between_rotations():
    """M-08: every model with close() is closed exactly once, after its rotation's last hand and before the next rotation's factories are called; models without close work."""
    log = []
    facs = {"a": Factory(Caller, "a", log), "b": Factory(Bare, "b", log),
            "c": Factory(SeedRaiser, "c", log)}
    play_match(facs, deals=2, rounds=2)
    for nm in ("a", "c"):
        for m in facs[nm].models:
            assert m.closed == 1
    # rotation g = t-th factory call of each name
    for g in range(6):
        closes = [i for i, e in enumerate(log)
                  if e[0] == "close" and e[2] == g]
        seeds = [i for i, e in enumerate(log) if e[0] == "seed" and e[2] == g]
        next_factories = [i for i, e in enumerate(log)
                          if e[0] == "factory" and e[2] == g + 1]
        assert len(closes) == 2
        assert min(closes) > max(seeds)
        if next_factories:
            assert max(closes) < min(next_factories)


def test_M09_protocol_only_models():
    """M-09: models exposing only seed and run (__slots__, no close) play normally."""
    facs = factories(dict(a=Bare, b=Bare, c=Bare))
    result = play_match(facs, deals=2)
    assert result.hands == 18 // 3
    assert result.faults == [0, 0, 0]
    assert sum(result.bb_per_100) == approx(0, abs=1e-9)


def test_M10_result_shape():
    """M-10: names keep dict order; hands = rounds*n*deals; deals/rounds echoed; per-model lists have n entries; round_bb_per_100 is rounds x n."""
    facs = factories({"zeta": Caller, "alpha": Folder, "mid": Caller})
    result = play_match(facs, deals=2, rounds=3)
    assert isinstance(result, MatchResult)
    assert result.names == ["zeta", "alpha", "mid"]
    assert (result.hands, result.deals, result.rounds) == (18, 2, 3)
    for field in ("bb_per_100", "ci95", "faults", "first_faults",
                  "max_move_seconds"):
        assert len(getattr(result, field)) == 3
    assert len(result.round_bb_per_100) == 3
    assert all(len(row) == 3 for row in result.round_bb_per_100)


# -- scoring -----------------------------------------------------------------

@pytest.mark.parametrize("kw", [{}, dict(stack=200, small_blind=5,
                                         big_blind=10)])
def test_M11_folder_vs_caller_heads_up(kw):
    """M-11: heads-up, always-fold vs always-call scores -75 / +75 bb/100 with ci95 0 (blind size does not matter)."""
    result = play_match(factories(dict(folder=Folder, caller=Caller)),
                        deals=2, **kw)
    assert result.bb_per_100 == approx([-75, 75])
    assert result.ci95 == approx([0, 0], abs=1e-9)
    result = play_match(factories(dict(caller=Caller, folder=Folder)),
                        deals=2, **kw)
    assert result.bb_per_100 == approx([75, -75])


def test_M12_two_folders_one_caller():
    """M-12: three-handed, two always-fold models and one always-call model score -50 / -50 / +100 in every round."""
    result = play_match(factories(dict(f1=Folder, f2=Folder, c=Caller)),
                        deals=1, rounds=2)
    assert result.bb_per_100 == approx([-50, -50, 100])
    assert result.round_bb_per_100 == [approx([-50, -50, 100])] * 2


def test_M13_single_sample_ci_inf():
    """M-13: with rounds*deals == 1, ci95 is inf for every model and bb_per_100 is finite."""
    result = play_match(factories(dict(a=CardBot, b=CardBot, c=Caller)),
                        deals=1)
    assert result.ci95 == [INF, INF, INF]
    assert all(math.isfinite(x) for x in result.bb_per_100)


def test_M14_M17_matches_direct_play_oracle():
    """M-14/M-17: bb_per_100, round_bb_per_100, ci95, faults and first_faults equal the values from playing the schedule with play_hand directly."""
    spec = dict(p=CardBot, q=SometimesFaults, r=CardBot, s=Caller)
    expected = oracle(spec, deals=3, rounds=2, seed=3)
    assert expected["faults"][1] > 0  # test precondition
    result = play_match(factories(spec), deals=3, rounds=2, seed=3)
    assert_matches_oracle(result, expected)
    assert result.first_faults[0] is None
    assert isinstance(result.first_faults[1], str)


# -- faults and timing -------------------------------------------------------

def test_M15_seed_faults_every_hand_and_is_closed():
    """M-15: a model whose seed raises faults in every hand, is never timed (0.0) and is still closed."""
    facs = factories(dict(bad=SeedRaiser, good=Caller))
    result = play_match(facs, deals=2, rounds=2)
    assert result.faults == [result.hands, 0]
    assert result.first_faults[0] and result.first_faults[1] is None
    assert result.max_move_seconds[0] == 0.0
    assert all(m.closed == 1 for m in facs["bad"].models)


def test_M16_run_raiser_faults_every_hand():
    """M-16: a model whose run always raises, heads-up vs a caller, faults in every hand."""
    result = play_match(factories(dict(bad=RunRaiser, good=Caller)),
                        deals=3)
    assert result.faults == [6, 0]
    assert isinstance(result.first_faults[0], str) and result.first_faults[0]


def test_M18_faults_never_stop_the_match():
    """M-18: faulting models never stop the match: every hand is played and every list is complete."""
    result = play_match(factories(dict(a=RunRaiser, b=SeedRaiser, c=Caller,
                                       d=Oddball)), deals=2, rounds=2)
    assert result.hands == 16
    assert result.faults[0] > 0 and result.faults[1] == 16
    assert result.faults[2] == 0 and result.faults[3] > 0
    assert sum(result.bb_per_100) == approx(0, abs=1e-9)


def test_M19_timing():
    """M-19: max_move_seconds is the slowest run (a 30 ms run, even one that raises, shows >= 0.03 s); all values >= 0."""
    result = play_match(factories(dict(slow=Sleeper, fast=Caller,
                                       raiser=SlowRaiser)), deals=1)
    slow, fast, raiser = result.max_move_seconds
    assert 0.03 <= slow < 2
    assert 0.03 <= raiser < 2
    assert 0.0 <= fast < slow


def test_M20_proxy_is_transparent():
    """M-20: wrapping models for timing changes nothing the engine sees: odd returns (None, PlayerAction subclasses) and raising runs/seeds score and fault exactly as in direct play."""
    spec = dict(o=Oddball, r=RunRaiser, s=SeedRaiser, c=CardBot)
    expected = oracle(spec, deals=2, rounds=1, seed=5)
    result = play_match(factories(spec), deals=2, rounds=1, seed=5)
    assert_matches_oracle(result, expected)


def test_M21_factory_error_propagates_after_closing():
    """M-21: a factory that raises propagates its exception, and every model already built in that rotation is closed exactly once."""
    log = []
    facs = {"a": Factory(Caller, "a", log),
            "b": Factory(Caller, "b", log, fail_on=1),
            "c": Factory(LateCloseRaiser, "c", log)}
    with pytest.raises(FactoryError):
        play_match(facs, deals=1)
    assert all(m.closed == 1 for m in models_of(facs))
    assert facs["b"].calls == 2


def test_M22_close_error_propagates_after_closing_rest():
    """M-22: a close that raises propagates after every other model of that rotation has had close called."""
    facs = factories(dict(a=CloseRaiser, b=Caller, c=Caller))
    with pytest.raises(CloseError):
        play_match(facs, deals=1)
    assert all(m.closed == 1 for m in models_of(facs))
    assert all(f.calls == 1 for f in facs.values())


def test_M22b_every_close_attempted_when_several_raise():
    """M-22: when several closes raise, every close is still attempted and one of those errors propagates."""
    facs = factories(dict(a=CloseRaiser, b=CloseRaiser, c=Caller))
    with pytest.raises(CloseError):
        play_match(facs, deals=1)
    assert all(m.closed == 1 for m in models_of(facs))


def test_M23_base_exception_propagates_and_wins():
    """M-23: a BaseException escaping play_hand propagates from play_match after every model of the rotation is closed, and wins over close errors."""
    facs = factories(dict(a=Booms, b=CloseRaiser, c=Caller))
    with pytest.raises(Boom):
        play_match(facs, deals=1)
    assert all(m.closed == 1 for m in models_of(facs))

    facs = factories(dict(a=BoomCloseRaiser, b=Caller))
    with pytest.raises(Boom):
        play_match(facs, deals=1)
    assert all(m.closed == 1 for m in models_of(facs))


def test_M23b_factory_error_wins_over_close_error():
    """M-23: a factory error propagating wins over a close error raised while closing that rotation."""
    facs = {"a": Factory(LateCloseRaiser, "a"),
            "b": Factory(Caller, "b", fail_on=1)}
    with pytest.raises(FactoryError):
        play_match(facs, deals=1)
    assert all(m.closed == 1 for m in models_of(facs))


# -- properties --------------------------------------------------------------

KINDS = [CardBot, SometimesFaults, Folder, Caller, RunRaiser]


@st.composite
def match_args(draw):
    n = draw(st.integers(2, 4))
    spec = {f"m{i}": draw(st.sampled_from(KINDS)) for i in range(n)}
    return dict(spec=spec, deals=draw(st.integers(1, 2)),
                rounds=draw(st.integers(1, 2)),
                seed=draw(st.integers(0, 10**6)))


def _play(args):
    facs = factories(args["spec"])
    result = play_match(facs, deals=args["deals"], rounds=args["rounds"],
                        seed=args["seed"])
    return facs, result


@settings(max_examples=15, deadline=None)
@given(match_args())
def test_MP1_bb_per_100_sums_to_zero(args):
    """MP-1: bb_per_100 sums to 0 across models, and so does every round's row."""
    _, result = _play(args)
    assert sum(result.bb_per_100) == approx(0, abs=1e-9)
    for row in result.round_bb_per_100:
        assert sum(row) == approx(0, abs=1e-9)


@settings(max_examples=15, deadline=None)
@given(match_args())
def test_MP2_deterministic(args):
    """MP-2: the same arguments and deterministic models give an identical MatchResult except max_move_seconds."""
    _, r1 = _play(args)
    _, r2 = _play(args)
    r1.max_move_seconds = r2.max_move_seconds = None
    assert r1 == r2


@settings(max_examples=15, deadline=None)
@given(match_args())
def test_MP3_every_model_every_seat_per_deck(args):
    """MP-3: for every round and deal, each model plays each seat exactly once and sees exactly that deck's n seat hands."""
    facs, _ = _play(args)
    n = len(facs)
    for f in facs.values():
        for r in range(args["rounds"]):
            rotation_models = f.models[r * n:(r + 1) * n]
            for d in range(args["deals"]):
                deck = deck_for(args["seed"], r, d)
                seen = [m.seeds[d] for m in rotation_models]
                assert sorted(pid for _, pid in seen) == list(range(n))
                assert sorted((tuple(map(str, h)) for h, _ in seen)) == sorted(
                    tuple(map(str, deck[2 * i:2 * i + 2])) for i in range(n))


@settings(max_examples=15, deadline=None)
@given(match_args())
def test_MP4_counts(args):
    """MP-4: hands = rounds*n*deals; each factory is called rounds*n times; 0 <= faults <= hands; first_faults is None exactly when faults is 0."""
    facs, result = _play(args)
    n = len(facs)
    assert result.hands == args["rounds"] * n * args["deals"]
    assert all(f.calls == args["rounds"] * n for f in facs.values())
    for count, first in zip(result.faults, result.first_faults):
        assert 0 <= count <= result.hands
        assert (first is None) == (count == 0)
