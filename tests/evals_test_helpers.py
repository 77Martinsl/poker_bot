"""Models, factories and an independent oracle for the evals tests."""

import math
import random
import statistics
import time

from deck import full_deck
from engine import play_hand
from player_action import PlayerAction as A

INF = math.inf

T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
       7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
       13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101,
       19: 2.093, 20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064,
       25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045}


def t95_ref(df):
    if df < 1:
        return INF
    return T95.get(df, 1.96)


def mse_ref(values):
    """Reference (mean, se)."""
    if not values:
        return None, INF
    if len(values) == 1:
        return float(values[0]), INF
    return (statistics.fmean(values),
            statistics.stdev(values) / math.sqrt(len(values)))


def deck_for(seed, r, d):
    deck = full_deck()
    random.Random(f"{seed}:{r}:{d}").shuffle(deck)
    return deck


# -- models ------------------------------------------------------------------

class Boom(BaseException):
    pass


class FactoryError(Exception):
    pass


class CloseError(Exception):
    pass


class Bot:
    """Calls (checks) everything. Records seeds, runs and closes."""

    def __init__(self, name, log=None, idx=0):
        self.name = name
        self.log = log if log is not None else []
        self.idx = idx
        self.seeds = []
        self.runs = []
        self.closed = 0
        self.player_id = None
        self.hand = None

    def seed(self, hand, player_id):
        self.seeds.append((list(hand), player_id))
        self.player_id = player_id
        self.hand = list(hand)
        self.log.append(("seed", self.name, self.idx))

    def run(self, actions, gs):
        self.runs.append({
            "actions": list(actions), "teams": tuple(gs.teams),
            "button": gs.button, "small_blind": gs.small_blind,
            "big_blind": gs.big_blind, "stacks": tuple(gs.stacks),
            "pot": gs.pot, "street": gs.street, "view": type(gs).__name__,
        })
        return self.decide(gs)

    def decide(self, gs):
        return A.call(self.player_id)

    def close(self):
        self.closed += 1
        self.log.append(("close", self.name, self.idx))


class Caller(Bot):
    pass


class Folder(Bot):
    def decide(self, gs):
        return A.fold(self.player_id)


class CardBot(Bot):
    """Pair: raise if it can; ace: call; otherwise check or fold."""

    def decide(self, gs):
        me = self.player_id
        a, b = self.hand
        if a.rank == b.rank and gs.can_raise:
            return A.raise_to(me, gs.min_raise_to)
        if "A" in (a.rank, b.rank) or gs.call_amount == 0:
            return A.call(me)
        return A.fold(me)


class SometimesFaults(CardBot):
    """Faults (raises) whenever its first hole card is a heart."""

    def decide(self, gs):
        if self.hand[0].suit == "H":
            raise ValueError(f"heart {self.hand[0]}{self.hand[1]}")
        return super().decide(gs)


class RunRaiser(Bot):
    def decide(self, gs):
        raise ValueError(f"run fails with {self.hand[0]}{self.hand[1]}")


class SeedRaiser(Bot):
    def seed(self, hand, player_id):
        super().seed(hand, player_id)
        raise RuntimeError("seed fails")


class Sleeper(Bot):
    def decide(self, gs):
        if len(self.runs) == 1:
            time.sleep(0.03)
        return A.call(self.player_id)


class SlowRaiser(Bot):
    def decide(self, gs):
        time.sleep(0.03)
        raise ValueError("slow then raise")


class SubAction(A):
    pass


class Oddball(Bot):
    """Returns a PlayerAction subclass, or None every other turn."""

    def decide(self, gs):
        if len(self.runs) % 2:
            return SubAction.call(self.player_id)
        return None


class Booms(Bot):
    def decide(self, gs):
        raise Boom()


class CloseRaiser(Bot):
    def close(self):
        super().close()
        raise CloseError(self.name)


class BoomCloseRaiser(Booms):
    def close(self):
        super().close()
        raise CloseError(self.name)


class Bare:
    """Only seed and run: no close, no other attributes."""

    __slots__ = ("player_id",)

    def seed(self, hand, player_id):
        self.player_id = player_id

    def run(self, actions, gs):
        return A.call(self.player_id)


class Factory:
    """Counts calls, logs them, keeps every model built."""

    def __init__(self, cls, name, log=None, fail_on=None):
        self.cls = cls
        self.name = name
        self.log = log if log is not None else []
        self.fail_on = fail_on
        self.calls = 0
        self.models = []

    def __call__(self):
        index = self.calls
        self.calls += 1
        self.log.append(("factory", self.name, index))
        if self.fail_on is not None and index == self.fail_on:
            raise FactoryError(self.name)
        if self.cls is Bare:
            model = Bare()
        else:
            model = self.cls(self.name, self.log, index)
        self.models.append(model)
        return model


def factories(spec, log=None):
    """spec: name -> model class. Returns {name: Factory}."""
    log = log if log is not None else []
    return {name: Factory(cls, name, log) for name, cls in spec.items()}


# -- oracle ------------------------------------------------------------------

def oracle(spec, deals, rounds=1, seed=0, stack=500, small_blind=10,
           big_blind=20):
    """Plays the schedule with play_hand directly (no proxy) and scores it."""
    names = list(spec)
    n = len(names)
    values = {m: [] for m in range(n)}
    rows = []
    faults = [0] * n
    first = [None] * n
    first_hand = [None] * n
    hand_no = 0
    nets = {}
    for r in range(rounds):
        for k in range(n):
            models = {nm: spec[nm](nm, None, 0) for nm in names}
            seated = [names[(i + k) % n] for i in range(n)]
            for d in range(deals):
                res = play_hand([models[nm] for nm in seated],
                                deck_for(seed, r, d), [stack] * n, button=0,
                                small_blind=small_blind, big_blind=big_blind,
                                teams=seated)
                for i, nm in enumerate(seated):
                    m = names.index(nm)
                    nets[(r, d, m)] = nets.get((r, d, m), 0) + res.net[i]
                    if i in res.faults:
                        faults[m] += 1
                        if first[m] is None:
                            first[m] = res.faults[i]
                            first_hand[m] = hand_no
                hand_no += 1
    for r in range(rounds):
        row = []
        for m in range(n):
            vals = [nets[(r, d, m)] / n / big_blind for d in range(deals)]
            values[m].extend(vals)
            row.append(100 * statistics.fmean(vals))
        rows.append(row)
    bb, ci = [], []
    for m in range(n):
        mean, se = mse_ref(values[m])
        bb.append(100 * mean)
        samples = len(values[m])
        ci.append(INF if samples < 2 else 100 * t95_ref(samples - 1) * se)
    return {"bb_per_100": bb, "ci95": ci, "round_bb_per_100": rows,
            "faults": faults, "first_faults": first,
            "first_fault_hand": first_hand, "hands": hand_no}


class LateCloseRaiser(Bot):
    """close raises from its second model (rotation 1) on."""

    def close(self):
        super().close()
        if self.idx >= 1:
            raise CloseError(self.name)
