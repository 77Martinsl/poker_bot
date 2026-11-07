import random
import time
from collections.abc import Callable
from dataclasses import dataclass

from deck import full_deck
from engine import play_hand
from evals.stats import ci95, mean_and_se

# Each call builds a fresh model: anything with seed() and run().
ModelFactory = Callable[[], object]


@dataclass
class MatchResult:
    """One match between named models. Per-model lists follow names."""

    names: list[str]
    hands: int  # hands played in total
    deals: int  # decks played per round (each once per seat rotation)
    rounds: int
    bb_per_100: list[float]  # big blinds won per 100 hands, all rounds
    ci95: list[float]  # half-width of its 95% confidence interval
    round_bb_per_100: list[list[float]]  # [round][model]
    faults: list[int]  # hands in which the model faulted
    first_faults: list[str | None]  # its first fault, to debug
    max_move_seconds: list[float]  # slowest run() call


def play_match(
    factories: dict[str, ModelFactory],
    deals: int,
    rounds: int = 1,
    seed: int = 0,
    stack: int = 500,
    small_blind: int = 10,
    big_blind: int = 20,
) -> MatchResult:
    """
    Plays every deal once per seat rotation, so every model sits in every
    seat with every hand; repeats it all for each round with new decks.
    """
    names = list(factories)
    count = len(names)
    # Every input is checked before any factory runs.
    if not 2 <= count <= 9:
        raise ValueError(f"a match needs 2 to 9 models, not {count}")
    for name in names:
        if not isinstance(name, str) or not name:
            raise ValueError(f"model names must be non-empty str: {name!r}")
    if deals < 1 or rounds < 1:
        raise ValueError(f"deals {deals} and rounds {rounds} must be >= 1")
    if small_blind < 1 or small_blind > big_blind:
        raise ValueError(
            f"blinds must satisfy 1 <= small_blind {small_blind} <= "
            f"big_blind {big_blind}"
        )
    if stack < big_blind:
        raise ValueError(f"stack {stack} is less than big_blind {big_blind}")

    faults = [0] * count
    first_faults: list[str | None] = [None] * count
    max_move_seconds = [0.0] * count
    samples: list[list[float]] = [[] for _ in range(count)]  # bb per hand
    round_bb_per_100 = []
    for r in range(rounds):
        decks = []
        for d in range(deals):
            deck = full_deck()
            random.Random(f"{seed}:{r}:{d}").shuffle(deck)
            decks.append(deck)
        # Chips each model won with each deck, over all its seats.
        net = [[0] * count for _ in range(deals)]
        for k in range(count):
            # Seat i is played by model order[i].
            order = [(i + k) % count for i in range(count)]
            models = []
            try:
                for name in names:
                    models.append(factories[name]())
                timed = [_Timed(model) for model in models]
                for d, deck in enumerate(decks):
                    result = play_hand(
                        [timed[m] for m in order],
                        deck,
                        [stack] * count,
                        0,
                        small_blind,
                        big_blind,
                        [names[m] for m in order],
                    )
                    for seat, m in enumerate(order):
                        net[d][m] += result.net[seat]
                    for seat, reason in result.faults.items():
                        m = order[seat]
                        faults[m] += 1
                        if first_faults[m] is None:
                            first_faults[m] = reason
                for m, proxy in enumerate(timed):
                    max_move_seconds[m] = max(
                        max_move_seconds[m], proxy.max_seconds
                    )
            except BaseException:
                _close(models)  # the error already raised wins
                raise
            error = _close(models)
            if error is not None:
                raise error
        # bb per hand, averaged over the seats each model played a deck from.
        values = [
            [net[d][m] / count / big_blind for d in range(deals)]
            for m in range(count)
        ]
        for m in range(count):
            samples[m] += values[m]
        round_bb_per_100.append(
            [100 * mean_and_se(values[m])[0] for m in range(count)]
        )

    bb_per_100 = []
    half_widths = []
    for m in range(count):
        mean, se = mean_and_se(samples[m])
        bb_per_100.append(100 * mean)
        half_widths.append(100 * ci95(se, len(samples[m])))
    return MatchResult(
        names=names,
        hands=rounds * count * deals,
        deals=deals,
        rounds=rounds,
        bb_per_100=bb_per_100,
        ci95=half_widths,
        round_bb_per_100=round_bb_per_100,
        faults=faults,
        first_faults=first_faults,
        max_move_seconds=max_move_seconds,
    )


class _Timed:
    """Passes seed and run through to a model, timing each run call, and
    end_game too when the model has one."""

    def __init__(self, model):
        self.model = model
        self.max_seconds = 0.0

    def seed(self, *args, **kwargs):
        return self.model.seed(*args, **kwargs)

    def run(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            return self.model.run(*args, **kwargs)
        finally:
            seconds = time.perf_counter() - start
            self.max_seconds = max(self.max_seconds, seconds)

    def __getattr__(self, name):
        # Only runs for names not set on the proxy: end_game is the
        # model's own, so the proxy has one exactly when the model does.
        if name == "end_game":
            end_game = self.model.end_game
            if callable(end_game):
                return end_game
        raise AttributeError(f"{type(self).__name__} has no {name!r}")


def _close(models: list) -> Exception | None:
    """Calls close() on every model that has one; returns the first error
    instead of raising it, so every model still gets closed."""
    first = None
    for model in models:
        try:
            close = getattr(model, "close", None)
            if close is not None:
                close()
        except Exception as error:
            if first is None:
                first = error
    return first
